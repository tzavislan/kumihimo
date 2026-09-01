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

## Containers

A node that at least one other node names in its `in` renders as a
container instead of a plain card: its members sit inside it, sized and
positioned to bound them plus a title-bar strip. The dashed membership line
"Reading edges" describes above never draws for that primary relationship —
the nesting says it instead; a member's *other* `in` entries (a second
group, or a target that isn't itself a container) still draw as ordinary
edges. Membership assignment matches the braid's own grouped-strategy
sections: a node's container is the first `in` target that is itself a
container, so what nests on the canvas is what sections in the compiled
prompt.

The container's title bar carries a small **▸/▾** button. Clicking it
collapses the container to a normal-card-sized chip showing a kind pill, an
*n*/*m* **done** count (members whose effective status is `done`), and a
member count — its members vanish from the canvas, and any edge that
touched one re-targets to the chip instead (two edges landing on the same
chip pair merge into one; an edge whose both ends fold into the same chip
disappears rather than drawing a loop). Collapse state is per-plan view
state, saved to `view.yaml`'s `collapsed` key exactly like positions — it
survives a reload and echoes to every other connected editor.

Jumping to a node that's currently hidden inside a collapsed container — via
the Ctrl+K palette, a clickable finding, or an edge panel's endpoint button —
selects and centers the **container** instead of silently doing nothing, and
a notice names what happened: "*title* is inside collapsed *container* —
expand to open it." Nothing auto-expands; that stays a deliberate click on
the ▸ button.

The container card is otherwise a normal node: click it to open its form,
double-click to focus it, and it takes part in every halo and lens like any
other card. Auto-layout treats a *collapsed* container as one node at chip
size, laid out along its (re-routed) needs edges same as any leaf. An
*expanded* container is not itself laid out by elk — elk arranges its
members exactly as it would if they weren't grouped, and the container's box
is drawn around wherever they land, so an expanded group's members can still
end up near unrelated nodes rather than in a clean cluster. Members stay
individually draggable inside their container, which is today's way to shape
a group by hand.

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

Double-clicking a **container** focuses the union of its members' own cones
instead of the container's own (always empty) needs list — everything any of
its threads needs or is needed by, minus its other members — and the sidebar
summary grows a member count: "Focused on M8 — Shape (6 members) — upstream
2, downstream 1."

Both lenses see through a collapsed container: if a hidden member sits in the
upstream or downstream cone (or on a trace path), its container tints or
lights up in its place, and a `needs` edge that got rerouted onto a chip
still dims or stays bright by the real endpoints its file names, never by
whatever the chip happens to be. Both are purely client-side view state,
computed over the `needs` edges already in the payload — nothing is written
to disk, and a live payload update (another editor, a file edit) recomputes
the cones instead of kicking you out, unless the node you'd focused or traced
is itself gone. Entering either one also pauses the lens bar's own tinting
(below) until Esc — see "Lenses"' precedence note.

## Findings on the canvas

A node named by a `check` finding gets a soft ring around its card — red for
an error, amber for a warning, error winning when a node carries both.
Sidebar finding rows underneath the counts stay in sync with the same rule:
a row whose finding points at a node (rather than a file like
`kumihimo.yaml`) is clickable — click it to select and center that node, the
same jump an edge panel's endpoint buttons do. Findings against a file list
the same as always, just not clickable. When `check` finds nothing, the
heading reads a quiet "Check: clean" instead of the usual counts.

## Semantic zoom

Nodes render differently depending how far you've zoomed, so a small plan
reads as a card catalog and a large one still reads as a plan instead of a
wall of identical boxes. Three tiers, switched on React Flow's zoom level:

- **Far** (zoom below 0.45) — a compact colored chip: the kind's color as a
  tint, the title, nothing else. This is the plan's silhouette — scroll out
  far enough on a big roadmap and you're reading shapes and titles, not
  cards.
- **Mid** (0.45 up to 1.3) — the normal card: title, kind pill, id, and now
  also a status glyph (○ todo, ◐ doing, ● done, ⛔ blocked) beside the status
  text, an effort chip when the node has one, and — on milestone nodes — a
  member-count badge ("*n* threads") counting how many nodes name it in
  their `in`. This is the default working zoom.
- **Near** (zoom 1.3 and above) — the mid card plus a one-line body preview
  and, when the node has an `acceptance` list, its first item as a read-only
  `☐` line with a "+*n* more" count alongside. Zoom in on one node to read a
  little more of it without opening the sidebar form.

A card's on-canvas footprint never changes size between tiers, near
included: everything above packs into the same box mid and far already use,
in smaller type — readable because you're zoomed in to see it. That keeps
dragging, edges, and the auto-layout stable across a zoom gesture, and
means cards never grow into their neighbors as you zoom in.

## Lenses

A four-way switch at the top of the sidebar — **Structure** (the default,
everything described above), **Status**, **Flow**, **Risk** — changes what
the canvas emphasizes without changing what it contains. Click a tab, or
press `1`-`4` with the canvas focused and no form field active. A lens
choice is pure view state: nothing is written to disk, and it survives a
payload echo untouched.

- **Status** tints each node by its effective status: doing picks up the
  accent color, blocked the error color, done dims and desaturates by about
  45%. The **ready frontier** — every node whose own status is `todo` and
  whose every dependency is satisfied — glows with its own ring. This is the
  same computation the MCP `ready()` tool uses, to the letter: a node is
  never shown as ready here and refused as not-ready there, or the reverse.
  A dependency hidden inside a collapsed container still counts as satisfied
  or not the same as if it were visible; if the ready node itself is the one
  that's hidden, its container glows in its place rather than the fact
  disappearing.
- **Flow** finds the longest `needs` chain through the graph — the critical
  path — and bolds its nodes and edges; every other edge fades. A collapsed
  container stands in for its hidden members here exactly as it does for
  auto-layout, so the chain can run straight through a chip.
- **Risk** enlarges every `risk`-kind node and every `decision`/`question`
  still `open`, gives them a stronger border, and shades everything
  downstream of them (through `needs`, containers substituted the same way
  as Flow) — the blast radius of what's currently unresolved. Everything
  else dims slightly.

**Precedence**, when more than one visual channel would apply to the same
node: a finding halo always wins, and for the two lens treatments that dim a
card (Status's done tinge, Risk's "everything else" dim) that's an
exclusion, not just a preference — a haloed node never gets those classes at
all, so the ring always renders at full, undimmed strength rather than being
faded along with the rest of the card the way plain CSS layering would fade
it (opacity dims a box-shadow too; a done node with an error halo used to
show no discernible ring until this was enforced). The Status lens's
ready-glow uses the same box-shadow channel as a halo and loses to it the
same way. Risk's enlarge-and-border (a source) and shaded wash (its blast
radius) don't dim anything, so they still show alongside a halo. Focus and
trace suspend lens emphasis entirely while active: the lens stays selected,
but its tints, bolding, and shading pause until Esc, since both already use
the same border/opacity channels a lens does and showing both at once would
just be noise. Semantic zoom tiers are unaffected by any of this.

## Command palette and keyboard

`Ctrl+K` (`Cmd+K` on macOS) opens a search palette over every node's id,
title, and body, plus four quick commands (Add node, Braid, Toggle theme,
Toggle auto-layout). With the palette closed and focus outside any form
field, `1`-`4` switch the lens bar above from anywhere on the canvas; with a
node also selected, arrow keys walk the graph itself rather than the screen,
F focuses, and Delete or Backspace removes with a confirmation. The full
gesture-by-gesture table — this and everything above — lives in the
[shortcuts reference](../reference/shortcuts.md).

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
