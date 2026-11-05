import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import make_vo as mv  # noqa: E402

FIXTURE = HERE / "engine" / "fixtures" / "all-scenes.json"


def fake_alignment(text):
    return {"characters": list(text), "character_start_times_seconds": [i * 0.05 for i in range(len(text))],
            "character_end_times_seconds": [i * 0.05 + 0.05 for i in range(len(text))]}


class MakeVoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        (self.out / "video").mkdir()
        shutil.copy(FIXTURE, self.out / "video" / "video.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = mv.main([str(self.out), *args])
        return code, buf.getvalue()

    def timeline(self):
        return json.loads((self.out / "video" / "timeline.json").read_text())

    def test_api_key_env_then_zshrc(self):
        self.assertEqual(mv.api_key({"ELEVENLABS_API_KEY": "sk_env"}, Path("/nonexistent")), "sk_env")
        rc = self.out / "zshrc"
        rc.write_text('export PATH=/x\nexport ELEVENLABS_API_KEY="sk_rc"\n')
        self.assertEqual(mv.api_key({}, rc), "sk_rc")
        with self.assertRaises(mv.VoiceError):
            mv.api_key({}, self.out / "missing")

    def test_line_starts_exact_alignment(self):
        says = ["Hi there.", "Bye."]
        text = "Hi there. Bye."
        starts = [i * 0.1 for i in range(len(text))]
        self.assertEqual([round(x, 3) for x in mv.line_starts(says, list(text), starts)], [0.0, 1.0])

    def test_line_starts_proportional_when_lengths_differ(self):
        says = ["Hi there.", "Bye."]
        starts = [i * 0.1 for i in range(7)]
        self.assertEqual([round(x, 3) for x in mv.line_starts(says, list("abcdefg"), starts)], [0.0, 0.5])

    def test_estimate(self):
        starts, total = mv.estimate(["one two three", "four"])
        self.assertEqual(starts, [0.0, 1.5])
        self.assertEqual(total, 2.2)

    def test_build_timeline_frames(self):
        spec = {"scenes": [{"id": "a", "lines": [{}, {}]}, {"id": "b", "lines": [{}]}]}
        per = [([0.0, 1.0], 2.0, "audio/a.mp3"), ([0.0], 1.0, "audio/b.mp3")]
        t = mv.build_timeline(spec, per, True, fps=30, lead=0.5, tail=1.0)
        self.assertEqual(t["totalFrames"], 180)
        self.assertEqual(t["scenes"][0], {"id": "a", "from": 0, "durationInFrames": 105, "leadFrames": 15,
                                          "audio": "audio/a.mp3", "lines": [{"start": 15}, {"start": 45}]})
        self.assertEqual(t["scenes"][1]["from"], 105)
        self.assertEqual(t["scenes"][1]["durationInFrames"], 75)

    def test_no_voice_flag(self):
        code, out = self.run_main("--no-voice")
        self.assertEqual(code, 0)
        self.assertIn("NO VOICE", out)
        t = self.timeline()
        self.assertFalse(t["hasAudio"])
        self.assertEqual(len(t["scenes"]), 6)
        self.assertTrue(all(s["audio"] is None for s in t["scenes"]))

    def test_voice_failure_falls_back(self):
        with mock.patch.object(mv, "api_key", return_value="k"), \
             mock.patch.object(mv, "tts", side_effect=mv.VoiceError("HTTP 401")):
            code, out = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("NO VOICE: HTTP 401", out)
        self.assertFalse(self.timeline()["hasAudio"])

    def test_voice_pass_writes_audio_and_caches_by_text(self):
        calls = []

        def fake_tts(key, voice, model, text, prev=None, nxt=None):
            calls.append(text)
            return b"ID3fake", fake_alignment(text)

        with mock.patch.object(mv, "api_key", return_value="k"), \
             mock.patch.object(mv, "tts", side_effect=fake_tts), \
             mock.patch.object(mv, "mp3_seconds", return_value=4.0):
            self.run_main()
            self.assertEqual(len(calls), 6)
            t = self.timeline()
            self.assertTrue(t["hasAudio"])
            self.assertEqual(t["scenes"][0]["audio"], "audio/s0.mp3")
            self.assertTrue((self.out / "video" / "audio" / "s0.mp3").exists())
            self.run_main()
            self.assertEqual(len(calls), 6, "unchanged scenes must not be regenerated")
            spec = json.loads((self.out / "video" / "video.json").read_text())
            spec["scenes"][2]["lines"][0]["say"] = "First, it wrote one new command."
            (self.out / "video" / "video.json").write_text(json.dumps(spec))
            self.run_main()
            self.assertEqual(len(calls), 7, "only the edited scene regenerates")
            self.assertEqual(calls[-1].split(".")[0], "First, it wrote one new command")

    def test_changing_the_voice_regenerates_every_scene(self):
        calls = []

        def fake_tts(key, voice, model, text, prev=None, nxt=None):
            calls.append(voice)
            return b"ID3fake", fake_alignment(text)

        with mock.patch.object(mv, "api_key", return_value="k"), \
             mock.patch.object(mv, "tts", side_effect=fake_tts), \
             mock.patch.object(mv, "mp3_seconds", return_value=4.0):
            self.run_main()
            spec = json.loads((self.out / "video" / "video.json").read_text())
            spec["voice_id"] = "OTHER_VOICE"
            (self.out / "video" / "video.json").write_text(json.dumps(spec))
            self.run_main()
        self.assertEqual(len(calls), 12)
        self.assertEqual(calls[-1], "OTHER_VOICE")


if __name__ == "__main__":
    unittest.main()
