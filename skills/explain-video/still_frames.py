#!/usr/bin/env python3
"""Pick one still frame per scene for the render check.

Usage: still_frames.py PATH/timeline.json   -> prints "<scene-id> <frame>" per line.
The frame is SETTLE frames after the scene's last line starts, so reveals and number
count-ups (30 frames) have finished, but never past the scene's last frame. Stdlib only.
"""
from __future__ import annotations

import json
import sys

SETTLE = 45


def still_frames(timeline: dict, settle: int = SETTLE) -> list[tuple[str, int]]:
    out = []
    for s in timeline["scenes"]:
        frame = s["from"] + s["lines"][-1]["start"] + settle
        out.append((s["id"], min(frame, s["from"] + s["durationInFrames"] - 1)))
    return out


if __name__ == "__main__":
    for scene_id, frame in still_frames(json.load(open(sys.argv[1]))):
        print(scene_id, frame)
