/**
 * @file        frontend/src/App.tsx
 * @purpose     The editor: payload in (fetch + live socket), React Flow out,
 *              and every gesture — drag, connect, form save, add, delete,
 *              rename, edge removal, container collapse — posted as one op
 *              envelope (containers.ts builds container nodes and reroutes
 *              edges; edges.ts builds/parses the rest). View.yaml positions
 *              honored with elk filling gaps, braid preview, dirty-vs-HEAD
 *              indicator, findings live in the sidebar — each also haloing
 *              its node on the canvas (error beats warning) and, when it
 *              names a node rather than a file, click-to-jump to select and
 *              center it; derive.ts computes the halo map and every other
 *              per-node render fact (color, member count, acceptance list,
 *              cone/halo class). Owns two client-side view lenses built on
 *              cones.ts's graph math: focus (double-click dims everything
 *              outside the node's up/downstream cone) and trace (alt-click a
 *              second node lights the needs-paths between them) — both pure
 *              view state, never posted as an op, recomputed whenever a
 *              payload echo arrives. Also tracks the semantic-zoom tier off
 *              React Flow's viewport (onMove), threshold-debounced so a zoom
 *              gesture only touches node state when the tier actually
 *              changes. Mounts useTheme (theme.ts) for light/dark and
 *              useGraphKeyboard (useGraphKeyboard.ts) for the graph-
 *              directional keyboard, alongside the Ctrl+K palette's own open
 *              state and listener — every window-level listener gated so
 *              none steals keys from a form field, the palette's own input,
 *              or React Flow's own keyboard handling (disabled below in
 *              favor of these).
 * @layer       frontend
 * @tags        react-flow, editor, ops, live, elk, sidebar, theme, focus,
 *              trace, semantic-zoom, findings, palette, keyboard, containers
 * @related     frontend/src/api.ts (the wire),
 *              frontend/src/containers.ts (grouping/containment math, the
 *              container node factory, and the collapsed-edge reroute this
 *              file's nodes-rebuild effect and edges memo call once each),
 *              frontend/src/KumiGroupNode.tsx (the container node type this
 *              mounts as "kumiGroup"),
 *              frontend/src/edges.ts (builds/parses edges, STATIC_HANDLES,
 *              the unlink envelope),
 *              frontend/src/derive.ts (every payload-derived per-node fact:
 *              color, member count, acceptance, cone/halo class, findings
 *              halos, minimap color),
 *              frontend/src/useGraphKeyboard.ts (the graph-directional
 *              keyboard hook this mounts),
 *              frontend/src/theme.ts (the useTheme hook this mounts),
 *              frontend/src/cones.ts (focus/trace graph math),
 *              frontend/src/KumiNode.tsx (zoomTier thresholds + tier render),
 *              frontend/src/NodeForm.tsx (the selected node's form),
 *              frontend/src/Palette.tsx (the Ctrl+K overlay this mounts),
 *              frontend/src/styles.css (the tokens data-theme switches),
 *              kumihimo/server/ops_api.py (where every gesture lands)
 * @design      PLAN.md §5.1-5.3, PLAN2.md §2.1-2.3, §2.4-2.5
 */
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useNodesState,
  type Connection,
  type EdgeMouseHandler,
  type Node,
  type NodeMouseHandler,
  type ReactFlowInstance,
  type Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchBraid, fetchDirty, fetchPlan, openLive, postOp } from "./api";
import { ancestorsOf, descendantsOf, pathsBetween } from "./cones";
import { buildContainerNode, containerEdges, groupNodes, membersByContainer, toRelative } from "./containers";
import {
  acceptanceList,
  colorFor,
  coneClassName,
  findingHalos,
  haloClassName,
  minimapNodeColor,
  nodeTitle,
  type FocusState,
  type TraceState,
} from "./derive";
import { edgeSentence, parseEdge, STATIC_HANDLES, unlinkEnvelope, type EdgeMode } from "./edges";
import { KumiGroupNode } from "./KumiGroupNode";
import { KumiNode, zoomTier, type KumiNodeData, type ZoomTier } from "./KumiNode";
import { elkPositions, NODE_HEIGHT, NODE_WIDTH, type ContainerSize } from "./layout";
import { NodeForm } from "./NodeForm";
import { Palette, type PaletteCommand } from "./Palette";
import { useTheme } from "./theme";
import type { Payload, Position } from "./types";
import { useGraphKeyboard } from "./useGraphKeyboard";

const NODE_TYPES = { kumi: KumiNode, kumiGroup: KumiGroupNode };

/** The whole application. */
export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [positions, setPositions] = useState<Record<string, Position>>({});
  // Elk's own computed size for each EXPANDED container, pure-auto mode only
  // (containers.ts's buildContainerNode falls back to boundingBox whenever
  // an entry here is missing — including always, in view.yaml mode).
  const [containerAutoSizes, setContainerAutoSizes] = useState<Record<string, ContainerSize>>({});
  const [useViewLayout, setUseViewLayout] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  // clientX/Y at last hover, not canvas coordinates — the tooltip is a
  // position:fixed div that follows the cursor, not a canvas overlay.
  const [edgeTip, setEdgeTip] = useState<{ edgeId: string; x: number; y: number } | null>(null);
  const [edgeMode, setEdgeMode] = useState<EdgeMode>("needs");
  const [linkRel, setLinkRel] = useState("see-also");
  const [notice, setNotice] = useState<string | null>(null);
  const [focus, setFocus] = useState<FocusState | null>(null);
  const [trace, setTrace] = useState<TraceState | null>(null);
  const [braidText, setBraidText] = useState<string | null>(null);
  const [dirty, setDirty] = useState<{ tracked: boolean; dirty: string[] }>({
    tracked: false,
    dirty: [],
  });
  const [newNode, setNewNode] = useState({ id: "", kind: "task", title: "" });
  // While a drag or connect gesture is in flight, payload echoes must not
  // rebuild the nodes under the pointer — the gesture would be cancelled.
  const [interacting, setInteracting] = useState(false);
  const { theme, toggleTheme } = useTheme();
  // Ctrl+K palette (PLAN2.md §2.5): open/close only, Palette.tsx owns query
  // and highlight state internally.
  const [paletteOpen, setPaletteOpen] = useState(false);
  // The palette's "Add node" command focuses this after closing — a ref, not
  // state, since focusing an existing DOM input is an imperative action with
  // nothing for a render to reflect.
  const addNodeIdRef = useRef<HTMLInputElement | null>(null);
  // Semantic zoom tier (PLAN2.md §2.2), tracked off React Flow's viewport by
  // the onMove handler below. Starts at "mid" — today's card — since that's
  // also the tier fitView's own maxZoom (1.25) lands a typical plan in.
  const [tier, setTier] = useState<ZoomTier>("mid");
  // Populated via onInit; a ref (not state) because it never needs to
  // trigger a re-render, only to be read from the jump buttons' click.
  const rfInstance = useRef<ReactFlowInstance | null>(null);

  // Which nodes are containers and who's in which (PLAN2.md §2.3 lens 1),
  // shared by elk (collapsed-as-one-node), the nodes-rebuild effect
  // (parenting), and the edges memo (reroute) — computed once so the three
  // never disagree. Payload's own `collapsed` list is the persisted source
  // of truth; toggling (below) posts a fresh set_collapsed op and waits for
  // the echo like every other gesture, rather than tracking a local copy.
  const grouping = useMemo(() => groupNodes(payload?.nodes ?? []), [payload]);
  const collapsedSet = useMemo(() => new Set(payload?.collapsed ?? []), [payload]);

  useEffect(() => {
    fetchPlan().then(setPayload).catch(console.error);
    return openLive(setPayload);
  }, []);

  // Esc exits either lens; a plain window listener since focus/trace apply
  // even when no form input has focus. Cleaned up on unmount like any other
  // subscription — nothing here to leak.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setFocus(null);
      setTrace(null);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Shared by the sidebar button and the palette's "Toggle auto-layout"
  // command, same reasoning as toggleTheme above.
  const toggleAutoLayout = useCallback(() => {
    setUseViewLayout((current) => !current);
  }, []);

  // Semantic zoom (PLAN2.md §2.2): onMove fires on every pointer-driven pan/
  // zoom tick, but a node only cares when it CROSSES a tier boundary. The
  // debounce is this comparison, not a timer — setTier only actually runs
  // (and only then does the nodes-rebuild effect below re-render every node)
  // when the computed tier differs from the current one, so a zoom gesture
  // costs at most one re-render per boundary crossed, not one per tick.
  const onMove = useCallback((_event: MouseEvent | TouchEvent | null, viewport: Viewport) => {
    setTier((current) => {
      const next = zoomTier(viewport.zoom);
      return next === current ? current : next;
    });
  }, []);

  useEffect(() => {
    if (!payload) return;
    fetchDirty().then(setDirty).catch(() => undefined);
    let cancelled = false;
    // A collapsed container's members are excluded from elk's graph
    // entirely (layout.ts substitutes the container itself), so they get no
    // fresh entry in `auto.positions` — merge over the previous positions
    // rather than replacing wholesale, or a hidden member's position would
    // reset to {0,0} the instant its container collapses, surfacing as a
    // jump on expand. Drags land in view.yaml and echo back through
    // payload.layout, applied last so it always wins over either.
    elkPositions(payload.nodes, {
      collapsed: collapsedSet,
      containers: grouping.containers,
      assignments: grouping.assignments,
    }).then((auto) => {
      if (cancelled) return;
      setPositions((previous) => ({
        ...previous,
        ...auto.positions,
        ...(useViewLayout ? payload.layout : {}),
      }));
      setContainerAutoSizes(auto.containerSizes);
    });
    return () => {
      cancelled = true;
    };
  }, [payload, useViewLayout, collapsedSet, grouping]);

  // Payload echoes (live socket, or any op's own response) must not silently
  // exit focus/trace — recompute the cones against the fresh node list
  // instead, only clearing when an endpoint itself is gone from this payload.
  // The functional setFocus/setTrace form reads current state without
  // needing focus/trace in the dependency array, so this only reruns on a
  // genuine new payload, never loops on its own setState.
  useEffect(() => {
    if (!payload) return;
    setFocus((current) => {
      if (!current) return current;
      if (!payload.nodes.some((node) => node.id === current.id)) return null;
      return {
        id: current.id,
        ancestors: ancestorsOf(payload.nodes, current.id),
        descendants: descendantsOf(payload.nodes, current.id),
      };
    });
    setTrace((current) => {
      if (!current) return current;
      const ids = new Set(payload.nodes.map((node) => node.id));
      if (!ids.has(current.a) || !ids.has(current.b)) return null;
      const onPath = pathsBetween(payload.nodes, current.a, current.b);
      return onPath.size > 0 ? { a: current.a, b: current.b, nodes: onPath } : null;
    });
  }, [payload]);

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

  // Toggle one container's fold state (the ▸/▾ button on its card).
  const toggleCollapse = useCallback(
    (id: string) => {
      if (!payload) return;
      const next = new Set(payload.collapsed);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      void applyOp({ op: "set_collapsed", collapsed: [...next] });
    },
    [payload, applyOp],
  );

  // Two React Flow v12 controlled-mode traps live here. (1) Without
  // onNodesChange, measure updates are dropped and edges never draw. (2) Any
  // setNodes with fresh objects loses `measured` — so rebuilds carry it over.
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  useEffect(() => {
    if (!payload || interacting) return;
    // Finding halos (PLAN2.md §2.1), shared by every node below rather than
    // recomputed per node; membership counts come from `grouping` above.
    const halos = findingHalos(payload.nodes, payload.findings);
    const members = membersByContainer(grouping.assignments);
    const byId = new Map(payload.nodes.map((node) => [node.id, node]));
    setNodes((previous) => {
      const byOldId = new Map(previous.map((node) => [node.id, node]));
      const built: Node[] = [];
      // Containers first: React Flow wants a parent present before any node
      // declares it via parentId.
      for (const id of grouping.containers) {
        const containerNode = byId.get(id);
        if (!containerNode) continue;
        built.push(
          buildContainerNode({
            node: containerNode,
            color: colorFor(payload, containerNode),
            collapsed: collapsedSet.has(id),
            memberIds: members.get(id) ?? [],
            byId,
            positions,
            // Only in pure-auto mode: elk's own compound size for this
            // container, when it has one — view.yaml mode always falls
            // through to containers.ts's boundingBox instead (see its own
            // comment on ContainerNodeParams.autoSize).
            autoSize: useViewLayout ? undefined : containerAutoSizes[id],
            onToggle: () => toggleCollapse(id),
            className:
              [coneClassName(id, focus, trace), haloClassName(id, halos)].filter(Boolean).join(" ") ||
              undefined,
            measured: byOldId.get(id)?.measured,
          }),
        );
      }
      const containerPosition = new Map(built.map((node) => [node.id, node.position]));
      for (const node of payload.nodes) {
        if (grouping.containers.has(node.id)) continue;
        const old = byOldId.get(node.id);
        const parentId = grouping.assignments.get(node.id);
        const hidden = parentId ? collapsedSet.has(parentId) : false;
        const parentPos = parentId ? containerPosition.get(parentId) : undefined;
        const absolute = positions[node.id] ?? { x: 0, y: 0 };
        const data: KumiNodeData = {
          node,
          color: colorFor(payload, node),
          tier,
          memberCount: grouping.counts.get(node.id) ?? 0,
          acceptance: acceptanceList(node),
        };
        built.push({
          id: node.id,
          type: "kumi",
          // Absolute stays the truth everywhere except this one conversion
          // (containers.ts's toRelative): a member of an EXPANDED container
          // renders parent-relative, per React Flow's own parentId contract.
          position: parentPos && !hidden ? toRelative(absolute, parentPos) : absolute,
          data,
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
          handles: STATIC_HANDLES,
          measured: old?.measured,
          hidden,
          parentId: !hidden ? parentId : undefined,
          extent: !hidden && parentId ? "parent" : undefined,
          className: [coneClassName(node.id, focus, trace), haloClassName(node.id, halos)]
            .filter(Boolean)
            .join(" ") || undefined,
        });
      }
      return built;
    });
  }, [
    payload,
    positions,
    setNodes,
    interacting,
    focus,
    trace,
    tier,
    grouping,
    collapsedSet,
    toggleCollapse,
    useViewLayout,
    containerAutoSizes,
  ]);

  // Focus/trace dim edges too: an edge stays full strength only when both
  // ends are in the active lens's highlighted set, same rule as the nodes.
  // containerEdges (not edges.ts's buildEdges directly) drops the primary
  // containment line and re-routes anything a collapsed container hides.
  const edges = useMemo(() => {
    if (!payload) return [];
    const built = containerEdges(payload, grouping.assignments, collapsedSet);
    const highlighted = focus
      ? new Set([focus.id, ...focus.ancestors.keys(), ...focus.descendants.keys()])
      : trace?.nodes ?? null;
    if (!highlighted) return built;
    return built.map((edge) => {
      const full = highlighted.has(edge.source) && highlighted.has(edge.target);
      return { ...edge, className: `${edge.className ?? ""} ${full ? "" : "kumi-edge-dim"}`.trim() };
    });
  }, [payload, focus, trace, grouping, collapsedSet]);

  // A live payload update can remove the hovered edge with the cursor still
  // parked on where it was — no DOM leave event ever fires, and the tooltip
  // would wedge with a stale sentence. Reconcile it against the edge set.
  useEffect(() => {
    if (edgeTip && !edges.some((edge) => edge.id === edgeTip.edgeId)) {
      setEdgeTip(null);
    }
  }, [edges, edgeTip]);
  const selected = payload?.nodes.find((node) => node.id === selectedId) ?? null;

  // Alt-click a second node (with one already selected) starts a trace
  // instead of reselecting — a plain click always still just selects, so
  // this only branches when both the modifier and a distinct prior
  // selection are present.
  const onNodeClick: NodeMouseHandler = useCallback(
    (event, node) => {
      if (event.altKey && payload && selectedId && selectedId !== node.id) {
        const onPath = pathsBetween(payload.nodes, selectedId, node.id);
        if (onPath.size === 0) {
          setNotice(
            `no dependency path between ${nodeTitle(payload, selectedId)} and ${nodeTitle(payload, node.id)}`,
          );
          return;
        }
        setFocus(null);
        setTrace({ a: selectedId, b: node.id, nodes: onPath });
        return;
      }
      setSelectedId(node.id);
      setSelectedEdge(null);
    },
    [payload, selectedId],
  );

  // Double-click and the graph keyboard's F key are the same gesture on two
  // different inputs — one shared callback so they can't drift apart.
  const focusOn = useCallback(
    (id: string) => {
      if (!payload) return;
      setTrace(null);
      setFocus({
        id,
        ancestors: ancestorsOf(payload.nodes, id),
        descendants: descendantsOf(payload.nodes, id),
      });
    },
    [payload],
  );

  const onNodeDoubleClick: NodeMouseHandler = useCallback((_, node) => focusOn(node.id), [focusOn]);

  // Empty-canvas click exits both lenses — the same "step back out" gesture
  // a user reaches for regardless of which one is active.
  const onPaneClick = useCallback(() => {
    setFocus(null);
    setTrace(null);
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

  // Shared by the sidebar Braid button and the palette's "Braid" command.
  const runBraid = useCallback(() => {
    fetchBraid()
      .then(setBraidText)
      .catch((err) => setNotice(String(err)));
  }, []);

  // The palette's "Add node" command: focus the sidebar's id input after the
  // overlay closes. A macrotask, not a bare call — React hasn't committed the
  // close yet at the point this runs, and queuing the focus for the next
  // tick is simpler than threading a "focus after paint" effect through
  // state just for this one gesture.
  const focusAddNodeInput = useCallback(() => {
    setTimeout(() => addNodeIdRef.current?.focus(), 0);
  }, []);

  const paletteCommands = useMemo<PaletteCommand[]>(
    () => [
      { id: "add-node", label: "Add node", run: focusAddNodeInput },
      { id: "braid", label: "Braid", run: runBraid },
      { id: "toggle-theme", label: "Toggle theme", run: toggleTheme },
      { id: "toggle-auto-layout", label: "Toggle auto-layout", run: toggleAutoLayout },
    ],
    [focusAddNodeInput, runBraid, toggleTheme, toggleAutoLayout],
  );

  // Ctrl+K / Cmd+K opens the palette from anywhere, form fields included —
  // standard command-palette behavior (VS Code, GitHub) that graph keyboard
  // below deliberately does not extend to. preventDefault stops the browser
  // taking it as its own shortcut (address/search bar in some browsers).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.key === "k" || event.key === "K") && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        setPaletteOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Graph-directional keyboard (PLAN2.md §2.5): arrows walk needs/in edges,
  // F focuses, Delete/Backspace removes — see useGraphKeyboard.ts for the
  // key bindings and the form-field guard.
  useGraphKeyboard({ payload, selectedId, paletteOpen, jumpTo, focusOn, applyOp });

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
      // A member of an expanded container reports node.position relative to
      // its parent (React Flow's own parentId contract) — this used to be
      // reversed here by hand (parent lookup + addition), which a live
      // regression traced to real corruption: the lookup could read this
      // component's own `nodes` state a tick behind React Flow's, or a
      // container's own position a tick behind ITS OWN boundingBox
      // recompute, landing the wrong absolute value. React Flow already
      // computes and maintains the correct one internally (it has to, to
      // render nested boxes at all) — reading it straight from the live
      // instance instead is both simpler and the actual fix: no lookup, no
      // same-tick feedback with anything this component derives, and by
      // construction exactly one id (node.id) is ever written.
      const absoluteLive = rfInstance.current?.getInternalNode(node.id)?.internals.positionAbsolute;
      const absolute = absoluteLive ?? node.position;
      const rounded = { x: Math.round(absolute.x), y: Math.round(absolute.y) };
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
  // Recomputed here (not lifted out of the nodes-rebuild effect above) for
  // the same reason errors/warnings are: this is render-time sidebar data,
  // cheap to derive fresh rather than thread through another piece of state.
  const halos = findingHalos(payload.nodes, payload.findings);
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
        {focus ? (
          <p className="kumi-focus-hint">
            Focused on {nodeTitle(payload, focus.id)} — upstream {focus.ancestors.size}, downstream{" "}
            {focus.descendants.size}. Esc to exit.
          </p>
        ) : null}
        {trace ? (
          <p className="kumi-focus-hint">
            {trace.nodes.size} nodes on paths between {nodeTitle(payload, trace.a)} and{" "}
            {nodeTitle(payload, trace.b)}.{" "}
            <button className="kumi-trace-clear" onClick={() => setTrace(null)}>
              Clear
            </button>
          </p>
        ) : null}
        <div className="kumi-actions">
          <button onClick={toggleAutoLayout}>{useViewLayout ? "Auto-layout" : "Use view.yaml"}</button>
          <button className="kumi-primary" onClick={runBraid}>
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
            ref={addNodeIdRef}
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
        {payload.findings.length > 0 ? (
          <h2>
            Check: {errors.length} error{errors.length === 1 ? "" : "s"}, {warnings.length} warning
            {warnings.length === 1 ? "" : "s"}
          </h2>
        ) : (
          <p className="kumi-hint">Check: clean</p>
        )}
        <ul className="kumi-findings">
          {payload.findings.map((finding, index) => {
            // Click-to-jump (PLAN2.md §2.1): only when `where` names a node
            // (halos' key set — see findingHalos) rather than a file like
            // kumihimo.yaml, which stays plain, inert text as today.
            const clickable = halos.has(finding.where);
            return (
              <li
                key={index}
                className={`kumi-${finding.level}${clickable ? " kumi-finding-clickable" : ""}`}
                onClick={clickable ? () => jumpTo(finding.where) : undefined}
              >
                <b>{finding.where}</b>: {finding.message}
              </li>
            );
          })}
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
          onNodeDoubleClick={onNodeDoubleClick}
          onPaneClick={onPaneClick}
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
          onMove={onMove}
          fitView
          fitViewOptions={{ maxZoom: 1.25, padding: 0.2 }}
          // Default minZoom (0.5) sits above the far tier's own threshold
          // (0.45, KumiNode.tsx's zoomTier) — left at the default, "far"
          // would be unreachable by any real gesture, only by the initial
          // state value.
          minZoom={0.2}
          nodesDraggable
          nodesConnectable
          edgesReconnectable={false}
          // K22's own Delete/Backspace handler (above) is the only one
          // allowed to remove a node — it's digest-gated and goes through
          // remove_node. React Flow's default deleteKeyCode ('Backspace')
          // would otherwise also fire on the same keypress and drop the node
          // from local canvas state directly, bypassing core.ops entirely
          // (CLAUDE.md invariant #1) and leaving a stale-looking canvas
          // behind if the user then cancels our confirm() prompt.
          deleteKeyCode={null}
          // Same reasoning for arrows: a focused, selected node's div has its
          // own built-in keyboard handling that nudges its position on
          // Arrow* — direct conflict with the selection-cycling K22 binds to
          // those same keys below. disableKeyboardA11y turns off React
          // Flow's whole per-node keyboard layer in favor of ours.
          disableKeyboardA11y
        >
          <Background />
          <MiniMap nodeColor={minimapNodeColor} />
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
      <Palette
        open={paletteOpen}
        nodes={payload.nodes}
        commands={paletteCommands}
        onClose={() => setPaletteOpen(false)}
        onSelectNode={jumpTo}
      />
    </div>
  );
}
