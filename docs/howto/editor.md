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
- **Click an edge** — a remove button appears in the sidebar.
- **Braid** — compiles the current plan and shows the prompt with a copy
  button.

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
