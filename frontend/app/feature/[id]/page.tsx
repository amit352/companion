"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { ArrowLeft, Code2, GitBranch, Shield, AlertTriangle, CornerDownRight } from "lucide-react";
import { HierarchyPanel } from "@/components/HierarchyPanel";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const API = "http://localhost:8000";

// Lazy-load ReactFlow for the mini sub-graph
const SubGraph = dynamic(() => import("./SubGraph"), { ssr: false,
  loading: () => <div className="h-64 bg-gray-900 rounded-lg animate-pulse" /> });

const RULE_ICONS: Record<string, any> = {
  condition: Shield, error: AlertTriangle, return: CornerDownRight,
};
const RULE_COLORS: Record<string, string> = {
  condition: "text-blue-400", error: "text-red-400", return: "text-green-400",
};

export default function FeatureDetailPage() {
  const { id }   = useParams() as { id: string };
  const router   = useRouter();
  const [full, setFull]           = useState<any>(null);
  const [atoms, setAtoms]         = useState<any>(null);
  const [code, setCode]           = useState<Record<string, any>>({});
  const [openFile, setOpenFile]   = useState<string | null>(null);
  const [highlightLine, setHighlightLine] = useState<number | null>(null);
  const codeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetch(`${API}/api/v1/features/${id}/full`).then((r) => r.json()),
      fetch(`${API}/api/v1/analysis/feature/${id}/atoms`).then((r) => r.json()),
    ]).then(([f, a]) => { setFull(f); setAtoms(a); });
  }, [id]);

  async function loadFile(path: string, jumpToLine?: number) {
    if (!code[path]) {
      const res = await fetch(`${API}/api/v1/code/file?path=${encodeURIComponent(path)}&feature_id=${id}`);
      if (res.ok) {
        const data = await res.json();
        setCode((c) => ({ ...c, [path]: data }));
      }
    }
    setOpenFile(path);
    if (jumpToLine) {
      setHighlightLine(jumpToLine);
      // Scroll to highlighted line after render
      setTimeout(() => {
        const el = codeRef.current?.querySelector(`[data-line="${jumpToLine}"]`);
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 200);
    }
  }

  const f = full?.feature;
  if (!f) return (
    <div className="h-screen bg-gray-950 flex items-center justify-center text-gray-500">
      Loading…
    </div>
  );

  const DOMAIN_COLOR: Record<string, string> = {
    auth: "#8b5cf6", billing: "#10b981", workflow: "#f59e0b",
    data: "#3b82f6", api: "#06b6d4", unknown: "#4b5563",
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Top bar */}
      <div className="border-b border-gray-800 px-6 py-3 flex items-center gap-3 sticky top-0 bg-gray-950/95 backdrop-blur z-10">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-gray-400 hover:text-gray-200 text-sm transition-colors"
        >
          <ArrowLeft size={15} /> Back
        </button>
        <div className="h-4 w-px bg-gray-700" />
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{ background: DOMAIN_COLOR[f.domain] ?? "#4b5563" }}
        />
        <h1 className="font-semibold text-gray-100">{f.name}</h1>
        <span className="text-xs text-gray-600 capitalize bg-gray-800 px-2 py-0.5 rounded">
          {f.domain}
        </span>
        <span className="text-xs text-gray-600 ml-auto">
          {Math.round((f.confidence ?? 1) * 100)}% confidence
        </span>
      </div>

      <div className="flex h-[calc(100vh-52px)]">
      {/* Hierarchy panel — right side */}
      <HierarchyPanel featureId={id} />

      {/* Main content — scrollable */}
      <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-6 grid grid-cols-3 gap-6">

        {/* LEFT: Feature overview + sub-graph */}
        <div className="col-span-1 space-y-4">

          {/* Description */}
          <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
            <p className="text-gray-300 text-sm leading-relaxed">{f.description}</p>
            {f.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {f.tags.map((t: string) => (
                  <span key={t} className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded">{t}</span>
                ))}
              </div>
            )}
          </div>

          {/* Sub-graph */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-gray-800 flex items-center gap-2">
              <GitBranch size={13} className="text-gray-500" />
              <span className="text-xs font-medium text-gray-400">Dependency Graph</span>
            </div>
            <div className="h-64">
              {full && <SubGraph featureId={id} full={full} />}
            </div>
          </div>

          {/* Dependencies */}
          {full?.dependencies?.length > 0 && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <p className="text-xs text-gray-600 uppercase tracking-wider mb-2">Depends On</p>
              {full.dependencies.map((d: any) => (
                <a key={d.id} href={`/feature/${d.id}`}
                  className="flex items-center gap-2 py-1 text-xs text-gray-300 hover:text-blue-400 transition-colors">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                  {d.name}
                </a>
              ))}
            </div>
          )}

          {/* Impact */}
          {full?.direct_dependents?.length > 0 && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <p className="text-xs text-gray-600 uppercase tracking-wider mb-2">
                Used By ({full.blast_radius})
              </p>
              {full.direct_dependents.map((d: any) => (
                <a key={d.id} href={`/feature/${d.id}`}
                  className="flex items-center gap-2 py-1 text-xs text-orange-400 hover:text-orange-300 transition-colors">
                  <div className="w-1.5 h-1.5 rounded-full bg-orange-600" />
                  {d.name}
                </a>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT: Code + Business Logic */}
        <div className="col-span-2 space-y-4">

          {/* Business rules summary */}
          {atoms?.business_rules?.length > 0 && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={14} className="text-blue-400" />
                <h2 className="text-sm font-semibold text-gray-200">
                  Business Rules ({atoms.rule_count})
                </h2>
                <span className="text-xs text-gray-600 ml-auto">
                  {atoms.function_count} functions analyzed
                </span>
              </div>
              <div className="space-y-1.5">
                {atoms.business_rules.slice(0, 20).map((rule: any, i: number) => {
                  const Icon = RULE_ICONS[rule.rule_type] ?? Shield;
                  const color = RULE_COLORS[rule.rule_type] ?? "text-gray-400";
                  const isHighlighted = openFile === rule.file && highlightLine === rule.line;
                  return (
                    <button
                      key={i}
                      onClick={() => rule.file && loadFile(rule.file, rule.line)}
                      className={`flex items-start gap-2 py-1.5 px-2 rounded w-full text-left transition-colors ${
                        isHighlighted
                          ? "bg-yellow-900/30 border border-yellow-700/50"
                          : "hover:bg-gray-800"
                      }`}
                      title={rule.file ? `Jump to line ${rule.line} in ${rule.file}` : ""}
                    >
                      <Icon size={12} className={`${color} mt-0.5 flex-shrink-0`} />
                      <div className="min-w-0 flex-1">
                        <span className="text-xs text-gray-500 mr-2">{rule.function}</span>
                        <code className={`text-xs ${color} font-mono break-all`}>
                          {rule.description}
                        </code>
                      </div>
                      {rule.line > 0 && (
                        <span className="text-xs text-gray-700 flex-shrink-0">L{rule.line}</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Source files with code */}
          {f.source_files?.map((fp: string) => (
            <div key={fp} className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <button
                onClick={() => loadFile(fp)}
                className="w-full flex items-center gap-2 px-4 py-3 hover:bg-gray-800 transition-colors text-left"
              >
                <Code2 size={13} className="text-gray-500 flex-shrink-0" />
                <span className="text-sm text-gray-300 font-mono">{fp}</span>
                <span className="ml-auto text-xs text-gray-600">
                  {openFile === fp ? "▲ collapse" : "▼ view code"}
                </span>
              </button>

              {openFile === fp && (
                code[fp] ? (
                  <div ref={codeRef}>
                    <SyntaxHighlighter
                      language={code[fp].language}
                      style={vscDarkPlus}
                      customStyle={{
                        margin: 0, padding: "16px", fontSize: "12px",
                        lineHeight: "1.6", maxHeight: "600px",
                        overflow: "auto", background: "#0d1117",
                      }}
                      showLineNumbers
                      lineNumberStyle={{ color: "#3d4451", fontSize: "10px" }}
                      wrapLines
                      lineProps={(lineNumber) => {
                        const isHL = highlightLine === lineNumber;
                        return {
                          "data-line": lineNumber,
                          style: isHL ? {
                            backgroundColor: "rgba(250, 204, 21, 0.12)",
                            borderLeft: "3px solid #fbbf24",
                            display: "block",
                            marginLeft: "-16px",
                            paddingLeft: "13px",
                          } : { display: "block" },
                        } as any;
                      }}
                    >
                      {code[fp].content}
                    </SyntaxHighlighter>
                  </div>
                ) : (
                  <div className="h-12 flex items-center justify-center text-gray-600 text-xs">
                    Loading code…
                  </div>
                )
              )}

              {/* Functions from this file */}
              {atoms?.functions?.filter((a: any) => a.file === fp).map((fn: any) => (
                <div key={`${fn.file}-${fn.name}-${fn.line}`}
                  className="px-4 py-2 border-t border-gray-800/50">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-blue-400 font-mono font-medium">{fn.name}</span>
                    {fn.params.length > 0 && (
                      <span className="text-xs text-gray-600">({fn.params.join(", ")})</span>
                    )}
                    <span className="text-xs text-gray-700 ml-auto">L{fn.line}</span>
                  </div>
                  {fn.docstring && (
                    <p className="text-xs text-gray-500 mt-0.5 italic">{fn.docstring.split("\n")[0]}</p>
                  )}
                  {fn.conditions.length > 0 && (
                    <div className="mt-1 space-y-0.5">
                      {fn.conditions.slice(0, 5).map((c: any, ci: number) => {
                        const color = RULE_COLORS[c.type] ?? "text-gray-500";
                        return (
                          <div key={ci} className="flex items-center gap-1.5">
                            <div className={`w-1 h-1 rounded-full ${
                              c.type === "error" ? "bg-red-600" :
                              c.type === "return" ? "bg-green-600" : "bg-blue-600"
                            }`} />
                            <code className={`text-xs font-mono ${color}`}>{c.text}</code>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
      </div>
      </div>
    </div>
  );
}
