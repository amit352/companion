"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Edge,
  Node,
  useEdgesState,
  useNodesState,
  Panel,
  NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCompanion } from "@/lib/hooks/useCompanion";
import { applyDagreLayout } from "@/lib/layout";
import { buildGroupedLayout, DOMAIN_COLORS } from "@/lib/groupLayout";
import { buildArchitectureLayout } from "@/lib/architectureLayout";
import { GroupNode } from "./GroupNode";
import { FeatureDetailPanel } from "./FeatureDetailPanel";
import { TourPanel } from "./TourPanel";

const API = "http://localhost:8000";

type ViewMode = "architecture" | "grouped" | "LR" | "TB";

const NODE_COLORS: Record<string, string> = {
  auth: "#7c3aed", billing: "#059669", workflow: "#d97706",
  data: "#2563eb", infra: "#475569", unknown: "#374151",
};

const NODE_TYPES: NodeTypes = { group: GroupNode as any };

interface Props {
  onFeatureSelect: (id: string | null) => void;
}

export default function FeatureExplorer({ onFeatureSelect }: Props) {
  const { features, relationships, isLoading } = useCompanion();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId]     = useState<string | null>(null);
  const [viewMode, setViewMode]        = useState<ViewMode>("architecture");
  const [searchQuery, setSearchQuery]  = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchOpen, setSearchOpen]       = useState(false);
  const [tourOpen, setTourOpen]           = useState(false);
  const [tourFocusId, setTourFocusId]     = useState<string | null>(null);

  useEffect(() => {
    if (!features.length) return;

    if (viewMode === "architecture") {
      const { nodes: n, edges: e } = buildArchitectureLayout(features, relationships);
      setNodes(n);
      setEdges(e);
      return;
    }
    if (viewMode === "grouped") {
      const { nodes: n, edges: e } = buildGroupedLayout(features, relationships);
      setNodes(n);
      setEdges(e);
      return;
    }

    const rawNodes: Node[] = features.map((f) => ({
      id: f.id,
      data: { label: f.name, feature: f },
      position: { x: 0, y: 0 },
      style: {
        background: NODE_COLORS[f.domain ?? "unknown"],
        color: "#fff",
        border: "1px solid rgba(255,255,255,0.15)",
        borderRadius: 8,
        fontSize: 11,
        padding: "6px 10px",
        width: 172,
        textAlign: "center" as const,
      },
    }));

    const rawEdges: Edge[] = relationships
      .filter((r) => r.source_id && r.target_id)
      .map((r) => ({
        id: `${r.source_id}-${r.target_id}`,
        source: r.source_id,
        target: r.target_id,
        style: { stroke: "#4b5563", strokeWidth: 1.5 },
        markerEnd: { type: "arrowclosed" as any, color: "#6b7280" },
      }));

    const { nodes: laid, edges: laidEdges } = applyDagreLayout(rawNodes, rawEdges, viewMode as "LR" | "TB");
    setNodes(laid);
    setEdges(laidEdges);
  }, [features, relationships, viewMode]);

  // ── BM25 search — debounced, populates dropdown ──────────────────────────
  useEffect(() => {
    if (!searchQuery.trim()) { setSearchResults([]); setSearchOpen(false); return; }
    const t = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/api/v1/search/semantic?q=${encodeURIComponent(searchQuery)}&limit=6`);
        const data = await res.json();
        setSearchResults(data.results ?? []);
        setSearchOpen(true);
      } catch { setSearchResults([]); }
    }, 250);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // ── Search — dim non-matching nodes ──────────────────────────────────────
  const q = searchQuery.trim().toLowerCase();
  const matchIds = useMemo(() => {
    if (!q) return null;
    return new Set(
      features
        .filter((f: any) =>
          f.name?.toLowerCase().includes(q) ||
          f.description?.toLowerCase().includes(q) ||
          f.tags?.some((t: string) => t.toLowerCase().includes(q)) ||
          f.domain?.toLowerCase().includes(q)
        )
        .map((f: any) => f.id)
    );
  }, [q, features]);

  const searchNodes = useMemo(() =>
    nodes.map((n) => {
      if (n.type === "group") return n;

      // Tour mode: highlight current tour node
      if (tourOpen && tourFocusId) {
        const isTourNode = n.id === tourFocusId;
        return {
          ...n,
          style: {
            ...n.style,
            opacity:   isTourNode ? 1 : 0.2,
            outline:   isTourNode ? "2px solid #60a5fa" : undefined,
            boxShadow: isTourNode ? "0 0 12px rgba(96,165,250,0.6)" : undefined,
          },
          zIndex: isTourNode ? 10 : 0,
        };
      }

      // Search mode: highlight matches
      if (!matchIds) return n;
      const isMatch = matchIds.has(n.id);
      return {
        ...n,
        style: {
          ...n.style,
          opacity: isMatch ? 1 : 0.15,
          outline: isMatch ? "2px solid #fbbf24" : undefined,
        },
        zIndex: isMatch ? 5 : 0,
      };
    }),
    [nodes, matchIds, tourOpen, tourFocusId]
  );

  // ── Edge visibility — show only connections of hovered/selected node ─────
  const focusId = hoveredId ?? selectedId;
  const visibleEdges = useMemo(() =>
    edges.map((e) => {
      const connected = !focusId || e.source === focusId || e.target === focusId;
      return {
        ...e,
        hidden: !connected && !!focusId,
        style: {
          ...e.style,
          stroke:       connected ? "#60a5fa" : "#374151",
          strokeWidth:  connected && focusId ? 2 : 1.5,
          opacity:      focusId ? (connected ? 1 : 0) : 0,
        },
        animated:   connected && !!focusId,
        markerEnd:  { type: "arrowclosed" as any, color: connected ? "#60a5fa" : "#4b5563" },
        zIndex:     connected ? 10 : 0,
      };
    }),
    [edges, focusId]
  );

  const handleNodeClick = useCallback((_: unknown, node: Node) => {
    if (node.type === "group") return;
    const newId = node.id === selectedId ? null : node.id;
    setSelectedId(newId);
    onFeatureSelect(newId);
  }, [onFeatureSelect, selectedId]);

  const handleNodeMouseEnter = useCallback((_: unknown, node: Node) => {
    if (node.type !== "group") setHoveredId(node.id);
  }, []);

  const handleNodeMouseLeave = useCallback(() => setHoveredId(null), []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        Loading feature graph...
      </div>
    );
  }

  if (!features.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-500 text-sm">
        <p>No features in graph yet.</p>
        <p className="text-xs">
          Run <code className="bg-gray-800 px-1 py-0.5 rounded">/fg-analyze &lt;repo-path&gt;</code> to populate.
        </p>
      </div>
    );
  }

  const modes: { id: ViewMode; label: string }[] = [
    { id: "architecture", label: "Architecture" },
    { id: "grouped",      label: "Grouped" },
    { id: "LR",           label: "L → R" },
    { id: "TB",           label: "T → B" },
  ];

  // Legend
  const domains = [...new Set(features.map((f: any) => f.domain))].filter(Boolean);

  return (
    <div className="flex h-full">
      <div className="flex-1 relative">
        <ReactFlow
          nodes={searchNodes}
          edges={visibleEdges}
          nodeTypes={NODE_TYPES}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onNodeMouseEnter={handleNodeMouseEnter}
          onNodeMouseLeave={handleNodeMouseLeave}
          onPaneClick={() => { setSelectedId(null); onFeatureSelect(null); }}
          fitView
          fitViewOptions={{ padding: 0.12 }}
        >
          <Background color="#111827" gap={28} />
          <Controls />

          {/* Search + Tour toggle */}
          <Panel position="top-left">
            <div className="flex flex-col gap-1.5">
              {/* Search box */}
              <div className="relative">
                <div className="flex items-center gap-2 bg-gray-900/95 border border-gray-700 rounded-lg px-3 py-1.5 shadow-lg">
                  <svg className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
                  </svg>
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Escape") { setSearchQuery(""); setSearchOpen(false); } }}
                    onFocus={() => searchResults.length && setSearchOpen(true)}
                    placeholder="Search features…"
                    className="bg-transparent text-xs text-gray-200 placeholder-gray-600 outline-none w-44"
                  />
                  {searchQuery && (
                    <button onClick={() => { setSearchQuery(""); setSearchOpen(false); }} className="text-gray-600 hover:text-gray-300 text-xs">✕</button>
                  )}
                </div>

                {/* BM25 results dropdown */}
                {searchOpen && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 mt-1 w-72 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden z-50">
                    {searchResults.map((r) => (
                      <button
                        key={r.id}
                        onClick={() => {
                          setSelectedId(r.id);
                          onFeatureSelect(r.id);
                          setSearchOpen(false);
                        }}
                        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-800 transition-colors text-left"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-gray-200 truncate">{r.name}</p>
                          <p className="text-xs text-gray-500 truncate">{r.domain}</p>
                        </div>
                        <span className="text-xs text-blue-400 ml-2 flex-shrink-0 font-mono">
                          {r.score.toFixed(2)}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Tour button */}
              <button
                onClick={() => setTourOpen(!tourOpen)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shadow-lg border ${
                  tourOpen
                    ? "bg-blue-600 border-blue-500 text-white"
                    : "bg-gray-900/95 border-gray-700 text-gray-400 hover:text-gray-200"
                }`}
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                {tourOpen ? "Exit Tour" : "Guided Tour"}
              </button>
            </div>
          </Panel>

          {/* View mode toggle */}
          <Panel position="top-right">
            <div className="flex gap-1 bg-gray-900/90 border border-gray-700 rounded-lg p-1 shadow-lg">
              {modes.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setViewMode(m.id)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    viewMode === m.id
                      ? "bg-blue-600 text-white"
                      : "text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </Panel>

          {/* Domain legend */}
          <Panel position="bottom-left">
            <div className="flex gap-2 flex-wrap bg-gray-900/80 border border-gray-700/50 rounded-lg px-3 py-2 shadow">
              {["shared", ...domains].map((d) => {
                const c = DOMAIN_COLORS[d] ?? DOMAIN_COLORS.unknown;
                return (
                  <div key={d} className="flex items-center gap-1.5">
                    <div
                      className="w-2.5 h-2.5 rounded-sm"
                      style={{ background: c.text }}
                    />
                    <span className="text-xs text-gray-400 capitalize">{d}</span>
                  </div>
                );
              })}
            </div>
          </Panel>
        </ReactFlow>
      </div>

      {selectedId && !tourOpen && (
        <FeatureDetailPanel
          featureId={selectedId}
          onClose={() => {
            setSelectedId(null);
            onFeatureSelect(null);
          }}
        />
      )}

      {tourOpen && (
        <TourPanel
          onNodeFocus={(id) => {
            setTourFocusId(id);
            setSelectedId(id);
            onFeatureSelect(id);
          }}
          onClose={() => {
            setTourOpen(false);
            setTourFocusId(null);
          }}
        />
      )}
    </div>
  );
}
