/**
 * @file        frontend/src/App.tsx
 * @purpose     The editor: payload in (fetch + live socket), React Flow out,
 *              and every gesture — drag, connect, form save, add, delete,
 *              rename, edge removal — posted as one op envelope. View.yaml
 *              positions honored with elk filling gaps, braid preview, dirty-
 *              vs-HEAD indicator, findings live in the sidebar. Also owns
 *              light/dark theme: init from storage or OS preference, toggle,
 *              persist — styles.css does the rest via [data-theme="dark"].
 * @layer       frontend
 * @tags        react-flow, editor, ops, live, elk, sidebar, theme
 * @related     frontend/src/api.ts (the wire),
 *              frontend/src/NodeForm.tsx (the selected node's form),
 *              frontend/src/styles.css (the tokens data-theme switches),
 *              kumihimo/server/ops_api.py (where every gesture lands)
 * @design      PLAN.md §5.1-5.3, PLAN2.md §2.5
 */
import {
  Background,
  Controls,
  MiniMap,
  Position as FlowPosition,
  ReactFlow,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeMouseHandler,
  type Node,
  type NodeHandle,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchBraid, fetchDirty, fetchPlan, openLive, postOp } from "./api";
import { FALLBACK_COLOR, KIND_COLORS, KumiNode } from "./KumiNode";
import { elkPositions, NODE_HEIGHT, NODE_WIDTH } from "./layout";
import { NodeForm } from "./NodeForm";
import type { Payload, PlanNode, Position } from "./types";

const NODE_TYPES = { kumi: KumiNode };

type EdgeMode = "needs" | "in" | "link";

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

const THEME_KEY = "kumi-theme";
type Theme = "light" | "dark";

// Storage wins once the user has chosen; before that, follow the OS so a
// fresh install doesn't default to a jarring light canvas on a dark desktop.
function initialTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

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
        // No fill here: an inline style beats CSS regardless of specificity,
        // which is exactly what silently broke this label in dark mode
        // before — styles.css themes it via --xy-edge-label-color instead.
        labelStyle: { fontSize: 10 },
      });
    }
  }
  return edges;
}

function unlinkEnvelope(edgeId: string): Record<string, unknown> | null {
  if (edgeId.startsWith("needs:")) {
    const [dep, node] = edgeId.slice(6).split("->");
    return { op: "unlink", src: node, needs: dep };
  }
  if (edgeId.startsWith("in:")) {
    const [member, group] = edgeId.slice(3).split("->");
    return { op: "unlink", src: member, in: group };
  }
  if (edgeId.startsWith("link:")) {
    const [src, toRel] = edgeId.slice(5).split("->");
    const separator = toRel.indexOf(":");
    return { op: "unlink", src, to: separator === -1 ? toRel : toRel.slice(0, separator) };
  }
  return null;
}

/** The whole application. */
export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [positions, setPositions] = useState<Record<string, Position>>({});
  const [useViewLayout, setUseViewLayout] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [edgeMode, setEdgeMode] = useState<EdgeMode>("needs");
  const [linkRel, setLinkRel] = useState("see-also");
  const [notice, setNotice] = useState<string | null>(null);
  const [braidText, setBraidText] = useState<string | null>(null);
  const [dirty, setDirty] = useState<{ tracked: boolean; dirty: string[] }>({
    tracked: false,
    dirty: [],
  });
  const [newNode, setNewNode] = useState({ id: "", kind: "task", title: "" });
  // While a drag or connect gesture is in flight, payload echoes must not
  // rebuild the nodes under the pointer — the gesture would be cancelled.
  const [interacting, setInteracting] = useState(false);
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    fetchPlan().then(setPayload).catch(console.error);
    return openLive(setPayload);
  }, []);

  // The attribute, not the state value, is what styles.css keys off of —
  // this is the one place that writes it, so toggle and persistence can't
  // drift apart.
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  useEffect(() => {
    if (!payload) return;
    fetchDirty().then(setDirty).catch(() => undefined);
    let cancelled = false;
    elkPositions(payload.nodes).then((auto) => {
      if (cancelled) return;
      // Drags land in view.yaml and echo back through payload.layout, so no
      // extra local merging: view mode is auto + the sidecar, auto mode is elk.
      setPositions(useViewLayout ? { ...auto, ...payload.layout } : auto);
    });
    return () => {
      cancelled = true;
    };
  }, [payload, useViewLayout]);

  const applyOp = useCallback(async (envelope: Record<string, unknown>) => {
    const result = await postOp(envelope);
    if (result.ok) {
      setPayload(result.payload);
      setNotice(null);
    } else if (result.status === 409) {
      setNotice(`Conflict: ${result.detail}`);
    } else {
      setNotice(result.detail);
    }
  }, []);

  // Two React Flow v12 controlled-mode traps live here. (1) Without
  // onNodesChange, measure updates are dropped and edges never draw. (2) Any
  // setNodes with fresh objects loses `measured` — so rebuilds carry it over.
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  useEffect(() => {
    if (!payload || interacting) return;
    setNodes((previous) => {
      const byId = new Map(previous.map((node) => [node.id, node]));
      return payload.nodes.map((node) => {
        const old = byId.get(node.id);
        return {
          id: node.id,
          type: "kumi",
          position: positions[node.id] ?? { x: 0, y: 0 },
          data: { node, color: colorFor(payload, node) },
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
          handles: STATIC_HANDLES,
          measured: old?.measured,
        };
      });
    });
  }, [payload, positions, setNodes, interacting]);

  const edges = useMemo(() => (payload ? buildEdges(payload) : []), [payload]);
  const selected = payload?.nodes.find((node) => node.id === selectedId) ?? null;

  const onNodeClick: NodeMouseHandler = useCallback((_, node) => {
    setSelectedId(node.id);
    setSelectedEdge(null);
  }, []);

  const onEdgeClick: EdgeMouseHandler = useCallback((_, edge) => {
    setSelectedEdge(edge.id);
  }, []);

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      if (edgeMode === "needs") {
        void applyOp({ op: "link", src: connection.target, needs: connection.source });
      } else if (edgeMode === "in") {
        void applyOp({ op: "link", src: connection.source, in: connection.target });
      } else {
        void applyOp({
          op: "link",
          src: connection.source,
          to: connection.target,
          rel: linkRel || "see-also",
        });
      }
    },
    [applyOp, edgeMode, linkRel],
  );

  const onNodeDragStop = useCallback(
    (_: unknown, node: Node) => {
      setInteracting(false);
      const rounded = { x: Math.round(node.position.x), y: Math.round(node.position.y) };
      setPositions((current) => ({ ...current, [node.id]: rounded }));
      void applyOp({ op: "set_positions", positions: { [node.id]: rounded } });
    },
    [applyOp],
  );

  // Mounting the canvas before positions exist would let fitView fire on the
  // placeholder {0,0} cluster and then watch the real layout slide away.
  const positionsReady =
    payload !== null && (payload.nodes.length === 0 || Object.keys(positions).length > 0);
  if (!payload || !positionsReady) {
    return <div className="kumi-loading">loading plan…</div>;
  }
  const errors = payload.findings.filter((finding) => finding.level === "error");
  const warnings = payload.findings.filter((finding) => finding.level === "warning");

  return (
    <div className="kumi-shell">
      <aside className="kumi-side">
        <div className="kumi-side-header">
          <h1>{payload.plan}</h1>
          <button
            className="kumi-theme-toggle"
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? "☀" : "🌙"}
          </button>
        </div>
        <p className="kumi-counts">
          {payload.nodes.length} nodes · {edges.length} edges
          {dirty.tracked
            ? dirty.dirty.length
              ? ` · ${dirty.dirty.length} file(s) differ from HEAD`
              : " · clean vs HEAD"
            : ""}
        </p>
        {notice ? (
          <div className="kumi-notice" onClick={() => setNotice(null)}>
            {notice}
          </div>
        ) : null}
        <div className="kumi-actions">
          <button onClick={() => setUseViewLayout((value) => !value)}>
            {useViewLayout ? "Auto-layout" : "Use view.yaml"}
          </button>
          <button
            className="kumi-primary"
            onClick={() => fetchBraid().then(setBraidText).catch((err) => setNotice(String(err)))}
          >
            Braid
          </button>
        </div>
        <h2>New edge draws as</h2>
        <div className="kumi-actions">
          <select value={edgeMode} onChange={(event) => setEdgeMode(event.target.value as EdgeMode)}>
            <option value="needs">needs (dependency)</option>
            <option value="in">in (membership)</option>
            <option value="link">link (annotation)</option>
          </select>
          {edgeMode === "link" ? (
            <input value={linkRel} onChange={(event) => setLinkRel(event.target.value)} />
          ) : null}
        </div>
        {selectedEdge ? (
          <div className="kumi-actions">
            <button
              onClick={() => {
                const envelope = unlinkEnvelope(selectedEdge);
                if (envelope) void applyOp(envelope);
                setSelectedEdge(null);
              }}
            >
              Remove edge {selectedEdge}
            </button>
          </div>
        ) : null}
        <h2>Add node</h2>
        <div className="kumi-add">
          <input
            placeholder="id-slug"
            value={newNode.id}
            onChange={(event) => setNewNode({ ...newNode, id: event.target.value })}
          />
          <select
            value={newNode.kind}
            onChange={(event) => setNewNode({ ...newNode, kind: event.target.value })}
          >
            {Object.keys(payload.kinds).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <input
            placeholder="title (optional)"
            value={newNode.title}
            onChange={(event) => setNewNode({ ...newNode, title: event.target.value })}
          />
          <button
            className="kumi-primary"
            disabled={!newNode.id}
            onClick={() => {
              void applyOp({
                op: "add_node",
                node_id: newNode.id,
                kind: newNode.kind,
                title: newNode.title || null,
              }).then(() => {
                setSelectedId(newNode.id);
                setNewNode({ id: "", kind: newNode.kind, title: "" });
              });
            }}
          >
            Add
          </button>
        </div>
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
          <NodeForm node={selected} kinds={payload.kinds} onApply={(env) => void applyOp(env)} />
        ) : (
          <p className="kumi-hint">Click a node to edit it; drag between handles to draw an edge.</p>
        )}
      </aside>
      <main className="kumi-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          nodeTypes={NODE_TYPES}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onConnect={onConnect}
          onConnectStart={() => setInteracting(true)}
          onConnectEnd={() => setInteracting(false)}
          onNodeDragStart={() => setInteracting(true)}
          onNodeDragStop={onNodeDragStop}
          fitView
          fitViewOptions={{ maxZoom: 1.25, padding: 0.2 }}
          nodesDraggable
          nodesConnectable
          edgesReconnectable={false}
        >
          <Background />
          <MiniMap />
          <Controls showInteractive={false} />
        </ReactFlow>
      </main>
      {braidText !== null ? (
        <div className="kumi-modal" onClick={() => setBraidText(null)}>
          <div className="kumi-modal-box" onClick={(event) => event.stopPropagation()}>
            <div className="kumi-actions">
              <button
                className="kumi-primary"
                onClick={() => void navigator.clipboard.writeText(braidText)}
              >
                Copy
              </button>
              <button onClick={() => setBraidText(null)}>Close</button>
            </div>
            <pre className="kumi-braid">{braidText}</pre>
          </div>
        </div>
      ) : null}
    </div>
  );
}
