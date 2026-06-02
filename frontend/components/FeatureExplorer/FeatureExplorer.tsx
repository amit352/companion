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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useFeatureGraph } from "@/lib/hooks/useFeatureGraph";
import { FeatureDetailPanel } from "./FeatureDetailPanel";

const LAYER_COLORS: Record<string, string> = {
  api: "#3b82f6",
  service: "#8b5cf6",
  data: "#10b981",
  ui: "#f59e0b",
  utility: "#6b7280",
};

// Defined outside component so the reference is stable — fixes the key warning
// from ReactFlow's NodeRenderer when nodeTypes changes on every render.
const NODE_TYPES = {};

interface Props {
  onFeatureSelect: (id: string | null) => void;
}

export default function FeatureExplorer({ onFeatureSelect }: Props) {
  const { features, relationships, isLoading } = useFeatureGraph();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Stable position seed per feature id — no Math.random() on re-render
  const positionMap = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    features.forEach((f, i) => {
      if (!map.has(f.id)) {
        map.set(f.id, {
          x: (i % 8) * 200,
          y: Math.floor(i / 8) * 130,
        });
      }
    });
    return map;
  }, [features]);

  useEffect(() => {
    const flowNodes: Node[] = features.map((f) => ({
      id: f.id,
      data: { label: f.name, feature: f },
      position: positionMap.get(f.id) ?? { x: 0, y: 0 },
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
  }, [features, relationships, positionMap]);

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
          nodeTypes={NODE_TYPES}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
        >
          <Background color="#1f2937" gap={24} />
          <Controls />
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
