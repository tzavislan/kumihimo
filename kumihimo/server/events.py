"""
@file        kumihimo/server/events.py
@purpose     Tails `.kumihimo/events.jsonl` for the live push (K31): one
             EventTail per running server, starting at end-of-file so a
             freshly opened editor never replays history, then handing back
             only the lines appended since the last read — including across
             the writer's own rare truncation, which a bounded memory of
             already-shipped raw lines keeps from ever repeating twice.
@layer       server
@tags        events, attribution, tail, live-loop
@related     kumihimo/core/ops.py (the advisory log this reads, _log_event,
             and EVENTS_TRUNCATE_AT/EVENTS_KEEP's own comment for why
             truncation is hysteresis rather than a tight cap),
             kumihimo/server/watch.py (the sole caller — one tail per plan,
             created once, read on every watcher-triggered rebuild)
@design      PLAN2.md §2.5 Motion & attribution, queue item K31
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from kumihimo.core.store import EVENTS_DIR, EVENTS_FILE, EVENTS_TRUNCATE_AT


class EventTail:
    """A running byte offset into one plan's events.jsonl.

    @purpose  One instance per server lifetime (watch.py constructs it once,
              before the watch loop starts): the initial offset is the file's
              size at that moment, so events from before this server started
              are never shown as if they just happened. Best-effort like the
              writer side (ops.py's _log_event) — no lock, nothing here can
              fail the watcher: every read problem, including the file not
              existing yet, yields no events rather than raising.
    """

    def __init__(self, root: Path) -> None:
        """Start at end-of-file — see the class docstring."""
        self._path = root / EVENTS_DIR / EVENTS_FILE
        try:
            self._offset = self._path.stat().st_size if self._path.is_file() else 0
        except OSError:
            self._offset = 0
        # Fix round: raw lines already handed to a caller, oldest first,
        # capped at the writer's own truncation ceiling (ops.py's
        # EVENTS_TRUNCATE_AT — the most lines the file can ever hold right
        # before a truncation, so this always has enough memory to recognize
        # every line a truncation might re-present). Consulted only on the
        # shrink path below: a bare offset reset without this would re-ship
        # every surviving line on EVERY truncation as if brand new, and a
        # stale replayed event can misattribute a genuinely-changing node's
        # toast (attributionDiff.ts's first-claim-wins matches the first
        # event whose targets include an id — a duplicate of an old event
        # racing a real new one is exactly the wrong one to win that race).
        self._shipped: deque[bytes] = deque(maxlen=EVENTS_TRUNCATE_AT)

    def read_new(self) -> list[dict[str, Any]]:
        """Events appended since the last call, oldest first; [] on any problem.

        @purpose  A single open/seek/read keeps the "how big is it really"
                  check and the read itself consistent with each other. If
                  the file has shrunk below the remembered offset since (the
                  writer's own rare truncation, mid-write between two of our
                  reads) the offset resets to 0 for this call and every
                  already-shipped line (see __init__) is filtered back out —
                  the caller sees exactly the genuinely new lines, never a
                  replay, even across a truncation.
        """
        try:
            with self._path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                shrunk = self._offset > size
                handle.seek(0 if shrunk else self._offset)
                chunk = handle.read()
                self._offset = size
        except OSError:
            return []
        events: list[dict[str, Any]] = []
        for raw_line in chunk.split(b"\n"):
            line = raw_line.strip()
            if not line:
                continue
            if shrunk and line in self._shipped:
                continue
            try:
                parsed = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            self._shipped.append(line)
            if isinstance(parsed, dict):
                events.append(parsed)
        return events
