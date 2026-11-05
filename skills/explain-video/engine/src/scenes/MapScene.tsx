import React from "react";
import { AbsoluteFill, interpolate } from "remotion";
import { type SceneProps, Legend } from "../common";
import { GraphView } from "../GraphView";
import { clamp, MAP_BOX } from "../theme";
import { graphActs } from "../timing";

export const MapScene: React.FC<SceneProps> = ({ spec, scene, ts, frame, li, layout, graphRevealAt, prevType }) => {
  if (!layout || !spec.graph) return null;
  const { nodes, edges } = graphActs(scene, ts, li);
  const o = prevType === "map" ? 1 : interpolate(frame, [ts.from, ts.from + 10], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <GraphView nodes={spec.graph.nodes} edges={spec.graph.edges} layout={layout} box={MAP_BOX} frame={frame}
        revealAt={graphRevealAt} nodeActs={nodes} edgeActs={edges} dim={0.35} />
      <Legend />
    </AbsoluteFill>
  );
};
