#!/usr/bin/env python3
"""phrase-times.py: where is it said? Finds each phrase in a transcript.json and prints the start of its
first word and the end of its last word (seconds), so storyboard beats can be timed to word starts without reading
the whole transcript. Fuzzy on punctuation and case; --after T restricts the search to after T seconds.
Usage: python3 phrase-times.py --transcript W/transcript.json "most important part" "driving force" ... [--after 30]
"""
import argparse, json, re
ap = argparse.ArgumentParser(); ap.add_argument("--transcript", required=True); ap.add_argument("phrases", nargs="+"); ap.add_argument("--after", type=float, default=0.0)
a = ap.parse_args()
d = json.load(open(a.transcript)); W = d["words"] if isinstance(d, dict) and "words" in d else d
# units: ASCII words whole, CJK per character — so a phrase matches across any whisper chunking
units = lambda s: [m.group() for m in re.finditer(r"[a-z0-9']+|[一-鿿]", s.lower())]
flat = [(u, float(w["start"]), float(w["end"])) for w in W for u in units(w["text"])]
for ph in a.phrases:
    p = units(ph); hits = []
    if not p:
        print("%-44s  NOT FOUND" % ph); continue
    for i in range(len(flat) - len(p) + 1):
        if flat[i][1] < a.after: continue
        if all(flat[i + k][0] == p[k] for k in range(len(p))): hits.append((flat[i][1], flat[i + len(p) - 1][2]))
    if not hits: print("%-44s  NOT FOUND" % ph); continue
    print("%-44s  " % ph + "   ".join("%.2f-%.2f" % h for h in hits[:4]) + ("   (+%d more)" % (len(hits) - 4) if len(hits) > 4 else ""))
