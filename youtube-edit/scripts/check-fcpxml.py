#!/usr/bin/env python3
"""check-fcpxml.py: pre-flight an FCPXML against the four failure modes that FCP only
reports AFTER import, one at a time, in its own words. Run this before handing the file over.

  1. INVALID EDIT ("未包含相应媒体的无效编辑" / FFXMLReasonInvalidEdit)
     A clip (or a marker/keyword on it) addresses media outside the asset's range.
     The usual cause is NOT a bad cut list: the camera file carries an embedded start
     timecode (09:15:30:00), FCP positions media by that timecode, and the XML declared
     asset start="0s" with 0-based in-points — so every clip lands before frame 1.
     Tell-tale: only the ENABLED clips are reported, disabled ones are not validated.
     Fix: asset/@start = the embedded timecode in seconds, and every SOURCE-side time
     (clip start, marker/keyword start, connected-clip in-point) gets that offset added.
     Timeline-side values (offset, sequence duration) do NOT. This script reads the
     timecode from the media itself and checks the whole file in that coordinate system.

  2. ASSET OVER-REPORT: a clip's start+duration exceeds what the media actually holds.
     FCP's symptom is the whole picture (or the sound) silently going dead, not a warning.
     The usable length is the LAST FRAME'S END, not the container duration — a container
     always runs a fraction of a frame past its last frame (261007's 1-录像: container
     428.360 s, but 10280 frames at 24 fps end at 428.333 s, so declaring the container
     makes the tail clip reference a frame that does not exist). For CFR media the frame
     count is authoritative; a VFR file whose nb_frames and duration disagree (261003's
     录屏-1 averages 53.3 fps against a 60 fps nominal) falls back to the container.

  3. UNALIGNED EDIT ("此项目不在编辑帧边界上" / FFXMLReasonUnalignedEdit): a clip-level
     offset/start/duration that is not a whole multiple of the sequence frameDuration.
     Asset durations and marker times are exempt (markers may land mid-frame).

  4. STRUCTURE: well-formedness, media files actually exist, anchor group (connected
     clips) before marker group on every element that has both, and every asset-clip
     `ref` resolving to a declared asset.

Usage:
  check-fcpxml.py PATH.fcpxml [--probe/--no-probe] [--fps 24]
Exit 1 on any problem, 0 when clean. --probe (default on) runs ffprobe to read each
media file's embedded timecode and frame count; pass --no-probe for a static-only pass.
"""
import argparse, json, os, re, subprocess, sys, urllib.parse
from fractions import Fraction
import xml.etree.ElementTree as ET

ap = argparse.ArgumentParser()
ap.add_argument("xml")
ap.add_argument("--probe", dest="probe", action="store_true", default=True)
ap.add_argument("--no-probe", dest="probe", action="store_false")
ap.add_argument("--fps", type=float, default=0, help="sequence fps; 0 = read frameDuration")
a = ap.parse_args()

bad, notes = [], []
fr = lambda s: Fraction(s[:-1]) if s and s.endswith("s") else Fraction(s or "0")


def probe(path):
    """(start_tc_seconds, usable_length_seconds) from the media itself, or (None, None).

    The usable length is the last frame's END, not the container duration: a container
    always runs a fraction of a frame past its last frame (261007's 1-录像: container
    428.360 s, but 10280 frames at 24 fps end at 428.333 s — declaring 428.360 makes the
    tail clip reference a frame that does not exist). Frame counting only means anything
    for CFR media, so a file whose nb_frames and container duration disagree (a VFR screen
    recording, e.g. 261003's 录屏-1 at an average 53.3 fps) falls back to the container.
    """
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", path],
                             capture_output=True, text=True, timeout=120).stdout
        st = json.loads(out).get("streams", [])
    except Exception:
        return None, None
    tc = None
    for s in st:
        t = (s.get("tags") or {}).get("timecode")
        if t and ":" in t:
            h, m, sec, f = (int(x) for x in t.split(":"))
            tc = h * 3600 + m * 60 + sec + (f / 24.0)
            break
    v = next((s for s in st if s.get("codec_type") == "video"), None)
    if not v:
        return tc, None
    dur = float(v.get("duration") or 0) or None
    nf, rate = v.get("nb_frames"), (v.get("r_frame_rate") or "0/1")
    try:
        num, den = (int(x) for x in rate.split("/"))
        nominal = num / den if den else 0
    except Exception:
        nominal = 0
    if nf and nominal and dur:
        by_frames = int(nf) / nominal
        if abs(by_frames - dur) < 0.5:            # CFR: the frame count is authoritative
            return tc, by_frames
    return tc, dur


try:
    root = ET.parse(a.xml).getroot()
except ET.ParseError as e:
    print("NOT WELL-FORMED: %s" % e); sys.exit(1)

seq = root.find(".//sequence")
fmt = root.find(".//format[@id='%s']" % (seq.get("format") if seq is not None else ""))
fps = a.fps or (1 / float(fr(fmt.get("frameDuration"))) if fmt is not None and fmt.get("frameDuration") else 24.0)
FPS = Fraction(round(fps * 1000), 1000)
on_grid = lambda v: (fr(v) * FPS).denominator == 1

assets = {}
for el in root.findall(".//asset"):
    rep = el.find("media-rep")
    src = urllib.parse.unquote(rep.get("src")[len("file://"):]) if rep is not None and rep.get("src", "").startswith("file://") else None
    assets[el.get("id")] = {"name": el.get("name"), "start": el.get("start") or "0s",
                            "dur": el.get("duration"), "src": src}

if a.probe:
    for aid, A in assets.items():
        if not A["src"]:
            continue
        if not os.path.exists(A["src"]):
            bad.append("MEDIA MISSING: %s → %s" % (A["name"], A["src"])); continue
        tc, usable = probe(A["src"])
        declared = float(fr(A["start"]))
        if tc is not None and abs(tc - declared) > 0.5:
            bad.append("TIMECODE MISMATCH: asset '%s' start=%s but the media's embedded start "
                       "timecode is %.0fs — every clip on it will report '无效编辑' "
                       "(set asset/@start=%ss and add the offset to all source-side times)"
                       % (A["name"], A["start"], tc, int(round(tc))))
        if usable and A["dur"] and float(fr(A["dur"])) > usable + 1e-6:
            bad.append("ASSET OVER-REPORT: asset '%s' duration=%.6fs > the media's usable %.6fs — "
                       "for CFR report nb_frames/fps (the last frame's END, not the container), "
                       "for VFR stay under the container duration"
                       % (A["name"], float(fr(A["dur"])), usable))

for el in root.iter():
    if el.tag not in ("asset-clip", "clip", "sync-clip", "mc-clip", "ref-clip"):
        continue
    # FCP validates ENABLED clips only — a disabled one past the media's end imports
    # without a word (verified: 261003's one over-report is enabled="0" and never warned),
    # so a disabled overrun is a note, not a failure.
    sink = bad if el.get("enabled", "1") == "1" else notes
    ref = el.get("ref")
    if el.tag == "asset-clip":
        if ref not in assets:
            bad.append("DANGLING REF: %s → %s" % (el.get("name"), ref)); continue
        A = assets[ref]
        a0, a1 = fr(A["start"]), fr(A["start"]) + fr(A["dur"] or "0s")
        for who, s, d in [("clip", el.get("start") or A["start"], el.get("duration"))] + \
                         [(c.tag, c.get("start") or "0s", c.get("duration")) for c in el.findall("marker")] + \
                         [(c.tag, c.get("start") or "0s", c.get("duration")) for c in el.findall("keyword")]:
            if d is None:
                continue
            s, d = fr(s), fr(d)
            if s < a0 - 1e-9 or s + d > a1 + 1e-9:
                sink.append("INVALID EDIT: %s '%s' on asset '%s' addresses %.3f–%.3f s, outside "
                            "asset range %.3f–%.3f s" % (who, el.get("name"), A["name"],
                                                         float(s), float(s + d), float(a0), float(a1)))
        # frame grid — clip-level only (browser clips and asset durations are exempt)
        if el.get("offset") is not None:
            if not (on_grid(el.get("offset", "0s")) and on_grid(el.get("start", "0s"))
                    and on_grid(el.get("duration", "0s"))):
                bad.append("UNALIGNED EDIT: %s '%s' offset=%s start=%s duration=%s not on the %.6g fps grid"
                           % (el.tag, el.get("name"), el.get("offset"), el.get("start"),
                              el.get("duration"), fps))
    # anchor group must precede the marker group
    kids = [c.tag for c in el]
    anchors = [i for i, t in enumerate(kids) if t in ("audio", "video", "clip", "title", "caption",
                                                      "mc-clip", "ref-clip", "sync-clip", "asset-clip",
                                                      "audition", "spine")]
    marks = [i for i, t in enumerate(kids) if t in ("marker", "chapter-marker", "rating", "keyword",
                                                    "analysis-marker")]
    if anchors and marks and max(anchors) > min(marks):
        bad.append("ORDER: %s '%s' has a connected clip after a marker/keyword" % (el.tag, el.get("name")))

# spine shape — informational: FCP reflows a hole or an overlap without warning, so
# neither predicts an import problem, but both mean the cut list and the XML disagree.
spine = root.find(".//spine")
if spine is not None:
    pos, holes, overlaps = Fraction(0), [], []
    for c in spine:
        o, d = fr(c.get("offset", "0s")), fr(c.get("duration", "0s"))
        if o > pos:
            holes.append((float(pos), float(o)))
        elif o < pos:
            overlaps.append((float(pos), float(o)))
        pos = o + d
    if holes:
        notes.append("SPINE HOLE: %d, first %s" % (len(holes), holes[:3]))
    if overlaps:
        notes.append("SPINE OVERLAP: %d, first %s (FCP reflows these; the段表 is inconsistent)"
                     % (len(overlaps), overlaps[:3]))
    if seq is not None and seq.get("duration") and abs(float(fr(seq.get("duration"))) - float(pos)) > 1e-6:
        bad.append("DURATION: sequence=%s but the spine ends at %.6f s" % (seq.get("duration"), float(pos)))

for b in bad:
    print("FAIL:", b)
for n in notes:
    print("NOTE:", n)
print("%s: %d problem(s), %d note(s)" % (os.path.basename(a.xml), len(bad), len(notes)))
sys.exit(1 if bad else 0)
