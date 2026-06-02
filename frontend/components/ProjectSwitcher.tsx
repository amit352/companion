"use client";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, FolderOpen, Globe, Check } from "lucide-react";
import { useProject } from "@/lib/projectContext";

export function ProjectSwitcher() {
  const { repos, selectedRepo, selectRepo } = useProject();
  const [open, setOpen]                     = useState(false);
  const containerRef                        = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  if (!repos.length) return null;

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      {/* Trigger */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          display:      "flex",
          alignItems:   "center",
          gap:          "var(--space-2)",
          width:        "100%",
          padding:      "var(--space-2) var(--space-3)",
          borderRadius: "var(--radius-md)",
          background:   open ? "var(--surface-active)" : "var(--surface-overlay)",
          border:       `1px solid ${open ? "var(--accent-blue)" : "var(--border-default)"}`,
          cursor:       "pointer",
          textAlign:    "left",
          transition:   "background var(--duration-fast), border-color var(--duration-fast)",
        }}
        onMouseEnter={(e) => {
          if (!open) {
            const el = e.currentTarget as HTMLElement;
            el.style.background   = "var(--surface-hover)";
            el.style.borderColor  = "var(--border-strong)";
          }
        }}
        onMouseLeave={(e) => {
          if (!open) {
            const el = e.currentTarget as HTMLElement;
            el.style.background  = "var(--surface-overlay)";
            el.style.borderColor = "var(--border-default)";
          }
        }}
      >
        {selectedRepo ? (
          <FolderOpen
            size={13}
            style={{ color: "var(--accent-blue)", flexShrink: 0 }}
          />
        ) : (
          <Globe
            size={13}
            style={{ color: "var(--text-tertiary)", flexShrink: 0 }}
          />
        )}

        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            style={{
              margin:       0,
              fontSize:     "var(--text-xs)",
              fontWeight:   "var(--weight-semibold)",
              color:        "var(--text-primary)",
              overflow:     "hidden",
              textOverflow: "ellipsis",
              whiteSpace:   "nowrap",
              lineHeight:   "var(--leading-tight)",
            }}
          >
            {selectedRepo?.name ?? "All Projects"}
          </p>
          {selectedRepo && (
            <p
              style={{
                margin:       0,
                fontSize:     "var(--text-2xs)",
                color:        "var(--text-tertiary)",
                overflow:     "hidden",
                textOverflow: "ellipsis",
                whiteSpace:   "nowrap",
                marginTop:    2,
              }}
            >
              {selectedRepo.feature_count} features
            </p>
          )}
        </div>

        <ChevronDown
          size={12}
          style={{
            color:       "var(--text-tertiary)",
            flexShrink:  0,
            transition:  "transform var(--duration-fast)",
            transform:   open ? "rotate(180deg)" : "rotate(0deg)",
          }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          style={{
            position:     "absolute",
            left:         0,
            right:        0,
            top:          "calc(100% + 4px)",
            background:   "var(--surface-overlay)",
            border:       "1px solid var(--border-default)",
            borderRadius: "var(--radius-lg)",
            boxShadow:    "var(--shadow-lg)",
            zIndex:       50,
            overflow:     "hidden",
          }}
        >
          {/* All projects */}
          <ProjectOption
            icon={<Globe size={13} style={{ color: "var(--text-tertiary)" }} />}
            label="All Projects"
            sublabel="Combined graph"
            isSelected={!selectedRepo}
            onClick={() => { selectRepo(null); setOpen(false); }}
          />

          {repos.length > 0 && (
            <div style={{ borderTop: "1px solid var(--border-subtle)" }} />
          )}

          {repos.map((repo) => (
            <ProjectOption
              key={repo.path}
              icon={
                <FolderOpen
                  size={13}
                  style={{
                    color: selectedRepo?.path === repo.path
                      ? "var(--accent-blue)"
                      : "var(--text-tertiary)",
                  }}
                />
              }
              label={repo.name}
              sublabel={`${repo.feature_count} features`}
              isSelected={selectedRepo?.path === repo.path}
              onClick={() => { selectRepo(repo); setOpen(false); }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Option row ───────────────────────────────────────────────────────────── */
function ProjectOption({
  icon,
  label,
  sublabel,
  isSelected,
  onClick,
}: {
  icon:       React.ReactNode;
  label:      string;
  sublabel?:  string;
  isSelected: boolean;
  onClick:    () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display:    "flex",
        alignItems: "center",
        gap:        "var(--space-2)",
        width:      "100%",
        padding:    "var(--space-2) var(--space-3)",
        background: isSelected ? "var(--accent-blue-muted)" : "transparent",
        border:     "none",
        cursor:     "pointer",
        textAlign:  "left",
        transition: "background var(--duration-fast)",
      }}
      onMouseEnter={(e) => {
        if (!isSelected)
          (e.currentTarget as HTMLElement).style.background = "var(--surface-hover)";
      }}
      onMouseLeave={(e) => {
        if (!isSelected)
          (e.currentTarget as HTMLElement).style.background = "transparent";
      }}
    >
      {icon}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            margin:       0,
            fontSize:     "var(--text-xs)",
            fontWeight:   "var(--weight-medium)",
            color:        isSelected ? "var(--accent-blue-text)" : "var(--text-secondary)",
            overflow:     "hidden",
            textOverflow: "ellipsis",
            whiteSpace:   "nowrap",
            lineHeight:   "var(--leading-tight)",
          }}
        >
          {label}
        </p>
        {sublabel && (
          <p
            style={{
              margin:       0,
              fontSize:     "var(--text-2xs)",
              color:        "var(--text-tertiary)",
              overflow:     "hidden",
              textOverflow: "ellipsis",
              whiteSpace:   "nowrap",
              marginTop:    2,
            }}
          >
            {sublabel}
          </p>
        )}
      </div>
      {isSelected && (
        <Check size={13} style={{ color: "var(--accent-blue)", flexShrink: 0 }} />
      )}
    </button>
  );
}
