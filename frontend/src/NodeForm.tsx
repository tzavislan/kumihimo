/**
 * @file        frontend/src/NodeForm.tsx
 * @purpose     The selected node's editor: an identity banner ("editing
 *              <title> · <id>", K41.3), title, kind, schema-driven field
 *              inputs (choice→select, bool→checkbox, int→number, list→comma
 *              text), chip editors for needs/agents/skills (K30 — id-
 *              autocomplete add, × to remove, each gesture its own
 *              link/unlink op rather than staged with Save; `chipPending`,
 *              K40, disables all three rows together for the round trip of
 *              whichever one is in flight, since they all race the same
 *              node-level digest), body textarea, rename, and delete — each
 *              action one op envelope carrying the node's digest. `trains`
 *              deliberately gets no chip editor: the queue text scopes chips
 *              to needs/agents/skills only — trains is the retro's edge,
 *              rare and deliberate, and stays file-edited.
 * @layer       frontend
 * @tags        form, fields, digest, ops, chips, mentions, race
 * @related     frontend/src/App.tsx (owns submission and errors, passes
 *              `nodes` for the chip editors' autocomplete/title lookups),
 *              frontend/src/ChipEditor.tsx (the presentational chip row this
 *              mounts three of),
 *              kumihimo/server/ops_api.py (the envelopes this emits)
 * @design      PLAN.md §5.3, PLAN2.md §3.2
 */
import { useEffect, useState } from "react";
import { ChipEditor, type ChipOption } from "./ChipEditor";
import type { FieldSpec, KindInfo, PlanNode } from "./types";

export interface NodeFormProps {
  node: PlanNode;
  kinds: Record<string, KindInfo>;
  // Every node in the plan (App.tsx's payload.nodes) — the chip editors'
  // source for autocomplete candidates and for resolving an id to a title;
  // nothing else in this form needs the full list.
  nodes: PlanNode[];
  // K40: returns App.tsx's applyOp promise (was fire-and-forget `void`)
  // so the chip handlers below can await the response and clear their
  // pending flag once it lands — success or failure alike. Every other
  // caller here (save/delete/rename) still just calls it and ignores the
  // returned promise, same as before.
  onApply: (envelope: Record<string, unknown>) => Promise<void>;
}

// Agent/skill kind, factored out once: `needs` suggests everything BUT
// these ("non-crew ids", the queue text's own phrase), `agents`/`skills`
// suggest exactly one of them each (below).
const CREW_KINDS = new Set(["agent", "skill"]);

/** Candidate ids for one chip field's autocomplete: every other node
 * matching `kindFilter` (or, for `needs`, every other node NOT of a crew
 * kind), minus whatever's already a chip — a typed id outside this list
 * still works, core.ops is the real gate (dangling/wrong-kind both 400). */
function chipOptions(
  nodes: PlanNode[],
  self: string,
  current: string[],
  kindFilter: (kind: string) => boolean,
): ChipOption[] {
  return nodes
    .filter(
      (candidate) =>
        candidate.id !== self && kindFilter(candidate.kind) && !current.includes(candidate.id),
    )
    .map((candidate) => ({ id: candidate.id, title: candidate.title || candidate.id }));
}

function fieldToInput(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (value === null || value === undefined) return "";
  return String(value);
}

function inputToField(spec: FieldSpec | undefined, raw: string | boolean): unknown {
  if (typeof raw === "boolean") return raw;
  if (!spec || spec.type === "str" || spec.type === "choice") return raw;
  if (spec.type === "int") {
    const parsed = Number.parseInt(raw, 10);
    return Number.isNaN(parsed) ? raw : parsed;
  }
  if (spec.type === "list") {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return raw;
}

/** Edit the selected node; every action goes up as one op envelope. */
export function NodeForm({ node, kinds, nodes, onApply }: NodeFormProps) {
  const [title, setTitle] = useState(node.title);
  const [kind, setKind] = useState(node.kind);
  const [body, setBody] = useState(node.body);
  const [fieldText, setFieldText] = useState<Record<string, string | boolean>>({});
  const [renameTo, setRenameTo] = useState(node.id);

  // Chip editors (K30): each gesture is its own link/unlink op, immediately
  // — no staged fieldText/Save round trip, the same "gesture is the op"
  // model drawing or removing a canvas edge already uses. `node.digest` is
  // read fresh at click time (this component always holds the latest
  // selected node, App.tsx recomputes it from payload.nodes every render),
  // so a second chip op after the first's payload echo carries the right
  // base_digest — PROVIDED the first has actually echoed back, which
  // chipPending below (K40) is what guarantees.
  const titleOf = (id: string) => nodes.find((candidate) => candidate.id === id)?.title || id;
  // K40: one shared in-flight flag for all three chip rows on this node —
  // base_digest is the WHOLE node file's digest, not per-field, so a
  // needs-add and an agents-add fired back to back would race the exact
  // same stale digest just as much as two needs-adds would (the audit's
  // own repro). Disabling every row together for the round trip, cleared
  // in `finally` so a 409/400 re-enables it exactly like a success does,
  // is the simplest fix that actually closes the race — not per-row, and
  // not the digest-chaining alternative (ChipEditor.tsx's own header notes
  // this is the caller's call).
  const [chipPending, setChipPending] = useState(false);
  const linkChip = async (key: "needs" | "agents" | "skills", value: string) => {
    setChipPending(true);
    try {
      await onApply({ op: "link", src: node.id, base_digest: node.digest, [key]: value });
    } finally {
      setChipPending(false);
    }
  };
  const unlinkChip = async (key: "needs" | "agents" | "skills", value: string) => {
    setChipPending(true);
    try {
      await onApply({ op: "unlink", src: node.id, base_digest: node.digest, [key]: value });
    } finally {
      setChipPending(false);
    }
  };

  useEffect(() => {
    setTitle(node.title);
    setKind(node.kind);
    setBody(node.body);
    setRenameTo(node.id);
    const specs = kinds[node.kind]?.fields ?? {};
    const initial: Record<string, string | boolean> = {};
    for (const name of Object.keys(specs)) {
      const value = node.fields[name];
      initial[name] = specs[name].type === "bool" ? value === true : fieldToInput(value);
    }
    for (const [name, value] of Object.entries(node.fields)) {
      if (!(name in initial)) initial[name] = fieldToInput(value);
    }
    setFieldText(initial);
  }, [node, kinds]);

  const specs = kinds[kind]?.fields ?? {};

  const save = () => {
    const set_fields: Record<string, unknown> = {};
    const unset_fields: string[] = [];
    for (const [name, raw] of Object.entries(fieldText)) {
      const spec = specs[name];
      const empty = typeof raw === "string" && raw.trim() === "";
      const hadValue = name in node.fields;
      if (empty) {
        if (hadValue) unset_fields.push(name);
        continue;
      }
      set_fields[name] = inputToField(spec, raw);
    }
    onApply({
      op: "update_node",
      node_id: node.id,
      base_digest: node.digest,
      title: title !== node.title ? title : null,
      kind: kind !== node.kind ? kind : null,
      body: body !== node.body ? body : null,
      set_fields,
      unset_fields,
    });
  };

  // needs suggests non-crew ids; agents/skills suggest exactly their own
  // kind — the queue text's own three rules, applied once here rather than
  // duplicated at each ChipEditor call site below.
  const needsOptions = chipOptions(nodes, node.id, node.needs, (k) => !CREW_KINDS.has(k));
  const agentOptions = chipOptions(nodes, node.id, node.agents, (k) => k === "agent");
  const skillOptions = chipOptions(nodes, node.id, node.skills, (k) => k === "skill");

  return (
    <div className="kumi-detail">
      {/* K41.3: which node this form is actually editing, at the top — title
          falls back to id when blank, defense-in-depth: store.py's own
          default_title already humanizes an empty title from the id before
          this ever sees it (core/model.py — "untitled-task" -> "Untitled
          task"), so a node loaded the normal way never actually exercises
          this fallback, but nothing here should assume that stays true.
          .kumi-detail-meta already existed in styles.css, unused until now. */}
      <p className="kumi-detail-meta">
        editing {node.title || node.id} · {node.id}
      </p>
      <label>
        Title
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        Kind
        <select value={kind} onChange={(event) => setKind(event.target.value)}>
          {Object.keys(kinds).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      {Object.entries(specs).map(([name, spec]) => (
        <label key={name}>
          {name}
          {spec.type === "choice" ? (
            <select
              value={typeof fieldText[name] === "string" ? (fieldText[name] as string) : ""}
              onChange={(event) => setFieldText({ ...fieldText, [name]: event.target.value })}
            >
              <option value="">
                {spec.default != null ? `(default: ${String(spec.default)})` : "(unset)"}
              </option>
              {spec.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          ) : spec.type === "bool" ? (
            <input
              type="checkbox"
              checked={fieldText[name] === true}
              onChange={(event) => setFieldText({ ...fieldText, [name]: event.target.checked })}
            />
          ) : (
            <input
              type={spec.type === "int" ? "number" : "text"}
              placeholder={spec.type === "list" ? "comma, separated" : ""}
              value={typeof fieldText[name] === "string" ? (fieldText[name] as string) : ""}
              onChange={(event) => setFieldText({ ...fieldText, [name]: event.target.value })}
            />
          )}
        </label>
      ))}
      <ChipEditor
        fieldKey="needs"
        label="Needs"
        values={node.needs}
        options={needsOptions}
        titleOf={titleOf}
        onAdd={(id) => linkChip("needs", id)}
        onRemove={(id) => unlinkChip("needs", id)}
        disabled={chipPending}
      />
      <ChipEditor
        fieldKey="agents"
        label="Agents"
        values={node.agents}
        options={agentOptions}
        titleOf={titleOf}
        onAdd={(id) => linkChip("agents", id)}
        onRemove={(id) => unlinkChip("agents", id)}
        disabled={chipPending}
      />
      <ChipEditor
        fieldKey="skills"
        label="Skills"
        values={node.skills}
        options={skillOptions}
        titleOf={titleOf}
        onAdd={(id) => linkChip("skills", id)}
        onRemove={(id) => unlinkChip("skills", id)}
        disabled={chipPending}
      />
      <label>
        Body
        <textarea rows={7} value={body} onChange={(event) => setBody(event.target.value)} />
      </label>
      <div className="kumi-actions">
        <button className="kumi-primary" onClick={save}>
          Save
        </button>
        <button
          onClick={() =>
            onApply({ op: "remove_node", node_id: node.id, base_digest: node.digest })
          }
        >
          Delete
        </button>
      </div>
      <div className="kumi-actions">
        <input value={renameTo} onChange={(event) => setRenameTo(event.target.value)} />
        <button
          disabled={renameTo === node.id}
          onClick={() =>
            onApply({ op: "rename_node", old: node.id, new: renameTo, base_digest: node.digest })
          }
        >
          Rename
        </button>
      </div>
    </div>
  );
}
