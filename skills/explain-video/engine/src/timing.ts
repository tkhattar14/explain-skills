import type { Cue, Scene, Timeline, TimelineScene } from "./types";

export type Act = { at: number; hot: boolean; rev?: boolean };

export const sceneIndex = (tl: Timeline, frame: number): number => {
  let i = tl.scenes.length - 1;
  while (i > 0 && frame < tl.scenes[i].from) i--;
  return i;
};

export const lineIndex = (ts: TimelineScene, frame: number): number => {
  let li = -1;
  ts.lines.forEach((l, j) => {
    if (frame >= ts.from + l.start) li = j;
  });
  return li;
};

export const lineFrame = (ts: TimelineScene, j: number): number => ts.from + ts.lines[j].start;

/** Highlights for graph views: cues 0..li build up, or only cue li when `only` is true. */
export const graphActs = (scene: Scene, ts: TimelineScene, li: number, only = false) => {
  const nodes: Record<string, Act> = {};
  const edges: Record<string, Act> = {};
  for (let j = only ? Math.max(li, 0) : 0; j <= li; j++) {
    const cue: Cue = scene.lines[j]?.cue ?? {};
    const at = lineFrame(ts, j);
    const hot = j === li;
    cue.nodes?.forEach((id) => (nodes[id] = { at, hot }));
    cue.edges?.forEach((id) => (edges[id] = { at, hot }));
    cue.rev?.forEach((id) => (edges[id] = { at, hot, rev: true }));
  }
  return { nodes, edges };
};

/** Frame at which item i first appears (from `reveal` cues), or null if not yet shown. */
export const revealFrames = (scene: Scene, ts: TimelineScene, li: number, count: number): (number | null)[] => {
  const out: (number | null)[] = Array(count).fill(null);
  for (let j = 0; j <= li; j++) {
    const r = scene.lines[j]?.cue?.reveal ?? 0;
    for (let i = 0; i < Math.min(r, count); i++) {
      if (out[i] === null) out[i] = lineFrame(ts, j);
    }
  }
  return out;
};
