"use client";
import { useFeatureDetail } from "@/lib/hooks/useFeatureDetail";
import { X } from "lucide-react";

interface Props {
  featureId: string;
  onClose: () => void;
}

export function FeatureDetailPanel({ featureId, onClose }: Props) {
  const { feature, impact, isLoading } = useFeatureDetail(featureId);

  return (
    <aside className="w-80 border-l border-gray-800 p-4 overflow-y-auto flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-sm text-gray-200">Feature Detail</h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-200">
          <X size={16} />
        </button>
      </div>

      {isLoading && <p className="text-gray-500 text-sm">Loading...</p>}

      {feature && (
        <>
          <section>
            <h3 className="text-blue-400 font-medium">{feature.name}</h3>
            <p className="text-xs text-gray-400 mt-1">{feature.description}</p>
            <div className="flex gap-2 mt-2 flex-wrap">
              {feature.tags?.map((t: string) => (
                <span key={t} className="text-xs bg-gray-800 px-2 py-0.5 rounded text-gray-300">
                  {t}
                </span>
              ))}
            </div>
          </section>

          <section>
            <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-1">Source Files</h4>
            {feature.source_files?.map((f: string) => (
              <p key={f} className="text-xs text-gray-400 font-mono">{f}</p>
            ))}
          </section>

          <section>
            <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              Confidence
            </h4>
            <div className="w-full bg-gray-800 rounded-full h-1.5">
              <div
                className="bg-blue-500 h-1.5 rounded-full"
                style={{ width: `${(feature.confidence ?? 1) * 100}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">{((feature.confidence ?? 1) * 100).toFixed(0)}%</p>
          </section>
        </>
      )}

      {impact && impact.dependents?.length > 0 && (
        <section>
          <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-1">
            Impact — {impact.dependents.length} dependent(s)
          </h4>
          {impact.dependents.map((d: any) => (
            <p key={d.id} className="text-xs text-orange-400 font-medium">{d.name}</p>
          ))}
        </section>
      )}
    </aside>
  );
}
