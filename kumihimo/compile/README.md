# compile — the braid

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The braid: turns an ordered plan graph into one deterministic prompt via strategies and Jinja2 templates. Lands at M2; until then this package holds only the k… |
<!-- END GENERATED INDEX -->

## What this is

Select → order → render → weave (PLAN.md §4). Strategies decide grouping and
weave; kind templates render nodes; the cord template wraps the whole. Imports
`core` and Jinja2, never any client layer. Substantive code lands at M2 — the
package exists now so the boundary tests bind from day one.
