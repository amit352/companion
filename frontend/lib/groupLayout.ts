/**
 * Grouped layout: domain swimlanes + shared center group.
 *
 * Layout:
 *   [AUTH]   [  SHARED (cross-domain)  ]   [BILLING]
 *   [               WORKFLOW                       ]
 *   [                 DATA                         ]
 */
import Dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";

// ── Constants ──────────────────────────────────────────────────────────────

const NODE_W = 172;
const NODE_H = 52;
const PAD    = 28;      // padding inside a group
const HEADER = 40;      // group title bar height
const GAP_X  = 80;      // horizontal gap between groups
const GAP_Y  = 60;      // vertical gap between groups

export const DOMAIN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  auth:    { bg: "rgba(139,92,246,0.08)",  border: "rgba(139,92,246,0.5)",  text: "#a78bfa" },
  billing: { bg: "rgba(16,185,129,0.08)",  border: "rgba(16,185,129,0.5)",  text: "#34d399" },
  workflow:{ bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.5)",  text: "#fbbf24" },
  data:    { bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.5)",  text: "#60a5fa" },
  shared:  { bg: "rgba(255,255,255,0.04)", border: "rgba(255,255,255,0.25)", text: "#e2e8f0" },
  unknown: { bg: "rgba(107,114,128,0.08)", border: "rgba(107,114,128,0.5)", text: "#9ca3af" },
};

const NODE_BG: Record<string, string> = {
  auth:    "#7c3aed",
  billing: "#059669",
  workflow:"#d97706",
  data:    "#2563eb",
  shared:  "#475569",
  unknown: "#374151",
};

// ── Cross-domain detection ─────────────────────────────────────────────────

function findSharedFeatures(
  features: any[],
  relationships: any[],
  minConnectedDomains = 2
): Set<string> {
  const byId = Object.fromEntries(features.map((f) => [f.id, f]));
  const connectedDomains: Record<string, Set<string>> = {};

  for (const r of relationships) {
    const src = byId[r.source_id];
    const tgt = byId[r.target_id];
    if (!src || !tgt || src.domain === tgt.domain) continue;
    connectedDomains[r.source_id] ??= new Set();
    connectedDomains[r.target_id] ??= new Set();
    connectedDomains[r.source_id].add(tgt.domain);
    connectedDomains[r.target_id].add(src.domain);
  }

  return new Set(
    Object.entries(connectedDomains)
      .filter(([, domains]) => domains.size >= minConnectedDomains)
      .map(([id]) => id)
  );
}

// ── Dagre within a group ───────────────────────────────────────────────────

function layoutGroup(members: any[], intraEdges: any[]): { nodes: any[]; w: number; h: number } {
  if (!members.length) return { nodes: [], w: 0, h: 0 };

  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", ranksep: 80, nodesep: 40 });

  members.forEach((f) => g.setNode(f.id, { width: NODE_W, height: NODE_H }));
  intraEdges.forEach((e) => {
    if (g.hasNode(e.source_id) && g.hasNode(e.target_id))
      g.setEdge(e.source_id, e.target_id);
  });

  Dagre.layout(g);

  let maxX = 0, maxY = 0;
  const nodes = members.map((f) => {
    const pos = g.node(f.id);
    const x = pos.x - NODE_W / 2 + PAD;
    const y = pos.y - NODE_H / 2 + HEADER + PAD;
    maxX = Math.max(maxX, x + NODE_W);
    maxY = Math.max(maxY, y + NODE_H);
    return { id: f.id, localX: x, localY: y, feature: f };
  });

  return {
    nodes,
    w: maxX + PAD,
    h: maxY + PAD,
  };
}

// ── Main export ────────────────────────────────────────────────────────────

export function buildGroupedLayout(
  features: any[],
  relationships: any[]
): { nodes: Node[]; edges: Edge[] } {
  if (!features.length) return { nodes: [], edges: [] };

  const sharedIds = findSharedFeatures(features, relationships);

  // Bucket features into groups
  const groups: Record<string, any[]> = { shared: [], auth: [], billing: [], workflow: [], data: [] };
  for (const f of features) {
    if (sharedIds.has(f.id)) {
      groups.shared.push(f);
    } else {
      const g = groups[f.domain] ?? (groups[f.domain] = []);
      g.push(f);
    }
  }
  // Remove empty groups
  for (const key of Object.keys(groups)) {
    if (!groups[key].length) delete groups[key];
  }

  // Build intra-group edge maps
  const memberSet: Record<string, string> = {};
  for (const [gname, feats] of Object.entries(groups)) {
    for (const f of feats) memberSet[f.id] = gname;
  }

  const intraEdges: Record<string, any[]> = {};
  for (const r of relationships) {
    const sg = memberSet[r.source_id];
    const tg = memberSet[r.target_id];
    if (sg && sg === tg) {
      intraEdges[sg] ??= [];
      intraEdges[sg].push({ source_id: r.source_id, target_id: r.target_id });
    }
  }

  // Layout each group
  const laid: Record<string, { nodes: any[]; w: number; h: number }> = {};
  for (const [gname, feats] of Object.entries(groups)) {
    laid[gname] = layoutGroup(feats, intraEdges[gname] ?? []);
  }

  // ── Arrange groups in space ────────────────────────────────────────────
  //
  //   row0: [auth | shared | billing]
  //   row1: [        workflow       ]
  //   row2: [         data          ]
  //
  const row0Groups = ["auth", "shared", "billing"].filter((g) => laid[g]);
  const row1Groups = ["workflow"].filter((g) => laid[g]);
  const row2Groups = ["data", ...Object.keys(laid).filter(
    (g) => !["auth", "shared", "billing", "workflow", "data"].includes(g)
  )];

  const groupPositions: Record<string, { x: number; y: number }> = {};

  // Row 0
  let curX = 0;
  const row0Height = Math.max(...row0Groups.map((g) => laid[g]?.h ?? 0));
  for (const g of row0Groups) {
    groupPositions[g] = { x: curX, y: 0 };
    curX += (laid[g]?.w ?? 0) + GAP_X;
  }
  const totalRow0W = curX - GAP_X;

  // Row 1 — full width of row 0
  const row1Y = row0Height + GAP_Y;
  curX = 0;
  for (const g of row1Groups) {
    // Stretch workflow to match row0 width if it's narrower
    groupPositions[g] = { x: curX, y: row1Y };
    if (laid[g] && laid[g].w < totalRow0W) {
      // stretch by adding extra padding (layout already computed, just widen the box)
      laid[g].w = Math.max(laid[g].w, totalRow0W);
    }
    curX += (laid[g]?.w ?? 0) + GAP_X;
  }

  // Row 2
  const row2Y = row1Y + Math.max(...row1Groups.map((g) => laid[g]?.h ?? 0), 0) + GAP_Y;
  curX = 0;
  for (const g of row2Groups) {
    groupPositions[g] = { x: curX, y: row2Y };
    curX += (laid[g]?.w ?? 0) + GAP_X;
  }

  // ── Build React Flow nodes ───────────────────────────────────────────────

  const flowNodes: Node[] = [];
  const colors = DOMAIN_COLORS;

  for (const [gname, { nodes: gNodes, w, h }] of Object.entries(laid)) {
    const gpos = groupPositions[gname] ?? { x: 0, y: 0 };
    const c = colors[gname] ?? colors.unknown;

    // Group container node
    flowNodes.push({
      id: `group-${gname}`,
      type: "group",
      position: gpos,
      data: { label: gname === "shared" ? "Shared / Cross-Domain" : gname.charAt(0).toUpperCase() + gname.slice(1) },
      style: {
        width: w,
        height: h,
        backgroundColor: c.bg,
        border: `1.5px solid ${c.border}`,
        borderRadius: 12,
        pointerEvents: "none" as const,
      },
    } as Node);

    // Feature nodes (children of group)
    for (const { id, localX, localY, feature: f } of gNodes) {
      flowNodes.push({
        id,
        parentId: `group-${gname}`,
        extent: "parent",
        position: { x: localX, y: localY },
        data: { label: f.name, feature: f },
        style: {
          background: NODE_BG[gname] ?? NODE_BG.unknown,
          color: "#fff",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 8,
          fontSize: 11,
          padding: "6px 10px",
          width: NODE_W,
          textAlign: "center" as const,
        },
      } as Node);
    }
  }

  // ── Build edges ───────────────────────────────────────────────────────────

  const nodeIds = new Set(flowNodes.map((n) => n.id));
  const flowEdges: Edge[] = relationships
    .filter((r) => nodeIds.has(r.source_id) && nodeIds.has(r.target_id))
    .map((r) => ({
      id: `${r.source_id}-${r.target_id}`,
      source: r.source_id,
      target: r.target_id,
      style: { stroke: "#4b5563", strokeWidth: 1.5 },
      animated: r.kind?.toUpperCase() === "DEPENDS_ON",
      markerEnd: { type: "arrowclosed" as any, color: "#6b7280" },
    }));

  return { nodes: flowNodes, edges: flowEdges };
}
