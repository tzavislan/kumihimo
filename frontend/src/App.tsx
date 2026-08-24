/**
 * @file        frontend/src/App.tsx
 * @purpose     The canvas: payload in (fetch, then live socket), React Flow out
 *              — kind-colored nodes, the three edge kinds drawn distinctly,
 *              view.yaml positions honored with elk filling the gaps, an
 *              auto-layout button, findings in the sidebar, and a read-only
 *              detail panel for the selected node.
 * @layer       frontend
 * @tags        react-flow, canvas, live, elk, sidebar
 * @related     frontend/src/api.ts (the wire),
 *              frontend/src/layout.ts (elk),
 *              frontend/src/KumiNode.tsx (the node component)
 * @design      PLAN.md §5.1-5.3
 */
import {
  Background,
  Controls,
  MiniMap,
  Position as FlowPosition,
  ReactFlow,
  useNodesState,
  type Edge,
  type Node,
  type NodeHandle,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchPlan, openLive } from "./api";
import { FALLBACK_COLOR, KIND_COLORS, KumiNode } from "./KumiNode";
import { elkPositions, NODE_HEIGHT, NODE_WIDTH } from "./layout";
import type { Payload, PlanNode, Position } from "./types";

const NODE_TYPES = { kumi: KumiNode };

// Static handle geometry (React Flow's SSR recipe): with node dimensions and
// handle coordinates declared, edges render without any browser measure pass —
// including in renderers that never composite a frame.
const STATIC_HANDLES: NodeHandle[] = [
  {
    type: "source",
    position: FlowPosition.Right,
    x: NODE_WIDTH,
    y: NODE_HEIGHT / 2,
    width: 6,
    height: 6,
  },
  {
    type: "target",
    position: FlowPosition.Left,
    x: 0,
    y: NODE_HEIGHT / 2,
    width: 6,
    height: 6,
  },
];

function colorFor(payload: Payload, node: PlanNode): string {
  return payload.kinds[node.kind]?.color ?? KIND_COLORS[node.kind] ?? FALLBACK_COLOR;
}

function buildEdges(payload: Payload): Edge[] {
  const ids = new Set(payload.nodes.map((node) => node.id));
  const edges: Edge[] = [];
  for (const node of payload.nodes) {
    for (const dep of node.needs) {
      if (!ids.has(dep)) continue;
      edges.push({
        id: `needs:${dep}->${node.id}`,
        source: dep,
        target: node.id,
        markerEnd: { type: "arrowclosed" as never },
        style: { strokeWidth: 2 },
      });
    }
    for (const group of node.in) {
      if (!ids.has(group)) continue;
      edges.push({
        id: `in:${node.id}->${group}`,
        source: node.id,
        target: group,
        style: { strokeDasharray: "6 4", stroke: "#8b5cf6", opacity: 0.55 },
      });
    }
    for (const link of node.links) {
      if (!ids.has(link.to)) continue;
      edges.push({
        id: `link:${node.id}->${link.to}:${link.rel}`,
        source: node.id,
        target: link.to,
        label: link.rel,
        style: { strokeDasharray: "2 4", stroke: "#6b7280" },
        labelStyle: { fontSize: 10, fill: "#6b7280" },
      });
    }
  }
  return edges;
}

/** The whole application. */
export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [positions, setPositions] = useState<Record<string, Position>>({});
  const [useViewLayout, setUseViewLayout] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    fetchPlan().then(setPayload).catch(console.error);
    return openLive(setPayload);
  }, []);

  useEffect(() => {
    if (!payload) return;
    let cancelled = false;
    elkPositions(payload.nodes).then((auto) => {
      if (cancelled) return;
      const merged = useViewLayout ? { ...auto, ...payload.layout } : auto;
      setPositions(merged);
    });
    return () => {
      cancelled = true;
    };
  }, [payload, useViewLayout]);

  // Two React Flow v12 controlled-mode traps live here. (1) Without
  // onNodesChange, measure updates are dropped and edges never draw. (2) Any
  // setNodes with fresh objects loses `measured`, and the ResizeObserver won't
  // refire for unchanged sizes — edges would vanish permanently after every
  // payload echo or layout toggle. So rebuilds carry `measured` over.
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  useEffect(() => {
    if (!payload) return;
    setNodes((previous) => {
      const byId = new Map(previous.map((node) => [node.id, node]));
      return payload.nodes.map((node) => {
        const old = byId.get(node.id);
        return {
          id: node.id,
          type: "kumi",
          position: positions[node.id] ?? { x: 0, y: 0 },
          data: { node, color: colorFor(payload, node) },
          // Declared dimensions and handle geometry (the CSS fixes both) make
          // edge rendering measurement-independent — see STATIC_HANDLES.
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
          handles: STATIC_HANDLES,
          measured: old?.measured,
        };
      });
    });
  }, [payload, positions, setNodes]);

  const edges = useMemo(() => (payload ? buildEdges(payload) : []), [payload]);
  const selected = payload?.nodes.find((node) => node.id === selectedId) ?? null;

  const onNodeClick: NodeMouseHandler = useCallback((_, node) => {
    setSelectedId(node.id);
  }, []);

  if (!payload) {
    return <div className="kumi-loading">loading plan…</div>;
  }
  const errors = payload.findings.filter((finding) => finding.level === "error");
  const warnings = payload.findings.filter((finding) => finding.level === "warning");

  return (
    <div className="kumi-shell">
      <aside className="kumi-side">
        <h1>{payload.plan}</h1>
        {payload.description ? <p className="kumi-desc">{payload.description}</p> : null}
        <p className="kumi-counts">
          {payload.nodes.length} nodes · {edges.length} edges · read-only (editing lands at M5)
        </p>
        <button onClick={() => setUseViewLayout((value) => !value)}>
          {useViewLayout ? "Auto-layout (ignore view.yaml)" : "Use view.yaml positions"}
        </button>
        <h2>
          Check: {errors.length} error{errors.length === 1 ? "" : "s"}, {warnings.length} warning
          {warnings.length === 1 ? "" : "s"}
        </h2>
        <ul className="kumi-findings">
          {payload.findings.map((finding, index) => (
            <li key={index} className={`kumi-${finding.level}`}>
              <b>{finding.where}</b>: {finding.message}
            </li>
          ))}
        </ul>
        {selected ? (
          <div className="kumi-detail">
            <h2>{selected.title}</h2>
            <p className="kumi-detail-meta">
              {selected.kind} · {selected.id}
            </p>
            <table>
              <tbody>
                {Object.entries(selected.effective).map(([name, value]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>{Array.isArray(value) ? value.join("; ") : String(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <pre className="kumi-body">{selected.body.trim() || "(empty body)"}</pre>
          </div>
        ) : (
          <p className="kumi-hint">Click a node for details.</p>
        )}
      </aside>
      <main className="kumi-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          nodeTypes={NODE_TYPES}
          onNodeClick={onNodeClick}
          fitView
          nodesDraggable={false}
          nodesConnectable={false}
          edgesReconnectable={false}
        >
          <Background />
          <MiniMap />
          <Controls showInteractive={false} />
        </ReactFlow>
      </main>
    </div>
  );
}
