"use client";
import { useEffect, useState } from "react";
import {
  X,
  Copy,
  Check,
  ChevronRight,
  Code2,
  ChevronDown,
  ExternalLink,
  Zap,
  GitMerge,
  Layers,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const API = "http://localhost:8000";

interface Props {
  featureId: string;
  onClose: () => void;
  onNodeFocus?: (id: string) => void;
}

interface FullFeature {
  feature:            Record<string, any>;
  dependencies:       any[];
  direct_dependents:  any[];
  level2_dependents:  any[];
  related_nodes:      any[];
  blast_radius:       number;
  context_for_claude: string;
}

// Maps domain → CSS token for the domain indicator dot
const DOMAIN_COLOR: Record<string, string> = {
  auth:     "var(--domain-auth)",
  billing:  "var(--domain-billing)",
  workflow: "var(--domain-workflow)",
  data:     "var(--domain-data)",
  api:      "var(--domain-api)",
  infra:    "var(--domain-infra)",
  unknown:  "var(--domain-unknown)",
};

const DOMAIN_BADGE_CLASS: Record<string, string> = {
  auth:     "badge badge-purple",
  billing:  "badge badge-green",
  workflow: "badge badge-amber",
  data:     "badge badge-blue",
  api:      "badge badge-cyan",
  infra:    "badge badge-gray",
  unknown:  "badge badge-gray",
};

const NODE_TYPE_ICON: Record<string, React.ReactNode> = {
  Service:        <Layers size={11} />,
  API:            <Zap size={11} />,
  DatabaseTable:  <span style={{ fontSize: 11 }}>▤</span>,
  UIComponent:    <span style={{ fontSize: 11 }}>▢</span>,
  Requirement:    <span style={{ fontSize: 11 }}>◉</span>,
  Feature:        <GitMerge size={11} />,
};

/* ── Section heading ──────────────────────────────────────────────────────── */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="label-section"
      style={{ marginBottom: "var(--space-2)", marginTop: 0 }}
    >
      {children}
    </p>
  );
}

/* ── Dependency / dependent row ──────────────────────────────────────────── */
function RelatedFeatureRow({
  name,
  domain,
  badge,
  badgeClass,
  accentVar,
  onClick,
}: {
  name: string;
  domain: string;
  badge?: string;
  badgeClass?: string;
  accentVar: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "var(--space-2)",
        width: "100%",
        padding: "var(--space-1) var(--space-2)",
        borderRadius: "var(--radius-md)",
        background: "transparent",
        border: "none",
        cursor: "pointer",
        textAlign: "left",
        color: accentVar,
        transition: "background var(--duration-fast)",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.background = "transparent";
      }}
    >
      <div
        style={{
          width: 6,
          height: 6,
          borderRadius: "var(--radius-full)",
          background: DOMAIN_COLOR[domain] ?? "var(--domain-unknown)",
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontSize: "var(--text-xs)",
          fontWeight: "var(--weight-medium)",
          flex: 1,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {name}
      </span>
      {badge && (
        <span className={badgeClass ?? "badge badge-gray"} style={{ flexShrink: 0 }}>
          {badge}
        </span>
      )}
      <ChevronRight size={11} style={{ opacity: 0.5, flexShrink: 0 }} />
    </button>
  );
}

/* ── Main component ──────────────────────────────────────────────────────── */
export function FeatureDetailPanel({ featureId, onClose, onNodeFocus }: Props) {
  const router = useRouter();
  const [data, setData]                 = useState<FullFeature | null>(null);
  const [loading, setLoading]           = useState(true);
  const [copied, setCopied]             = useState(false);
  const [showLevel2, setShowLevel2]     = useState(false);
  const [codeFile, setCodeFile]         = useState<string | null>(null);
  const [codeData, setCodeData]         = useState<{
    content: string;
    language: string;
    total_lines: number;
  } | null>(null);
  const [codeLoading, setCodeLoading]   = useState(false);

  async function loadCode(path: string) {
    if (codeFile === path) { setCodeFile(null); setCodeData(null); return; }
    setCodeFile(path);
    setCodeLoading(true);
    try {
      const res = await fetch(
        `${API}/api/v1/code/file?path=${encodeURIComponent(path)}&feature_id=${featureId}`
      );
      if (res.ok) setCodeData(await res.json());
    } catch { /* ignore */ }
    setCodeLoading(false);
  }

  useEffect(() => {
    setLoading(true);
    setShowLevel2(false);
    setCodeFile(null);
    setCodeData(null);
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
  const domainColor = f ? (DOMAIN_COLOR[f.domain] ?? "var(--domain-unknown)") : "var(--domain-unknown)";
  const domainBadgeClass = f ? (DOMAIN_BADGE_CLASS[f.domain] ?? "badge badge-gray") : "badge badge-gray";

  return (
    <aside className="detail-panel">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "var(--space-3)",
          padding: "var(--space-3) var(--space-3) var(--space-3) var(--space-4)",
          borderBottom: "1px solid var(--border-subtle)",
          flexShrink: 0,
        }}
      >
        {/* Domain accent bar */}
        <div
          style={{
            width: 3,
            alignSelf: "stretch",
            borderRadius: "var(--radius-full)",
            background: domainColor,
            flexShrink: 0,
            minHeight: 20,
            marginTop: 2,
          }}
        />

        <div style={{ flex: 1, minWidth: 0 }}>
          {loading || !f ? (
            <div
              style={{
                height: 18,
                width: "60%",
                borderRadius: "var(--radius-sm)",
                background: "var(--surface-overlay)",
                animation: "pulse 1.5s ease-in-out infinite",
              }}
            />
          ) : (
            <>
              <h2
                style={{
                  margin: 0,
                  fontSize: "var(--text-base)",
                  fontWeight: "var(--weight-semibold)",
                  color: "var(--text-primary)",
                  lineHeight: "var(--leading-tight)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {f.name}
              </h2>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-2)",
                  marginTop: "var(--space-1)",
                }}
              >
                <span className={domainBadgeClass}>{f.domain ?? "unknown"}</span>
                {f.node_type && (
                  <span className="badge badge-gray">{f.node_type}</span>
                )}
              </div>
            </>
          )}
        </div>

        {/* Header actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-1)", flexShrink: 0 }}>
          <button
            className="icon-btn"
            onClick={() => router.push(`/feature/${featureId}`)}
            title="Open full detail view"
          >
            <ExternalLink size={14} />
          </button>
          <button
            className="icon-btn"
            onClick={onClose}
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* ── Loading skeleton ────────────────────────────────────────── */}
      {loading && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-4)",
            padding: "var(--space-4)",
          }}
        >
          {[80, 100, 60, 90].map((w, i) => (
            <div
              key={i}
              style={{
                height: 12,
                width: `${w}%`,
                borderRadius: "var(--radius-sm)",
                background: "var(--surface-overlay)",
                opacity: 1 - i * 0.15,
              }}
            />
          ))}
        </div>
      )}

      {/* ── Content ─────────────────────────────────────────────────── */}
      {!loading && f && (
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "var(--space-4)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-5)",
          }}
        >
          {/* Description */}
          <section>
            <p
              style={{
                margin: 0,
                fontSize: "var(--text-sm)",
                color: "var(--text-secondary)",
                lineHeight: "var(--leading-loose)",
              }}
            >
              {f.description || (
                <span style={{ color: "var(--text-disabled)", fontStyle: "italic" }}>
                  No description available.
                </span>
              )}
            </p>
          </section>

          {/* Tags */}
          {f.tags?.length > 0 && (
            <section>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-1)" }}>
                {f.tags.map((t: string) => (
                  <span key={t} className="badge badge-gray">{t}</span>
                ))}
              </div>
            </section>
          )}

          {/* Confidence */}
          <section>
            <SectionLabel>Confidence</SectionLabel>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <div
                style={{
                  flex: 1,
                  height: 4,
                  borderRadius: "var(--radius-full)",
                  background: "var(--surface-overlay)",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    borderRadius: "var(--radius-full)",
                    width: `${(f.confidence ?? 1) * 100}%`,
                    background:
                      (f.confidence ?? 1) > 0.7
                        ? "var(--color-success)"
                        : (f.confidence ?? 1) > 0.4
                        ? "var(--color-warning)"
                        : "var(--color-danger)",
                    transition: "width var(--duration-slow) var(--ease-out)",
                  }}
                />
              </div>
              <span
                style={{
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--weight-semibold)",
                  color: "var(--text-secondary)",
                  fontFamily: "var(--font-mono)",
                  flexShrink: 0,
                }}
              >
                {Math.round((f.confidence ?? 1) * 100)}%
              </span>
            </div>
          </section>

          {/* Source files */}
          {f.source_files?.length > 0 && (
            <section>
              <SectionLabel>Source Files ({f.source_files.length})</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                {f.source_files.map((fp: string) => (
                  <div key={fp}>
                    <button
                      onClick={() => loadCode(fp)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--space-2)",
                        width: "100%",
                        padding: "var(--space-2) var(--space-2)",
                        borderRadius: "var(--radius-md)",
                        background:
                          codeFile === fp ? "var(--surface-active)" : "var(--surface-overlay)",
                        border: `1px solid ${codeFile === fp ? "var(--accent-blue)" : "var(--border-subtle)"}`,
                        cursor: "pointer",
                        textAlign: "left",
                        color: codeFile === fp ? "var(--accent-blue-text)" : "var(--text-secondary)",
                        transition: "background var(--duration-fast), border-color var(--duration-fast)",
                      }}
                    >
                      <Code2 size={12} style={{ flexShrink: 0 }} />
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "var(--text-2xs)",
                          flex: 1,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {fp}
                      </span>
                      <ChevronDown
                        size={11}
                        style={{
                          flexShrink: 0,
                          transition: "transform var(--duration-fast)",
                          transform: codeFile === fp ? "rotate(180deg)" : "rotate(0deg)",
                        }}
                      />
                    </button>

                    {/* Inline code viewer */}
                    {codeFile === fp && (
                      <div className="code-viewer" style={{ marginTop: "var(--space-1)" }}>
                        {codeLoading ? (
                          <div
                            style={{
                              padding: "var(--space-4)",
                              textAlign: "center",
                              color: "var(--text-disabled)",
                              fontSize: "var(--text-xs)",
                            }}
                          >
                            Loading…
                          </div>
                        ) : codeData ? (
                          <>
                            <div className="code-viewer-header">
                              <span>{codeData.language}</span>
                              <span>{codeData.total_lines} lines</span>
                            </div>
                            <SyntaxHighlighter
                              language={codeData.language}
                              style={vscDarkPlus}
                              customStyle={{
                                margin: 0,
                                padding: "var(--space-3)",
                                fontSize: "11px",
                                lineHeight: "1.55",
                                maxHeight: "380px",
                                overflow: "auto",
                                background: "var(--surface-sunken)",
                              }}
                              showLineNumbers
                              lineNumberStyle={{
                                color: "var(--text-disabled)",
                                fontSize: "10px",
                                paddingRight: "12px",
                                minWidth: "2.5em",
                              }}
                              wrapLines
                            >
                              {codeData.content}
                            </SyntaxHighlighter>
                          </>
                        ) : (
                          <div
                            style={{
                              padding: "var(--space-3)",
                              color: "var(--color-danger)",
                              fontSize: "var(--text-xs)",
                            }}
                          >
                            Could not load file.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Dependencies */}
          {data!.dependencies.length > 0 && (
            <section>
              <SectionLabel>
                Depends On ({data!.dependencies.length})
              </SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {data!.dependencies.map((d) => (
                  <RelatedFeatureRow
                    key={d.id}
                    name={d.name}
                    domain={d.domain}
                    accentVar="var(--text-secondary)"
                    onClick={() => onNodeFocus?.(d.id)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Impact / blast radius */}
          {(data!.direct_dependents.length > 0 || data!.level2_dependents.length > 0) && (
            <section>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "var(--space-2)",
                }}
              >
                <SectionLabel>Blast Radius</SectionLabel>
                <span
                  className="badge badge-amber"
                  title={`${data!.blast_radius} total dependents`}
                >
                  {data!.blast_radius} affected
                </span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {data!.direct_dependents.map((d) => (
                  <RelatedFeatureRow
                    key={d.id}
                    name={d.name}
                    domain={d.domain}
                    badge="L1"
                    badgeClass="badge badge-amber"
                    accentVar="var(--color-warning)"
                    onClick={() => onNodeFocus?.(d.id)}
                  />
                ))}

                {data!.level2_dependents.length > 0 && (
                  <>
                    <button
                      onClick={() => setShowLevel2(!showLevel2)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "var(--space-1)",
                        padding: "var(--space-1) var(--space-2)",
                        background: "transparent",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--text-tertiary)",
                        fontSize: "var(--text-xs)",
                        borderRadius: "var(--radius-sm)",
                        marginTop: "var(--space-1)",
                      }}
                    >
                      <ChevronRight
                        size={11}
                        style={{
                          transition: "transform var(--duration-fast)",
                          transform: showLevel2 ? "rotate(90deg)" : "rotate(0deg)",
                        }}
                      />
                      {showLevel2 ? "Hide" : "Show"} {data!.level2_dependents.length} indirect dependents
                    </button>

                    {showLevel2 &&
                      data!.level2_dependents.map((d) => (
                        <RelatedFeatureRow
                          key={d.id}
                          name={d.name}
                          domain={d.domain}
                          badge="L2"
                          badgeClass="badge badge-gray"
                          accentVar="var(--text-tertiary)"
                          onClick={() => onNodeFocus?.(d.id)}
                        />
                      ))}
                  </>
                )}
              </div>
            </section>
          )}

          {/* Related infrastructure */}
          {data!.related_nodes.length > 0 && (
            <section>
              <SectionLabel>Infrastructure ({data!.related_nodes.length})</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {data!.related_nodes.map((n, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "var(--space-2)",
                      padding: "var(--space-1) var(--space-2)",
                      borderRadius: "var(--radius-md)",
                    }}
                  >
                    <span style={{ color: "var(--text-tertiary)", flexShrink: 0, lineHeight: 1 }}>
                      {NODE_TYPE_ICON[n.type] ?? <span style={{ fontSize: 11 }}>○</span>}
                    </span>
                    <span
                      style={{
                        fontSize: "var(--text-xs)",
                        color: "var(--text-secondary)",
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {n.name}
                    </span>
                    {n.relationship && (
                      <span className="badge badge-gray" style={{ flexShrink: 0 }}>
                        {n.relationship.toLowerCase().replace(/_/g, " ")}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Claude context */}
          <section
            style={{
              borderTop: "1px solid var(--border-subtle)",
              paddingTop: "var(--space-4)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "var(--space-2)",
              }}
            >
              <SectionLabel>Claude Context</SectionLabel>
              <button
                onClick={copyContext}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-1)",
                  padding: "var(--space-1) var(--space-2)",
                  borderRadius: "var(--radius-md)",
                  background: copied ? "var(--color-success-muted)" : "var(--surface-overlay)",
                  border: `1px solid ${copied ? "var(--color-success)" : "var(--border-subtle)"}`,
                  cursor: "pointer",
                  color: copied ? "var(--color-success)" : "var(--text-secondary)",
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--weight-medium)",
                  transition: "all var(--duration-fast)",
                }}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                fontFamily: "var(--font-mono)",
                fontSize: "var(--text-2xs)",
                color: "var(--text-secondary)",
                background: "var(--surface-sunken)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "var(--space-3)",
                lineHeight: "var(--leading-loose)",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 200,
                overflowY: "auto",
              }}
            >
              {data!.context_for_claude}
            </pre>
          </section>
        </div>
      )}
    </aside>
  );
}
