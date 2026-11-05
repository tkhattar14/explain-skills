import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { Heading, type SceneProps } from "../common";
import { GraphView } from "../GraphView";
import { clamp, ease, MINI_BOX, MUTED, PANEL, STATUS_COLOR, TEXT } from "../theme";
import { graphActs, revealFrames } from "../timing";

export const TakeawaysScene: React.FC<SceneProps> = ({ spec, scene, ts, frame, li, miniLayout, graphRevealAt }) => {
  if (scene.type !== "takeaways") return null;
  const shown = revealFrames(scene, ts, li, scene.cards.length);
  const current = (scene.lines[li]?.cue?.reveal ?? 0) - 1;
  const withMap = !!scene.mini_map && !!miniLayout && !!spec.graph;
  const acts = graphActs(scene, ts, li, true);
  const left = withMap ? 1160 : 360;
  const width = withMap ? 720 : 1200;
  return (
    <AbsoluteFill>
      {withMap && miniLayout && spec.graph && (
        <GraphView nodes={spec.graph.nodes} edges={spec.graph.edges} layout={miniLayout} box={MINI_BOX}
          frame={frame} revealAt={graphRevealAt} nodeActs={acts.nodes} edgeActs={acts.edges} dim={0.3} />
      )}
      <div style={{ position: "absolute", left, top: 130, width }}>
        <Heading text={scene.chip} frame={frame} at={ts.from} />
        {scene.cards.map((c, i) => {
          const at = shown[i];
          if (at === null) return null;
          const o = interpolate(frame, [at, at + 12], [0, 1], clamp);
          const x = interpolate(frame, [at, at + 16], [30, 0], { ...clamp, easing: ease });
          const color = STATUS_COLOR[c.status];
          const pulse = i === current ? 0.5 + 0.5 * Math.sin((frame - at) / 5) : 0;
          return (
            <div key={i} style={{ opacity: o, transform: `translateX(${x}px)`, display: "flex", gap: 22, alignItems: "flex-start",
              marginBottom: 26, padding: "20px 24px", borderRadius: 18, background: PANEL, border: `2px solid ${color}`,
              boxShadow: pulse ? `0 0 ${12 + 18 * pulse}px ${color}AA` : "none" }}>
              <div style={{ color, fontSize: 44, fontWeight: 800, lineHeight: 1, width: 30 }}>{i + 1}</div>
              <div>
                <div style={{ color: TEXT, fontSize: 32, fontWeight: 700 }}>{c.title}</div>
                {c.sub && <div style={{ color: MUTED, fontSize: 24, marginTop: 8 }}>{c.sub}</div>}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
