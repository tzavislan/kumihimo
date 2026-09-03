# Claude over MCP

`kumihimo mcp <plan>` serves one plan over MCP stdio: twelve tools, each a
thin twin of the same operations layer the CLI and editor use. Connect an
agent and it can orient (`get_plan`, `get_node`), restructure (`add_node`,
`update_node`, `remove_node`, `link`, `unlink`, `rename_node`), keep the plan
honest (`check`), ask what's unblocked (`ready`, or `ready(for_agent=...)`
for one agent's), see the roster (`crew`), and compile (`braid`, or
`braid(for_agent=...)` for one agent's work orders).

## Claude Code

Drop a `.mcp.json` next to your plan (or in the repo that holds it):

```json
{
  "mcpServers": {
    "myplan": {
      "command": "kumihimo",
      "args": ["mcp", "path/to/myplan"]
    }
  }
}
```

Open Claude Code in that directory and approve the server. From then on:

> "Split rate-limit-core into three smaller tasks, keep the acceptance
> criteria, and re-braid the milestone."

…is a sequence of `get_node`, `add_node`, `link`, `update_node`, and `braid`
calls — all landing as ordinary file edits you can diff and commit.

Any MCP client works the same way; the server is plain stdio.

## The live loop

Because files are the only truth, run `kumihimo edit` at the same time: every
MCP write lands on disk, the watcher sees it, and the canvas rearranges while
Claude works. The same loop runs the other way — drag or edit in the canvas
and the next `get_plan` reflects it.

## `ready` — "what should I work on?"

A node is ready when its own `status` is `todo` and every dependency is
satisfied: a dependency with no `status` field counts as satisfied, and one
with a status counts when it reads `done`, `settled`, or `answered`. That
rule is generic over kinds — a task blocked on an open decision stays blocked
until the decision is settled.

## Kumihimo plans Kumihimo

This repository maintains its own roadmap as a Kumihimo plan
(`plans/roadmap/`), wired through the repo's `.mcp.json`. Milestone prompts
for building the tool are braided from it — the tool eats its own cooking.
Here is that roadmap on the canvas today — v0.1 and v0.2 built end to
end, the crew on the canvas, and the release node still blocked on a
human with a tag:

![Kumihimo's own roadmap: milestones M3-M10 done, the release node blocked, the crew — agents, skills, the training log — on the canvas](../assets/canvas-roadmap.png#only-light)
![Kumihimo's own roadmap: milestones M3-M10 done, the release node blocked, the crew — agents, skills, the training log — on the canvas](../assets/canvas-roadmap-dark.png#only-dark)
