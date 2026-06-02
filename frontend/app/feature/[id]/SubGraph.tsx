"use client";
import { useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow, Background, Node, Edge,
  useNodesState, useEdgesState, NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const DOMAIN_BG: Record<string, string> = {
  auth: "#4c1d95", billing: "#064e3b", workflow: "#78350f",
  data: "#1e3a5f", api: "#0c4a6e", unknown: "#1f2937",
};

const NODE_TYPES: NodeTypes = {};

interface Props {
  featureId: string;
  full: {
    feature: any;
    dependencies: any[];
    direct_dependents: any[];
  };
}

export default function SubGraph({ featureId, full }: Props) {
  const router = useRouter();
  const f = full.feature;

  // Build nodes
  const rawNodes: Node[] = useMemo(() => {
    const nodes: Node[] = [];
    const CX = 180, CY = 120;

    // Center: the feature itself
    nodes.push({
      id: featureId,
      data: { label: f.name },
      position: { x: CX, y: CY },
      style: {
        background: DOMAIN_BG[f.domain] ?? DOMAIN_BG.unknown,
        color: "#fff",
        border: "2px solid rgba(255,255,255,0.3)",
        borderRadius: 8, fontSize: 11, padding: "6px 10px",
        fontWeight: "600", width: 160, textAlign: "center" as const,
      },
    });

    // Dependencies (left)
    full.dependencies.slice(0, 5).forEach((d, i) => {
      const total = Math.min(full.dependencies.length, 5);
      nodes.push({
        id: d.id,
        data: { label: d.name },
        position: {
          x: -60,
          y: (i - (total - 1) / 2) * 70 + CY,
        },
        style: {
          background: DOMAIN_BG[d.domain] ?? DOMAIN_BG.unknown,
          color: "#fff",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 6, fontSize: 10, padding: "4px 8px",
          width: 140, textAlign: "center" as const, opacity: 0.85,
        },
      });
    });

    // Dependents (right)
    full.direct_dependents.slice(0, 5).forEach((d, i) => {
      const total = Math.min(full.direct_dependents.length, 5);
      nodes.push({
        id: d.id,
        data: { label: d.name },
        position: {
          x: 420,
          y: (i - (total - 1) / 2) * 70 + CY,
        },
        style: {
          background: DOMAIN_BG[d.domain] ?? DOMAIN_BG.unknown,
          color: "#fff",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 6, fontSize: 10, padding: "4px 8px",
          width: 140, textAlign: "center" as const, opacity: 0.85,
        },
      });
    });

    return nodes;
  }, [featureId, full]);

  const rawEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];
    full.dependencies.slice(0, 5).forEach((d) => {
      edges.push({
        id: `dep-${d.id}`, source: featureId, target: d.id,
        style: { stroke: "#4b5563", strokeWidth: 1.5 },
        markerEnd: { type: "arrowclosed" as any, color: "#6b7280" },
      });
    });
    full.direct_dependents.slice(0, 5).forEach((d) => {
      edges.push({
        id: `use-${d.id}`, source: d.id, target: featureId,
        style: { stroke: "#d97706", strokeWidth: 1.5 },
        markerEnd: { type: "arrowclosed" as any, color: "#d97706" },
        animated: true,
      });
    });
    return edges;
  }, [featureId, full]);

  const [nodes, , onNodesChange] = useNodesState(rawNodes);
  const [edges, , onEdgesChange] = useEdgesState(rawEdges);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_, node) => {
        if (node.id !== featureId) router.push(`/feature/${node.id}`);
      }}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      nodesDraggable={false}
      elementsSelectable={false}
      zoomOnScroll={false}
      panOnScroll={false}
      preventScrolling={false}
    >
      <Background color="#111827" gap={20} />
    </ReactFlow>
  );
}
