# Python API

The library behind every surface. Import from the top level:

```python
from kumihimo import Plan, braid, export, KumihimoError

plan = Plan.load("myplan/")
findings = plan.check()  # list[Finding], errors first
prompt = plan.braid(strategy="grouped", where={"status": "todo"})
mermaid_source = export.mermaid(plan)
```

Mutations go through the ops layer — the same functions the CLI, editor, and
MCP server call:

```python
from kumihimo.core import ops

ops.add_node(plan.root, "cache", "task", needs=("api-endpoints",))
ops.link(plan.root, "cache", to="redis-outage", rel="threatened-by")
ops.rename_node(plan.root, "cache", "response-cache")
```

Every op loads fresh from disk, writes atomically, and returns the reloaded
result; structural mistakes (dangling targets, cycle-closing edges, id
collisions) raise `KumihimoError` with a printable message.

## Plan

::: kumihimo.core.plan.Plan

## The braid

::: kumihimo.compile.braid.braid

::: kumihimo.compile.braid.BraidResult

## Operations

::: kumihimo.core.ops

## Model

::: kumihimo.core.model
