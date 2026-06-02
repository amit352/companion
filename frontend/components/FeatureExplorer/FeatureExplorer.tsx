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
import { useFeatureGraph } from "@/lib/hooks/useFeatureGraph";
import { applyDagreLayout } from "@/lib/layout";
import { buildGroupedLayout, DOMAIN_COLORS } from "@/lib/groupLayout";
import { buildArchitectureLayout } from "@/lib/architectureLayout";
import { GroupNode } from "./GroupNode";
import { FeatureDetailPanel } from "./FeatureDetailPanel";

type ViewMode = "architecture" | "grouped" | "LR" | "TB";

const NODE_COLORS: Record<string, string> = {
  auth: "#7c3aed", billing: "#059669", workflow: "#d97706",
  data: "#2563eb", infra: "#475569", unknown: "#374151",
};

// Stable reference — must be outside component
const NODE_TYPES: NodeTypes = { group: GroupNode as any };

interface Props {
  onFeatureSelect: (id: string | null) => void;
}

export default function FeatureExplorer({ onFeatureSelect }: Props) {
  const { features, relationships, isLoading } = useFeatureGraph();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("architecture");

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

    // Flat dagre layout
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
        animated: r.kind?.toUpperCase() === "DEPENDS_ON",
        markerEnd: { type: "arrowclosed" as any, color: "#6b7280" },
      }));

    const { nodes: laid, edges: laidEdges } = applyDagreLayout(
      rawNodes, rawEdges, viewMode as "LR" | "TB"
    );
    setNodes(laid);
    setEdges(laidEdges);
  }, [features, relationships, viewMode]);

  const handleNodeClick = useCallback(
    (_: unknown, node: Node) => {
      if (node.type === "group") return; // ignore group container clicks
      setSelectedId(node.id);
      onFeatureSelect(node.id);
    },
    [onFeatureSelect]
  );

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
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
          fitViewOptions={{ padding: 0.12 }}
        >
          <Background color="#111827" gap={28} />
          <Controls />

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

      {selectedId && (
        <FeatureDetailPanel
          featureId={selectedId}
          onClose={() => {
            setSelectedId(null);
            onFeatureSelect(null);
          }}
        />
      )}
    </div>
  );
}
