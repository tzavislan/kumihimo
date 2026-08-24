"""
@file        kumihimo/server/__init__.py
@purpose     The editor's localhost server: FastAPI app, file watcher, WebSocket
             push, static frontend assets. Lands at M4; the package exists now so
             boundaries and layout are fixed from day one.
@layer       server
@tags        editor, fastapi, websocket, watchfiles
@related     kumihimo/core/__init__.py (ops this exposes over HTTP)
@design      PLAN.md §5
"""
