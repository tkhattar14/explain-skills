import React from "react";
import { interpolate } from "remotion";
import type { Layout } from "./layout";
import type { Scene, Spec, TimelineScene } from "./types";
import { BG, CAPTION_H, clamp, GRID, LEGEND, MUTED, TEXT } from "./theme";

export type SceneProps = {
  spec: Spec;
  scene: Scene;
  ts: TimelineScene;
  frame: number;
  li: number;
  layout: Layout | null;
  miniLayout: Layout | null;
  graphRevealAt: number;
  prevType: Scene["type"] | null;
};

export const Grid: React.FC = () => (
  <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
    {Array.from({ length: 33 }, (_, i) => (
      <line key={`v${i}`} x1={i * 60} y1={0} x2={i * 60} y2={1080} stroke={GRID} strokeWidth={1} />
    ))}
    {Array.from({ length: 19 }, (_, i) => (
      <line key={`h${i}`} x1={0} y1={i * 60} x2={1920} y2={i * 60} stroke={GRID} strokeWidth={1} />
    ))}
    <defs>
      <radialGradient id="vig" cx="50%" cy="45%" r="75%">
        <stop offset="55%" stopColor={BG} stopOpacity={0} />
        <stop offset="100%" stopColor={BG} stopOpacity={0.95} />
      </radialGradient>
    </defs>
    <rect width={1920} height={1080} fill="url(#vig)" />
  </svg>
);

export const CaptionBar: React.FC<{ scene: Scene; ts: TimelineScene; frame: number; li: number }> = ({ scene, ts, frame, li }) => {
  if (li < 0) return null;
  const at = ts.from + ts.lines[li].start;
  const o = interpolate(frame, [at, at + 6], [0, 1], clamp);
  const chipO = interpolate(frame, [ts.from, ts.from + 10], [0, 1], clamp);
  const line = scene.lines[li];
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: CAPTION_H,
      background: "linear-gradient(180deg, rgba(10,16,32,0) 0%, rgba(10,16,32,0.92) 35%)",
      display: "flex", alignItems: "center", gap: 28, padding: "16px 48px 0", boxSizing: "border-box" }}>
      <div style={{ opacity: chipO, flexShrink: 0, color: BG, background: "#38BDF8", fontWeight: 800, fontSize: 20,
        letterSpacing: 1, textTransform: "uppercase", padding: "8px 16px", borderRadius: 8 }}>
        {scene.chip}
      </div>
      <div style={{ opacity: o, color: TEXT, fontSize: 32, fontWeight: 500, lineHeight: 1.25 }}>{line.show ?? line.say}</div>
    </div>
  );
};

export const Heading: React.FC<{ text: string; frame: number; at: number }> = ({ text, frame, at }) => {
  const o = interpolate(frame, [at, at + 12], [0, 1], clamp);
  return <div style={{ color: TEXT, fontSize: 48, fontWeight: 800, opacity: o, marginBottom: 30 }}>{text}</div>;
};

export const Legend: React.FC = () => (
  <div style={{ position: "absolute", right: 40, top: 26, display: "flex", gap: 26 }}>
    {LEGEND.map(([c, t]) => (
      <div key={t} style={{ display: "flex", alignItems: "center", gap: 8, color: MUTED, fontSize: 19 }}>
        <div style={{ width: 12, height: 12, borderRadius: 3, background: c }} />
        {t}
      </div>
    ))}
  </div>
);
