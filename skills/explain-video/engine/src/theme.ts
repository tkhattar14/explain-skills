import { Easing } from "remotion";
import type { Status } from "./types";

export const W = 1920;
export const H = 1080;
export const CAPTION_H = 116;
export const BG = "#0A1020";
export const GRID = "#141D33";
export const PANEL = "#111A2E";
export const TEXT = "#F1F5F9";
export const MUTED = "#8A9BB5";
export const FONT = "Inter, 'SF Pro Display', -apple-system, 'Helvetica Neue', Arial, sans-serif";

const BLUE = "#38BDF8";
const AMBER = "#F59E0B";
const RED = "#F87171";
const GREEN = "#34D399";
const GREY = "#94A3B8";

export const STATUS_COLOR: Record<Status, string> = {
  auto: BLUE, human: AMBER, risk: RED, failed: RED, done: GREEN, verified: GREEN,
  unverified: GREY, pending: GREY, todo: GREY,
};
export const STATUS_LABEL: Record<Status, string> = {
  auto: "automatic", human: "needs you", risk: "risk", failed: "failed", done: "done",
  verified: "verified", unverified: "not verified", pending: "pending", todo: "not done",
};
export const LEGEND: [string, string][] = [
  [BLUE, "automatic"], [AMBER, "needs a person"], [RED, "risk or failed"],
  [GREEN, "done"], [GREY, "not done or not verified"],
];
export const MAP_BOX = { x: 40, y: 80, w: 1840, h: H - CAPTION_H - 100 };
export const MINI_BOX = { x: 40, y: 140, w: 1080, h: 740 };
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const ease = Easing.bezier(0.25, 0.1, 0.25, 1);
