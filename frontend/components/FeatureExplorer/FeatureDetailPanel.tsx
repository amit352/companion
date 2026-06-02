"use client";
import { useEffect, useState } from "react";
import { X, Copy, Check, ChevronRight } from "lucide-react";

const API = "http://localhost:8000";

interface Props {
  featureId: string;
  onClose: () => void;
  onNodeFocus?: (id: string) => void;   // navigate to a related feature in graph
}

interface FullFeature {
  feature:           Record<string, any>;
  dependencies:      any[];
  direct_dependents: any[];
  level2_dependents: any[];
  related_nodes:     any[];
  blast_radius:      number;
  context_for_claude: string;
}

const DOMAIN_DOT: Record<string, string> = {
  auth: "#8b5cf6", billing: "#10b981", workflow: "#f59e0b",
  data: "#3b82f6", api: "#06b6d4", unknown: "#4b5563",
};

const NODE_TYPE_ICON: Record<string, string> = {
  Service: "⚙", API: "⚡", DatabaseTable: "🗄", UIComponent: "🖼",
  Requirement: "📋", Feature: "◈",
};

export function FeatureDetailPanel({ featureId, onClose, onNodeFocus }: Props) {
  const [data, setData]       = useState<FullFeature | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied]   = useState(false);
  const [showLevel2, setShowLevel2] = useState(false);

  useEffect(() => {
    setLoading(true);
    setShowLevel2(false);
    fetch(`${API}/api/v1/features/${featureId}/full`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [featureId]);

  function copyContext() {
    if (!data) return;
    navigator.clipboard.writeText(data.context_for_claude);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  const f = data?.feature;

  return (
    <aside className="w-80 border-l border-gray-800 flex flex-col overflow-hidden bg-gray-950">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-200">Feature Detail</h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-200 transition-colors">
          <X size={16} />
        </button>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center text-gray-600 text-xs">Loading…</div>
      )}

      {!loading && f && (
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-xs">

          {/* Name + domain */}
          <section>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full" style={{ background: DOMAIN_DOT[f.domain] ?? "#4b5563" }} />
              <h3 className="text-blue-400 font-semibold text-sm leading-tight">{f.name}</h3>
            </div>
            <p className="text-gray-400 leading-relaxed">{f.description}</p>
          </section>

          {/* Tags */}
          {f.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {f.tags.map((t: string) => (
                <span key={t} className="bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded text-xs">{t}</span>
              ))}
            </div>
          )}

          {/* Confidence */}
          <section>
            <p className="text-gray-600 uppercase tracking-wider text-xs mb-1">Confidence</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-gray-800 rounded-full">
                <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${(f.confidence ?? 1) * 100}%` }} />
              </div>
              <span className="text-gray-400">{Math.round((f.confidence ?? 1) * 100)}%</span>
            </div>
          </section>

          {/* Source files */}
          {f.source_files?.length > 0 && (
            <section>
              <p className="text-gray-600 uppercase tracking-wider mb-1">Source Files</p>
              {f.source_files.map((fp: string) => (
                <p key={fp} className="text-gray-400 font-mono text-xs break-all">{fp}</p>
              ))}
            </section>
          )}

          {/* Dependencies — what this feature NEEDS */}
          {data!.dependencies.length > 0 && (
            <section>
              <p className="text-gray-600 uppercase tracking-wider mb-1.5">Depends On</p>
              {data!.dependencies.map((d) => (
                <button
                  key={d.id}
                  onClick={() => onNodeFocus?.(d.id)}
                  className="flex items-center gap-1.5 w-full text-left py-1 hover:text-blue-400 transition-colors group"
                >
                  <ChevronRight size={11} className="text-gray-600 group-hover:text-blue-400" />
                  <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: DOMAIN_DOT[d.domain] ?? "#4b5563" }} />
                  <span className="text-gray-300 group-hover:text-blue-400 truncate">{d.name}</span>
                </button>
              ))}
            </section>
          )}

          {/* Blast radius — what NEEDS this feature */}
          {(data!.direct_dependents.length > 0 || data!.level2_dependents.length > 0) && (
            <section>
              <p className="text-gray-600 uppercase tracking-wider mb-1.5">
                Impact — {data!.blast_radius} dependent(s)
              </p>

              {/* Level 1 */}
              {data!.direct_dependents.map((d) => (
                <button
                  key={d.id}
                  onClick={() => onNodeFocus?.(d.id)}
                  className="flex items-center gap-1.5 w-full text-left py-1 hover:text-orange-300 transition-colors group"
                >
                  <ChevronRight size={11} className="text-orange-600 group-hover:text-orange-400" />
                  <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: DOMAIN_DOT[d.domain] ?? "#4b5563" }} />
                  <span className="text-orange-400 group-hover:text-orange-300 truncate">{d.name}</span>
                  <span className="text-gray-600 ml-auto text-xs">L1</span>
                </button>
              ))}

              {/* Level 2 toggle */}
              {data!.level2_dependents.length > 0 && (
                <>
                  <button
                    onClick={() => setShowLevel2(!showLevel2)}
                    className="text-gray-600 hover:text-gray-400 text-xs mt-1 flex items-center gap-1"
                  >
                    <ChevronRight size={10} className={`transition-transform ${showLevel2 ? "rotate-90" : ""}`} />
                    {data!.level2_dependents.length} more (level 2)
                  </button>
                  {showLevel2 && data!.level2_dependents.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => onNodeFocus?.(d.id)}
                      className="flex items-center gap-1.5 w-full text-left py-0.5 hover:text-yellow-300 transition-colors ml-3 group"
                    >
                      <div className="w-1 h-1 rounded-full bg-yellow-700 flex-shrink-0" />
                      <span className="text-yellow-600 group-hover:text-yellow-400 truncate">{d.name}</span>
                      <span className="text-gray-700 ml-auto text-xs">L2</span>
                    </button>
                  ))}
                </>
              )}
            </section>
          )}

          {/* Related nodes: APIs, Services, DB tables */}
          {data!.related_nodes.length > 0 && (
            <section>
              <p className="text-gray-600 uppercase tracking-wider mb-1.5">Related Infrastructure</p>
              {data!.related_nodes.map((n, i) => (
                <div key={i} className="flex items-center gap-1.5 py-0.5">
                  <span className="text-gray-600">{NODE_TYPE_ICON[n.type] ?? "○"}</span>
                  <span className="text-gray-400 truncate">{n.name}</span>
                  <span className="text-gray-700 ml-auto capitalize text-xs">
                    {n.relationship?.toLowerCase().replace(/_/g, " ")}
                  </span>
                </div>
              ))}
            </section>
          )}

          {/* Context for Claude — copy button */}
          <section className="border-t border-gray-800 pt-3">
            <div className="flex items-center justify-between mb-1.5">
              <p className="text-gray-600 uppercase tracking-wider">Claude Context</p>
              <button
                onClick={copyContext}
                className="flex items-center gap-1 text-gray-600 hover:text-gray-300 transition-colors"
                title="Copy context for Claude"
              >
                {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
                <span className="text-xs">{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="text-gray-600 font-mono text-xs bg-gray-900 rounded p-2 leading-relaxed overflow-x-auto whitespace-pre-wrap">
              {data!.context_for_claude}
            </pre>
          </section>

        </div>
      )}
    </aside>
  );
}
