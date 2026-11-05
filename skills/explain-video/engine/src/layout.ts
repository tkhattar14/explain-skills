import dagre from "@dagrejs/dagre";
import type { GEdge, GNode } from "./types";

export type Pt = [number, number];
export type EdgeGeo = { pts: Pt[]; cum: number[]; len: number; d: string; mid: Pt };
export type Layout = {
  width: number;
  height: number;
  scale: number;
  nodes: Record<string, { x: number; y: number }>;
  edges: Record<string, EdgeGeo>;
};

export const NODE_W = 300;
export const NODE_H = 104;

const run = (nodes: GNode[], edges: GEdge[], rankdir: "LR" | "TB") => {
  const g = new dagre.graphlib.Graph({ multigraph: true });
  g.setGraph({ rankdir, nodesep: 40, ranksep: 80, edgesep: 20, marginx: 24, marginy: 24 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  // Reserve room for each label so dagre keeps it clear of the boxes.
  const labelBox = (label?: string) => (label ? { width: Math.min(300, 24 + label.length * 13), height: 34, labelpos: "c" } : {});
  edges.forEach((e) => g.setEdge(e.from, e.to, labelBox(e.label), e.id));
  dagre.layout(g);
  return g;
};

/** Catmull-Rom spline through dagre's bend points, sampled into a polyline. */
const smooth = (p: Pt[], per = 14): Pt[] => {
  if (p.length < 3) return p;
  const out: Pt[] = [];
  for (let i = 0; i < p.length - 1; i++) {
    const p0 = p[Math.max(0, i - 1)];
    const p1 = p[i];
    const p2 = p[i + 1];
    const p3 = p[Math.min(p.length - 1, i + 2)];
    for (let s = 0; s < per; s++) {
      const t = s / per;
      const t2 = t * t;
      const t3 = t2 * t;
      const at = (k: 0 | 1) =>
        0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3);
      out.push([at(0), at(1)]);
    }
  }
  out.push(p[p.length - 1]);
  return out;
};

export const pointAt = (g: Pick<EdgeGeo, "pts" | "cum" | "len">, t: number): Pt => {
  const target = Math.max(0, Math.min(1, t)) * g.len;
  let i = 1;
  while (i < g.cum.length - 1 && g.cum[i] < target) i++;
  const seg = g.cum[i] - g.cum[i - 1] || 1;
  const k = (target - g.cum[i - 1]) / seg;
  return [g.pts[i - 1][0] + (g.pts[i][0] - g.pts[i - 1][0]) * k, g.pts[i - 1][1] + (g.pts[i][1] - g.pts[i - 1][1]) * k];
};

const geo = (pts: Pt[]): EdgeGeo => {
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const len = cum[cum.length - 1];
  const d = "M" + pts.map((q) => `${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(" L");
  return { pts, cum, len, d, mid: pointAt({ pts, cum, len }, 0.5) };
};

/** Lay out left-to-right, or top-to-bottom when that fits the box at a clearly (30%) larger scale. */
export const layoutGraph = (nodes: GNode[], edges: GEdge[], box: { w: number; h: number }): Layout => {
  const options = (["LR", "TB"] as const).map((dir) => {
    const g = run(nodes, edges, dir);
    const gw = g.graph().width ?? 1;
    const gh = g.graph().height ?? 1;
    return { g, gw, gh, scale: Math.min(1, box.w / gw, box.h / gh) };
  });
  // Left-to-right reads best on a 16:9 screen; go top-to-bottom only when it fits clearly larger.
  const best = options[1].scale > options[0].scale * 1.3 ? options[1] : options[0];
  const outNodes: Layout["nodes"] = {};
  nodes.forEach((n) => {
    const v = best.g.node(n.id);
    outNodes[n.id] = { x: v.x, y: v.y };
  });
  const outEdges: Layout["edges"] = {};
  edges.forEach((e) => {
    const lab = best.g.edge({ v: e.from, w: e.to, name: e.id });
    let pts = (lab?.points ?? []).map((p: { x: number; y: number }) => [p.x, p.y] as Pt);
    if (pts.length < 2) pts = [[outNodes[e.from].x, outNodes[e.from].y], [outNodes[e.to].x, outNodes[e.to].y]];
    const eg = geo(smooth(pts));
    if (e.label && typeof lab?.x === "number" && typeof lab?.y === "number") eg.mid = [lab.x, lab.y];
    outEdges[e.id] = eg;
  });
  return { width: best.gw, height: best.gh, scale: best.scale, nodes: outNodes, edges: outEdges };
};
