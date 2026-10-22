"""retranscribe-holes.py: the level test that separates a hallucinated transcript from real speech.

The ASR endpoint is faked: --mcp-url points at a local server that returns a fixed word list in VoiceMagic
MCP shape, so the test exercises detection and merge logic without calling the real service.
"""
import json, os, threading, unittest, wave
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np

from .helpers import run, scratch, write, needs_ffmpeg


def _wav(path, seconds, sr=16000, segments=None, floor=40):
    """Silence at `floor`, with a 2 kHz tone at 8000 over each (start, end) of `segments` (speech)."""
    x = np.random.default_rng(7).normal(0, floor, int(seconds * sr))
    for a, b in (segments or []):
        i0, i1 = int(a * sr), int(b * sr)
        x[i0:i1] = 8000 * np.sin(2 * np.pi * 2000 * np.arange(i1 - i0) / sr)
    w = wave.open(path, "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(np.clip(x, -32768, 32767).astype("<i2").tobytes()); w.close()
    return path


class _FakeMCP(BaseHTTPRequestHandler):
    words = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self.rfile.read(n)
        inner = json.dumps({
            "transcript": {
                "format": "words",
                "words": [{"word": t, "start": s, "end": e} for s, e, t in self.words],
            },
        })
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": inner}]},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def _serve(words):
    _FakeMCP.words = words
    srv = HTTPServer(("127.0.0.1", 0), _FakeMCP)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d/mcp" % srv.server_address[1]


@needs_ffmpeg
class RetranscribeHoles(unittest.TestCase):
    def setUp(self):
        self.d = scratch(self)
        os.environ["VOICEMAGIC_MCP_TOKEN"] = "test-token"

    def make(self, seconds, speech, words):
        """A wav with `speech` zones, a transcript holding `words`, and a fake MCP ASR. Returns (wav, json)."""
        audio = _wav(os.path.join(self.d, "a.wav"), seconds, segments=speech)
        tr = write(os.path.join(self.d, "t.json"), {"words": [{"start": s, "end": e, "text": t} for s, e, t in words]})
        srv, url = _serve([(1.0, 1.4, "新"), (1.5, 1.9, "词")])
        self.addCleanup(srv.shutdown)
        return audio, tr, url

    def read(self, tr):
        with open(tr) as f:
            return json.load(f)["words"]

    def test_loud_zone_with_no_word_is_re_transcribed(self):
        audio, tr, url = self.make(4.0, [(0.0, 2.0)], [(2.2, 2.6, "后")])
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url,
                "--win", "3", "--step", "2", "--thr", "600")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = self.read(tr)
        self.assertEqual([q["text"] for q in got if q["start"] < 2.0], ["新", "词"])
        self.assertEqual([q["text"] for q in got if q["start"] >= 2.0], ["后"], "the tail must survive untouched")

    def test_word_over_silence_is_dropped_as_invented(self):
        audio, tr, url = self.make(7.0, [(0.0, 1.0), (6.0, 7.0)],
                                   [(0.2, 0.6, "真"), (3.0, 3.4, "幻"), (3.6, 4.0, "觉"), (4.2, 4.6, "词"),
                                    (6.1, 6.5, "真2")])
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url,
                "--thr", "600", "--phantom-run", "3", "--phantom-span", "1.0")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = [q["text"] for q in self.read(tr)]
        self.assertIn("真", got); self.assertIn("真2", got)
        for bad in ("幻", "觉", "词"):
            self.assertNotIn(bad, got, r.stdout)

    def test_a_single_quiet_word_is_not_dropped(self):
        audio, tr, url = self.make(4.0, [(0.0, 1.0), (2.0, 4.0)],
                                   [(0.2, 0.6, "真"), (1.2, 1.5, "顿")])
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url,
                "--thr", "600", "--phantom-run", "3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = [q["text"] for q in self.read(tr)]
        self.assertIn("顿", got, r.stdout)

    def test_original_is_kept_as_orig(self):
        audio, tr, url = self.make(4.0, [(0.0, 2.0)], [])
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url,
                "--win", "3", "--step", "2", "--thr", "600")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(tr + ".orig"), "the first patch must leave a .orig copy")

    def test_dry_run_changes_nothing(self):
        audio, tr, url = self.make(4.0, [(0.0, 2.0)], [(2.2, 2.6, "后")])
        with open(tr) as f:
            before = f.read()
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url,
                "--win", "3", "--step", "2", "--thr", "600", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stdout)
        with open(tr) as f:
            self.assertEqual(f.read(), before)
        self.assertFalse(os.path.exists(tr + ".orig"))

    def test_clean_transcript_is_left_alone(self):
        audio, tr, url = self.make(4.0, [(0.0, 2.0), (2.4, 4.0)],
                                   [(0.2, 0.6, "一"), (1.0, 1.4, "二"), (2.6, 3.0, "三")])
        with open(tr) as f:
            before = f.read()
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url, "--thr", "600")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("nothing to do", r.stdout)
        with open(tr) as f:
            self.assertEqual(f.read(), before)

    def test_head_until_replaces_the_whole_head(self):
        audio, tr, url = self.make(6.0, [(0.0, 3.0)], [(0.2, 0.6, "旧"), (3.2, 3.6, "后")])
        r = run("retranscribe-holes.py", "--audio", audio, "--transcript", tr, "--mcp-url", url,
                "--win", "3", "--step", "2", "--thr", "600", "--head-until", "3")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = [q["text"] for q in self.read(tr)]
        self.assertNotIn("旧", got, "the head's old words must be replaced wholesale")
        self.assertIn("新", got)
        self.assertIn("后", got)


if __name__ == "__main__":
    unittest.main()
