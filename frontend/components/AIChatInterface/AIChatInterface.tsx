"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Send, ThumbsUp, ThumbsDown, MessageSquare, X } from "lucide-react";
import ReactMarkdown from "react-markdown";

const API = "http://localhost:8000";

interface Message {
  role:      "user" | "assistant";
  content:   string;
  source?:   "graph" | "llm";
  question?: string;
  rated?:    "up" | "down";
  streaming?: boolean;
}

interface FeatureContext {
  id:   string;
  name: string;
}

interface Props {
  featureId: string | null;
}

const SUGGESTIONS = [
  "What breaks if auth changes?",
  "What breaks if Invoice Fee Calculation changes?",
  "List all billing features",
  "Which features have the highest blast radius?",
];

// Fetches the feature name so we can display it in the context chip.
// We cache the result to avoid duplicate requests.
const nameCache = new Map<string, string>();

async function resolveFeatureName(id: string): Promise<string> {
  if (nameCache.has(id)) return nameCache.get(id)!;
  try {
    const res  = await fetch(`${API}/api/v1/features/${id}/full`);
    const data = await res.json();
    const name = data?.feature?.name ?? id;
    nameCache.set(id, name);
    return name;
  } catch {
    return id;
  }
}

export default function AIChatInterface({ featureId }: Props) {
  const [messages, setMessages]             = useState<Message[]>([]);
  const [input, setInput]                   = useState("");
  const [loading, setLoading]               = useState(false);
  const [featureCtx, setFeatureCtx]         = useState<FeatureContext | null>(null);
  const bottomRef                           = useRef<HTMLDivElement>(null);
  const inputRef                            = useRef<HTMLInputElement>(null);

  // Resolve feature name whenever featureId changes
  useEffect(() => {
    if (!featureId) { setFeatureCtx(null); return; }
    resolveFeatureName(featureId).then((name) => setFeatureCtx({ id: featureId, name }));
  }, [featureId]);

  function scrollToBottom(smooth = true) {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "instant" });
  }

  function append(content: string, source?: "graph" | "llm", question?: string, streaming = false) {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant") {
        return [
          ...prev.slice(0, -1),
          { ...last, content, source, question: question ?? last.question, streaming },
        ];
      }
      return [...prev, { role: "assistant", content, source, question, streaming }];
    });
  }

  async function rateFeedback(msg: Message, verdict: "up" | "down") {
    setMessages((prev) => prev.map((x) => (x === msg ? { ...x, rated: verdict } : x)));
    await fetch(`${API}/api/v1/chat/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: msg.question ?? "",
        answer:   msg.content,
        source:   msg.source ?? "graph",
        verdict:  verdict === "up" ? "correct" : "wrong",
      }),
    }).catch(() => {});
  }

  async function sendMessage(question: string) {
    if (!question.trim() || loading) return;
    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user",      content: question },
      { role: "assistant", content: "", question, streaming: true },
    ]);
    setLoading(true);
    scrollToBottom();

    try {
      const res = await fetch(`${API}/api/v1/chat/`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ question, feature_id: featureId }),
      });

      const contentType = res.headers.get("content-type") ?? "";

      if (contentType.includes("application/json")) {
        const data = await res.json();
        append(data.answer, "graph", question, false);
      } else {
        const reader  = res.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) return;
        let full = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          full += decoder.decode(value);
          append(full, "llm", question, true);
          scrollToBottom();
        }
        append(full, "llm", question, false);
      }
    } catch {
      append(
        "Could not reach the API. Make sure the server is running on port 8000.",
        undefined,
        question,
        false
      );
    } finally {
      setLoading(false);
      scrollToBottom();
      inputRef.current?.focus();
    }
  }

  const showSuggestions = messages.length === 0;

  return (
    <div
      style={{
        display:       "flex",
        flexDirection: "column",
        height:        "100%",
        background:    "var(--surface-base)",
      }}
    >
      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div
        style={{
          display:       "flex",
          alignItems:    "center",
          gap:           "var(--space-3)",
          padding:       "0 var(--space-4)",
          height:        40,
          borderBottom:  "1px solid var(--border-subtle)",
          flexShrink:    0,
          background:    "var(--surface-raised)",
        }}
      >
        <MessageSquare size={14} style={{ color: "var(--text-tertiary)" }} />
        <span
          style={{
            fontSize:   "var(--text-xs)",
            fontWeight: "var(--weight-semibold)",
            color:      "var(--text-secondary)",
            letterSpacing: "0.01em",
          }}
        >
          AI Chat
        </span>

        {/* Feature context chip */}
        {featureCtx && (
          <div
            style={{
              display:     "flex",
              alignItems:  "center",
              gap:         "var(--space-1)",
              marginLeft:  "var(--space-2)",
              padding:     "2px 6px 2px 8px",
              borderRadius: "var(--radius-full)",
              background:  "var(--accent-blue-muted)",
              border:      "1px solid rgba(59,130,246,0.25)",
              color:       "var(--accent-blue-text)",
              fontSize:    "var(--text-2xs)",
              fontWeight:  "var(--weight-medium)",
            }}
          >
            <span
              style={{
                width:        5,
                height:       5,
                borderRadius: "var(--radius-full)",
                background:   "var(--accent-blue)",
                flexShrink:   0,
              }}
            />
            Context: {featureCtx.name}
            <button
              onClick={() => setFeatureCtx(null)}
              style={{
                marginLeft:  "var(--space-1)",
                background:  "transparent",
                border:      "none",
                cursor:      "pointer",
                color:       "inherit",
                opacity:     0.7,
                padding:     0,
                lineHeight:  1,
                display:     "flex",
              }}
              title="Clear context"
            >
              <X size={10} />
            </button>
          </div>
        )}

        {/* Message count badge */}
        {messages.length > 0 && (
          <span
            className="badge badge-gray"
            style={{ marginLeft: "auto" }}
          >
            {Math.floor(messages.length / 2)} turn{messages.length / 2 !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* ── Message list ────────────────────────────────────────────── */}
      <div
        style={{
          flex:      1,
          overflowY: "auto",
          padding:   "var(--space-6) var(--space-6)",
          display:   "flex",
          flexDirection: "column",
          gap:       "var(--space-4)",
        }}
      >
        {/* Empty state */}
        {showSuggestions && (
          <div
            style={{
              display:        "flex",
              flexDirection:  "column",
              alignItems:     "center",
              justifyContent: "center",
              flex:           1,
              gap:            "var(--space-6)",
              paddingBottom:  "var(--space-8)",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  width:        40,
                  height:       40,
                  borderRadius: "var(--radius-xl)",
                  background:   "var(--surface-overlay)",
                  border:       "1px solid var(--border-default)",
                  display:      "flex",
                  alignItems:   "center",
                  justifyContent: "center",
                  margin:       "0 auto var(--space-3)",
                }}
              >
                <MessageSquare size={18} style={{ color: "var(--text-tertiary)" }} />
              </div>
              <p
                style={{
                  margin:     0,
                  fontSize:   "var(--text-base)",
                  fontWeight: "var(--weight-semibold)",
                  color:      "var(--text-secondary)",
                }}
              >
                Ask anything about your codebase
              </p>
              <p
                style={{
                  margin:   "var(--space-1) 0 0",
                  fontSize: "var(--text-xs)",
                  color:    "var(--text-tertiary)",
                }}
              >
                {featureCtx
                  ? `Currently scoped to: ${featureCtx.name}`
                  : "Select a feature in the graph to scope your question"}
              </p>
            </div>

            {/* Suggestion chips */}
            <div
              style={{
                display:             "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap:                 "var(--space-2)",
                maxWidth:            480,
                width:               "100%",
              }}
            >
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  style={{
                    textAlign:    "left",
                    padding:      "var(--space-3)",
                    borderRadius: "var(--radius-lg)",
                    background:   "var(--surface-overlay)",
                    border:       "1px solid var(--border-default)",
                    cursor:       "pointer",
                    color:        "var(--text-secondary)",
                    fontSize:     "var(--text-xs)",
                    fontWeight:   "var(--weight-medium)",
                    lineHeight:   "var(--leading-normal)",
                    transition:   "background var(--duration-fast), border-color var(--duration-fast), color var(--duration-fast)",
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.background    = "var(--surface-hover)";
                    el.style.borderColor   = "var(--accent-blue)";
                    el.style.color         = "var(--text-primary)";
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLElement;
                    el.style.background    = "var(--surface-overlay)";
                    el.style.borderColor   = "var(--border-default)";
                    el.style.color         = "var(--text-secondary)";
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display:        "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            }}
          >
            {msg.role === "user" ? (
              <div className="chat-bubble-user">{msg.content}</div>
            ) : (
              <div className="chat-bubble-assistant">
                {msg.content ? (
                  <div className={`companion-prose${msg.streaming ? " streaming-cursor" : ""}`}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  /* Thinking placeholder */
                  <div
                    style={{
                      display:    "flex",
                      gap:        "var(--space-1)",
                      alignItems: "center",
                      padding:    "var(--space-1) 0",
                    }}
                  >
                    {[0, 0.15, 0.3].map((delay, di) => (
                      <div
                        key={di}
                        style={{
                          width:            6,
                          height:           6,
                          borderRadius:     "var(--radius-full)",
                          background:       "var(--text-disabled)",
                          animation:        `bounce 1.2s ease-in-out ${delay}s infinite`,
                        }}
                      />
                    ))}
                  </div>
                )}

                {/* Source + feedback row */}
                {msg.source && msg.content && !msg.streaming && (
                  <div
                    style={{
                      display:        "flex",
                      alignItems:     "center",
                      justifyContent: "space-between",
                      marginTop:      "var(--space-3)",
                      paddingTop:     "var(--space-2)",
                      borderTop:      "1px solid var(--border-subtle)",
                    }}
                  >
                    <span
                      className={
                        msg.source === "graph"
                          ? "badge badge-green"
                          : "badge badge-purple"
                      }
                    >
                      {msg.source === "graph" ? "From graph" : "From AI"}
                    </span>

                    <div style={{ display: "flex", gap: "var(--space-1)" }}>
                      <button
                        className="icon-btn"
                        onClick={() => rateFeedback(msg, "up")}
                        title="Correct"
                        style={
                          msg.rated === "up"
                            ? { color: "var(--color-success)" }
                            : {}
                        }
                      >
                        <ThumbsUp size={12} />
                      </button>
                      <button
                        className="icon-btn"
                        onClick={() => rateFeedback(msg, "down")}
                        title="Wrong"
                        style={
                          msg.rated === "down"
                            ? { color: "var(--color-danger)" }
                            : {}
                        }
                      >
                        <ThumbsDown size={12} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} style={{ height: 1 }} />
      </div>

      {/* ── Input bar ───────────────────────────────────────────────── */}
      <form
        onSubmit={(e: FormEvent) => { e.preventDefault(); sendMessage(input); }}
        style={{
          display:      "flex",
          gap:          "var(--space-2)",
          padding:      "var(--space-3) var(--space-4)",
          borderTop:    "1px solid var(--border-subtle)",
          flexShrink:   0,
          background:   "var(--surface-raised)",
          alignItems:   "flex-end",
        }}
      >
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            featureCtx
              ? `Ask about ${featureCtx.name}…`
              : "Ask about your codebase…"
          }
          className="chat-input"
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            display:        "flex",
            alignItems:     "center",
            justifyContent: "center",
            width:          38,
            height:         38,
            flexShrink:     0,
            borderRadius:   "var(--radius-md)",
            background:     loading || !input.trim()
              ? "var(--surface-overlay)"
              : "var(--accent-blue)",
            border:         "none",
            cursor:         loading || !input.trim() ? "not-allowed" : "pointer",
            color:          loading || !input.trim()
              ? "var(--text-disabled)"
              : "#fff",
            transition:     "background var(--duration-fast), color var(--duration-fast)",
          }}
        >
          <Send size={15} />
        </button>
      </form>

      {/* Bounce animation for thinking dots */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
