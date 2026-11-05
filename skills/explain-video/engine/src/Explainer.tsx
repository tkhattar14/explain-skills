import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import { CaptionBar, Grid, type SceneProps } from "./common";
import { layoutGraph } from "./layout";
import { BeforeAfterScene } from "./scenes/BeforeAfterScene";
import { MapScene } from "./scenes/MapScene";
import { NumbersScene } from "./scenes/NumbersScene";
import { StepsScene } from "./scenes/StepsScene";
import { TakeawaysScene } from "./scenes/TakeawaysScene";
import { TitleScene } from "./scenes/TitleScene";
import { BG, FONT, MAP_BOX, MINI_BOX, MUTED } from "./theme";
import { lineIndex, sceneIndex } from "./timing";
import type { Props, Scene } from "./types";

const Unbuilt: React.FC<SceneProps> = ({ scene }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", color: MUTED, fontSize: 36 }}>
    Scene type "{scene.type}" is not built yet
  </AbsoluteFill>
);

export const VIEWS: Partial<Record<Scene["type"], React.FC<SceneProps>>> = {
  title: TitleScene,
  map: MapScene,
  steps: StepsScene,
  before_after: BeforeAfterScene,
  numbers: NumbersScene,
  takeaways: TakeawaysScene,
};

const usesGraph = (s: Scene) => s.type === "map" || (s.type === "takeaways" && !!s.mini_map);

export const Explainer: React.FC<Props> = ({ spec, timeline }) => {
  const frame = useCurrentFrame();
  const layout = useMemo(
    () => (spec.graph?.nodes.length ? layoutGraph(spec.graph.nodes, spec.graph.edges, { w: MAP_BOX.w, h: MAP_BOX.h }) : null),
    [spec],
  );
  // The takeaways mini map gets its own layout fitted to its narrower box (usually top-to-bottom).
  const miniLayout = useMemo(
    () => (spec.graph?.nodes.length ? layoutGraph(spec.graph.nodes, spec.graph.edges, { w: MINI_BOX.w, h: MINI_BOX.h }) : null),
    [spec],
  );
  if (spec.scenes.length !== timeline.scenes.length) {
    return <AbsoluteFill style={{ background: BG, color: "#F87171", fontSize: 40, padding: 80 }}>video.json and timeline.json disagree; rerun make_vo.py</AbsoluteFill>;
  }
  const si = sceneIndex(timeline, frame);
  const ts = timeline.scenes[si];
  const scene = spec.scenes[si];
  const li = lineIndex(ts, frame);
  const firstGraph = spec.scenes.findIndex(usesGraph);
  const props: SceneProps = {
    spec, scene, ts, frame, li, layout, miniLayout,
    graphRevealAt: firstGraph >= 0 ? timeline.scenes[firstGraph].from : 0,
    prevType: si > 0 ? spec.scenes[si - 1].type : null,
  };
  const View = VIEWS[scene.type] ?? Unbuilt;
  return (
    <AbsoluteFill style={{ backgroundColor: BG, fontFamily: FONT }}>
      <Grid />
      {timeline.hasAudio &&
        timeline.scenes.map((t) =>
          t.audio ? (
            <Sequence key={t.id} from={t.from + t.leadFrames} durationInFrames={t.durationInFrames}>
              <Audio src={staticFile(t.audio)} />
            </Sequence>
          ) : null,
        )}
      <View {...props} />
      <CaptionBar scene={scene} ts={ts} frame={frame} li={li} />
    </AbsoluteFill>
  );
};
