#!/usr/bin/env python3
"""retranscribe-holes.py: rebuild a transcript the ASR hallucinated over, before the cut stage trusts it.

Why: over the head of a file the ASR invents a boilerplate line ("请不吝点赞订阅转发打赏支持明镜与点点栏目")
and weaves it through the real speech. Everything downstream then goes wrong in a way no later check sees:
paper-cut reads the line as one repeated take, keeps the last copy, and drops the rest — including the
stretch where the real opening line was spoken. The audio was fine the whole time; only the text lied.

Level decides, not text. A word the ASR invented sits over silence; a word it heard sits over speech.
(Text matching fails here: Chinese ASR emits one character per word and scatters the invented line across
seconds of silence, so it never appears as one contiguous sentence.)

Two repairs:
  - loud run with NO trusted word over it → re-transcribe that zone in small windows (--win/--step);
  - word sitting over silence anywhere → drop it as invented.
A hallucinated head is woven through real speech (the line is recited over it) so level cannot separate the
two there; pass --head-until T to re-transcribe [0, T] wholesale, which is the only repair that works for it.

Usage:
  retranscribe-holes.py --audio W/audio.wav --transcript W/transcript.json [--head-until 120]
                        [--out W/transcript.json] [--win 20] [--step 15] [--thr 800] [--min-loud 0.35]
                        [--merge-gap 0.6] [--engine auto] [--mcp-url URL]
                        [--dry-run]

--thr is the RMS level that counts as speech (261007's camera audio runs 2500-6000 while speaking, <200
silent). Always read the printed zones before trusting the result; --dry-run lists them and stops. Writes
the patched transcript to --out (default: in place) and keeps a .orig copy on the first patch. Re-run the
cut stage from paper-cut.py afterwards — a transcript change invalidates the cut list.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, wave

import numpy as np

from voicemagic_asr import DEFAULT_MCP_URL, transcribe_file

BOILER = ["请不吝点赞订阅转发打赏支持明镜与点点栏目", "简体中文", "请不吝点赞订阅转发打赏"]
BOILER_CHARS = BOILER[0]

ap = argparse.ArgumentParser()
ap.add_argument("--audio", required=True)
ap.add_argument("--transcript", required=True)
ap.add_argument("--out", default="")
ap.add_argument("--win", type=float, default=20.0, help="re-transcribe window length (s)")
ap.add_argument("--step", type=float, default=15.0, help="window step; must be < win so windows overlap")
ap.add_argument("--thr", type=float, default=800, help="RMS at or above this is speech")
ap.add_argument("--min-loud", type=float, default=0.35, help="ignore loud runs shorter than this (s)")
ap.add_argument("--merge-gap", type=float, default=0.6, help="merge holes closer than this (s)")
ap.add_argument("--phantom-run", type=int, default=6, help="a quiet run this many words long is an invented line")
ap.add_argument("--phantom-span", type=float, default=2.0, help="…and must span at least this many seconds")
ap.add_argument("--frac", type=float, default=0.15, help="fraction of a word's span that must be above --thr to trust it")
ap.add_argument("--max-word", type=float, default=1.5, help="a word stretched past this many seconds is invented")
ap.add_argument("--engine", default="auto", help="VoiceMagic ASR engine (see voicemagic skill)")
ap.add_argument("--mcp-url", default=os.environ.get("VOICEMAGIC_MCP_URL", DEFAULT_MCP_URL))
ap.add_argument("--head-until", type=float, default=0.0,
                help="also re-transcribe [0, T] wholesale — for a head the ASR hallucinated end to end, "
                     "where the invented line is woven through real speech and level cannot separate them")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

if a.step >= a.win:
    sys.exit("--step must be smaller than --win so consecutive windows overlap")

T = json.load(open(a.transcript))
words = T["words"] if isinstance(T, dict) else T
words.sort(key=lambda w: w["start"])

# A word the ASR invented sits over silence; a word it heard sits over speech. So level, not text, decides
# which words to trust — matching the boilerplate by text fails anyway, because Chinese ASR emits one
# character per word and scatters the invented line across seconds of silence.
w = wave.open(a.audio)
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
if w.getnchannels() > 1:
    x = x.reshape(-1, w.getnchannels()).mean(axis=1)
hop = max(1, int(0.05 * sr))
n = len(x) // hop
env = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])

def frac(t0, t1):
    """Fraction of [t0, t1] whose RMS window is above threshold — an invented word stretches over silence."""
    i0, i1 = max(0, int(t0 / 0.05)), min(n, max(1, int(t1 / 0.05)))
    return float((env[i0:i1] >= a.thr).mean()) if i1 > i0 else 0.0

trusted = [q for q in words if frac(q["start"], q["end"]) >= a.frac]

# An invented word sits over silence; a heard word sits over speech. Judge by the FRACTION of the word's
# span that is above threshold, not the peak: the ASR stretches an invented word across seconds of silence,
# so one stray syllable inside its span would make a peak test call it real. A word stretched far past any
# plausible syllable is invented on its own, run or not.
PUNCT = set("，。、,.?？!！:：;；")
quiet_run, run = [], []
for q in words + [None]:
    quiet = q is not None and frac(q["start"], q["end"]) < a.frac and q["text"].strip() not in PUNCT
    if quiet:
        run.append(q)
    else:
        if len(run) >= a.phantom_run and run[-1]["end"] - run[0]["start"] >= a.phantom_span:
            quiet_run.extend(run)
        run = []
stretched = [q for q in words if q["end"] - q["start"] > a.max_word]
seen, phantom_drop = set(), []
for q in quiet_run + stretched:
    if id(q) not in seen:
        seen.add(id(q)); phantom_drop.append(q)
phantom_drop.sort(key=lambda q: q["start"])
print("words: %d; dropped as invented: %d (%d in quiet runs, %d stretched past %.1fs)"
      % (len(words), len(phantom_drop), len(quiet_run), len(stretched), a.max_word))
for q in phantom_drop[:8]:
    print("    %7.2f- %7.2f  %5.2fs  %s" % (q["start"], q["end"], q["end"] - q["start"], q["text"]))
if len(phantom_drop) > 8:
    print("    … and %d more, last ends at %.1fs" % (len(phantom_drop) - 8, phantom_drop[-1]["end"]))

runs, cur = [], None
for i, v in enumerate(env >= a.thr):
    if v:
        cur = [i, i] if cur is None else [cur[0], i]
    elif cur is not None:
        if (cur[1] - cur[0] + 1) * 0.05 >= a.min_loud:
            runs.append((cur[0] * 0.05, (cur[1] + 1) * 0.05))
        cur = None
if cur is not None and (cur[1] - cur[0] + 1) * 0.05 >= a.min_loud:
    runs.append((cur[0] * 0.05, (cur[1] + 1) * 0.05))

print("audio %.1fs; loud runs (RMS >= %.0f, >= %.2fs): %d, %.1fs total"
      % (len(x) / sr, a.thr, a.min_loud, len(runs), sum(b - s for s, b in runs)))

# ---- a hole = a loud run with no trusted word in it ----------------------------------
holes = []
for s0, s1 in runs:
    if any(s0 - 0.5 <= q["start"] < s1 for q in trusted):
        continue
    if holes and s0 - holes[-1][1] < a.merge_gap:
        holes[-1][1] = max(holes[-1][1], s1)
    else:
        holes.append([s0, s1])

# A hallucinated head is woven through real speech (the line is recited over it), so level cannot separate
# the two there — but the invented line reads as one repeated take and paper-cut then keeps only the last
# copy. Re-transcribe the whole head instead of guessing.
if a.head_until > 0:
    holes = [[0.0, a.head_until]] + [h for h in holes if h[0] >= a.head_until]

print("\nholes: audio speaking, transcript blank: %d zone(s), %.1fs total" % (len(holes), sum(b - x for x, b in holes)))
for s0, s1 in holes:
    print("    %8.2f- %8.2f  %6.1fs" % (s0, s1, s1 - s0))

if a.head_until > 0:
    phantom_drop = [q for q in phantom_drop if q["start"] >= a.head_until]
kept_words = [q for q in words if q not in phantom_drop]

if not holes and not phantom_drop:
    print("nothing to do"); sys.exit(0)
if a.dry_run:
    print("\n--dry-run: stopping before any transcription"); sys.exit(0)

W = tempfile.mkdtemp(prefix="retholes-")
def transcribe(t0, dur):
    """One ffmpeg cut + one VoiceMagic ASR call; returns [(start, end, text)] in SOURCE seconds."""
    clip = os.path.join(W, "%.2f.mp3" % t0)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t0, "-t", "%.3f" % dur,
                    "-i", a.audio, "-codec:a", "libmp3lame", "-q:a", "2", clip], check=True)
    j = transcribe_file(clip, language="zh", engine=a.engine, mcp_url=a.mcp_url)
    out = []
    for q in j["words"]:
        if q["end"] <= a.step + 1e-6:      # first `step` seconds only: the tail belongs to the next window
            out.append((t0 + q["start"], t0 + q["end"], q["text"]))
    return out

patched = []
for s0, s1 in holes:
    new, t = [], s0
    while t < s1 - 0.05:
        new += transcribe(t, min(a.win, s1 - t))
        t += a.step
    new = [q for q in new if s0 - 0.5 <= q[0] <= s1 + 0.5]
    new.sort()
    dedup, prev = [], None
    for st, en, tx in new:
        if prev is not None and st < prev - 0.01:      # an overlapping window already covered this word
            continue
        dedup.append((st, en, tx)); prev = en
    print("\n  %.2f-%.2f  →  %d words" % (s0, s1, len(dedup)))
    print("     %s" % "".join(q[2] for q in dedup)[:220])
    if dedup:
        patched.append((s0, s1, dedup))

if not patched and not phantom_drop:
    print("\nnothing usable came back; transcript untouched"); sys.exit(1)

out = [q for k, q in enumerate(kept_words)
       if not any(s0 <= q["start"] < s1 for s0, s1, _ in patched)]
for s0, s1, new in patched:
    for st, en, tx in new:
        out.append({"start": round(st, 3), "end": round(en, 3), "text": tx})
out.sort(key=lambda q: q["start"])

dest = a.out or a.transcript
if not os.path.exists(dest + ".orig"):
    shutil.copy(dest, dest + ".orig")
if isinstance(T, dict):
    T["words"] = out
    json.dump(T, open(dest, "w"), ensure_ascii=False, indent=1)
else:
    json.dump(out, open(dest, "w"), ensure_ascii=False, indent=1)
print("\nwrote %s: %d words (was %d; %d dropped as invented, %d replaced by %d re-transcribed)"
      % (dest, len(out), len(words), len(phantom_drop),
         sum(1 for q in words if any(s0 <= q["start"] < s1 for s0, s1, _ in patched)),
         sum(len(n) for _, _, n in patched)))
print("original kept at %s.orig — re-run the cut stage from paper-cut.py; a transcript change invalidates the cut list." % dest)
