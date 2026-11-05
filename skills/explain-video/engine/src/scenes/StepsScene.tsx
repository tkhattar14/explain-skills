import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { Heading, type SceneProps } from "../common";
import { clamp, ease, PANEL, STATUS_COLOR, STATUS_LABEL, TEXT } from "../theme";
import { revealFrames } from "../timing";

export const StepsScene: React.FC<SceneProps> = ({ scene, ts, frame, li }) => {
  if (scene.type !== "steps") return null;
  const shown = revealFrames(scene, ts, li, scene.items.length);
  const current = (scene.lines[li]?.cue?.reveal ?? 0) - 1;
  const rowH = Math.min(84, 720 / scene.items.length);
  return (
    <AbsoluteFill style={{ padding: "70px 200px 0" }}>
      <Heading text={scene.chip} frame={frame} at={ts.from} />
      {scene.items.map((it, i) => {
        const at = shown[i];
        if (at === null) return null;
        const o = interpolate(frame, [at, at + 12], [0, 1], clamp);
        const x = interpolate(frame, [at, at + 16], [40, 0], { ...clamp, easing: ease });
        const color = STATUS_COLOR[it.status];
        const hot = i === current;
        return (
          <div key={i} style={{ position: "absolute", left: 200, right: 200, top: 170 + i * rowH, height: rowH - 12,
            opacity: o, transform: `translateX(${x}px)`, display: "flex", alignItems: "center", gap: 24,
            padding: "0 24px", borderRadius: 14, background: hot ? PANEL : "transparent",
            boxShadow: hot ? `0 0 18px ${color}66` : "none", border: hot ? `2px solid ${color}` : "2px solid transparent" }}>
            <div style={{ width: 46, height: 46, borderRadius: 23, border: `3px solid ${color}`, color, fontSize: 24, fontWeight: 800,
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</div>
            <div style={{ color: TEXT, fontSize: 32, fontWeight: 600, flex: 1 }}>{it.text}</div>
            <div style={{ color, fontSize: 22, fontWeight: 700, border: `2px solid ${color}`, borderRadius: 999, padding: "4px 14px",
              textTransform: "uppercase", letterSpacing: 1, flexShrink: 0 }}>{STATUS_LABEL[it.status]}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
