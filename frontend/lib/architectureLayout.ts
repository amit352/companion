/**
 * Architecture layout — fully dynamic grouping.
 *
 * Algorithm:
 *  1. Extract primary entity from each feature name (first meaningful noun)
 *  2. Small normalization table only for genuinely ambiguous prefixes
 *  3. Within each entity group, sub-group by action type (also derived from name)
 *  4. Arrange entity groups in a 2-column grid, largest groups first
 */
import type { Edge, Node } from "@xyflow/react";

// ── Constants ──────────────────────────────────────────────────────────────

const NODE_W     = 160;
const NODE_H     = 44;
const PAD        = 20;
const HEADER     = 36;
const SUB_HEADER = 28;
const H_GAP      = 20;   // between nodes in a row
const V_GAP      = 12;   // between rows of nodes
const COL_GAP    = 36;   // between entity columns
const ROW_GAP    = 32;   // between entity rows

// ── Color palette (assigned by index) ─────────────────────────────────────

const PALETTE = [
  { bg: "rgba(59,130,246,0.07)",  border: "rgba(59,130,246,0.45)",  text: "#93c5fd", node: "#1d4ed8" },  // blue
  { bg: "rgba(34,197,94,0.07)",   border: "rgba(34,197,94,0.45)",   text: "#86efac", node: "#15803d" },  // green
  { bg: "rgba(251,191,36,0.07)",  border: "rgba(251,191,36,0.45)",  text: "#fde68a", node: "#b45309" },  // amber
  { bg: "rgba(168,85,247,0.07)",  border: "rgba(168,85,247,0.45)",  text: "#d8b4fe", node: "#7e22ce" },  // purple
  { bg: "rgba(20,184,166,0.07)",  border: "rgba(20,184,166,0.45)",  text: "#5eead4", node: "#0f766e" },  // teal
  { bg: "rgba(99,102,241,0.07)",  border: "rgba(99,102,241,0.45)",  text: "#a5b4fc", node: "#4338ca" },  // indigo
  { bg: "rgba(244,63,94,0.07)",   border: "rgba(244,63,94,0.45)",   text: "#fda4af", node: "#be123c" },  // rose
  { bg: "rgba(6,182,212,0.07)",   border: "rgba(6,182,212,0.45)",   text: "#67e8f9", node: "#0e7490" },  // cyan
  { bg: "rgba(249,115,22,0.07)",  border: "rgba(249,115,22,0.45)",  text: "#fdba74", node: "#c2410c" },  // orange
];

// ── Entity extraction ──────────────────────────────────────────────────────

// Only entries that genuinely can't be guessed from the first word
const ENTITY_OVERRIDES: Array<[RegExp, string]> = [
  [/oauth|user auth|entitle/i,                                         "Identity"],
  [/supply chain|loan syndicat|program participant|liquidity pool/i,   "Program"],
  [/daily fee|iso8601|subscription.based|async notif/i,               "Automation"],
  [/invoice.to.asset|deposit reconcili/i,                             "Deposit"],
  [/scheduled invoice|scheduled report/i,                             "Automation"],
  [/prepare invoice|auto invoice/i,                                   "Invoice"],
];

function extractEntity(name: string): string {
  for (const [re, entity] of ENTITY_OVERRIDES) {
    if (re.test(name)) return entity;
  }
  // First significant word (skip short articles/prepositions)
  const words = name.replace(/[()]/g, "").split(/\s+/);
  const skip = new Set(["a", "an", "the", "of", "for", "and", "or", "to", "in"]);
  const first = words.find((w) => !skip.has(w.toLowerCase()) && w.length > 2);
  return first ?? "Other";
}

// ── Sub-group (action) extraction ─────────────────────────────────────────

const ACTION_RULES: Array<[RegExp, string]> = [
  [/upload|file upload|creation|build/i,       "Input"],
  [/lifecycle|state|status|eligib/i,           "Lifecycle"],
  [/accept|reject|reversal|approval/i,         "Approval"],
  [/auto .+select|prepare|calculat|fee/i,      "Processing"],
  [/reconcili/i,                               "Reconciliation"],
  [/schedule|worker|notif|rule|bod/i,          "Automation"],
  [/config|setup|participant|management/i,     "Configuration"],
  [/pool|credit|syndicat|liquidity/i,          "Financial"],
];

function extractAction(name: string): string {
  for (const [re, action] of ACTION_RULES) {
    if (re.test(name)) return action;
  }
  return "General";
}

// ── Layout computation ─────────────────────────────────────────────────────

function layoutSubGroup(
  features: any[],
  offsetY: number,
  cols = 2
): { items: Array<{ id: string; lx: number; ly: number; feature: any }>; height: number } {
  const items = features.map((f, i) => ({
    id: f.id,
    lx: PAD + (i % cols) * (NODE_W + H_GAP),
    ly: offsetY + (Math.floor(i / cols)) * (NODE_H + V_GAP),
    feature: f,
  }));
  const rows = Math.ceil(features.length / cols);
  return { items, height: rows * NODE_H + (rows - 1) * V_GAP };
}

function layoutEntityGroup(
  features: any[],
  color: (typeof PALETTE)[number]
): {
  nodes: Array<{ id: string; lx: number; ly: number; feature: any; subLabel?: string }>;
  subGroupNodes: Array<{ id: string; lx: number; ly: number; w: number; h: number; label: string }>;
  w: number;
  h: number;
} {
  // Sub-group by action
  const actionMap: Record<string, any[]> = {};
  for (const f of features) {
    const action = extractAction(f.name);
    (actionMap[action] ??= []).push(f);
  }

  const actions = Object.entries(actionMap);

  // If only 1 action or all in "General", skip sub-groups
  const useSubGroups = actions.length > 1 && features.length > 3;

  let curY = HEADER + PAD;
  const allItems: Array<{ id: string; lx: number; ly: number; feature: any; subLabel?: string }> = [];
  const subGroupNodes: Array<{ id: string; lx: number; ly: number; w: number; h: number; label: string }> = [];

  const cols = Math.min(features.length, 3);

  if (!useSubGroups) {
    const { items, height } = layoutSubGroup(features, curY, cols);
    allItems.push(...items);
    curY += height + PAD;
  } else {
    for (const [actionLabel, feats] of actions) {
      const subCols = Math.min(feats.length, 3);
      const subY = curY + SUB_HEADER + PAD / 2;
      const { items, height } = layoutSubGroup(feats, subY, subCols);
      const subW = subCols * NODE_W + (subCols - 1) * H_GAP + PAD;
      const subH = SUB_HEADER + PAD / 2 + height + PAD / 2;

      subGroupNodes.push({ id: `sub-${actionLabel}`, lx: PAD / 2, ly: curY, w: subW, h: subH, label: actionLabel });
      allItems.push(...items);
      curY += subH + V_GAP;
    }
    curY += PAD / 2;
  }

  // Width = widest row of nodes + padding
  const maxCols = Math.min(features.length, 3);
  const w = PAD * 2 + maxCols * NODE_W + (maxCols - 1) * H_GAP;

  return { nodes: allItems, subGroupNodes, w, h: curY + (useSubGroups ? 0 : PAD / 2) };
}

// ── Main export ────────────────────────────────────────────────────────────

export function buildArchitectureLayout(
  features: any[],
  relationships: any[]
): { nodes: Node[]; edges: Edge[] } {
  if (!features.length) return { nodes: [], edges: [] };

  // Step 1 — cluster by entity
  const entityMap: Record<string, any[]> = {};
  for (const f of features) {
    const entity = extractEntity(f.name);
    (entityMap[entity] ??= []).push(f);
  }

  // Step 2 — sort entity groups: larger groups first
  const sorted = Object.entries(entityMap).sort((a, b) => b[1].length - a[1].length);

  // Step 3 — assign colors
  const colorOf: Record<string, (typeof PALETTE)[number]> = {};
  sorted.forEach(([name], i) => { colorOf[name] = PALETTE[i % PALETTE.length]; });

  // Step 4 — layout each group
  const laidGroups: Record<string, ReturnType<typeof layoutEntityGroup> & { label: string; color: (typeof PALETTE)[number] }> = {};
  for (const [entity, feats] of sorted) {
    laidGroups[entity] = { ...layoutEntityGroup(feats, colorOf[entity]), label: entity, color: colorOf[entity] };
  }

  // Step 5 — arrange groups in a 2-column grid
  const groupKeys = sorted.map(([k]) => k);
  const groupPos: Record<string, { x: number; y: number }> = {};
  const COL_COUNT = 2;

  // Pair groups into rows of 2
  let curY = 0;
  for (let i = 0; i < groupKeys.length; i += COL_COUNT) {
    const row = groupKeys.slice(i, i + COL_COUNT);
    const rowH = Math.max(...row.map((k) => laidGroups[k].h));
    let curX = 0;
    for (const k of row) {
      groupPos[k] = { x: curX, y: curY };
      curX += laidGroups[k].w + COL_GAP;
    }
    curY += rowH + ROW_GAP;
  }

  // Step 6 — build React Flow nodes
  const flowNodes: Node[] = [];

  for (const [entity, grp] of Object.entries(laidGroups)) {
    const pos = groupPos[entity] ?? { x: 0, y: 0 };
    const { color, label, nodes: gNodes, subGroupNodes, w, h } = grp;

    // Outer group container
    flowNodes.push({
      id: `arch-${entity}`,
      type: "group",
      position: pos,
      data: { label, colorText: color.text },
      style: {
        width: w, height: h,
        backgroundColor: color.bg,
        border: `1.5px solid ${color.border}`,
        borderRadius: 10,
        pointerEvents: "none" as const,
      },
    } as Node);

    // Sub-group boxes (visual only, not React Flow parents)
    for (const sg of subGroupNodes) {
      flowNodes.push({
        id: `${entity}-sub-${sg.label}`,
        parentId: `arch-${entity}`,
        extent: "parent",
        type: "group",
        position: { x: sg.lx, y: sg.ly },
        data: { label: sg.label, colorText: color.text + "aa" },
        style: {
          width: sg.w, height: sg.h,
          backgroundColor: "rgba(255,255,255,0.02)",
          border: `1px dashed ${color.border}`,
          borderRadius: 6,
          pointerEvents: "none" as const,
        },
        zIndex: 1,
      } as Node);
    }

    // Feature nodes
    for (const { id, lx, ly, feature: f } of gNodes) {
      flowNodes.push({
        id,
        parentId: `arch-${entity}`,
        extent: "parent",
        position: { x: lx, y: ly },
        data: { label: f.name, feature: f },
        style: {
          background: color.node,
          color: "#fff",
          border: `1px solid ${color.border}`,
          borderRadius: 6,
          fontSize: 10.5,
          padding: "4px 8px",
          width: NODE_W,
          textAlign: "center" as const,
          lineHeight: "1.35",
        },
        zIndex: 2,
      } as Node);
    }
  }

  // Step 7 — edges
  const nodeIds = new Set(flowNodes.map((n) => n.id));
  const flowEdges: Edge[] = relationships
    .filter((r) => nodeIds.has(r.source_id) && nodeIds.has(r.target_id))
    .map((r) => ({
      id: `${r.source_id}-${r.target_id}`,
      source: r.source_id,
      target: r.target_id,
      style: { stroke: "#374151", strokeWidth: 1.5 },
      markerEnd: { type: "arrowclosed" as any, color: "#4b5563" },
      zIndex: 3,
    }));

  return { nodes: flowNodes, edges: flowEdges };
}
