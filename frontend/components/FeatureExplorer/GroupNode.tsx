import { DOMAIN_COLORS } from "@/lib/groupLayout";

export function GroupNode({ data }: { data: { label: string } }) {
  const key = data.label.toLowerCase().replace(/ .*/, ""); // first word
  const color = DOMAIN_COLORS[key] ?? DOMAIN_COLORS.unknown;

  return (
    <div
      className="w-full h-full relative"
      style={{ pointerEvents: "none" }}
    >
      <div
        className="absolute top-0 left-0 right-0 flex items-center px-3"
        style={{
          height: 36,
          borderBottom: `1px solid ${color.border}`,
          background: color.bg,
          borderRadius: "10px 10px 0 0",
        }}
      >
        <span
          className="text-xs font-semibold tracking-wider uppercase"
          style={{ color: color.text }}
        >
          {data.label}
        </span>
      </div>
    </div>
  );
}
