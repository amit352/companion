"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import AIChatInterface from "@/components/AIChatInterface/AIChatInterface";
import { QuickStart } from "@/components/QuickStart";
import { DocViewer } from "@/components/DocViewer";
import { ProjectSwitcher } from "@/components/ProjectSwitcher";
import { FileText, Loader2, History } from "lucide-react";

const FeatureExplorer = dynamic(
  () => import("@/components/FeatureExplorer/FeatureExplorer"),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-full text-gray-500 text-sm">Loading graph...</div> }
);

type View = "explorer" | "chat";
type DocType = "srs" | "readme" | "adr";

const DOC_LABELS: Record<DocType, string> = {
  srs:    "Software Requirements Spec",
  readme: "README",
  adr:    "Architecture Decision Record",
};

export default function Home() {
  const [view, setView]                   = useState<View>("explorer");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | null>(null);
  const [docContent, setDocContent]       = useState<string | null>(null);
  const [docType, setDocType]             = useState<DocType | null>(null);
  const [docLoading, setDocLoading]       = useState<DocType | null>(null);
  const [runs, setRuns]                   = useState<any[]>([]);

  // Load run history once
  useEffect(() => {
    fetch("http://localhost:8000/api/v1/analysis/runs")
      .then((r) => r.json())
      .then((d) => setRuns(d.runs ?? []))
      .catch(() => {});
  }, []);

  async function openDoc(type: DocType) {
    setDocLoading(type);
    try {
      // Fetch as markdown for the viewer
      const res = await fetch("http://localhost:8000/api/v1/docs/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_type: type, format: "markdown", repo_name: "SCiCustomer" }),
      });
      const text = await res.text();
      setDocContent(text);
      setDocType(type);
    } finally {
      setDocLoading(null);
    }
  }

  async function downloadDoc(format: "markdown" | "pdf" | "html" | "json" = "markdown") {
    if (!docType) return;
    const res = await fetch("http://localhost:8000/api/v1/docs/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ doc_type: docType, format, repo_name: "SCiCustomer" }),
    });
    const blob = await res.blob();
    const ext  = { markdown: "md", pdf: "pdf", html: "html", json: "json" }[format];
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${docType}.${ext}`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 flex flex-col p-4 gap-4">
        <div className="flex items-center gap-2 py-2">
          <span className="text-lg font-bold text-blue-400">Companion</span>
          <span className="text-xs text-gray-500 mt-1">v0.1</span>
        </div>

        <ProjectSwitcher />

        <nav className="flex flex-col gap-1">
          {(["explorer", "chat"] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-2 rounded text-left text-sm transition-colors ${
                view === v ? "bg-blue-600 text-white" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              {v === "explorer" ? "Feature Explorer" : "AI Chat"}
            </button>
          ))}
        </nav>

        {/* Run history */}
        {runs.length > 0 && (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-1.5 text-xs text-gray-600 uppercase tracking-wider">
              <History size={11} />
              Recent Analyses
            </div>
            {runs.slice(0, 5).map((r) => (
              <div key={r.id} className="px-2 py-1.5 rounded bg-gray-900 border border-gray-800">
                <p className="text-xs text-gray-300 font-medium truncate">{r.repo_name || "Unknown"}</p>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-xs text-gray-600">{r.features_out} features</span>
                  <span className="text-xs text-gray-700">
                    {r.completed_at ? new Date(r.completed_at).toLocaleDateString() : ""}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-auto flex flex-col gap-2">
          <p className="text-xs text-gray-600 uppercase tracking-wider">Generate Docs</p>
          {(Object.keys(DOC_LABELS) as DocType[]).map((t) => (
            <button
              key={t}
              onClick={() => openDoc(t)}
              disabled={!!docLoading}
              className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors disabled:opacity-50"
            >
              {docLoading === t
                ? <Loader2 size={13} className="animate-spin" />
                : <FileText size={13} />
              }
              {t.toUpperCase()}
            </button>
          ))}
          <div className="border-t border-gray-800 pt-2">
            <QuickStart />
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {view === "explorer" ? (
          <FeatureExplorer onFeatureSelect={setSelectedFeatureId} />
        ) : (
          <AIChatInterface featureId={selectedFeatureId} />
        )}
      </main>

      {/* Doc drawer */}
      {docContent && docType && (
        <DocViewer
          title={DOC_LABELS[docType]}
          content={docContent}
          onClose={() => { setDocContent(null); setDocType(null); }}
          onDownload={downloadDoc}
        />
      )}
    </div>
  );
}
