"use client";
import { FormEvent, useRef, useState } from "react";
import { Send } from "lucide-react";
import ReactMarkdown from "react-markdown";

const API = "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
  source?: "graph" | "llm";
}

const SUGGESTIONS = [
  "What breaks if auth changes?",
  "What breaks if Invoice Fee Calculation changes?",
  "List billing features",
  "List all features",
];

interface Props {
  featureId: string | null;
}

export default function AIChatInterface({ featureId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const append = (content: string, source?: "graph" | "llm") =>
    setMessages((m) => {
      const last = m[m.length - 1];
      if (last?.role === "assistant") {
        return [...m.slice(0, -1), { ...last, content, source }];
      }
      return [...m, { role: "assistant", content, source }];
    });

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;
    setInput("");
    setMessages((m) => [
      ...m,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/v1/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, feature_id: featureId }),
      });

      const contentType = res.headers.get("content-type") ?? "";

      if (contentType.includes("application/json")) {
        // Graph-native structured answer
        const data = await res.json();
        append(data.answer, "graph");
      } else {
        // LLM streaming answer
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) return;
        let full = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          full += decoder.decode(value);
          append(full, "llm");
          bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        }
      }
    } catch (e) {
      append("⚠ Could not reach the API. Make sure the server is running on port 8000.");
    } finally {
      setLoading(false);
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <p className="text-gray-500 text-sm">Ask anything about your codebase</p>
            <div className="grid grid-cols-2 gap-2 max-w-lg">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-left text-xs px-3 py-2 rounded border border-gray-700 text-gray-400 hover:border-blue-500 hover:text-blue-400 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-2xl rounded-lg text-sm ${
              msg.role === "user"
                ? "bg-blue-600 text-white px-4 py-2"
                : "bg-gray-800 text-gray-200 px-4 py-3"
            }`}>
              {msg.role === "assistant" ? (
                <>
                  {msg.content ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <span className="animate-pulse text-gray-500">Thinking…</span>
                  )}
                  {msg.source && (
                    <div className="mt-2 pt-2 border-t border-gray-700">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        msg.source === "graph"
                          ? "bg-green-900 text-green-300"
                          : "bg-purple-900 text-purple-300"
                      }`}>
                        {msg.source === "graph" ? "⬡ from graph" : "✦ from AI"}
                      </span>
                    </div>
                  )}
                </>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e: FormEvent) => { e.preventDefault(); sendMessage(input); }}
        className="p-4 border-t border-gray-800 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={featureId ? "Ask about selected feature…" : "Ask about your codebase…"}
          className="flex-1 bg-gray-800 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 outline-none focus:ring-1 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-3 py-2 bg-blue-600 rounded hover:bg-blue-500 disabled:opacity-50 transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
