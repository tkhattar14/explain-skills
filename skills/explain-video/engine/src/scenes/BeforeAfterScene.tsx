import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { Heading, type SceneProps } from "../common";
import { clamp, ease, MUTED, PANEL, TEXT } from "../theme";
import { revealFrames } from "../timing";

const GREEN = "#34D399";

export const BeforeAfterScene: React.FC<SceneProps> = ({ scene, ts, frame, li }) => {
  if (scene.type !== "before_after") return null;
  const shown = revealFrames(scene, ts, li, scene.pairs.length);
  const rowH = Math.min(130, 640 / scene.pairs.length);
  const card = (text: string, after: boolean): React.CSSProperties => ({
    width: 680, minHeight: rowH - 24, boxSizing: "border-box", padding: "16px 24px", borderRadius: 16, background: PANEL,
    border: `2px solid ${after ? GREEN : "#334155"}`, color: after ? TEXT : MUTED, fontSize: 30, fontWeight: after ? 600 : 400,
    display: "flex", alignItems: "center",
  });
  return (
    <AbsoluteFill style={{ padding: "70px 160px 0" }}>
      <Heading text={scene.chip} frame={frame} at={ts.from} />
      <div style={{ display: "flex", gap: 120, color: MUTED, fontSize: 24, letterSpacing: 4, textTransform: "uppercase", marginBottom: 18 }}>
        <div style={{ width: 680 }}>Before</div>
        <div style={{ width: 680, color: GREEN }}>After</div>
      </div>
      {scene.pairs.map((p, i) => {
        const at = shown[i];
        if (at === null) return null;
        const o = interpolate(frame, [at, at + 12], [0, 1], clamp);
        const slide = interpolate(frame, [at + 6, at + 24], [-60, 0], { ...clamp, easing: ease });
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 40, marginBottom: 20, opacity: o }}>
            <div style={card(p.before, false)}>{p.before}</div>
            <div style={{ color: GREEN, fontSize: 44, width: 40, textAlign: "center" }}>{"→"}</div>
            <div style={{ ...card(p.after, true), transform: `translateX(${slide}px)` }}>{p.after}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
