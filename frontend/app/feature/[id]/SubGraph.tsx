"use client";
import { useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  ReactFlow, Background, Node, Edge,
  useNodesState, useEdgesState, NodeTypes,
  Handle, Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const DOMAIN_BG: Record<string, string> = {
  auth: "#4c1d95", billing: "#064e3b", workflow: "#78350f",
  data: "#1e3a5f", api: "#0c4a6e", unknown: "#1f2937",
};
const DOMAIN_BORDER: Record<string, string> = {
  auth: "#7c3aed", billing: "#059669", workflow: "#d97706",
  data: "#2563eb", api: "#0891b2", unknown: "#374151",
};

// Custom node with source/target handles
function FeatureNode({ data }: { data: any }) {
  return (
    <div
      style={{
        background: data.bg,
        border: `1.5px solid ${data.border}`,
        borderRadius: 8,
        padding: "6px 12px",
        fontSize: 11,
        color: "#fff",
        textAlign: "center",
        width: 150,
        cursor: data.current ? "default" : "pointer",
        fontWeight: data.current ? 600 : 400,
        boxShadow: data.current ? "0 0 0 2px rgba(96,165,250,0.5)" : "none",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "#4b5563", width: 6, height: 6 }} />
      {data.label}
      <Handle type="source" position={Position.Right} style={{ background: "#4b5563", width: 6, height: 6 }} />
    </div>
  );
}

const NODE_TYPES: NodeTypes = { feature: FeatureNode as any };

interface Props {
  featureId: string;
  full: { feature: any; dependencies: any[]; direct_dependents: any[] };
}

export default function SubGraph({ featureId, full }: Props) {
  const router = useRouter();
  const f = full.feature;

  const rawNodes: Node[] = useMemo(() => {
    const nodes: Node[] = [];
    const CX = 210, CY = 110;
    const spacingY = 65;

    // Current feature — center
    nodes.push({
      id: featureId, type: "feature",
      data: {
        label: f.name,
        bg: DOMAIN_BG[f.domain] ?? DOMAIN_BG.unknown,
        border: "#60a5fa",
        current: true,
      },
      position: { x: CX, y: CY },
    });

    // Dependencies — LEFT column
    const deps = full.dependencies.slice(0, 5);
    deps.forEach((d, i) => {
      const total = deps.length;
      nodes.push({
        id: d.id, type: "feature",
        data: {
          label: d.name,
          bg: DOMAIN_BG[d.domain] ?? DOMAIN_BG.unknown,
          border: DOMAIN_BORDER[d.domain] ?? "#374151",
          current: false,
        },
        position: {
          x: 10,
          y: (i - (total - 1) / 2) * spacingY + CY,
        },
      });
    });

    // Dependents — RIGHT column
    const users = full.direct_dependents.slice(0, 5);
    users.forEach((d, i) => {
      const total = users.length;
      nodes.push({
        id: d.id, type: "feature",
        data: {
          label: d.name,
          bg: DOMAIN_BG[d.domain] ?? DOMAIN_BG.unknown,
          border: DOMAIN_BORDER[d.domain] ?? "#374151",
          current: false,
        },
        position: {
          x: 410,
          y: (i - (total - 1) / 2) * spacingY + CY,
        },
      });
    });

    return nodes;
  }, [featureId, full]);

  const rawEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [];

    // Current → dependencies (current needs these)
    full.dependencies.slice(0, 5).forEach((d) => {
      edges.push({
        id: `dep-${d.id}`,
        source: featureId, target: d.id,
        style: { stroke: "#60a5fa", strokeWidth: 1.5 },
        markerEnd: { type: "arrowclosed" as any, color: "#60a5fa" },
        label: "needs",
        labelStyle: { fill: "#6b7280", fontSize: 9 },
        labelBgStyle: { fill: "#111827" },
      });
    });

    // Dependents → current (these need the current feature)
    full.direct_dependents.slice(0, 5).forEach((d) => {
      edges.push({
        id: `use-${d.id}`,
        source: d.id, target: featureId,
        style: { stroke: "#d97706", strokeWidth: 1.5 },
        markerEnd: { type: "arrowclosed" as any, color: "#d97706" },
        animated: true,
        label: "uses",
        labelStyle: { fill: "#6b7280", fontSize: 9 },
        labelBgStyle: { fill: "#111827" },
      });
    });

    return edges;
  }, [featureId, full]);

  const [nodes, , onNodesChange] = useNodesState(rawNodes);
  const [edges, , onEdgesChange] = useEdgesState(rawEdges);

  return (
    <div className="h-full relative">
      {/* Legend */}
      <div className="absolute top-2 right-2 z-10 flex flex-col gap-1 bg-gray-900/80 px-2 py-1.5 rounded text-xs">
        <div className="flex items-center gap-1.5 text-blue-400">
          <div className="w-5 h-px border-t-2 border-blue-400" /> needs
        </div>
        <div className="flex items-center gap-1.5 text-amber-500">
          <div className="w-5 h-px border-t-2 border-amber-500 border-dashed" /> uses
        </div>
      </div>

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
        fitViewOptions={{ padding: 0.15 }}
        nodesDraggable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnScroll={false}
        preventScrolling={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#111827" gap={20} />
      </ReactFlow>
    </div>
  );
}
