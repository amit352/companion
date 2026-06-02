"use client";
import { useState } from "react";
import { Check, Copy, Terminal, ChevronDown, ChevronUp } from "lucide-react";

interface Props {
  onManualIngest?: () => void;
}

export function QuickStart({ onManualIngest }: Props) {
  const [copied, setCopied]       = useState(false);
  const [showAlt, setShowAlt]     = useState(false);
  const [repoPath, setRepoPath]   = useState("");
  const [status, setStatus]       = useState<"idle" | "running" | "done" | "error">("idle");

  const CMD = "/companion <repo-path>";

  function copyCmd() {
    navigator.clipboard.writeText(CMD);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  async function runStandalone() {
    if (!repoPath.trim()) return;
    setStatus("running");
    try {
      const res = await fetch("http://localhost:8000/api/v1/analysis/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_path: repoPath, incremental: false }),
      });
      if (res.ok) { setStatus("done"); onManualIngest?.(); }
      else setStatus("error");
    } catch { setStatus("error"); }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Primary: Claude Code command */}
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Analyze Repo</p>
        <div className="bg-gray-900 border border-gray-700 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-2 leading-relaxed">
            Run in Claude Code — no API key needed:
          </p>
          <div className="flex items-center gap-2 bg-gray-800 rounded px-2.5 py-1.5">
            <Terminal size={11} className="text-blue-400 flex-shrink-0" />
            <code className="text-xs text-blue-300 flex-1 select-all">{CMD}</code>
            <button
              onClick={copyCmd}
              className="text-gray-500 hover:text-gray-200 transition-colors flex-shrink-0"
              title="Copy"
            >
              {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            </button>
          </div>
        </div>
      </div>

      {/* Secondary: standalone pipeline (collapsed) */}
      <button
        onClick={() => setShowAlt(!showAlt)}
        className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-gray-400 transition-colors"
      >
        {showAlt ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        Use API key instead
      </button>

      {showAlt && (
        <div className="flex flex-col gap-1.5">
          <input
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="/path/to/repo"
            className="bg-gray-800 rounded px-2.5 py-1.5 text-xs text-gray-300 placeholder-gray-600 outline-none focus:ring-1 focus:ring-gray-600"
          />
          <button
            onClick={runStandalone}
            disabled={status === "running" || !repoPath.trim()}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded text-xs text-gray-300 transition-colors"
          >
            {status === "running" ? "Analyzing…" : status === "done" ? "✓ Done" : "Run Analysis"}
          </button>
          {status === "error" && (
            <p className="text-xs text-red-400">Failed — check API key or path</p>
          )}
        </div>
      )}
    </div>
  );
}
