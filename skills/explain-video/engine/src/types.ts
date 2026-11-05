export type Status = "auto" | "human" | "risk" | "failed" | "done" | "verified" | "unverified" | "pending" | "todo";
export type GNode = { id: string; title: string; sub?: string; status: Status };
export type GEdge = { id: string; from: string; to: string; label?: string };
export type Cue = { nodes?: string[]; edges?: string[]; rev?: string[]; reveal?: number };
export type Line = { say: string; show?: string; cue?: Cue };
type Base = { id: string; chip: string; lines: Line[] };
export type Scene =
  | (Base & { type: "title" })
  | (Base & { type: "map" })
  | (Base & { type: "steps"; items: { text: string; status: Status }[] })
  | (Base & { type: "before_after"; pairs: { before: string; after: string }[] })
  | (Base & { type: "numbers"; stats: { label: string; value: string; prefix?: string; suffix?: string }[] })
  | (Base & { type: "takeaways"; mini_map?: boolean; cards: { title: string; sub?: string; status: Status }[] });
export type Spec = {
  title: string;
  subtitle?: string;
  voice_id?: string;
  model_id?: string;
  graph?: { nodes: GNode[]; edges: GEdge[] };
  scenes: Scene[];
};
export type TimelineScene = {
  id: string;
  from: number;
  durationInFrames: number;
  leadFrames: number;
  audio: string | null;
  lines: { start: number }[];
};
export type Timeline = { fps: number; totalFrames: number; hasAudio: boolean; scenes: TimelineScene[] };
export type Props = { spec: Spec; timeline: Timeline };
