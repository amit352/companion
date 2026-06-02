"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LayoutDashboard, ChevronRight, ChevronDown, Layers, Network, Circle } from "lucide-react";

const API = "http://localhost:8000";

const DOMAIN_COLOR: Record<string, string> = {
  auth: "#8b5cf6", billing: "#10b981", workflow: "#f59e0b",
  data: "#3b82f6", api: "#06b6d4", unknown: "#4b5563",
};

interface TreeNode {
  id:       string;
  label:    string;
  type:     "architecture" | "domain" | "feature" | "dep" | "user";
  href?:    string;
  color?:   string;
  children?: TreeNode[];
  current?: boolean;
  defaultOpen?: boolean;
}

function TreeItem({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  const router  = useRouter();
  const [open, setOpen] = useState(node.defaultOpen ?? false);
  const hasChildren = node.children && node.children.length > 0;
  const indent = depth * 16;

  return (
    <div>
      <div
        className={`flex items-center gap-1.5 py-1 px-2 rounded cursor-pointer group transition-colors ${
          node.current
            ? "bg-blue-900/30 border border-blue-700/40"
            : "hover:bg-gray-800"
        }`}
        style={{ paddingLeft: `${indent + 8}px` }}
        onClick={() => {
          if (hasChildren) setOpen(!open);
          if (node.href) router.push(node.href);
        }}
      >
        {/* Expand/collapse arrow */}
        <span className="w-3 flex-shrink-0">
          {hasChildren
            ? open
              ? <ChevronDown size={11} className="text-gray-600" />
              : <ChevronRight size={11} className="text-gray-600" />
            : null}
        </span>

        {/* Color dot */}
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{
            background: node.current ? "#60a5fa" : (node.color ?? "#4b5563"),
            opacity: node.current ? 1 : 0.7,
          }}
        />

        {/* Label */}
        <span className={`text-xs truncate ${
          node.current ? "text-blue-300 font-semibold" :
          node.href    ? "text-gray-400 group-hover:text-gray-200" :
          "text-gray-500"
        }`}>
          {node.label}
        </span>

        {node.current && (
          <span className="ml-auto text-xs text-blue-600 flex-shrink-0">◀</span>
        )}
      </div>

      {open && hasChildren && (
        <div className="relative">
          {/* Vertical connector line */}
          <div
            className="absolute border-l border-gray-800"
            style={{ left: `${indent + 14}px`, top: 0, bottom: 0 }}
          />
          {node.children!.map((child) => (
            <TreeItem key={child.id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface Props {
  featureId: string;
}

export function HierarchyPanel({ featureId }: Props) {
  const router  = useRouter();
  const [full, setFull]       = useState<any>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [allFeatures, setAllFeatures] = useState<any[]>([]);

  useEffect(() => {
    if (!featureId) return;
    Promise.all([
      fetch(`${API}/api/v1/features/${featureId}/full`).then((r) => r.json()),
      fetch(`${API}/api/v1/features/`).then((r) => r.json()),
    ]).then(([f, list]) => {
      setFull(f);
      setAllFeatures(list.features ?? []);
    }).catch(() => {});
  }, [featureId]);

  if (!full) return null;

  const f        = full.feature;
  const domain   = f?.domain ?? "unknown";
  const domColor = DOMAIN_COLOR[domain] ?? DOMAIN_COLOR.unknown;

  // Siblings: other features in same domain
  const siblings = allFeatures
    .filter((x) => x.domain === domain && x.id !== featureId)
    .slice(0, 5);

  const tree: TreeNode = {
    id:    "architecture",
    label: "Architecture",
    type:  "architecture",
    href:  "/",
    color: "#374151",
    defaultOpen: true,
    children: [{
      id:    `domain-${domain}`,
      label: domain.charAt(0).toUpperCase() + domain.slice(1),
      type:  "domain",
      color: domColor,
      defaultOpen: true,
      children: [
        // Siblings in same domain
        ...siblings.map((s) => ({
          id:    s.id,
          label: s.name,
          type:  "feature" as const,
          href:  `/feature/${s.id}`,
          color: domColor,
        })),
        // Current feature
        {
          id:      featureId,
          label:   f.name,
          type:    "feature" as const,
          color:   "#60a5fa",
          current: true,
          defaultOpen: true,
          children: [
            // Dependencies branch
            ...(full.dependencies?.length > 0 ? [{
              id:    "deps-group",
              label: `Depends on (${full.dependencies.length})`,
              type:  "dep" as const,
              color: "#4b5563",
              defaultOpen: true,
              children: full.dependencies.map((d: any) => ({
                id:    d.id,
                label: d.name,
                type:  "dep" as const,
                href:  `/feature/${d.id}`,
                color: DOMAIN_COLOR[d.domain] ?? "#4b5563",
              })),
            }] : []),
            // Dependents branch
            ...(full.direct_dependents?.length > 0 ? [{
              id:    "users-group",
              label: `Used by (${full.direct_dependents.length})`,
              type:  "user" as const,
              color: "#4b5563",
              defaultOpen: true,
              children: [
                ...full.direct_dependents.map((d: any) => ({
                  id:    d.id,
                  label: d.name,
                  type:  "user" as const,
                  href:  `/feature/${d.id}`,
                  color: DOMAIN_COLOR[d.domain] ?? "#4b5563",
                })),
                ...(full.level2_dependents?.length > 0 ? [{
                  id:    "l2-group",
                  label: `+${full.level2_dependents.length} more (L2)`,
                  type:  "user" as const,
                  color: "#374151",
                  children: full.level2_dependents.map((d: any) => ({
                    id:    d.id,
                    label: d.name,
                    type:  "user" as const,
                    href:  `/feature/${d.id}`,
                    color: DOMAIN_COLOR[d.domain] ?? "#4b5563",
                  })),
                }] : []),
              ],
            }] : []),
          ],
        },
      ],
    }],
  };

  return (
    <aside className={`border-l border-gray-800 bg-gray-950 flex flex-col flex-shrink-0 transition-all ${
      collapsed ? "w-10" : "w-64"
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-gray-800 flex-shrink-0">
        {!collapsed && (
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Hierarchy
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto text-gray-600 hover:text-gray-300 transition-colors"
          title={collapsed ? "Expand" : "Collapse"}
        >
          <ChevronRight size={14} className={`transition-transform ${collapsed ? "" : "rotate-180"}`} />
        </button>
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto py-2">
          <TreeItem node={tree} depth={0} />
        </div>
      )}

      {/* Dashboard button */}
      {!collapsed && (
        <div className="border-t border-gray-800 p-2 flex-shrink-0">
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-2 w-full px-2 py-1.5 text-xs text-gray-500 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
          >
            <LayoutDashboard size={12} />
            Dashboard
          </button>
        </div>
      )}
    </aside>
  );
}
