# compile — the braid

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `__init__.py` | The braid: select → order → render → weave. Exports braid and BraidResult, and registers itself as Plan.braid's implementation so core never has to import this… |
| `braid.py` | The pipeline itself: gate on check errors, select, order, hand to the strategy, weave — or stop at --dry with just the order. Returns a BraidResult carrying te… |
| `diagram.py` | The graph as a picture, in text: Mermaid (embedded in braids and README-ready) and Graphviz DOT. Membership draws as subgraphs/ clusters, needs as solid arrows… |
| `export.py` | The public export surface: a plan as Mermaid or DOT text, exactly what `kumihimo export` and kumihimo.export.* hand out. |
| `render.py` | Stage three of the braid: each node through its kind's Jinja2 template, sandboxed. Resolves templates (manifest inline or file → pack file → built-in default),… |
| `select.py` | Stage one of the braid: decide which nodes are in. Filters compose by intersection (--where on effective fields, --from/--until cones, --in membership), and th… |
| `weave.py` | Stage four of the braid: assign global numbers across the strategy's sections, render every intro and item, and wrap the whole in the cord template (built-in, … |
<!-- END GENERATED INDEX -->

## What this is

Select → order → render → weave (PLAN.md §4). Strategies decide grouping and
weave; kind templates render nodes; the cord template wraps the whole. Imports
`core` and Jinja2, never any client layer. Substantive code lands at M2 — the
package exists now so the boundary tests bind from day one.
