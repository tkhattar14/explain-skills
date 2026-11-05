import React from "react";
import { Composition } from "remotion";
import { Explainer } from "./Explainer";
import type { Props } from "./types";
import sample from "../fixtures/props.sample.json";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Explainer"
    component={Explainer}
    fps={30}
    width={1920}
    height={1080}
    durationInFrames={90}
    defaultProps={sample as unknown as Props}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.max(1, props.timeline.totalFrames),
      fps: props.timeline.fps,
    })}
  />
);
