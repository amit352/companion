"use client";
import { useEffect, useState } from "react";
import { X, ChevronLeft, ChevronRight, MapPin } from "lucide-react";

const API = "http://localhost:8000";

interface TourStep {
  step: number;
  total: number;
  id: string;
  name: string;
  description: string;
  domain: string;
  confidence: number;
  tags: string[];
  depends_on: string[];
}

interface Props {
  onNodeFocus: (id: string) => void;
  onClose: () => void;
}

export function TourPanel({ onNodeFocus, onClose }: Props) {
  const [steps, setSteps]       = useState<TourStep[]>([]);
  const [current, setCurrent]   = useState(0);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/tour/`)
      .then((r) => r.json())
      .then((d) => { setSteps(d.steps ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (steps[current]) onNodeFocus(steps[current].id);
  }, [current, steps]);

  if (loading) return (
    <div className="fixed bottom-4 left-4 z-30 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 shadow-xl text-xs text-gray-500">
      Loading tour…
    </div>
  );

  if (!steps.length) return (
    <div className="fixed bottom-4 left-4 z-30 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 shadow-xl">
      <p className="text-xs text-gray-500">No features to tour yet.</p>
      <button onClick={onClose} className="text-xs text-gray-600 mt-1 hover:text-gray-300">Close</button>
    </div>
  );

  const step = steps[current];
  const progress = ((current + 1) / steps.length) * 100;

  const DOMAIN_DOT: Record<string, string> = {
    auth: "#8b5cf6", billing: "#10b981", workflow: "#f59e0b",
    data: "#3b82f6", api: "#06b6d4", unknown: "#4b5563",
  };

  return (
    <div className="fixed bottom-4 left-4 z-30 w-80 bg-gray-950 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-2">
          <MapPin size={13} className="text-blue-400" />
          <span className="text-xs font-semibold text-gray-200">
            Step {step.step} of {step.total}
          </span>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-300 transition-colors">
          <X size={14} />
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-0.5 bg-gray-800">
        <div
          className="h-full bg-blue-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Content */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-start gap-2">
          <div
            className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
            style={{ background: DOMAIN_DOT[step.domain] ?? DOMAIN_DOT.unknown }}
          />
          <h3 className="text-sm font-semibold text-gray-100 leading-tight">{step.name}</h3>
        </div>
        <p className="text-xs text-gray-400 leading-relaxed pl-4">{step.description}</p>

        {step.depends_on.length > 0 && (
          <div className="pl-4">
            <span className="text-xs text-gray-600">Depends on: </span>
            <span className="text-xs text-gray-500">{step.depends_on.join(" → ")}</span>
          </div>
        )}

        {step.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 pl-4">
            {step.tags.slice(0, 4).map((t) => (
              <span key={t} className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between px-4 pb-3 pt-1">
        <button
          onClick={() => setCurrent((c) => Math.max(0, c - 1))}
          disabled={current === 0}
          className="flex items-center gap-1 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-100 disabled:opacity-30 transition-colors rounded hover:bg-gray-800"
        >
          <ChevronLeft size={13} /> Prev
        </button>

        <div className="flex gap-1">
          {steps.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              className={`w-1.5 h-1.5 rounded-full transition-colors ${
                i === current ? "bg-blue-400" : "bg-gray-700 hover:bg-gray-500"
              }`}
            />
          ))}
        </div>

        <button
          onClick={() => setCurrent((c) => Math.min(steps.length - 1, c + 1))}
          disabled={current === steps.length - 1}
          className="flex items-center gap-1 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-100 disabled:opacity-30 transition-colors rounded hover:bg-gray-800"
        >
          Next <ChevronRight size={13} />
        </button>
      </div>
    </div>
  );
}
