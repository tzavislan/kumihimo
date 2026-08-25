# The editor

```bash
kumihimo edit myplan          # serves 127.0.0.1:8720 and opens the browser
```

The canvas renders the plan live: kind-colored nodes, solid arrows for
`needs`, dashed edges for membership, dotted labeled edges for annotations.
The sidebar carries the live `check` findings, an add-node form, the braid
button, and — when the plan lives in git — a dirty-vs-HEAD indicator.

Everything you do writes through the same operations layer as the CLI:

- **Drag a node** — its position lands in `view.yaml`, never in a node file.
- **Drag handle to handle** — draws an edge; the selector above the canvas
  chooses whether new edges mean `needs`, `in`, or an annotation `link` (with
  a relation label). An edge that would close a dependency cycle is refused
  with the cycle's path.
- **Click a node** — edit title, kind, fields (inputs generated from the
  kind's schema), and body; **Save** writes the file, preserving any hand-
  written comments in its frontmatter. Rename fixes every referrer; Delete
  refuses while referenced, naming the referrers.
- **Click an edge** — opens the edge panel in the sidebar (see "Reading
  edges" below).
- **Braid** — compiles the current plan and shows the prompt with a copy
  button.

## Reading edges

Each edge kind keeps its own ports, so membership stops fighting dependency
arrows for the same two pixels: `needs` edges run left→right, from the
dependency's right handle to the dependent's left handle. `in` (membership)
and `link` (annotation) edges both run bottom→top — member or link source at
the bottom, group or link target at the top — distinguished from each other
by dash pattern and color, not by port. `needs` and `in` edges carry a closed
arrowhead pointing at the dependent/group; `link` edges carry none, since an
annotation is already a labeled, not directional, relation.

Hovering an edge thickens and brightens its stroke and shows a small tooltip
naming it in words — "rate-limit-core needs pick-algorithm" — using titles,
never ids. Clicking an edge opens a panel with that same sentence, a jump
button per endpoint (selects the node and centers the canvas on it, zoom
unchanged), and the Remove edge button.

## Focus and trace

Double-click a node to focus it: everything it needs (upstream) tints
fuchsia, everything that needs it (downstream) tints lime, each fading over
three steps with distance, and every unrelated node dims to about 15% (the
minimap follows too, showing dimmed nodes as faint gray). The sidebar
shows a one-line "Focused on … — upstream *n*, downstream *m*" summary. Esc,
or clicking empty canvas, exits.

With a node selected, alt-click a second node to trace between them instead:
every node on any dependency path connecting the two — in either direction —
keeps full strength with a dashed ring, everything else dims, and the
sidebar shows a "*N* nodes on paths between A and B" summary with a Clear
button. If the two aren't connected by any `needs` chain, a notice says so
and trace mode isn't entered. Esc clears trace the same way it exits focus.

Both lenses are purely client-side view state, computed over the `needs`
edges already in the payload — nothing is written to disk, and a live
payload update (another editor, a file edit) recomputes the cones instead of
kicking you out, unless the node you'd focused or traced is itself gone.

## Sync, conflicts, and undo

The canvas never holds unsaved state — there is no save button for the plan,
only for the node form, and even that writes immediately. External edits
(vim, MCP, `git checkout`) reach the canvas in well under a second via the
file watcher.

Each form save carries the digest of the file it was based on. If someone
else changed that file meanwhile, the save is rejected with a conflict notice
and nothing is clobbered — refresh (the watcher already did) and re-apply.

Undo is git. That's a feature: every session's worth of edits is a reviewable
diff, and `git checkout -- .` is a bigger undo than any editor ships.

## Auto-layout

`view.yaml` positions win when present; the elk layered algorithm fills the
gaps. The Auto-layout button toggles to a pure elk arrangement (left to right
along dependencies) without touching your saved positions.

## Dark mode

A moon/sun toggle sits next to the plan name at the top of the sidebar. On
first load it follows your OS's light/dark preference; after that, your
choice is remembered (`localStorage`) and wins over the OS setting until you
toggle back.
