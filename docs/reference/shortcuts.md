# Shortcuts

Every click, drag, and keypress the editor (`kumihimo edit`) responds to, one
table per surface. Every one of them still goes through the same operations
layer as the CLI — see [The editor](../howto/editor.md) for the fuller
explanation of what each gesture means and shows.

## Canvas

| Gesture | Does |
|---|---|
| Click a node | Select it; the sidebar shows its form |
| Double-click a node | Enter focus mode: ancestors tint fuchsia, descendants tint lime, both fading over three steps with distance, everything else dims to ~15% |
| Alt-click a second node (one already selected) | Enter trace mode: every node on a dependency path between the two keeps full strength, everything else dims |
| Click empty canvas | Exit focus or trace |
| Drag a node | Move it; the position lands in `view.yaml`, never in the node file |
| Drag handle to handle | Draw an edge — `needs`, `in`, or an annotation `link`, chosen by the selector above the canvas; a `needs` edge that would close a cycle is refused with the cycle's path. Mentions (`agents`/`skills`/`trains`) can't be drawn this way — use the sidebar's chip editors instead |
| Click an edge | Open the edge panel in the sidebar: relation sentence, a jump button per endpoint, Remove edge — works on mention edges too |
| Hover an edge | Thicken and brighten its stroke; show a tooltip naming it in words ("A needs B") |
| Click a clickable finding row | Select and center the node it names (a row naming a file, like `kumihimo.yaml`, isn't clickable) |

Jumping to a node hidden inside a collapsed container — any of the rows
above, or an edge panel's endpoint button, or a palette result — selects and
centers the **container** instead, with a notice naming what happened;
nothing auto-expands.

## Lens bar

A five-way segmented control at the top of the sidebar, right below the
plan name. See [The editor](../howto/editor.md#lenses) for what each one
actually shows.

| Gesture | Does |
|---|---|
| Click a tab, or press `1`-`5` (canvas focused, no form field active) | Switch to Structure / Status / Flow / Risk / Crew |

## Ctrl+K palette

`Ctrl+K` (`Cmd+K` on macOS) opens a centered search overlay from anywhere —
form fields included, since that's standard command-palette behavior, not
just a canvas shortcut.

| Key | Does |
|---|---|
| Type | Search two groups: NODES (substring match over id, title, and body — title/id hits rank above body-only hits, which carry a snippet around where the hit landed) and COMMANDS (filtered by label) |
| ↑ / ↓ | Move the highlight |
| Enter | Run the highlighted result — a node result selects and centers it, same as clicking it on the canvas; a command runs its action |
| Click a result | Same as highlighting it and pressing Enter |
| Esc | Close the palette without running anything |

Commands: **Add node** (closes the palette and focuses the sidebar's id
field), **Braid**, **Toggle theme**, **Toggle auto-layout**, **Lanes
layout**, **Re-layout branch** (see [The editor](../howto/editor.md#layout)
for what the last two do). Results are capped around 12 with a trailing
"*n* more" line rather than listing an entire large plan.

## Graph keyboard

Active on the canvas whenever the palette is closed and focus isn't in a
text field; the arrow/F/Delete rows below additionally need a node selected.

| Key | Does |
|---|---|
| 1 / 2 / 3 / 4 / 5 | Switch to the Structure / Status / Flow / Risk / Crew lens — works with or without a selection |
| ← | Select the node's first dependency (`needs[0]`) |
| → | Select its first dependent (the first other node whose `needs` names it) |
| ↑ / ↓ | Cycle among siblings: other nodes sharing this one's first `in` group, or, if it belongs to no group, other likewise-ungrouped nodes — both rings in id order |
| F | Enter focus mode on the selection (same as double-click; a container focuses the union of its members' cones) |
| Delete / Backspace | Confirm, then remove the node; a referenced node's removal is refused, naming the referrers — same rule as the sidebar's Delete button, and there's no auto-force from the keyboard |
| Ctrl+Z (Cmd+Z on macOS) | Undo: post the inverse of the sidebar's topmost *enabled* trail entry — works with or without a selection. A no-op when every entry is grayed (or the trail is empty); see [The editor](../howto/editor.md#sync-conflicts-and-undo) for what grays an entry and why removal has no entry to undo at all |
| Esc | Exit focus or trace |

**A direction note.** PLAN2.md's design prose says up = dependency,
down = dependent. This editor maps **left = dependency, right = dependent**
instead: the ports work (`needs` edges drawn left-to-right, dependency's
right handle to dependent's left handle) already committed the canvas to
that axis, and arrows that point the way the edges actually run beat arrows
matching prose written before the ports existed. Up/Down were free as a
result, so they cycle siblings rather than sitting unused.

## Chip editors

The selected node's form (**Needs** / **Agents** / **Skills** rows). See
[The editor](../howto/editor.md#chip-editors) for the suggestion-filtering
rules and why there's no **Trains** row.

| Gesture | Does |
|---|---|
| Type an id, press Enter or click Add | Post a `link` op immediately for that field — no Save needed |
| Click a chip's × | Post an `unlink` op immediately for that chip |

## Elsewhere in the sidebar

| Control | Does |
|---|---|
| 🌙 / ☀ toggle, top of sidebar | Switch light/dark theme; your choice is remembered across reloads, otherwise the OS preference wins |
| Auto-layout / Use view.yaml button | Toggle between the elk auto-layout and your saved positions, without touching what's saved |
| Lanes button | Arrange every node into one column per dependency depth ([Layout](../howto/editor.md#layout)) |
| Re-layout branch button | With a node selected, re-arrange just its container or dependency cone in place, leaving everything else untouched ([Layout](../howto/editor.md#layout)) |
| Braid button | Compile the current plan and open the [braid preview](../howto/editor.md#braid-preview): styled Rendered/Raw views, a Diagram fold, Copy, and Download |
| Undo trail entry click | Post that entry's inverse op through the same write door every other gesture uses; a grayed entry's title attribute says why it can't fire ([The editor](../howto/editor.md#sync-conflicts-and-undo)) |
