"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { LayoutDashboard, Layers, Network, Code2, Shield, ChevronRight } from "lucide-react";

const API = "http://localhost:8000";

interface HierarchyLevel {
  key:   string;
  label: string;
  icon:  any;
  href:  string | null;
  active: boolean;
  sublabel?: string;
}

interface Props {
  featureId?: string;    // current feature (if on detail page)
  functionName?: string; // current function focus (if drilling into code)
}

export function HierarchyPanel({ featureId, functionName }: Props) {
  const router   = useRouter();
  const pathname = usePathname();
  const [feature, setFeature] = useState<any>(null);
  const [domains, setDomains] = useState<string[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    // Load domain list for the architecture level
    fetch(`${API}/api/v1/graph/overview`)
      .then((r) => r.json())
      .then((d) => {
        const domainCounts: Record<string, number> = {};
        (d.nodes ?? []).forEach((n: any) => {
          if (n.label !== "Repository" && n.label !== "Feature") return;
        });
        setDomains(["auth", "billing", "workflow", "data"]);
      })
      .catch(() => {});

    // Load feature if on detail page
    if (featureId) {
      fetch(`${API}/api/v1/features/${featureId}/full`)
        .then((r) => r.json())
        .then((d) => setFeature(d))
        .catch(() => {});
    }
  }, [featureId]);

  const isOnDashboard = pathname === "/";
  const isOnFeature   = !!featureId;

  const levels: HierarchyLevel[] = [
    {
      key:     "architecture",
      label:   "Architecture",
      icon:    LayoutDashboard,
      href:    "/",
      active:  isOnDashboard && !featureId,
      sublabel: "All domains",
    },
    {
      key:     "domain",
      label:   feature?.feature?.domain
               ? feature.feature.domain.charAt(0).toUpperCase() + feature.feature.domain.slice(1)
               : "Domain",
      icon:    Layers,
      href:    isOnFeature ? "/" : null,
      active:  false,
      sublabel: isOnFeature ? feature?.feature?.domain : undefined,
    },
    {
      key:    "feature",
      label:  feature?.feature?.name ?? "Feature",
      icon:   Network,
      href:   null,
      active: isOnFeature,
      sublabel: isOnFeature
        ? `${feature?.dependencies?.length ?? 0} deps · ${feature?.direct_dependents?.length ?? 0} users`
        : undefined,
    },
    ...(functionName ? [{
      key:     "function",
      label:   functionName,
      icon:    Code2,
      href:    null,
      active:  true,
      sublabel: "function",
    }] : []),
  ];

  // Only show panel on feature detail pages
  if (!featureId) return null;

  return (
    <aside
      className={`border-l border-gray-800 bg-gray-950 flex flex-col transition-all ${
        collapsed ? "w-10" : "w-56"
      }`}
    >
      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-b border-gray-800 text-gray-600 hover:text-gray-300 transition-colors flex-shrink-0"
        title={collapsed ? "Expand hierarchy" : "Collapse"}
      >
        <ChevronRight size={14} className={`transition-transform ${collapsed ? "" : "rotate-180"}`} />
      </button>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3">
          <p className="text-xs text-gray-600 uppercase tracking-wider mb-3">You are here</p>

          {levels.map((level, i) => {
            const Icon = level.icon;
            const isLast = i === levels.length - 1;
            return (
              <div key={level.key} className="flex items-start gap-2 mb-1">
                {/* Connector line */}
                <div className="flex flex-col items-center flex-shrink-0 mt-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    level.active ? "bg-blue-400" : "bg-gray-700"
                  }`} />
                  {!isLast && <div className="w-px flex-1 bg-gray-800 my-0.5" style={{ height: "24px" }} />}
                </div>

                {/* Level card */}
                {level.href ? (
                  <button
                    onClick={() => router.push(level.href!)}
                    className="flex items-start gap-2 flex-1 py-1 px-2 rounded hover:bg-gray-800 transition-colors text-left group"
                  >
                    <Icon size={12} className="text-gray-500 group-hover:text-gray-300 mt-0.5 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs text-gray-400 group-hover:text-gray-200 font-medium truncate">
                        {level.label}
                      </p>
                      {level.sublabel && (
                        <p className="text-xs text-gray-700 truncate">{level.sublabel}</p>
                      )}
                    </div>
                  </button>
                ) : (
                  <div className={`flex items-start gap-2 flex-1 py-1 px-2 rounded ${
                    level.active ? "bg-blue-900/20 border border-blue-800/30" : ""
                  }`}>
                    <Icon size={12} className={`${level.active ? "text-blue-400" : "text-gray-600"} mt-0.5 flex-shrink-0`} />
                    <div className="min-w-0">
                      <p className={`text-xs font-medium truncate ${level.active ? "text-blue-300" : "text-gray-500"}`}>
                        {level.label}
                      </p>
                      {level.sublabel && (
                        <p className="text-xs text-gray-700 truncate">{level.sublabel}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Quick actions */}
          <div className="mt-4 pt-3 border-t border-gray-800 space-y-1">
            <button
              onClick={() => router.push("/")}
              className="flex items-center gap-2 w-full px-2 py-1.5 text-xs text-gray-500 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
            >
              <LayoutDashboard size={12} />
              Back to dashboard
            </button>
            {feature?.dependencies?.[0] && (
              <button
                onClick={() => router.push(`/feature/${feature.dependencies[0].id}`)}
                className="flex items-center gap-2 w-full px-2 py-1.5 text-xs text-gray-500 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
              >
                <ChevronRight size={12} />
                Drill into dependency
              </button>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
