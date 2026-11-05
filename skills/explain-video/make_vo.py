#!/usr/bin/env python3
"""Make narration and line timings for an explain-video spec.

Usage: make_vo.py OUTDIR [--no-voice] [--force]

Reads OUTDIR/video/video.json. Writes OUTDIR/video/audio/<scene>.mp3 (one ElevenLabs
call per scene, cached by scene text) and OUTDIR/video/timeline.json for the Remotion
engine. The voice is video.json's voice_id, else $EXPLAIN_VOICE_ID, else DEFAULT_VOICE.
If the voice call fails, or with --no-voice, it estimates timings at 150 words
per minute, writes no audio, and prints a line starting "NO VOICE:". Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

FPS = 30
LEAD_S = 0.35
TAIL_S = 0.9
WPM = 150
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # ElevenLabs premade voice "George"
DEFAULT_MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.55, "similarity_boost": 0.8, "style": 0.15, "speed": 0.97}


class VoiceError(Exception):
    pass


def api_key(env=os.environ, zshrc: Path = Path.home() / ".zshrc") -> str:
    if env.get("ELEVENLABS_API_KEY"):
        return env["ELEVENLABS_API_KEY"]
    if zshrc.is_file():
        match = re.search(r"ELEVENLABS_API_KEY=['\"]?([^'\"\s]+)", zshrc.read_text(errors="replace"))
        if match:
            return match.group(1)
    raise VoiceError("ELEVENLABS_API_KEY not found in environment or ~/.zshrc")


def scene_text(scene: dict) -> str:
    return " ".join(line["say"].strip() for line in scene["lines"])


def line_starts(says: list[str], chars: list[str], starts: list[float]) -> list[float]:
    """Seconds at which each line begins, from ElevenLabs character alignment."""
    text = " ".join(says)
    exact = len(chars) == len(text)
    result, offset = [], 0
    for say in says:
        if exact:
            result.append(starts[offset])
        else:
            idx = min(len(starts) - 1, round(offset / max(1, len(text)) * len(starts)))
            result.append(starts[idx])
        offset += len(say) + 1
    return result


def estimate(says: list[str], wpm: int = WPM) -> tuple[list[float], float]:
    """Line start seconds and total seconds when there is no audio."""
    per_word = 60.0 / wpm
    starts, t = [], 0.0
    for say in says:
        starts.append(round(t, 3))
        t += max(1, len(say.split())) * per_word + 0.3
    return starts, round(t, 3)


def build_timeline(spec: dict, per_scene: list[tuple], has_audio: bool,
                   fps: int = FPS, lead: float = LEAD_S, tail: float = TAIL_S) -> dict:
    """per_scene: one (line_start_seconds, duration_seconds, audio_path_or_None) per scene."""
    scenes, cursor = [], 0
    lead_f = round(lead * fps)
    for scene, (starts, duration, audio) in zip(spec["scenes"], per_scene):
        dur = round((lead + duration + tail) * fps)
        scenes.append({
            "id": scene["id"],
            "from": cursor,
            "durationInFrames": dur,
            "leadFrames": lead_f,
            "audio": audio,
            "lines": [{"start": lead_f + round(s * fps)} for s in starts],
        })
        cursor += dur
    return {"fps": fps, "totalFrames": cursor, "hasAudio": has_audio, "scenes": scenes}


def tts(key: str, voice: str, model: str, text: str, prev: str | None = None, nxt: str | None = None):
    body = {"text": text, "model_id": model, "voice_settings": SETTINGS}
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise VoiceError(f"HTTP {exc.code}: {exc.read()[:200]!r}") from exc
    except urllib.error.URLError as exc:
        raise VoiceError(f"network: {exc.reason}") from exc
    return base64.b64decode(data["audio_base64"]), data["alignment"]


def mp3_seconds(path: Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", str(path)])
    return float(out.strip())


def voice_pass(spec: dict, vdir: Path, force: bool) -> list[tuple]:
    key = api_key()
    voice = spec.get("voice_id") or os.environ.get("EXPLAIN_VOICE_ID") or DEFAULT_VOICE
    model = spec.get("model_id", DEFAULT_MODEL)
    audio_dir = vdir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    scenes = spec["scenes"]
    per_scene = []
    for i, scene in enumerate(scenes):
        mp3 = audio_dir / f"{scene['id']}.mp3"
        align_path = audio_dir / f"{scene['id']}.align.json"
        text = scene_text(scene)
        saved = json.loads(align_path.read_text()) if align_path.exists() else {}
        cached = (mp3.exists() and saved.get("text") == text
                  and saved.get("voice") == voice and saved.get("model") == model)
        if force or not cached:
            prev = scene_text(scenes[i - 1]) if i else None
            nxt = scene_text(scenes[i + 1]) if i + 1 < len(scenes) else None
            audio, alignment = tts(key, voice, model, text, prev, nxt)
            mp3.write_bytes(audio)
            align_path.write_text(json.dumps({"text": text, "voice": voice, "model": model, "alignment": alignment}))
        alignment = json.loads(align_path.read_text())["alignment"]
        says = [line["say"].strip() for line in scene["lines"]]
        starts = line_starts(says, alignment["characters"], alignment["character_start_times_seconds"])
        per_scene.append((starts, mp3_seconds(mp3), f"audio/{scene['id']}.mp3"))
    return per_scene


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Narration + timeline for explain-video")
    ap.add_argument("outdir")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    vdir = Path(os.path.expanduser(args.outdir)) / "video"
    spec = json.loads((vdir / "video.json").read_text(encoding="utf-8"))
    has_audio = not args.no_voice
    per_scene: list[tuple] = []
    if has_audio:
        try:
            per_scene = voice_pass(spec, vdir, args.force)
        except VoiceError as exc:
            print(f"NO VOICE: {exc}")
            has_audio = False
    else:
        print("NO VOICE: --no-voice given")
    if not has_audio:
        per_scene = []
        for scene in spec["scenes"]:
            starts, total = estimate([line["say"] for line in scene["lines"]])
            per_scene.append((starts, total, None))
    timeline = build_timeline(spec, per_scene, has_audio)
    (vdir / "timeline.json").write_text(json.dumps(timeline, indent=1))
    print(f"timeline: {len(timeline['scenes'])} scenes, {timeline['totalFrames'] / FPS:.1f} s, audio={has_audio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
