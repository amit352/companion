import { DOMAIN_COLORS } from "@/lib/groupLayout";

interface GroupNodeData {
  label: string;
  colorText?: string; // optional override from architecture layout
}

export function GroupNode({ data }: { data: GroupNodeData }) {
  // Architecture layout passes colorText directly; domain layout derives from label
  const textColor =
    data.colorText ??
    (DOMAIN_COLORS[data.label.toLowerCase().split(/[\s/]/)[0]]?.text ?? "#9ca3af");

  const borderColor =
    data.colorText ??
    (DOMAIN_COLORS[data.label.toLowerCase().split(/[\s/]/)[0]]?.border ?? "rgba(107,114,128,0.4)");

  return (
    <div className="w-full h-full relative" style={{ pointerEvents: "none" }}>
      <div
        className="absolute top-0 left-0 right-0 flex items-center px-3 gap-2"
        style={{
          height: 36,
          borderBottom: `1px solid ${borderColor}20`,
          borderRadius: "8px 8px 0 0",
        }}
      >
        <div
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ background: textColor, opacity: 0.8 }}
        />
        <span
          className="text-xs font-semibold tracking-widest uppercase truncate"
          style={{ color: textColor }}
        >
          {data.label}
        </span>
      </div>
    </div>
  );
}
