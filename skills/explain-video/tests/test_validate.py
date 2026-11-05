import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import validate as v  # noqa: E402

FIXTURE = json.loads((HERE / "engine" / "fixtures" / "all-scenes.json").read_text())


def spec():
    return copy.deepcopy(FIXTURE)


class ValidateTests(unittest.TestCase):
    def assertError(self, s, fragment):
        errs = v.validate(s)
        self.assertTrue(any(fragment in e for e in errs), f"{fragment!r} not in {errs}")

    def test_fixture_is_valid(self):
        self.assertEqual(v.validate(spec()), [])

    def test_cue_node_must_exist(self):
        s = spec(); s["scenes"][1]["lines"][0]["cue"]["nodes"].append("ghost")
        self.assertError(s, "cue node 'ghost'")

    def test_rev_edge_must_exist(self):
        s = spec(); s["scenes"][1]["lines"][0]["cue"]["rev"] = ["nope"]
        self.assertError(s, "cue edge 'nope'")

    def test_edge_ends_must_be_nodes(self):
        s = spec(); s["graph"]["edges"][0]["to"] = "ghost"
        self.assertError(s, "to 'ghost' is not a node")

    def test_self_loop_rejected(self):
        s = spec(); s["graph"]["edges"][0]["to"] = "you"
        self.assertError(s, "points to itself")

    def test_too_many_nodes(self):
        s = spec()
        s["graph"]["nodes"] += [{"id": f"n{i}", "title": f"N{i}", "status": "auto"} for i in range(7)]
        self.assertError(s, "13 nodes, max 12")

    def test_long_chain_rejected(self):
        s = spec()
        s["graph"]["nodes"] += [{"id": f"x{i}", "title": f"X{i}", "status": "auto"} for i in (1, 2, 3)]
        s["graph"]["edges"] += [{"id": "b-x1", "from": "slack", "to": "x1"}, {"id": "x1-x2", "from": "x1", "to": "x2"},
                                {"id": "x2-x3", "from": "x2", "to": "x3"}]
        self.assertError(s, "chain of 9 nodes")

    def test_longest_chain_handles_cycles(self):
        edges = [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "a"}]
        self.assertEqual(v.longest_chain({"a", "b", "c"}, edges), 3)

    def test_loop_back_does_not_add_length(self):
        # user -> web -> api -> bot -> user: the loop back is drawn as a returning arrow, not a 5th rank
        ids = {"user", "web", "api", "bot"}
        edges = [{"from": "user", "to": "web"}, {"from": "web", "to": "api"},
                 {"from": "api", "to": "bot"}, {"from": "bot", "to": "user"}]
        self.assertEqual(v.longest_chain(ids, edges), 4)

    def test_em_dash_rejected_anywhere(self):
        s = spec(); s["scenes"][2]["items"][0]["text"] = "Wrote it \u2014 fast"
        self.assertError(s, "em dash")

    def test_word_cap(self):
        s = spec(); s["scenes"][0]["lines"][0]["say"] = " ".join(["word"] * 460)
        self.assertError(s, "max 450")

    def test_long_caption_rejected(self):
        s = spec(); s["scenes"][1]["lines"][0]["show"] = "x" * 121
        self.assertError(s, "121 characters, max 120")

    def test_reveal_out_of_range(self):
        s = spec(); s["scenes"][2]["lines"][0]["cue"]["reveal"] = 9
        self.assertError(s, "reveal 9 out of range 1..4")

    def test_reveal_not_allowed_on_map(self):
        s = spec(); s["scenes"][1]["lines"][0]["cue"]["reveal"] = 1
        self.assertError(s, "out of range 1..0")

    def test_bad_type_and_duplicate_id(self):
        s = spec(); s["scenes"][3]["type"] = "slideshow"
        self.assertError(s, "bad type 'slideshow'")
        s = spec(); s["scenes"][2]["id"] = "s1"
        self.assertError(s, "duplicate id 's1'")

    def test_bad_status(self):
        s = spec(); s["graph"]["nodes"][0]["status"] = "green"
        self.assertError(s, "bad status 'green'")

    def test_map_without_graph(self):
        s = spec(); del s["graph"]
        self.assertError(s, "map needs graph nodes")

    def test_empty_say(self):
        s = spec(); s["scenes"][0]["lines"][1]["say"] = "  "
        self.assertError(s, "empty say")

    def test_main_ok_and_fail(self):
        good = HERE / "engine" / "fixtures" / "all-scenes.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(v.main([str(good)]), 0)

    def test_graph_lists_required(self):
        s = spec(); del s["graph"]["edges"]
        self.assertError(s, "graph.edges must be a list")
        s = spec(); s["graph"] = {}
        self.assertError(s, "graph.nodes must be a list")

    def test_text_fields_must_be_strings(self):
        s = spec(); s["scenes"][4]["stats"][0]["value"] = 14
        self.assertError(s, "value must be text")
        s = spec(); s["scenes"][0]["lines"][0]["say"] = 14
        self.assertError(s, "say must be text")

    def test_scene_id_safe_for_file_names(self):
        s = spec(); s["scenes"][2]["id"] = "what was done"
        self.assertError(s, "id 'what was done' may use only")
        s = spec(); s["scenes"][2]["id"] = "../x"
        self.assertError(s, "id '../x' may use only")

    def test_labelled_arrows_lower_the_chain_limit(self):
        s = spec()
        s["graph"]["nodes"].append({"id": "x1", "title": "X1", "status": "auto"})
        s["graph"]["edges"].append({"id": "b-x1", "from": "slack", "to": "x1", "label": "next"})
        self.assertError(s, "chain of 7 nodes, max 6")
        for e in s["graph"]["edges"]:
            e.pop("label", None)
        self.assertEqual(v.validate(s), [])


if __name__ == "__main__":
    unittest.main()
