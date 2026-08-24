"""
@file        kumihimo/server/watch.py
@purpose     The file→browser half of the live loop: a broadcaster fanning
             payloads out to every connected WebSocket, and the watchfiles task
             that rebuilds and publishes on any relevant change under the plan
             root.
@layer       server
@tags        watchfiles, websocket, broadcast, live-loop
@related     kumihimo/server/app.py (wires the task and the sockets),
             kumihimo/server/payload.py (what gets pushed)
@design      PLAN.md §5.2
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

from watchfiles import awatch

from kumihimo.server.payload import plan_payload

RELEVANT_SUFFIXES = (".md", ".yaml", ".yml")


def is_relevant(root: Path, changed: str) -> bool:
    """Whether a changed path can affect the payload.

    @purpose  The watcher must ignore .git churn, editor swap files, and the
              tool's own atomic-write temp files, or the canvas flickers.
    """
    path = Path(changed)
    if path.suffix not in RELEVANT_SUFFIXES:
        return False
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    first = relative.parts[0] if relative.parts else ""
    if first == store_nodes_dir():
        return path.suffix == ".md"
    return relative.as_posix() in ("kumihimo.yaml", "view.yaml")


def store_nodes_dir() -> str:
    """The nodes directory name, without importing store at call sites.

    @purpose  One string, one home; keeps is_relevant a pure function tests can
              hammer with plain paths.
    """
    from kumihimo.core.store import NODES_DIR

    return NODES_DIR


class Broadcaster:
    """Fan-out of payloads to every connected WebSocket.

    @purpose  Connections come and go; the watcher publishes once and every
              subscriber's queue gets it. No history, no state — the next
              payload always supersedes.
    @tags     broadcast, websocket
    """

    def __init__(self) -> None:
        """Start with no subscribers.

        @purpose  Trivial init; the interesting parts are subscribe/publish.
        """
        self._queues: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new subscriber and return its queue.

        @purpose  Each socket drains its own queue so one slow client cannot
                  stall the rest.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=4)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber.

        @purpose  Dropped sockets must not leak queues.
        """
        self._queues.discard(queue)

    def publish(self, payload: dict[str, Any]) -> None:
        """Hand a payload to every subscriber, dropping stale backlog.

        @purpose  Only the newest plan state matters; a full queue sheds its
                  oldest entry rather than blocking the watcher.
        """
        for queue in list(self._queues):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)


async def watch_plan(root: Path, broadcaster: Broadcaster, stop: asyncio.Event) -> None:
    """Rebuild and publish the payload whenever the plan changes on disk.

    @purpose  The demo promise, literally: edit a file in vim or over MCP and
              the canvas follows. Payload build errors must never kill the
              watcher — a plan mid-edit is often briefly malformed.
    @tags     watchfiles, live-loop
    """
    async for changes in awatch(root, stop_event=stop, debounce=200, step=100):
        if not any(is_relevant(root, changed_path) for _, changed_path in changes):
            continue
        try:
            payload = plan_payload(root)
        except Exception:
            # A plan mid-edit is often briefly unloadable (locked file, torn
            # write); the watcher outlives it and the next change republishes.
            continue
        broadcaster.publish(payload)
