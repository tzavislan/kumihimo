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
 * @design      PLAN.md §5.1-5.3, PLAN2.md §2.1, §2.4-2.5
 */
import {
  Background,
  Controls,
  MarkerType,
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
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
//
// Four handles, one per edge kind, so membership stops fighting dependencies
// for the same two pixels (PLAN2.md §2.4): needs run left/right, in/link run
// top/bottom. Ids are referenced by buildEdges' sourceHandle/targetHandle.
const STATIC_HANDLES: NodeHandle[] = [
  {
    id: "in-left",
    type: "target",
    position: FlowPosition.Left,
    x: 0,
    y: NODE_HEIGHT / 2,
    width: 6,
    height: 6,
  },
  {
    id: "out-right",
    type: "source",
    position: FlowPosition.Right,
    x: NODE_WIDTH,
    y: NODE_HEIGHT / 2,
    width: 6,
    height: 6,
  },
  {
    id: "in-top",
    type: "target",
    position: FlowPosition.Top,
    x: NODE_WIDTH / 2,
    y: 0,
    width: 6,
    height: 6,
  },
  {
    id: "out-bottom",
    type: "source",
    position: FlowPosition.Bottom,
    x: NODE_WIDTH / 2,
    y: NODE_HEIGHT,
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

// Readable-scale closed arrows on the two directional kinds; links stay
// unmarked since they're a bidirectional annotation, not a dependency arrow.
const ARROW_NEEDS = { type: MarkerType.ArrowClosed, width: 18, height: 18, color: "var(--kumi-edge)" };
const ARROW_IN = { type: MarkerType.ArrowClosed, width: 18, height: 18, color: "var(--kumi-edge-in)" };

function buildEdges(payload: Payload): Edge[] {
  const ids = new Set(payload.nodes.map((node) => node.id));
  const edges: Edge[] = [];
  for (const node of payload.nodes) {
    for (const dep of node.needs) {
      if (!ids.has(dep)) continue;
      edges.push({
        id: `needs:${dep}->${node.id}`,
        source: dep,
        sourceHandle: "out-right",
        target: node.id,
        targetHandle: "in-left",
        className: "kumi-edge-needs",
        markerEnd: ARROW_NEEDS,
      });
    }
    for (const group of node.in) {
      if (!ids.has(group)) continue;
      edges.push({
        id: `in:${node.id}->${group}`,
        source: node.id,
        sourceHandle: "out-bottom",
        target: group,
        targetHandle: "in-top",
        className: "kumi-edge-in",
        markerEnd: ARROW_IN,
      });
    }
    for (const link of node.links) {
      if (!ids.has(link.to)) continue;
      edges.push({
        id: `link:${node.id}->${link.to}:${link.rel}`,
        source: node.id,
        sourceHandle: "out-bottom",
        target: link.to,
        targetHandle: "in-top",
        label: link.rel,
        className: "kumi-edge-link",
        // No color/dasharray here: an inline style beats CSS regardless of
        // specificity, which is exactly what silently broke this label in
        // dark mode before — styles.css themes stroke and label via
        // --kumi-edge-link and --xy-edge-label-color instead.
        labelStyle: { fontSize: 10 },
      });
    }
  }
  return edges;
}

// One id format ("kind:from->to[:rel]"), three consumers: the unlink op, the
// hover tooltip sentence, and the edge panel's jump buttons — parsed once so
// they can't drift apart.
interface EdgeInfo {
  kind: EdgeMode;
  from: string;
  to: string;
  rel?: string;
}

function parseEdge(edgeId: string): EdgeInfo | null {
  if (edgeId.startsWith("needs:")) {
    const [dep, node] = edgeId.slice(6).split("->");
    return { kind: "needs", from: node, to: dep };
  }
  if (edgeId.startsWith("in:")) {
    const [member, group] = edgeId.slice(3).split("->");
    return { kind: "in", from: member, to: group };
  }
  if (edgeId.startsWith("link:")) {
    const [src, toRel] = edgeId.slice(5).split("->");
    const separator = toRel.indexOf(":");
    const to = separator === -1 ? toRel : toRel.slice(0, separator);
    const rel = separator === -1 ? undefined : toRel.slice(separator + 1);
    return { kind: "link", from: src, to, rel };
  }
  return null;
}

function nodeTitle(payload: Payload, id: string): string {
  return payload.nodes.find((node) => node.id === id)?.title ?? id;
}

/** "A needs B" / "A is in B" / "A links B (rel)" — titles, not ids. */
function edgeSentence(payload: Payload, info: EdgeInfo): string {
  const from = nodeTitle(payload, info.from);
  const to = nodeTitle(payload, info.to);
  if (info.kind === "needs") return `${from} needs ${to}`;
  if (info.kind === "in") return `${from} is in ${to}`;
  return `${from} links ${to}${info.rel ? ` (${info.rel})` : ""}`;
}

function unlinkEnvelope(edgeId: string): Record<string, unknown> | null {
  const info = parseEdge(edgeId);
  if (!info) return null;
  if (info.kind === "needs") return { op: "unlink", src: info.from, needs: info.to };
  if (info.kind === "in") return { op: "unlink", src: info.from, in: info.to };
  return { op: "unlink", src: info.from, to: info.to };
}

/** The whole application. */
export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [positions, setPositions] = useState<Record<string, Position>>({});
  const [useViewLayout, setUseViewLayout] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  // clientX/Y at last hover, not canvas coordinates — the tooltip is a
  // position:fixed div that follows the cursor, not a canvas overlay.
  const [edgeTip, setEdgeTip] = useState<{ edgeId: string; x: number; y: number } | null>(null);
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
  // Populated via onInit; a ref (not state) because it never needs to
  // trigger a re-render, only to be read from the jump buttons' click.
  const rfInstance = useRef<ReactFlowInstance | null>(null);

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

  // A live payload update can remove the hovered edge with the cursor still
  // parked on where it was — no DOM leave event ever fires, and the tooltip
  // would wedge with a stale sentence. Reconcile it against the edge set.
  useEffect(() => {
    if (edgeTip && !edges.some((edge) => edge.id === edgeTip.edgeId)) {
      setEdgeTip(null);
    }
  }, [edges, edgeTip]);
  const selected = payload?.nodes.find((node) => node.id === selectedId) ?? null;

  const onNodeClick: NodeMouseHandler = useCallback((_, node) => {
    setSelectedId(node.id);
    setSelectedEdge(null);
  }, []);

  const onEdgeClick: EdgeMouseHandler = useCallback((_, edge) => {
    setSelectedEdge(edge.id);
  }, []);

  const onEdgeMouseEnter: EdgeMouseHandler = useCallback((event, edge) => {
    setEdgeTip({ edgeId: edge.id, x: event.clientX, y: event.clientY });
  }, []);

  const onEdgeMouseLeave: EdgeMouseHandler = useCallback(() => {
    setEdgeTip(null);
  }, []);

  // Shared by the edge panel's two endpoint buttons: select like a node
  // click would, then re-center the viewport if the instance is ready and
  // the endpoint has a known position (elk/view.yaml may still be loading).
  const jumpTo = useCallback((nodeId: string) => {
    setSelectedId(nodeId);
    setSelectedEdge(null);
    const instance = rfInstance.current;
    const position = positions[nodeId];
    if (instance && position) {
      void instance.setCenter(position.x + NODE_WIDTH / 2, position.y + NODE_HEIGHT / 2, {
        zoom: instance.getZoom(),
      });
    }
  }, [positions]);

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
  const selectedEdgeInfo = selectedEdge ? parseEdge(selectedEdge) : null;
  const edgeTipInfo = edgeTip ? parseEdge(edgeTip.edgeId) : null;

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
        {selectedEdge && selectedEdgeInfo ? (
          <div className="kumi-edge-panel">
            <p className="kumi-edge-sentence">{edgeSentence(payload, selectedEdgeInfo)}</p>
            <div className="kumi-actions">
              <button onClick={() => jumpTo(selectedEdgeInfo.from)}>
                ↷ {nodeTitle(payload, selectedEdgeInfo.from)}
              </button>
              <button onClick={() => jumpTo(selectedEdgeInfo.to)}>
                ↷ {nodeTitle(payload, selectedEdgeInfo.to)}
              </button>
            </div>
            <div className="kumi-actions">
              <button
                onClick={() => {
                  const envelope = unlinkEnvelope(selectedEdge);
                  if (envelope) void applyOp(envelope);
                  setSelectedEdge(null);
                }}
              >
                Remove edge
              </button>
            </div>
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
          onEdgeMouseEnter={onEdgeMouseEnter}
          onEdgeMouseLeave={onEdgeMouseLeave}
          onConnect={onConnect}
          onConnectStart={() => setInteracting(true)}
          onConnectEnd={() => setInteracting(false)}
          onNodeDragStart={() => setInteracting(true)}
          onNodeDragStop={onNodeDragStop}
          onInit={(instance) => {
            rfInstance.current = instance;
          }}
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
        {edgeTip && edgeTipInfo ? (
          <div className="kumi-edge-tip" style={{ left: edgeTip.x + 14, top: edgeTip.y + 14 }}>
            {edgeSentence(payload, edgeTipInfo)}
          </div>
        ) : null}
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
