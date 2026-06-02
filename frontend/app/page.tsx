"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import AIChatInterface from "@/components/AIChatInterface/AIChatInterface";
import { AnalysisLauncher } from "@/components/AnalysisLauncher";

// @xyflow/react uses browser-only APIs (ResizeObserver, DOM transforms).
// Rendering it server-side corrupts the store and triggers false key warnings.
const FeatureExplorer = dynamic(
  () => import("@/components/FeatureExplorer/FeatureExplorer"),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-full text-gray-500 text-sm">Loading graph...</div> }
);

type View = "explorer" | "chat";

export default function Home() {
  const [view, setView] = useState<View>("explorer");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | null>(null);

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 flex flex-col p-4 gap-4">
        <div className="flex items-center gap-2 py-2">
          <span className="text-lg font-bold text-blue-400">Companion</span>
          <span className="text-xs text-gray-500 mt-1">v0.1</span>
        </div>

        <nav className="flex flex-col gap-1">
          {(["explorer", "chat"] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-2 rounded text-left text-sm capitalize transition-colors ${
                view === v
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              {v === "explorer" ? "Feature Explorer" : "AI Chat"}
            </button>
          ))}
        </nav>

        <div className="mt-auto">
          <AnalysisLauncher />
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
    </div>
  );
}
