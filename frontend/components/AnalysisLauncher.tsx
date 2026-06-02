"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { PlayCircle } from "lucide-react";

export function AnalysisLauncher() {
  const [repoPath, setRepoPath] = useState("");
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [jobId, setJobId] = useState<string | null>(null);

  const launch = async () => {
    if (!repoPath.trim()) return;
    setStatus("running");
    try {
      const res = await api.post("/api/v1/analysis/", {
        repo_path: repoPath,
        incremental: false,
      });
      setJobId(res.data.job_id);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 uppercase tracking-wider">Analyze Repo</p>
      <input
        value={repoPath}
        onChange={(e) => setRepoPath(e.target.value)}
        placeholder="/path/to/repo"
        className="w-full bg-gray-800 rounded px-2 py-1.5 text-xs text-gray-300 placeholder-gray-600 outline-none focus:ring-1 focus:ring-blue-500"
      />
      <button
        onClick={launch}
        disabled={status === "running" || !repoPath.trim()}
        className="w-full flex items-center justify-center gap-1 px-3 py-1.5 bg-blue-700 hover:bg-blue-600 disabled:opacity-50 rounded text-xs transition-colors"
      >
        <PlayCircle size={14} />
        {status === "running" ? "Analyzing..." : "Run Analysis"}
      </button>
      {jobId && status === "done" && (
        <p className="text-xs text-green-500 truncate">Job: {jobId.slice(0, 8)}...</p>
      )}
      {status === "error" && (
        <p className="text-xs text-red-400">Analysis failed</p>
      )}
    </div>
  );
}
