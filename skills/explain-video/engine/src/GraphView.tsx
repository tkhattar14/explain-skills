import React from "react";
import { interpolate } from "remotion";
import { type EdgeGeo, type Layout, NODE_H, NODE_W, pointAt, type Pt } from "./layout";
import { clamp, ease, MUTED, STATUS_COLOR, TEXT } from "./theme";
import type { Act } from "./timing";
import type { GEdge, GNode } from "./types";

type Box = { x: number; y: number; w: number; h: number };

export const GraphView: React.FC<{
  nodes: GNode[];
  edges: GEdge[];
  layout: Layout;
  box: Box;
  frame: number;
  revealAt: number;
  nodeActs: Record<string, Act>;
  edgeActs: Record<string, Act>;
  dim: number;
}> = ({ nodes, edges, layout, box, frame, revealAt, nodeActs, edgeActs, dim }) => {
  const s = Math.min(1, box.w / layout.width, box.h / layout.height);
  const ox = box.x + (box.w - layout.width * s) / 2;
  const oy = box.y + (box.h - layout.height * s) / 2;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: layout.width, height: layout.height,
      transformOrigin: "0 0", transform: `translate(${ox}px, ${oy}px) scale(${s})` }}>
      <svg width={layout.width} height={layout.height} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {edges.map((e) => (
          <EdgeView key={e.id} edge={e} geo={layout.edges[e.id]} frame={frame} act={edgeActs[e.id]} revealAt={revealAt} />
        ))}
      </svg>
      {nodes.map((n, i) => (
        <NodeView key={n.id} node={n} pos={layout.nodes[n.id]} frame={frame} act={nodeActs[n.id]} revealAt={revealAt + i * 3} dim={dim} />
      ))}
    </div>
  );
};

const NodeView: React.FC<{ node: GNode; pos: { x: number; y: number }; frame: number; act?: Act; revealAt: number; dim: number }> = ({
  node, pos, frame, act, revealAt, dim,
}) => {
  const color = STATUS_COLOR[node.status];
  const reveal = interpolate(frame, [revealAt, revealAt + 14], [0, 1], { ...clamp, easing: ease });
  const on = act ? interpolate(frame, [act.at, act.at + 10], [0, 1], clamp) : 0;
  const level = dim + (1 - dim) * on;
  const pulse = act?.hot ? 0.5 + 0.5 * Math.sin((frame - act.at) / 5) : 0;
  const glow = act ? (act.hot ? 14 + 16 * pulse : 6) : 0;
  const pop = act?.hot ? interpolate(frame, [act.at, act.at + 6, act.at + 14], [1, 1.07, 1.03], clamp) : 1;
  return (
    <div style={{ position: "absolute", left: pos.x - NODE_W / 2, top: pos.y - NODE_H / 2, width: NODE_W, height: NODE_H,
      borderRadius: 16, background: "linear-gradient(180deg, #16213A 0%, #0F182B 100%)", border: `2px solid ${color}`,
      boxShadow: glow ? `0 0 ${glow}px ${color}${act?.hot ? "AA" : "55"}` : "none",
      opacity: reveal * level, transform: `scale(${(0.9 + 0.1 * reveal) * pop})`,
      display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 18px", boxSizing: "border-box" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 10, height: 10, borderRadius: 5, background: color, flexShrink: 0 }} />
        <div style={{ color: TEXT, fontSize: 27, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{node.title}</div>
      </div>
      {node.sub && (
        <div style={{ color: MUTED, fontSize: 18, marginTop: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{node.sub}</div>
      )}
    </div>
  );
};

const EdgeView: React.FC<{ edge: GEdge; geo: EdgeGeo; frame: number; act?: Act; revealAt: number }> = ({ edge, geo, frame, act, revealAt }) => {
  const faint = interpolate(frame, [revealAt + 20, revealAt + 45], [0, 1], clamp);
  const draw = act ? interpolate(frame, [act.at, act.at + 20], [0, 1], { ...clamp, easing: ease }) : 0;
  const color = act?.hot ? "#BAE6FD" : "#7DD3FC";
  const n = geo.pts.length;
  const end = act?.rev ? geo.pts[0] : geo.pts[n - 1];
  const prev = act?.rev ? geo.pts[1] : geo.pts[n - 2];
  const ang = Math.atan2(end[1] - prev[1], end[0] - prev[0]);
  const tip = (r: number, a: number): Pt => [end[0] - r * Math.cos(ang + a), end[1] - r * Math.sin(ang + a)];
  const head = [end, tip(16, 0.45), tip(16, -0.45)].map((p) => p.join(",")).join(" ");
  let packet: Pt | null = null;
  if (act?.hot && frame >= act.at + 8) {
    const t = ((frame - act.at - 8) % 54) / 42;
    if (t <= 1) packet = pointAt(geo, act.rev ? 1 - t : t);
  }
  return (
    <g>
      <path d={geo.d} fill="none" stroke="#2A3753" strokeWidth={2} opacity={faint * 0.8} />
      {act && (
        <>
          <path d={geo.d} fill="none" stroke={color} strokeWidth={act.hot ? 4 : 3} strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray={geo.len} strokeDashoffset={act.rev ? -geo.len * (1 - draw) : geo.len * (1 - draw)}
            opacity={act.hot ? 1 : 0.5} filter={act.hot ? "url(#glow)" : undefined} />
          {draw > 0.95 && <polygon points={head} fill={color} opacity={act.hot ? 1 : 0.5} />}
          {act.hot && edge.label && draw > 0.95 && (
            <text x={geo.mid[0]} y={geo.mid[1] - 14} fill={TEXT} fontSize={24} textAnchor="middle"
              style={{ paintOrder: "stroke", stroke: "#0A1020", strokeWidth: 6 }}>{edge.label}</text>
          )}
          {packet && <circle cx={packet[0]} cy={packet[1]} r={9} fill="#FFFFFF" filter="url(#glow)" />}
        </>
      )}
    </g>
  );
};
