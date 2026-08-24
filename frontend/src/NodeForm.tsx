/**
 * @file        frontend/src/NodeForm.tsx
 * @purpose     The selected node's editor: title, kind, schema-driven field
 *              inputs (choice→select, bool→checkbox, int→number, list→comma
 *              text), body textarea, rename, and delete — each action one op
 *              envelope carrying the node's digest.
 * @layer       frontend
 * @tags        form, fields, digest, ops
 * @related     frontend/src/App.tsx (owns submission and errors),
 *              kumihimo/server/ops_api.py (the envelopes this emits)
 * @design      PLAN.md §5.3
 */
import { useEffect, useState } from "react";
import type { FieldSpec, KindInfo, PlanNode } from "./types";

export interface NodeFormProps {
  node: PlanNode;
  kinds: Record<string, KindInfo>;
  onApply: (envelope: Record<string, unknown>) => void;
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
export function NodeForm({ node, kinds, onApply }: NodeFormProps) {
  const [title, setTitle] = useState(node.title);
  const [kind, setKind] = useState(node.kind);
  const [body, setBody] = useState(node.body);
  const [fieldText, setFieldText] = useState<Record<string, string | boolean>>({});
  const [renameTo, setRenameTo] = useState(node.id);

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

  return (
    <div className="kumi-detail">
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
