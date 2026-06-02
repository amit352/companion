"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import AIChatInterface from "@/components/AIChatInterface/AIChatInterface";
import { QuickStart } from "@/components/QuickStart";
import { DocViewer } from "@/components/DocViewer";
import { ProjectSwitcher } from "@/components/ProjectSwitcher";
import {
  FileText,
  Loader2,
  History,
  GitBranch,
  MessageSquare,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

const FeatureExplorer = dynamic(
  () => import("@/components/FeatureExplorer/FeatureExplorer"),
  {
    ssr: false,
    loading: () => (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <div
          className="w-8 h-8 rounded-full border-2 animate-spin"
          style={{
            borderColor: "var(--border-default)",
            borderTopColor: "var(--accent-blue)",
          }}
        />
        <span style={{ color: "var(--text-tertiary)", fontSize: "var(--text-xs)" }}>
          Loading graph…
        </span>
      </div>
    ),
  }
);

type View = "explorer" | "chat";
type DocType = "srs" | "readme" | "adr";

const DOC_LABELS: Record<DocType, string> = {
  srs:    "Software Requirements",
  readme: "README",
  adr:    "Architecture Decision",
};

const NAV_ITEMS: { id: View; label: string; icon: React.ReactNode }[] = [
  {
    id: "explorer",
    label: "Feature Explorer",
    icon: <GitBranch size={15} />,
  },
  {
    id: "chat",
    label: "AI Chat",
    icon: <MessageSquare size={15} />,
  },
];

export default function Home() {
  const [view, setView]                         = useState<View>("explorer");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | null>(null);
  const [docContent, setDocContent]             = useState<string | null>(null);
  const [docType, setDocType]                   = useState<DocType | null>(null);
  const [docLoading, setDocLoading]             = useState<DocType | null>(null);
  const [runs, setRuns]                         = useState<any[]>([]);
  const [runsExpanded, setRunsExpanded]         = useState(false);
  const [docsExpanded, setDocsExpanded]         = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/analysis/runs")
      .then((r) => r.json())
      .then((d) => setRuns(d.runs ?? []))
      .catch(() => {});
  }, []);

  async function openDoc(type: DocType) {
    setDocLoading(type);
    try {
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
    <div className="app-shell">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="app-sidebar">

        {/* Logo + version */}
        <div
          style={{
            padding: "var(--space-4) var(--space-4) var(--space-3)",
            borderBottom: "1px solid var(--border-subtle)",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            {/* Logo mark */}
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, var(--accent-blue), var(--color-purple))",
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <GitBranch size={13} color="#fff" />
            </div>
            <span
              style={{
                fontSize: "var(--text-md)",
                fontWeight: "var(--weight-semibold)",
                color: "var(--text-primary)",
                letterSpacing: "-0.02em",
              }}
            >
              Companion
            </span>
            <span
              style={{
                marginLeft: "auto",
                fontSize: "var(--text-2xs)",
                color: "var(--text-disabled)",
                fontFamily: "var(--font-mono)",
              }}
            >
              v0.1
            </span>
          </div>
        </div>

        {/* Project switcher */}
        <div
          style={{
            padding: "var(--space-3) var(--space-3)",
            borderBottom: "1px solid var(--border-subtle)",
            flexShrink: 0,
          }}
        >
          <ProjectSwitcher />
        </div>

        {/* Primary navigation */}
        <nav
          style={{
            padding: "var(--space-2) var(--space-2)",
            flexShrink: 0,
          }}
        >
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`sidebar-nav-item ${view === item.id ? "active" : ""}`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Scrollable lower section */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-1)",
          }}
        >
          {/* Run history — collapsible */}
          {runs.length > 0 && (
            <div
              style={{
                borderTop: "1px solid var(--border-subtle)",
                padding: "var(--space-2) var(--space-2)",
              }}
            >
              <button
                onClick={() => setRunsExpanded(!runsExpanded)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-1)",
                  width: "100%",
                  padding: "var(--space-1) var(--space-2)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "var(--text-tertiary)",
                  borderRadius: "var(--radius-sm)",
                }}
              >
                <History size={11} />
                <span className="label-section" style={{ flex: 1, textAlign: "left" }}>
                  Recent Analyses
                </span>
                <span
                  style={{
                    fontSize: "var(--text-2xs)",
                    background: "var(--surface-overlay)",
                    color: "var(--text-secondary)",
                    borderRadius: "var(--radius-full)",
                    padding: "0 6px",
                    lineHeight: "18px",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  {runs.length}
                </span>
                {runsExpanded
                  ? <ChevronDown size={11} />
                  : <ChevronRight size={11} />
                }
              </button>

              {runsExpanded && (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "var(--space-1)",
                    marginTop: "var(--space-1)",
                    padding: "0 var(--space-1)",
                  }}
                >
                  {runs.slice(0, 5).map((r) => (
                    <div
                      key={r.id}
                      style={{
                        padding: "var(--space-2) var(--space-3)",
                        borderRadius: "var(--radius-md)",
                        background: "var(--surface-overlay)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <p
                        style={{
                          fontSize: "var(--text-xs)",
                          fontWeight: "var(--weight-medium)",
                          color: "var(--text-secondary)",
                          margin: 0,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {r.repo_name || "Unknown"}
                      </p>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginTop: "var(--space-1)",
                        }}
                      >
                        <span className="badge badge-blue">{r.features_out} features</span>
                        <span
                          style={{
                            fontSize: "var(--text-2xs)",
                            color: "var(--text-disabled)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {r.completed_at
                            ? new Date(r.completed_at).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                              })
                            : ""}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bottom tools section */}
        <div
          style={{
            borderTop: "1px solid var(--border-subtle)",
            padding: "var(--space-2) var(--space-2)",
            flexShrink: 0,
          }}
        >
          {/* Generate Docs — collapsible */}
          <button
            onClick={() => setDocsExpanded(!docsExpanded)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-1)",
              width: "100%",
              padding: "var(--space-1) var(--space-2)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "var(--text-tertiary)",
              borderRadius: "var(--radius-sm)",
              marginBottom: "var(--space-1)",
            }}
          >
            <FileText size={11} />
            <span className="label-section" style={{ flex: 1, textAlign: "left" }}>
              Generate Docs
            </span>
            {docsExpanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </button>

          {docsExpanded && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "var(--space-1)",
                paddingBottom: "var(--space-1)",
              }}
            >
              {(Object.keys(DOC_LABELS) as DocType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => openDoc(t)}
                  disabled={!!docLoading}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--space-2)",
                    padding: "var(--space-2) var(--space-3)",
                    borderRadius: "var(--radius-md)",
                    background: "transparent",
                    border: "1px solid transparent",
                    cursor: docLoading ? "not-allowed" : "pointer",
                    opacity: docLoading && docLoading !== t ? 0.5 : 1,
                    transition: "background var(--duration-fast), border-color var(--duration-fast)",
                    textAlign: "left",
                    width: "100%",
                    color:
                      docLoading === t
                        ? "var(--accent-blue-text)"
                        : "var(--text-secondary)",
                  }}
                  onMouseEnter={(e) => {
                    if (!docLoading) {
                      (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)";
                      (e.currentTarget as HTMLElement).style.borderColor = "var(--border-subtle)";
                      (e.currentTarget as HTMLElement).style.color = "var(--text-primary)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = "transparent";
                    (e.currentTarget as HTMLElement).style.borderColor = "transparent";
                    (e.currentTarget as HTMLElement).style.color =
                      docLoading === t ? "var(--accent-blue-text)" : "var(--text-secondary)";
                  }}
                >
                  {docLoading === t ? (
                    <Loader2 size={13} className="animate-spin" style={{ color: "var(--accent-blue)" }} />
                  ) : (
                    <FileText size={13} style={{ color: "var(--text-disabled)" }} />
                  )}
                  <span style={{ fontSize: "var(--text-xs)", fontWeight: "var(--weight-medium)" }}>
                    {DOC_LABELS[t]}
                  </span>
                  {docLoading === t && (
                    <span
                      style={{
                        marginLeft: "auto",
                        fontSize: "var(--text-2xs)",
                        color: "var(--accent-blue-text)",
                      }}
                    >
                      Generating…
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-2)" }}>
            <QuickStart />
          </div>
        </div>
      </aside>

      {/* ── Main workspace ──────────────────────────────────────────── */}
      <main className="app-main">
        {view === "explorer" ? (
          <FeatureExplorer onFeatureSelect={setSelectedFeatureId} />
        ) : (
          <AIChatInterface featureId={selectedFeatureId} />
        )}
      </main>

      {/* ── Doc drawer ──────────────────────────────────────────────── */}
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
