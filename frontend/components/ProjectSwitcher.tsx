"use client";
import { useState } from "react";
import { ChevronDown, FolderOpen, Globe } from "lucide-react";
import { useProject } from "@/lib/projectContext";

export function ProjectSwitcher() {
  const { repos, selectedRepo, selectRepo } = useProject();
  const [open, setOpen] = useState(false);

  if (!repos.length) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-left hover:border-gray-600 transition-colors"
      >
        {selectedRepo ? (
          <FolderOpen size={13} className="text-blue-400 flex-shrink-0" />
        ) : (
          <Globe size={13} className="text-gray-500 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-200 truncate">
            {selectedRepo?.name ?? "All Projects"}
          </p>
          {selectedRepo && (
            <p className="text-xs text-gray-600 truncate">
              {selectedRepo.feature_count} features
            </p>
          )}
        </div>
        <ChevronDown size={12} className={`text-gray-600 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
          {/* All projects option */}
          <button
            onClick={() => { selectRepo(null); setOpen(false); }}
            className={`flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-gray-800 transition-colors ${
              !selectedRepo ? "bg-blue-900/20" : ""
            }`}
          >
            <Globe size={12} className="text-gray-500" />
            <div>
              <p className="text-xs font-medium text-gray-300">All Projects</p>
              <p className="text-xs text-gray-600">Combined graph</p>
            </div>
          </button>

          <div className="border-t border-gray-800" />

          {repos.map((repo) => (
            <button
              key={repo.path}
              onClick={() => { selectRepo(repo); setOpen(false); }}
              className={`flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-gray-800 transition-colors ${
                selectedRepo?.path === repo.path ? "bg-blue-900/20" : ""
              }`}
            >
              <FolderOpen size={12} className={selectedRepo?.path === repo.path ? "text-blue-400" : "text-gray-500"} />
              <div className="min-w-0 flex-1">
                <p className={`text-xs font-medium truncate ${
                  selectedRepo?.path === repo.path ? "text-blue-300" : "text-gray-300"
                }`}>
                  {repo.name}
                </p>
                <p className="text-xs text-gray-600 truncate">{repo.feature_count} features</p>
              </div>
              {selectedRepo?.path === repo.path && (
                <span className="text-blue-500 text-xs">✓</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
