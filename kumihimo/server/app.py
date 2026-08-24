"""
@file        kumihimo/server/app.py
@purpose     The FastAPI application for one plan: GET /api/plan, the /api/ws
             live socket (initial payload, then every change), and the built
             frontend served from static/ — with an honest fallback page when
             the frontend has not been built.
@layer       server
@tags        fastapi, websocket, static, localhost
@related     kumihimo/server/watch.py (the live loop),
             kumihimo/cli/edit_cmd.py (runs this under uvicorn)
@design      PLAN.md §5.1-5.2
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from kumihimo.server.payload import plan_payload
from kumihimo.server.watch import Broadcaster, watch_plan

_UNBUILT = """<!doctype html><meta charset="utf-8"><title>kumihimo</title>
<body style="font-family: system-ui; max-width: 40rem; margin: 4rem auto;">
<h1>kumihimo</h1>
<p>The canvas frontend is not built in this installation.</p>
<p>The API is live: <a href="/api/plan">/api/plan</a>. To build the canvas
from a source checkout: <code>npm --prefix frontend install &amp;&amp;
npm --prefix frontend run build</code>, then restart.</p></body>"""


def build_app(root: Path, static_dir: Path | None = None) -> FastAPI:
    """The server for one plan directory.

    @purpose  Everything is bound at build time — plan root and static dir —
              so tests can point both anywhere.
    @tags     fastapi, app-factory
    """
    static = static_dir if static_dir is not None else Path(__file__).parent / "static"
    broadcaster = Broadcaster()

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Run the file watcher for as long as the server lives.

        @purpose  The watcher is the live half of the product; it starts and
                  stops with the app, never independently.
        """
        stop = asyncio.Event()
        task = asyncio.create_task(watch_plan(root, broadcaster, stop))
        try:
            yield
        finally:
            stop.set()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="kumihimo", lifespan=lifespan)

    @app.get("/api/plan")
    def get_plan() -> dict[str, Any]:
        """The full payload, rebuilt from disk on every call.

        @purpose  No cache to lie: this is what the files say right now.
        """
        return plan_payload(root)

    @app.websocket("/api/ws")
    async def live(websocket: WebSocket) -> None:
        """Initial payload immediately, then one message per plan change.

        @purpose  The canvas never polls; the filesystem is the bus and this is
                  its last stop.
        """
        await websocket.accept()
        queue = broadcaster.subscribe()
        try:
            await websocket.send_json(plan_payload(root))
            while True:
                payload = await queue.get()
                await websocket.send_json(payload)
        except WebSocketDisconnect:
            pass
        finally:
            broadcaster.unsubscribe(queue)

    if (static / "index.html").is_file():
        app.mount("/", StaticFiles(directory=static, html=True), name="static")
    else:

        @app.get("/")
        def unbuilt() -> HTMLResponse:
            """Say plainly that the frontend is not built, and what still works.

            @purpose  A blank page reads as broken; this page reads as honest.
            """
            return HTMLResponse(_UNBUILT)

    # Exposed for tests: publishing through the app's broadcaster must reach
    # connected sockets exactly like a watcher event does.
    app.state.broadcaster = broadcaster
    return app
