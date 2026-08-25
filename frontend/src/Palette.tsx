/**
 * @file        frontend/src/Palette.tsx
 * @purpose     Ctrl+K/Cmd+K command palette: one text box searching two
 *              groups — NODES (substring match over id/title/body, title-or-
 *              id hits ranked above body-only hits, the latter carrying a
 *              snippet around where it hit) and COMMANDS (four static
 *              actions App.tsx hands down). Up/Down/Enter/Esc drive it from
 *              the input; a mouse click runs a result the same way Enter
 *              does. App.tsx owns open/close state and mounts this
 *              unconditionally, toggling `open`.
 * @layer       frontend
 * @tags        palette, search, keyboard, commands
 * @related     frontend/src/App.tsx (Ctrl+K listener, open state, jumpTo and
 *              the four command actions passed in as `commands`),
 *              frontend/src/styles.css (kumi-palette-* rules)
 * @design      PLAN2.md §2.5
 */
import { useEffect, useMemo, useState } from "react";
import type { PlanNode } from "./types";

export interface PaletteCommand {
  id: string;
  label: string;
  run: () => void;
}

export interface PaletteProps {
  open: boolean;
  nodes: PlanNode[];
  commands: PaletteCommand[];
  onClose: () => void;
  onSelectNode: (id: string) => void;
}

// Cap + a trailing "n more" line rather than an unbounded list — a plan with
// hundreds of nodes must not turn Ctrl+K into a second scrollable canvas.
const MAX_VISIBLE = 12;
// Chars of body kept on each side of a hit, whitespace-collapsed so a match
// spanning a line break still reads as one line in the result row.
const SNIPPET_RADIUS = 28;

interface NodeResult {
  kind: "node";
  node: PlanNode;
  snippet: string | null;
}
interface CommandResult {
  kind: "command";
  command: PaletteCommand;
}
type Result = NodeResult | CommandResult;

function snippetAround(body: string, query: string): string {
  const at = body.toLowerCase().indexOf(query);
  if (at === -1) return "";
  const start = Math.max(0, at - SNIPPET_RADIUS);
  const end = Math.min(body.length, at + query.length + SNIPPET_RADIUS);
  const text = body.slice(start, end).replace(/\s+/g, " ").trim();
  return `${start > 0 ? "…" : ""}${text}${end < body.length ? "…" : ""}`;
}

// Substring only — no fuzzy-match dependency. The whole id/title/body index
// already sits in memory as `nodes` (it's just the payload), so a plain
// includes() scan is instant at the plan sizes this tool targets, and it's
// one fewer dependency than pulling in something like fuzzysort for this.
// Two buckets, not a sort-by-score: title/id hits always outrank body-only
// hits, so a stable filter into two arrays and concatenating them is exactly
// the ranking asked for, without inventing a scoring function.
function matchNodes(nodes: PlanNode[], query: string): NodeResult[] {
  const titleOrId: NodeResult[] = [];
  const bodyOnly: NodeResult[] = [];
  for (const node of nodes) {
    if (node.title.toLowerCase().includes(query) || node.id.toLowerCase().includes(query)) {
      titleOrId.push({ kind: "node", node, snippet: null });
    } else if (node.body.toLowerCase().includes(query)) {
      bodyOnly.push({ kind: "node", node, snippet: snippetAround(node.body, query) });
    }
  }
  return [...titleOrId, ...bodyOnly];
}

/** Ctrl+K palette. Always mounted by App.tsx; renders nothing while closed
 * (hooks still run, so state resets in the effects below stay well-defined
 * across an open/close/open cycle). */
export function Palette({ open, nodes, commands, onClose, onSelectNode }: PaletteProps) {
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);

  // Fresh box every time the palette opens — not whatever query was left
  // over from the last time it closed.
  useEffect(() => {
    if (open) setQuery("");
  }, [open]);

  // Every keystroke re-ranks both groups; the highlight snaps back to the
  // top match rather than trying to track "the same" result across a re-rank.
  useEffect(() => {
    setHighlight(0);
  }, [query]);

  const q = query.trim().toLowerCase();
  const nodeResults = useMemo(() => (q ? matchNodes(nodes, q) : []), [nodes, q]);
  const commandResults = useMemo<CommandResult[]>(() => {
    const pool = q ? commands.filter((command) => command.label.toLowerCase().includes(q)) : commands;
    return pool.map((command) => ({ kind: "command" as const, command }));
  }, [commands, q]);

  // One flat, ordered list — Up/Down/Enter drive a single index instead of
  // juggling two group-local ones. Nodes get first claim on the ~12 visible
  // slots (matching the NODES-before-COMMANDS section order below); commands
  // fill whatever's left.
  const visibleNodes = nodeResults.slice(0, MAX_VISIBLE);
  const visibleCommands = commandResults.slice(0, Math.max(0, MAX_VISIBLE - visibleNodes.length));
  const visible: Result[] = [...visibleNodes, ...visibleCommands];
  const hiddenCount =
    nodeResults.length - visibleNodes.length + (commandResults.length - visibleCommands.length);

  if (!open) return null;

  function run(result: Result) {
    // Close first: "Add node" (App.tsx's command) focuses a sidebar input
    // that this overlay would otherwise sit on top of.
    onClose();
    if (result.kind === "node") onSelectNode(result.node.id);
    else result.command.run();
  }

  return (
    <div className="kumi-palette-overlay" onClick={onClose}>
      <div className="kumi-palette-box" onClick={(event) => event.stopPropagation()}>
        <input
          autoFocus
          className="kumi-palette-input"
          placeholder="Search nodes by id, title, or body… or run a command"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            // stopPropagation on the keys this palette itself handles: App.tsx
            // has its own window-level Escape listener (clears focus/trace)
            // that must not also fire when Escape here only means "close the
            // palette." Plain typing (including a bare "k") is left alone so
            // it never fights the Ctrl+K-reopens-palette listener up on
            // window — that one only ever matches with ctrl/meta held anyway.
            if (event.key === "ArrowDown") {
              event.preventDefault();
              event.stopPropagation();
              setHighlight((current) => Math.min(current + 1, Math.max(visible.length - 1, 0)));
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              event.stopPropagation();
              setHighlight((current) => Math.max(current - 1, 0));
            } else if (event.key === "Enter") {
              event.preventDefault();
              event.stopPropagation();
              const result = visible[highlight];
              if (result) run(result);
            } else if (event.key === "Escape") {
              event.preventDefault();
              event.stopPropagation();
              onClose();
            }
          }}
        />
        <ul className="kumi-palette-results">
          {visibleNodes.length > 0 ? <li className="kumi-palette-group">NODES</li> : null}
          {visibleNodes.map((result, index) => (
            <li
              key={result.node.id}
              className={`kumi-palette-row${index === highlight ? " kumi-palette-active" : ""}`}
              onMouseEnter={() => setHighlight(index)}
              onClick={() => run(result)}
            >
              <span className="kumi-palette-title">{result.node.title || result.node.id}</span>
              <span className="kumi-palette-id">{result.node.id}</span>
              {result.snippet ? <span className="kumi-palette-snippet">{result.snippet}</span> : null}
            </li>
          ))}
          {visibleCommands.length > 0 ? <li className="kumi-palette-group">COMMANDS</li> : null}
          {visibleCommands.map((result, offset) => {
            const index = visibleNodes.length + offset;
            return (
              <li
                key={result.command.id}
                className={`kumi-palette-row${index === highlight ? " kumi-palette-active" : ""}`}
                onMouseEnter={() => setHighlight(index)}
                onClick={() => run(result)}
              >
                <span className="kumi-palette-title">{result.command.label}</span>
              </li>
            );
          })}
          {visible.length === 0 ? <li className="kumi-palette-empty">No matches</li> : null}
          {hiddenCount > 0 ? <li className="kumi-palette-more">{hiddenCount} more</li> : null}
        </ul>
      </div>
    </div>
  );
}
