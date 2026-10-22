"""Chinese route: transcribe-api.py (VoiceMagic ASR -> transcript.json) and CJK-aware
matching in paper-cut.py / phrase-times.py / beat-check.py. The video language defaults to Chinese."""
import json, os, unittest
from .helpers import ffmpeg, load, run, scratch, write


class TranscribeApi(unittest.TestCase):
    def setUp(self):
        self.d = scratch(self)
        self.out = os.path.join(self.d, "transcript.json")

    def test_from_json_converts_words_to_skill_shape(self):
        resp = {"text": "你好,这是", "words": [
            {"word": "你好,", "start": 0.0, "end": 0.38},
            {"word": "这是", "start": 0.8, "end": 1.06}]}
        r = run("transcribe-api.py", "--from-json", write(os.path.join(self.d, "resp.json"), resp), "--out", self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(load(self.out), {"words": [
            {"text": "你好,", "start": 0.0, "end": 0.38},
            {"text": "这是", "start": 0.8, "end": 1.06}]})

    def test_defaults_are_chinese(self):
        r = run("transcribe-api.py", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        req = json.loads(r.stdout)
        self.assertEqual(req["language"], "zh")
        self.assertEqual(req["service"], "voicemagic")
        self.assertEqual(req["output_format"], "words")

    def test_text_only_response_is_refused(self):
        # a text-only API (no words[]) cannot feed the cut pipeline — refuse loudly, do not fake times
        r = run("transcribe-api.py", "--from-json", write(os.path.join(self.d, "resp.json"),
                {"text": "你好", "duration": 1.0}), "--out", self.out)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("words", r.stderr)

    def test_service_down_is_a_loud_error(self):
        os.environ["VOICEMAGIC_MCP_TOKEN"] = "test-token"
        mp3 = os.path.join(self.d, "a.mp3")
        ffmpeg("-f", "lavfi", "-i", "sine=f=440:d=0.2", "-ar", "16000", "-ac", "1", mp3)
        r = run("transcribe-api.py", "--audio", mp3, "--out", self.out, "--mcp-url", "http://127.0.0.1:1/mcp")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("127.0.0.1:1", r.stderr)


class PaperCutZh(unittest.TestCase):
    def setUp(self):
        self.d = scratch(self)

    def cut(self, words, duration):
        tr = write(os.path.join(self.d, "transcript.json"), {"words": words})
        out = os.path.join(self.d, "out")
        r = run("paper-cut.py", "--transcript", tr, "--duration", str(duration), "--out-dir", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        return load(os.path.join(out, "cut-list.json"))

    def test_repeated_line_keeps_the_last_take(self):
        # 今天天气很好。 said twice 0.5 s apart: one breath, so only the 。 can split the takes
        w, t = [], 1.0
        for _ in range(2):
            for txt, dur in [("今天", 0.25), ("天气", 0.25), ("很好。", 0.30)]:
                w.append({"text": txt, "start": t, "end": t + dur}); t += dur + 0.05
            t += 0.50 - 0.05
        cl = self.cut(w, duration=10.0)
        self.assertTrue(any(str(r["reason"]).startswith("retake") for r in cl["removed"]), cl["removed"])
        self.assertTrue(all(s["start"] >= 2.0 for s in cl["kept"]), cl["kept"])

    def test_mid_sentence_restart_dropped(self):
        # 昨天 我 | 昨天 我们 去了 公园。 — the flub head goes, the clean take stays
        w = [{"text": t, "start": s, "end": s + 0.25} for t, s in
             [("昨天", 1.0), ("我", 1.30), ("昨天", 1.55), ("我们", 1.85), ("去了", 2.15), ("公园。", 2.45)]]
        cl = self.cut(w, duration=10.0)
        self.assertTrue(any(r["reason"] == "restart" for r in cl["removed"]), cl["removed"])
        self.assertTrue(all(s["start"] >= 1.3 for s in cl["kept"]), cl["kept"])

    def test_idiom_with_you_is_not_a_restart(self):
        # 一 遍 又 一 遍 is the phrase, not "keep only the last 一遍"
        w = [{"text": t, "start": 1.0 + i * 0.2, "end": 1.15 + i * 0.2}
             for i, t in enumerate(["一", "遍", "又", "一", "遍。"])]
        cl = self.cut(w, duration=10.0)
        self.assertFalse(any(r["reason"] == "restart" for r in cl["removed"]), cl["removed"])
        self.assertTrue(cl["kept"], cl)

    def test_bare_stutter_still_restarts(self):
        w = [{"text": t, "start": 1.0 + i * 0.2, "end": 1.15 + i * 0.2}
             for i, t in enumerate(["一", "遍", "一", "遍。"])]
        cl = self.cut(w, duration=10.0)
        self.assertTrue(any(r["reason"] == "restart" for r in cl["removed"]), cl["removed"])

    def test_short_chinese_marker_drops_the_flub(self):
        w = [{"text": t, "start": s, "end": s + 0.25} for t, s in
             [("今天", 1.0), ("很好。", 1.4), ("重来", 3.2)]]
        cl = self.cut(w, duration=10.0)
        self.assertTrue(any(str(r["reason"]).startswith("marker") for r in cl["removed"]), cl["removed"])
        self.assertTrue(any(str(r["reason"]).startswith("flub") for r in cl["removed"]), cl["removed"])

    def test_mentioning_retake_in_a_real_sentence_is_kept(self):
        w = [{"text": t, "start": 1.0 + i * 0.3, "end": 1.2 + i * 0.3}
             for i, t in enumerate(["说错了", "就", "重录。"])]
        cl = self.cut(w, duration=10.0)
        self.assertFalse(any("marker" in str(r["reason"]) for r in cl["removed"]), cl["removed"])


class PhraseTimesZh(unittest.TestCase):
    def phrase(self, words, *phrases):
        tr = write(os.path.join(scratch(self), "transcript.json"), {"words": words})
        r = run("phrase-times.py", "--transcript", tr, *phrases)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_finds_phrase_across_chunk_boundaries(self):
        # whisper may chunk 重要的是 as 重/要/的/是 — the phrase must still resolve to its times
        w = [{"text": t, "start": s, "end": s + 0.2} for t, s in
             [("重", 1.0), ("要", 1.2), ("的", 1.4), ("是", 1.6), ("这样", 1.9)]]
        self.assertIn("1.00-1.80", self.phrase(w, "重要的是"))

    def test_english_still_matches(self):
        w = [{"text": "hello", "start": 1.0, "end": 1.2}, {"text": "world", "start": 1.3, "end": 1.5}]
        self.assertIn("1.00-1.50", self.phrase(w, "hello world"))


class BeatCheckZh(unittest.TestCase):
    def test_chinese_anchor_matches_across_chunks(self):
        d = scratch(self)
        w = [{"text": t, "start": s, "end": s + 0.2} for t, s in
             [("重", 1.0), ("要", 1.2), ("的", 1.4), ("是", 1.6)]]
        tr = write(os.path.join(d, "transcript.json"), {"words": w})
        html = write(os.path.join(d, "index.html"),
                     '<div id="c1" class="card-host" data-anchor="重要的是" data-start="1.05"></div>')
        r = run("beat-check.py", "--index", html, "--transcript", tr)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
