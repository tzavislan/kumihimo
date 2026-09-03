/**
 * @file        frontend/src/App.tsx
 * @purpose     The editor: payload in (fetch + live socket), React Flow out,
 *              and every gesture — drag, connect, form save, add, delete,
 *              rename, edge removal, container collapse, lens switch —
 *              posted as one op envelope or held as pure view state.
 *              canvasBuild.ts turns payload+view-state into React Flow's
 *              nodes/edges arrays (containers.ts builds container nodes and
 *              reroutes edges; edges.ts builds/parses the rest; lenses.ts
 *              supplies the Status/Flow/Risk math); derive.ts computes the
 *              halo map and every other per-node render fact. View.yaml
 *              positions honored with elk filling gaps, braid preview,
 *              dirty-vs-HEAD indicator, findings live in the sidebar — each
 *              also haloing its node on the canvas (error beats warning)
 *              and, when it names a node rather than a file, click-to-jump
 *              to select and center it (jumpTo also resolves a hidden
 *              container member to its collapsed container, with a notice —
 *              Inherited fix A, K26). layoutMode (K27) picks the position
 *              source — view.yaml-with-elk-gaps, pure elk (Auto), or
 *              lanes.ts's depth-lanes (Lanes) — and Re-layout branch
 *              (relayoutBranch) re-runs elk over just a selection's
 *              container-or-cone scope, translated back onto its own prior
 *              centroid; both are ephemeral like Auto always was. Owns the
 *              client-side view lenses built
 *              on cones.ts's graph math: focus (double-click dims everything
 *              outside the node's up/downstream cone — a container unions
 *              its members' cones, Inherited fix C) and trace (alt-click a
 *              second node lights the needs-paths between them), plus the
 *              lens bar itself (LensBar.tsx; Structure/Status/Flow/Risk/
 *              Crew, keys 1-5 via useGraphKeyboard.ts) — entering focus/trace
 *              suspends lens emphasis (PLAN2.md §2.3), all four pure view
 *              state, never posted as an op, recomputed whenever a payload
 *              echo arrives. Also tracks the semantic-zoom tier off React
 *              Flow's viewport (onMove), threshold-debounced so a zoom
 *              gesture only touches node state when the tier actually
 *              changes. Mounts useTheme (theme.ts) for light/dark and
 *              useGraphKeyboard (useGraphKeyboard.ts) for the graph-
 *              directional keyboard, alongside the Ctrl+K palette's own open
 *              state and listener — every window-level listener gated so
 *              none steals keys from a form field, the palette's own input,
 *              or React Flow's own keyboard handling (disabled below in
 *              favor of these). Motion (K27): once positions first exist,
 *              a `glideArmed` ref latch stays on for the rest of the
 *              session, and the canvas wrapper carries .kumi-glide (a CSS
 *              transition on the RF node transform, styles.css) whenever
 *              that's true and no drag/connect gesture (`interacting`) is
 *              in flight — echoes, Auto/Lanes, and Re-layout branch all
 *              glide by the same flag; only a live drag's own continuous
 *              position updates are excluded, by suppressing the class
 *              rather than by tracking "was this an echo" anywhere.
 *              Attribution (K31): useAttribution.ts now owns the payload
 *              subscription itself (this file only calls the one hook and
 *              hands it setPayload) — it diffs each live push, turns an
 *              externally-caused change into a toast (Toasts.tsx, top-right
 *              stack) and a pulsingIds set threaded into buildCanvasNodes
 *              alongside onPulseEnd, so K27's glide and K31's pulse ride the
 *              same nodes-rebuild effect without fighting over it. Undo
 *              (K32): useUndoTrail.ts owns the trail's state; applyOp's own
 *              success branch is the ONLY place that pushes onto it (every
 *              op this file posts — drag, connect, form save, add, delete,
 *              rename, edge removal, container collapse, lens-adjacent state
 *              excepted — goes through applyOp, so nothing can post without
 *              also landing on the trail). UndoPanel.tsx renders it as a
 *              collapsible sidebar section; useGraphKeyboard.ts's Ctrl+Z
 *              fires its topmost enabled entry. The edge panel moved out to
 *              EdgePanel.tsx (K32) purely to buy room under the line cap for
 *              the above — same "primitives and callbacks in, JSX out" split
 *              NodeForm.tsx/LensBar.tsx/ChipEditor.tsx already use. Braid
 *              preview (K33): this file still only fetches braidText
 *              (runBraid) and mounts BraidModal.tsx unconditionally, exactly
 *              like Palette.tsx — the Rendered/Raw switch, diagram fold, and
 *              Download all live there so a plain useState inside it
 *              survives a close-and-reopen without this file's help.
 * @layer       frontend
 * @tags        react-flow, editor, ops, live, elk, sidebar, theme, focus,
 *              trace, semantic-zoom, findings, palette, keyboard, containers,
 *              lenses, lanes, layout-mode, re-layout, motion, glide,
 *              attribution, toasts, pulse, undo, braid-preview
 * @related     frontend/src/canvasBuild.ts (buildCanvasNodes/buildCanvasEdges
 *              — the nodes-rebuild effect's and edges memo's own bodies,
 *              moved out to stay under the line cap),
 *              frontend/src/containers.ts (grouping/containment math,
 *              jumpTarget for Inherited fix A, relayoutScope, and
 *              relayoutBranchPositions — elk-plus-clearCollisions in one
 *              call, K27 fix round),
 *              frontend/src/layout.ts (elkPositions and the LayoutMode
 *              type — one of the three layoutMode position sources, K27;
 *              also elkBranchPositions, relayoutBranchPositions' own first
 *              half),
 *              frontend/src/lanes.ts (lanesPositions — a second source),
 *              frontend/src/LayoutControls.tsx (the sidebar's Auto/Lanes/
 *              Re-layout branch buttons this mounts, K27),
 *              frontend/src/KumiGroupNode.tsx (the container node type this
 *              mounts as "kumiGroup"),
 *              frontend/src/edges.ts (parseEdge/edgeSentence — parses the
 *              selected/hovered edge id and sentences it for the panel and
 *              tooltip; EdgePanel.tsx is the one that also needs
 *              unlinkEnvelope),
 *              frontend/src/EdgePanel.tsx (the selected-edge sidebar panel
 *              this mounts, K32),
 *              frontend/src/derive.ts (nodeTitle, findingHalos, FocusState/
 *              TraceState),
 *              frontend/src/lenses.ts (Lens, computeLensContext — the
 *              Status/Flow/Risk math LensBar.tsx and canvasBuild.ts share),
 *              frontend/src/LensBar.tsx (the sidebar segmented control this
 *              mounts),
 *              frontend/src/useGraphKeyboard.ts (the graph-directional
 *              keyboard hook this mounts, keys 1-5 included),
 *              frontend/src/theme.ts (the useTheme hook this mounts),
 *              frontend/src/cones.ts (focus/trace graph math, containerCones
 *              for Inherited fix C),
 *              frontend/src/KumiNode.tsx (zoomTier thresholds + tier render),
 *              frontend/src/NodeForm.tsx (the selected node's form; its own
 *              chip editors post link/unlink for needs/agents/skills, K30),
 *              frontend/src/Palette.tsx (the Ctrl+K overlay this mounts),
 *              frontend/src/styles.css (the tokens data-theme switches),
 *              frontend/src/useAttribution.ts (K31: owns the plan
 *              subscription plus toast/pulse state, the one hook call this
 *              file makes for all of it),
 *              frontend/src/Toasts.tsx (the toast stack this mounts),
 *              frontend/src/useUndoTrail.ts (K32: the undo trail's state and
 *              enabled/reason math, the hook call plus one push() from
 *              applyOp this file makes for all of it),
 *              frontend/src/UndoPanel.tsx (the undo trail's own sidebar
 *              section this mounts, K32),
 *              frontend/src/BraidModal.tsx (the braid preview this mounts
 *              unconditionally, K33 — Rendered/Raw, diagram fold, Copy,
 *              Download all live there, not here),
 *              frontend/src/braidPreview.ts (fold/render/slug —
 *              BraidModal.tsx's own pure and lazy-`marked` support, K33),
 *              kumihimo/server/ops_api.py (where every gesture lands, and
 *              since K32 where its inverse envelope is computed)
 * @design      PLAN.md §5.1-5.3, PLAN2.md §2.1-2.5, §2.5 Undo trail, §3
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
import { fetchBraid, fetchDirty, postOp } from "./api";
import { BraidModal } from "./BraidModal";
import { buildCanvasEdges, buildCanvasNodes } from "./canvasBuild";
import { ancestorsOf, containerCones, descendantsOf, pathsBetween } from "./cones";
import { groupNodes, jumpTarget, membersByContainer, relayoutBranchPositions, relayoutScope } from "./containers";
import { findingHalos, minimapNodeColor, nodeTitle, type FocusState, type TraceState } from "./derive";
import { EdgePanel } from "./EdgePanel";
import { edgeSentence, parseEdge, type EdgeMode } from "./edges";
import { KumiGroupNode } from "./KumiGroupNode";
import { KumiNode, zoomTier, type ZoomTier } from "./KumiNode";
import { lanesPositions } from "./lanes";
import { elkPositions, hasLayoutGaps, NODE_HEIGHT, NODE_WIDTH, type ContainerSize, type LayoutMode } from "./layout";
import { computeLensContext, type Lens } from "./lenses";
import { LensBar } from "./LensBar";
import { LayoutControls } from "./LayoutControls";
import { NodeForm } from "./NodeForm";
import { Palette, type PaletteCommand } from "./Palette";
import { Toasts } from "./Toasts";
import { useTheme } from "./theme";
import type { Payload, Position } from "./types";
import { UndoPanel } from "./UndoPanel";
import { useAttribution } from "./useAttribution";
import { useCenterNewNode } from "./useCenterNewNode";
import { useGraphKeyboard } from "./useGraphKeyboard";
import { useUndoTrail } from "./useUndoTrail";

const NODE_TYPES = { kumi: KumiNode, kumiGroup: KumiGroupNode };

/** The whole application. */
export default function App() {
  const [payload, setPayload] = useState<Payload | null>(null);
  // K31: the plan subscription itself (initial fetch + live socket) now
  // lives inside this hook, alongside the attribution toast/pulse state it
  // derives from every live push — see useAttribution.ts's own header.
  const { toasts, dismissToast, pulsingIds, onPulseEnd } = useAttribution(setPayload);
  const undoTrail = useUndoTrail(payload); // K32 — see useUndoTrail.ts's header
  const [positions, setPositions] = useState<Record<string, Position>>({});
  // Elk's own computed size for each EXPANDED container, pure-auto mode only
  // (containers.ts's buildContainerNode falls back to boundingBox whenever
  // an entry here is missing — including always, in view.yaml mode).
  const [containerAutoSizes, setContainerAutoSizes] = useState<Record<string, ContainerSize>>({});
  // Which position source drives the canvas (PLAN2.md §2.3-2.5, K27):
  // view.yaml-with-elk-gaps (today's default, was useViewLayout=true), pure
  // elk (was useViewLayout=false), or the new Lanes algorithm — see
  // layout.ts's own doc comment on the type.
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("view");
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
  // The lens bar (PLAN2.md §2.3, K26): pure view state, never posted as an
  // op. Structure is the default — today's rendering, no extra emphasis.
  const [lens, setLens] = useState<Lens>("structure");
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

  // Mounting the canvas before positions exist would let fitView fire on the
  // placeholder {0,0} cluster and then watch the real layout slide away —
  // also the gate below for arming motion, so the very first paint never
  // glides in from nothing.
  const positionsReady =
    payload !== null && (payload.nodes.length === 0 || Object.keys(positions).length > 0);
  // Motion (PLAN2.md §2.5, K27): a ref latch, set the instant positions
  // first exist and never unset — every position change from then on is
  // either a payload echo or a layout action the user just triggered, and
  // both are meant to glide (styles.css's .kumi-glide; the class is
  // withheld only while `interacting`, below, never by unsetting this).
  // Mutated during render rather than in an effect+state pair — a safe,
  // idempotent "remember the first time a condition held" latch (React's own
  // documented escape hatch for exactly this), and one fewer render-cycle
  // delay than an effect would add.
  const glideArmed = useRef(false);
  if (positionsReady) glideArmed.current = true;

  // Which nodes are containers and who's in which (PLAN2.md §2.3 lens 1),
  // shared by elk (collapsed-as-one-node), canvasBuild.ts (parenting,
  // reroute), and jumpTo/focusOn below — computed once so none of them can
  // disagree. Payload's own `collapsed` list is the persisted source of
  // truth; toggling (below) posts a fresh set_collapsed op and waits for the
  // echo like every other gesture, rather than tracking a local copy.
  const grouping = useMemo(() => groupNodes(payload?.nodes ?? []), [payload]);
  const collapsedSet = useMemo(() => new Set(payload?.collapsed ?? []), [payload]);
  // Container id -> its member ids, the reverse of grouping.assignments —
  // shared by focusOn (Inherited fix C) and the payload-echo reconciliation
  // effect below, so a container's own cones are never rebuilt two ways.
  const members = useMemo(() => membersByContainer(grouping.assignments), [grouping]);
  // Status/Flow/Risk math (lenses.ts): recomputed only for the active lens,
  // and only while focus/trace aren't suspending lens emphasis (PLAN2.md
  // §2.3) — computeLensContext leaves the other two null either way, so
  // canvasBuild.ts's per-node/per-edge lookups are no-ops outside their lens.
  const lensCtx = useMemo(
    () => computeLensContext(payload?.nodes ?? [], lens, !focus && !trace, grouping.assignments, collapsedSet),
    [payload, lens, focus, trace, grouping, collapsedSet],
  );

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
  // command, same reasoning as toggleTheme above. Two-way regardless of the
  // third mode (K27): "not view" collapses lanes into the same bucket as
  // auto, so clicking this while Lanes is active goes straight to view.yaml,
  // same as it would from Auto — Lanes gets its own dedicated button
  // (LayoutControls.tsx) rather than a slot in this toggle's cycle.
  const toggleAutoLayout = useCallback(() => {
    setLayoutMode((current) => (current === "view" ? "auto" : "view"));
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
    const context = { collapsed: collapsedSet, containers: grouping.containers, assignments: grouping.assignments };
    // Lanes (K27) needs no elk call: lanesPositions is a pure, synchronous
    // longest-path-plus-stacking computation (lanes.ts) that gives every
    // visible node a fresh entry every run (unlike elk's collapsed-member
    // gap below), so a plain merge is enough and there's nothing to cancel.
    // containerAutoSizes is elk-compound-size-only (containers.ts) and would
    // go stale the moment members land somewhere Lanes put them instead, so
    // it's cleared rather than left stale.
    if (layoutMode === "lanes") {
      const lanes = lanesPositions(payload.nodes, context);
      setPositions((previous) => ({ ...previous, ...lanes.positions }));
      setContainerAutoSizes({});
      return;
    }
    // K34: view.yaml already positions every node this payload would render
    // — nothing for elk to fill, so skip layout.ts's elk call (and its
    // dynamic import) entirely rather than run it just to have view.yaml
    // override every result a line below. A plan WITH gaps (a freshly added
    // node, or no view.yaml at all) still falls through to elkPositions,
    // same as before K34 — elk fetching on that cold load is correct, not a
    // regression, and the existing "loading plan…" screen below
    // (positionsReady gates on it) is already the loading affordance for
    // that case, so K34 adds no separate spinner for it.
    if (layoutMode === "view" && !hasLayoutGaps(payload.nodes, payload.layout, context)) {
      setPositions((previous) => ({ ...previous, ...payload.layout }));
      setContainerAutoSizes({});
      return;
    }
    // A collapsed container's members are excluded from elk's graph
    // entirely (layout.ts substitutes the container itself), so they get no
    // fresh entry in `auto.positions` — merge over the previous positions
    // rather than replacing wholesale, or a hidden member's position would
    // reset to {0,0} the instant its container collapses, surfacing as a
    // jump on expand. Drags land in view.yaml and echo back through
    // payload.layout, applied last so it always wins over either.
    elkPositions(payload.nodes, context).then((auto) => {
      if (cancelled) return;
      setPositions((previous) => ({
        ...previous,
        ...auto.positions,
        ...(layoutMode === "view" ? payload.layout : {}),
      }));
      setContainerAutoSizes(auto.containerSizes);
    });
    return () => {
      cancelled = true;
    };
  }, [payload, layoutMode, collapsedSet, grouping]);

  // Payload echoes (live socket, or any op's own response) must not silently
  // exit focus/trace — recompute the cones against the fresh node list
  // instead, only clearing when an endpoint itself is gone from this payload.
  // The functional setFocus/setTrace form reads current state without
  // needing focus/trace in the dependency array, so this only reruns on a
  // genuine new payload, never loops on its own setState. A container focus
  // (FocusState.members set — Inherited fix C) re-derives via containerCones,
  // never degrading to plain leaf ancestors/descendants on an echo.
  useEffect(() => {
    if (!payload) return;
    setFocus((current) => {
      if (!current) return current;
      if (!payload.nodes.some((node) => node.id === current.id)) return null;
      if (current.members) {
        const memberIds = members.get(current.id) ?? [];
        const { ancestors, descendants } = containerCones(payload.nodes, memberIds);
        return { id: current.id, ancestors, descendants, members: new Set(memberIds) };
      }
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
  }, [payload, members]);

  const applyOp = useCallback(async (envelope: Record<string, unknown>) => {
    const result = await postOp(envelope);
    if (result.ok) {
      setPayload(result.payload);
      setNotice(null);
      undoTrail.push(result.inverse, result.preconditions, result.label); // K32
    } else if (result.status === 409) {
      setNotice(`Conflict: ${result.detail}`);
    } else {
      setNotice(result.detail);
    }
  }, [undoTrail.push]);

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
    setNodes((previous) =>
      buildCanvasNodes({
        payload,
        positions,
        grouping,
        collapsedSet,
        focus,
        trace,
        tier,
        selectedId,
        useElkSizes: layoutMode === "auto",
        containerAutoSizes,
        lensCtx,
        previous,
        onToggleCollapse: toggleCollapse,
        pulsingIds,
        onPulseEnd,
      }),
    );
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
    layoutMode,
    containerAutoSizes,
    selectedId,
    lensCtx,
    pulsingIds,
    onPulseEnd,
  ]);

  // Focus/trace dim edges; the Flow lens bolds/faints them instead, only
  // while neither is active (PLAN2.md §2.3 — computeLensContext already
  // nulls lensCtx.flow whenever focus/trace is set, so buildCanvasEdges
  // never has to choose between the two itself).
  const edges = useMemo(() => {
    if (!payload) return [];
    return buildCanvasEdges({ payload, grouping, collapsedSet, focus, trace, flow: lensCtx.flow, crew: lensCtx.crew });
  }, [payload, focus, trace, grouping, collapsedSet, lensCtx]);

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
  // Inherited fix C (K26): focusing a CONTAINER unions its members' own
  // cones (cones.ts's containerCones) instead of reading the container's
  // own always-empty needs list ("upstream 0, downstream 0" regardless of
  // what its threads actually depend on).
  const focusOn = useCallback(
    (id: string) => {
      if (!payload) return;
      setTrace(null);
      if (grouping.containers.has(id)) {
        const memberIds = members.get(id) ?? [];
        const { ancestors, descendants } = containerCones(payload.nodes, memberIds);
        setFocus({ id, ancestors, descendants, members: new Set(memberIds) });
        return;
      }
      setFocus({
        id,
        ancestors: ancestorsOf(payload.nodes, id),
        descendants: descendantsOf(payload.nodes, id),
      });
    },
    [payload, grouping, members],
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

  // Shared by the edge panel's two endpoint buttons, the sidebar's clickable
  // finding rows, and the palette's node results: select like a node click
  // would, then re-center the viewport if the instance is ready and the
  // endpoint has a known position (elk/view.yaml may still be loading).
  // Inherited fix A (K26): when the target is hidden inside a collapsed
  // container, redirect to that container instead (never auto-expand) and
  // say why — jumping "into" nothing on the canvas is the sidebar-detached-
  // from-canvas bug this closes.
  const jumpTo = useCallback(
    (nodeId: string) => {
      if (!payload) return;
      const { targetId, hiddenIn } = jumpTarget(nodeId, grouping.assignments, collapsedSet);
      setSelectedId(targetId);
      setSelectedEdge(null);
      if (hiddenIn) {
        setNotice(
          `${nodeTitle(payload, nodeId)} is inside collapsed ${nodeTitle(payload, hiddenIn)} — expand to open it`,
        );
      }
      const instance = rfInstance.current;
      const position = positions[targetId];
      if (instance && position) {
        void instance.setCenter(position.x + NODE_WIDTH / 2, position.y + NODE_HEIGHT / 2, {
          zoom: instance.getZoom(),
        });
      }
    },
    [payload, positions, grouping, collapsedSet],
  );
  // K41.2: centers a freshly added node once its layout position actually
  // exists (useCenterNewNode.ts — add_node always starts as a gap elk/Lanes
  // fills in afterwards); the Add button's onClick below is the one caller.
  const centerWhenAdded = useCenterNewNode(positions, jumpTo);

  // Shared by the sidebar Braid button and the palette's "Braid" command.
  const runBraid = useCallback(() => {
    fetchBraid()
      .then(setBraidText)
      .catch((err) => setNotice(String(err)));
  }, []);

  // "Re-layout branch" (PLAN2.md §2.3-2.5, K27): scope resolution lives in
  // containers.ts's relayoutScope, and collision clearing (fix round: a
  // centroid-preserving translate alone let scope land on unrelated cards)
  // in its clearCollisions — both pure functions, kept out of this
  // component for the same reason canvasBuild.ts's own header gives, this
  // stays orchestration. Ephemeral like Auto/Lanes: only setPositions,
  // never an op, so view.yaml never sees it.
  const relayoutBranch = useCallback(() => {
    if (!payload || !selectedId) {
      setNotice("select a node to re-layout its branch");
      return;
    }
    const { scope, collapsedContainer } = relayoutScope(payload.nodes, selectedId, grouping, collapsedSet, members);
    if (collapsedContainer) {
      setNotice(`expand ${nodeTitle(payload, selectedId)} to re-layout its members`);
      return;
    }
    if (scope.size === 0) {
      setNotice("nothing in scope to re-layout");
      return;
    }
    const containerId = grouping.containers.has(selectedId) ? selectedId : null;
    void relayoutBranchPositions(payload.nodes, scope, containerId, grouping, collapsedSet, positions).then((r) => {
      setPositions((current) => ({ ...current, ...r.positions }));
      // Elk's compound size for THIS container (pure-auto mode only) was
      // computed from where its members stood before this — now stale.
      // Dropping the entry falls back to boundingBox, which re-reads
      // wherever they actually are (containers.ts's own doc comment).
      if (containerId) setContainerAutoSizes(({ [containerId]: _dropped, ...rest }) => rest);
    });
  }, [payload, selectedId, grouping, collapsedSet, members, positions]);

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
      { id: "lanes-layout", label: "Lanes layout", run: () => setLayoutMode("lanes") },
      { id: "relayout-branch", label: "Re-layout branch", run: relayoutBranch },
    ],
    [focusAddNodeInput, runBraid, toggleTheme, toggleAutoLayout, relayoutBranch],
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
  // F focuses, Delete/Backspace removes, Escape clears the selection once
  // focus/trace/palette/modal are all already out of its way (K41.4),
  // digits 1-5 switch the lens bar (K26) — see useGraphKeyboard.ts for the
  // key bindings, the Escape priority chain, and the form-field guard.
  useGraphKeyboard({
    payload,
    selectedId,
    paletteOpen,
    modalOpen: braidText !== null,
    focusOrTraceActive: !!focus || !!trace,
    jumpTo,
    focusOn,
    clearSelection: () => setSelectedId(null),
    applyOp,
    onLensChange: setLens,
    undoEntries: undoTrail.entries,
  });

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
        <LensBar lens={lens} onChange={setLens} />
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
            Focused on {nodeTitle(payload, focus.id)}
            {focus.members ? ` (${focus.members.size} member${focus.members.size === 1 ? "" : "s"})` : ""} —
            upstream {focus.ancestors.size}, downstream {focus.descendants.size}. Esc to exit.
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
        <LayoutControls
          mode={layoutMode}
          onToggleAuto={toggleAutoLayout}
          onLanes={() => setLayoutMode("lanes")}
          onRelayoutBranch={relayoutBranch}
          canRelayout={selectedId !== null}
        />
        <div className="kumi-actions">
          <button className="kumi-primary" onClick={runBraid}>
            Braid
          </button>
        </div>
        <UndoPanel entries={undoTrail.entries} onUndo={(entry) => entry.inverse && void applyOp(entry.inverse)} />
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
          <EdgePanel
            payload={payload}
            edgeId={selectedEdge}
            info={selectedEdgeInfo}
            onJump={jumpTo}
            onApply={(env) => void applyOp(env)}
            onClose={() => setSelectedEdge(null)}
          />
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
                centerWhenAdded(newNode.id); // K41.2
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
          <NodeForm node={selected} kinds={payload.kinds} nodes={payload.nodes} onApply={applyOp} />
        ) : (
          <p className="kumi-hint">Click a node to edit it; drag between handles to draw an edge.</p>
        )}
      </aside>
      <main className={`kumi-canvas${glideArmed.current && !interacting ? " kumi-glide" : ""}`}>
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
      <BraidModal text={braidText} planName={payload.plan} onClose={() => setBraidText(null)} />
      <Palette
        open={paletteOpen}
        nodes={payload.nodes}
        commands={paletteCommands}
        onClose={() => setPaletteOpen(false)}
        onSelectNode={jumpTo}
      />
      <Toasts toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
