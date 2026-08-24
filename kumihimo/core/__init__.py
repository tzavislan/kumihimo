"""
@file        kumihimo/core/__init__.py
@purpose     The plan model and every operation on it: load, validate, order,
             mutate, save. Imports no CLI, server, MCP, or template code — that
             boundary is enforced by tests/test_boundaries.py.
@layer       core
@tags        model, store, graph, ops, boundary
@related     kumihimo/compile/__init__.py (consumes this model),
             tests/test_boundaries.py (enforces the import boundary)
@design      PLAN.md §7.1-7.2
"""
