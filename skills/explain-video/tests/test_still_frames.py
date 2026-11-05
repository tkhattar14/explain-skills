import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import still_frames as sf  # noqa: E402


class StillFramesTests(unittest.TestCase):
    def test_waits_for_count_ups_to_settle(self):
        tl = {"scenes": [{"id": "s4", "from": 100, "durationInFrames": 300, "lines": [{"start": 10}, {"start": 120}]}]}
        self.assertEqual(sf.still_frames(tl), [("s4", 100 + 120 + 45)])

    def test_never_runs_past_the_scene(self):
        tl = {"scenes": [{"id": "s0", "from": 0, "durationInFrames": 60, "lines": [{"start": 40}]}]}
        self.assertEqual(sf.still_frames(tl), [("s0", 59)])


if __name__ == "__main__":
    unittest.main()
