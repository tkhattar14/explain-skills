import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import type { SceneProps } from "../common";
import { clamp, ease, MUTED, TEXT } from "../theme";
import { lineFrame } from "../timing";

export const TitleScene: React.FC<SceneProps> = ({ spec, scene, ts, frame }) => {
  const end = ts.from + ts.durationInFrames;
  const o = interpolate(frame, [ts.from, ts.from + 18, end - 16, end], [0, 1, 1, 0], clamp);
  const y = interpolate(frame, [ts.from, ts.from + 24], [24, 0], { ...clamp, easing: ease });
  const subAt = ts.lines.length > 1 ? lineFrame(ts, 1) : ts.from + 20;
  const sub = interpolate(frame, [subAt, subAt + 14], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: o }}>
      <div style={{ transform: `translateY(${y}px)`, textAlign: "center", maxWidth: 1600 }}>
        <div style={{ color: MUTED, fontSize: 26, letterSpacing: 6, textTransform: "uppercase", marginBottom: 22 }}>{scene.chip}</div>
        <div style={{ color: TEXT, fontSize: 88, fontWeight: 800, letterSpacing: -2, lineHeight: 1.1 }}>{spec.title}</div>
        {spec.subtitle && <div style={{ color: "#38BDF8", fontSize: 38, marginTop: 26, opacity: sub }}>{spec.subtitle}</div>}
      </div>
    </AbsoluteFill>
  );
};
