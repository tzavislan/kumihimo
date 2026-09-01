# frontend/src — the editor application

<!-- BEGIN GENERATED INDEX -- do not edit by hand -->
| file | purpose |
|---|---|
| `App.tsx` | The editor: payload in (fetch + live socket), React Flow out, and every gesture — drag, connect, form save, add, delete, rename, edge removal, container collap… |
| `KumiGroupNode.tsx` | The container React Flow node (PLAN2.md §2.3 lens 1): any node with members renders as this instead of KumiNode.tsx's leaf card. Two looks, chosen by data.coll… |
| `KumiNode.tsx` | The leaf React Flow node: kind-colored edge stripe, title, id, and a kind pill. Renders one of three semantic-zoom tiers (far/mid/near), chosen upstream in App… |
| `NodeForm.tsx` | The selected node's editor: title, kind, schema-driven field inputs (choice→select, bool→checkbox, int→number, list→comma text), body textarea, rename, and del… |
| `Palette.tsx` | Ctrl+K/Cmd+K command palette: one text box searching two groups — NODES (substring match over id/title/body, title-or- id hits ranked above body-only hits, the… |
| `api.ts` | The wire: fetch the initial payload, then hold a WebSocket that delivers every change, reconnecting quietly when the server restarts. |
| `cones.ts` | Pure graph math over the payload's needs edges: ancestor and descendant cones (BFS hop-distance) for focus mode, and the node set lying on any needs-path betwe… |
| `containers.ts` | Container math for PLAN2.md §2.3 lens 1: which nodes are containers and who belongs to which (first `in`-target that is itself a container — mirrors kumihimo/c… |
| `derive.ts` | Pure functions turning one payload (or one payload plus an active lens) into the small per-node facts App.tsx and KumiNode need to render: node title/color loo… |
| `edges.ts` | The edge model: build every React Flow edge from a payload's needs/in/link lists, the static four-port handle geometry those edges (and every node) anchor to, … |
| `elk.d.ts` | Types for the bundled elkjs entry point, which ships without its own declaration for this subpath. |
| `layout.ts` | Auto-layout: run elk's layered algorithm over the needs edges (order-carrying edges only) and return positions per node id, plus computed sizes for expanded co… |
| `main.tsx` | Entry point: mount App under #root. |
| `theme.ts` | Light/dark theme (PLAN2.md §2.5): init from localStorage or OS preference, persist on change, toggle. The DOM write (data-theme on <html>) is the one place tha… |
| `types.ts` | The TypeScript mirror of the server's payload contract — one shape, defined once on each side of the wire. |
| `useGraphKeyboard.ts` | Graph-directional keyboard (PLAN2.md §2.5): with a node selected, the palette closed, and focus outside any form field, Left/Right walk the first needs depende… |
<!-- END GENERATED INDEX -->

## What this is

Everything the canvas editor (M4) is built from. `main.tsx` mounts `App.tsx`,
which is the whole application shell: payload in (`api.ts`'s fetch and
WebSocket), React Flow out, and every gesture — drag, connect, form save,
add, delete, rename, edge removal — posted back as one op envelope through
`api.ts`'s `postOp`. Nothing here mutates a plan directly: the server-side
`core.ops` layer is still the only path (CLAUDE.md invariant 1), this app is
just another thin client of it.

`KumiNode.tsx`, `KumiGroupNode.tsx`, `NodeForm.tsx`, and `Palette.tsx` are
the other pieces App.tsx renders — the leaf graph node (with its
semantic-zoom tiers), the container node a node with members renders as
instead (PLAN2.md §2.3 lens 1), the selected node's field-driven edit form,
and the Ctrl+K command palette. `cones.ts`, `containers.ts`, `derive.ts`,
`edges.ts`, `layout.ts`, `theme.ts`, and `useGraphKeyboard.ts` are pure logic
and hooks with no server calls of their own — needs-graph math for focus/
trace, container math (who's in which, bounding boxes, collapsed-edge
rerouting), per-node render facts, the edge model, elk auto-layout, the
light/dark theme hook, and the graph-directional keyboard, respectively —
each consumed by App.tsx. `types.ts` is the TypeScript mirror of the
server's payload contract (`kumihimo/server/payload.py`); `elk.d.ts` types
the one elkjs subpath import that ships without its own declarations.
`styles.css` (not TypeScript, not scanned here) holds every class these
files reference, switched by `[data-theme]` for light/dark.
