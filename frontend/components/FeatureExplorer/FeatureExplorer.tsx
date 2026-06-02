"use client";
import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Edge,
  Node,
  useEdgesState,
  useNodesState,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useFeatureGraph } from "@/lib/hooks/useFeatureGraph";
import { applyDagreLayout } from "@/lib/layout";
import { FeatureDetailPanel } from "./FeatureDetailPanel";

const DOMAIN_COLORS: Record<string, string> = {
  api:      "#3b82f6",
  service:  "#8b5cf6",
  data:     "#10b981",
  ui:       "#f59e0b",
  utility:  "#6b7280",
  auth:     "#8b5cf6",
  billing:  "#10b981",
  workflow: "#f59e0b",
  infra:    "#6b7280",
  unknown:  "#374151",
};

const NODE_TYPES = {};

interface Props {
  onFeatureSelect: (id: string | null) => void;
}

export default function FeatureExplorer({ onFeatureSelect }: Props) {
  const { features, relationships, isLoading } = useFeatureGraph();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [direction, setDirection] = useState<"LR" | "TB">("LR");

  useEffect(() => {
    if (!features.length) return;

    const rawNodes: Node[] = features.map((f) => ({
      id: f.id,
      data: { label: f.name, feature: f },
      position: { x: 0, y: 0 },
      style: {
        background: DOMAIN_COLORS[f.layer ?? f.domain ?? "unknown"],
        color: "#fff",
        border: "1px solid rgba(255,255,255,0.15)",
        borderRadius: 8,
        fontSize: 12,
        padding: "6px 12px",
        width: 180,
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

    const { nodes: laid, edges: laidEdges } = applyDagreLayout(rawNodes, rawEdges, direction);
    setNodes(laid);
    setEdges(laidEdges);
  }, [features, relationships, direction]);

  const handleNodeClick = useCallback(
    (_: unknown, node: Node) => {
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
        <p className="text-xs">Run <code className="bg-gray-800 px-1 py-0.5 rounded">/fg-analyze &lt;repo-path&gt;</code> to populate.</p>
      </div>
    );
  }

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
          fitViewOptions={{ padding: 0.15 }}
        >
          <Background color="#1f2937" gap={24} />
          <Controls />
          <Panel position="top-right">
            <div className="flex gap-1 bg-gray-900 border border-gray-700 rounded p-1">
              <button
                onClick={() => setDirection("LR")}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  direction === "LR" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Left → Right
              </button>
              <button
                onClick={() => setDirection("TB")}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  direction === "TB" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Top → Bottom
              </button>
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
