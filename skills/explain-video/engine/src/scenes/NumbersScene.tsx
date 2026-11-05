import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { Heading, type SceneProps } from "../common";
import { clamp, ease, MUTED, PANEL, TEXT } from "../theme";
import { revealFrames } from "../timing";

const numeric = (v: string): number | null => {
  const n = Number(v.replace(/,/g, ""));
  return Number.isFinite(n) ? n : null;
};

export const NumbersScene: React.FC<SceneProps> = ({ scene, ts, frame, li }) => {
  if (scene.type !== "numbers") return null;
  const shown = revealFrames(scene, ts, li, scene.stats.length);
  return (
    <AbsoluteFill style={{ padding: "70px 160px 0" }}>
      <Heading text={scene.chip} frame={frame} at={ts.from} />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 40 }}>
        {scene.stats.map((st, i) => {
          const at = shown[i];
          if (at === null) return <div key={i} style={{ width: 500, height: 260 }} />;
          const o = interpolate(frame, [at, at + 12], [0, 1], clamp);
          const p = interpolate(frame, [at, at + 30], [0, 1], { ...clamp, easing: ease });
          const target = numeric(st.value);
          const value = target === null || p >= 1 ? st.value : Math.round(target * p).toLocaleString("en-US");
          return (
            <div key={i} style={{ width: 500, height: 260, boxSizing: "border-box", padding: 32, borderRadius: 20, background: PANEL,
              border: "2px solid #38BDF8", opacity: o, display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <div style={{ color: TEXT, fontSize: 96, fontWeight: 800, lineHeight: 1 }}>
                {st.prefix ?? ""}{value}{st.suffix ?? ""}
              </div>
              <div style={{ color: MUTED, fontSize: 28, marginTop: 18 }}>{st.label}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
