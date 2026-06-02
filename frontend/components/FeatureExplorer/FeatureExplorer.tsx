"use client";
import { useCallback, useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MiniMap,
  Node,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { useFeatureGraph } from "@/lib/hooks/useFeatureGraph";
import { FeatureDetailPanel } from "./FeatureDetailPanel";

const LAYER_COLORS: Record<string, string> = {
  api: "#3b82f6",
  service: "#8b5cf6",
  data: "#10b981",
  ui: "#f59e0b",
  utility: "#6b7280",
};

interface Props {
  onFeatureSelect: (id: string | null) => void;
}

export default function FeatureExplorer({ onFeatureSelect }: Props) {
  const { features, relationships, isLoading } = useFeatureGraph();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!features.length) return;

    const flowNodes: Node[] = features.map((f, i) => ({
      id: f.id,
      data: { label: f.name, feature: f },
      position: {
        x: (i % 8) * 180 + Math.random() * 40,
        y: Math.floor(i / 8) * 120 + Math.random() * 20,
      },
      style: {
        background: LAYER_COLORS[f.layer ?? "utility"],
        color: "#fff",
        border: "1px solid rgba(255,255,255,0.2)",
        borderRadius: 8,
        fontSize: 12,
        padding: "6px 12px",
      },
    }));

    const flowEdges: Edge[] = relationships.map((r) => ({
      id: `${r.source_id}-${r.target_id}`,
      source: r.source_id,
      target: r.target_id,
      label: r.kind,
      style: { stroke: "#4b5563" },
      animated: r.kind === "depends_on",
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [features, relationships]);

  const handleNodeClick = useCallback(
    (_: unknown, node: Node) => {
      setSelectedId(node.id);
      onFeatureSelect(node.id);
    },
    [onFeatureSelect]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Loading feature graph...
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
        >
          <Background color="#1f2937" gap={24} />
          <Controls />
          <MiniMap
            nodeStrokeColor="#374151"
            nodeColor={(n) => (n.style?.background as string) ?? "#6b7280"}
            maskColor="rgba(0,0,0,0.4)"
          />
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
