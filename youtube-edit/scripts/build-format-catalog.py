#!/usr/bin/env python3
"""Generate videos/format-catalog: placeholder media + storyboard.json showcasing every compose.py beat type."""
import json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SK = os.path.join(ROOT, "youtube-edit")
W = os.path.join(ROOT, "videos", "format-catalog")
SHARED = os.path.join(W, "_shared")
STEP = 4.2
PAD = 0.35


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def slot(i):
    t = PAD + i * STEP
    return t, t + STEP - 0.15


def main():
    os.makedirs(os.path.join(W, "public"), exist_ok=True)
    os.makedirs(os.path.join(SHARED, "img", "thumbs"), exist_ok=True)
    os.makedirs(os.path.join(SHARED, "sfx"), exist_ok=True)
    os.makedirs(os.path.join(W, "broll"), exist_ok=True)

    # reuse house sfx when available
    for name in ("typing.mp3", "pop.mp3"):
        for base in (
            os.path.expanduser("~/.cursor/skills/media-use/audio/assets/sfx"),
            os.path.expanduser("~/.claude/skills/media-use/audio/assets/sfx"),
        ):
            src = os.path.join(base, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(SHARED, "sfx", name))
                break

    pub = os.path.join(W, "public")
    inp = os.path.join(pub, "input-video.mp4")
    if not os.path.isfile(inp):
        run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=0x5a5a62:s=1920x1080:r=30:d=300",
            "-f", "lavfi", "-i", "testsrc2=s=420x520:r=30:d=300",
            "-f", "lavfi", "-i", "sine=f=180:sample_rate=48000:d=300",
            "-filter_complex",
            "[1]hue=s=0.25[h];[0][h]overlay=x='960-210+90*sin(2*PI*t/5)':y='280+25*sin(2*PI*t/4)'[v]",
            "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", inp,
        ])

    site_png = os.path.join(SHARED, "img", "site.png")
    if not os.path.isfile(site_png):
        run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "gradients=s=1340x830:c0=0x1a2332:c1=0x0d1118",
            "-frames:v", "1", site_png,
        ])
    studio = os.path.join(SHARED, "img", "studio.png")
    if not os.path.isfile(studio):
        run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "testsrc2=s=1920x1080:rate=1:duration=1",
            "-frames:v", "1", studio,
        ])
    photo = os.path.join(SHARED, "img", "photo.jpg")
    if not os.path.isfile(photo):
        run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "testsrc=size=1200x800:rate=1:duration=1",
            "-frames:v", "1", photo,
        ])
    for i in range(6):
        p = os.path.join(SHARED, "img", "thumbs", "t%d.jpg" % i)
        if not os.path.isfile(p):
            run([
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                "-i", "testsrc2=s=640x360:rate=1:duration=1",
                "-vf", "hue=h=%d" % (i * 40),
                "-frames:v", "1", p,
            ])
    for name, color in (("logo-a.svg", "#e74c3c"), ("logo-b.svg", "#3498db"), ("tool.svg", "#9b59b6")):
        path = os.path.join(SHARED, "img", name)
        if not os.path.isfile(path):
            open(path, "w").write(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" fill="%s"/></svg>' % color
            )
    yt = os.path.join(SHARED, "img", "youtube.svg")
    if not os.path.isfile(yt):
        open(yt, "w").write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80"><rect width="120" height="80" rx="12" fill="#ff0000"/>'
            '<polygon points="52,24 52,56 78,40" fill="#fff"/></svg>'
        )
    li = os.path.join(SHARED, "img", "linkedin.svg")
    if not os.path.isfile(li):
        open(li, "w").write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 30"><text x="0" y="22" font-size="20" fill="#0A66C2">in</text></svg>'
        )
    clip_mp4 = os.path.join(W, "broll", "desk.mp4")
    if not os.path.isfile(clip_mp4):
        run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
            "-i", "testsrc2=s=1920x1080:rate=30:duration=8",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", clip_mp4,
        ])

    beats = []
    i = 0

    def add(b):
        nonlocal i
        tin, tout = slot(i)
        b = dict(b)
        b.setdefault("in", tin)
        b.setdefault("out", tout)
        b.setdefault("anchor", "-")
        beats.append(b)
        i += 1

    add({"type": "line", "id": "ln0", "text": "Format 2 lower line", "em": [2]})
    tin, _ = slot(i - 1)
    add({"type": "line", "id": "ln1", "text": "Format 16 shimmer line", "shimmer": True, "em": [1]})
    add({"type": "logo", "id": "lg", "src": "img/youtube.svg", "pop": slot(i - 1)[0] + 0.2, "pos": "tl"})
    add({"type": "list", "id": "ls", "eyebrow": "Glass list 3a", "items": [["One", slot(i)[0] + 0.3], ["Two", slot(i)[0] + 0.7]]})
    add({"type": "list", "id": "lsc", "eyebrow": "Check list", "marker": "check",
         "items": [["Done", slot(i)[0] + 0.35], ["Next", slot(i)[0] + 0.75]]})
    add({"type": "bullets", "id": "bu", "items": [["Bullet A", slot(i)[0] + 0.3], ["Bullet B", slot(i)[0] + 0.8]]})
    add({"type": "chip", "id": "ch", "text": "Format 5 chip", "em": [1]})
    add({"type": "vignette", "id": "vg"})
    add({"type": "pointer", "id": "pt"})
    add({"type": "site", "id": "st", "src": "img/site.png", "domain": "example.com"})
    add({"type": "grid", "id": "gr", "images": ["img/thumbs/t%d.jpg" % j for j in range(6)],
         "click_index": 2, "click_at": slot(i)[0] + 1.2})
    for kind, steps in (
        ("money", {"drop": None}),
        ("catalog", {"fill": None, "shine": None}),
        ("room", {"furnish": None, "shine": None}),
        ("plate", {"snap": None, "spice": None}),
        ("profile", {"card": None, "headshot": None}),
    ):
        tin, tout = slot(i)
        st = {k: (tin + 0.3 if k == list(steps.keys())[0] else tin + 1.6) for k in steps}
        if kind == "profile":
            st = {"card": tin + 0.2, "headshot": tin + 2.0}
        elif kind == "room":
            st = {"furnish": tin + 0.4, "shine": tin + 2.2}
        elif kind == "catalog":
            st = {"fill": tin + 0.3, "shine": tin + 1.5}
        elif kind == "plate":
            st = {"snap": tin + 0.2, "spice": tin + 1.6}
        else:
            st = {"drop": tin + 0.3}
        add({"type": "scene", "id": "sc-" + kind, "kind": kind, "steps": st, "label": "Scene " + kind, "label_at": tin + 0.5})
    tin, tout = slot(i)
    add({"type": "browser3d", "id": "b3", "src": "img/site.png", "domain": "demo.app", "scroll": 400,
         "find_at": tin + 1.0, "label": "3D browser 4c"})
    add({"type": "fan3d", "id": "fn", "images": ["img/thumbs/t0.jpg", "img/thumbs/t1.jpg", "img/thumbs/t2.jpg"],
         "frame": "card", "at": [slot(i)[0] + 0.2, slot(i)[0] + 0.35, slot(i)[0] + 0.5],
         "focus": {"index": 1, "at": slot(i)[0] + 1.5}})
    tin, tout = slot(i)
    add({"type": "stats", "id": "sta", "title": "Stat tiles 24", "layout": "row",
         "items": [{"value": 128, "suffix": "+", "label": "Videos", "at": tin + 0.4}]})
    tin, tout = slot(i)
    add({"type": "growth", "id": "gw", "eyebrow": "Growth 25", "value": 48, "prefix": "+", "suffix": "%",
         "bars": [20, 35, 55, 75, 100], "count_at": tin + 0.3, "bars_at": tin + 0.9})
    tin, tout = slot(i)
    add({"type": "growth", "id": "gwm", "morph": True, "badge": "Best week", "eyebrow": "Morph 25m",
         "value": 62, "prefix": "+", "suffix": "%", "bars": [15, 30, 50, 70, 95],
         "count_at": tin + 0.3, "bars_at": tin + 0.8})
    tin, tout = slot(i)
    add({"type": "bars", "id": "bar", "title": "Bar compare 26",
         "rows": [{"label": "A", "value": 6, "text": "6 h", "at": tin + 0.3},
                  {"label": "B", "value": 1.2, "text": "1.2 h", "hi": True, "at": tin + 0.9}]})
    tin, tout = slot(i)
    add({"type": "pipeline", "id": "pip", "steps": [
        {"label": "Idea", "icon": "chat", "at": tin + 0.3},
        {"label": "Ship", "icon": "check", "at": tin + 1.0, "payoff": True}]})
    tin, tout = slot(i)
    add({"type": "hub", "id": "hb", "center": "Trust", "ring_at": tin + 0.3,
         "spokes": [["Earned", tin + 0.6], ["Owned", tin + 1.0]], "resolve_at": tin + 1.8})
    tin, tout = slot(i)
    add({"type": "equation", "id": "eq", "terms": [
        ["A", tin + 0.3], ["+", tin + 0.5], ["B", tin + 0.7], ["=", tin + 0.9], ["C", tin + 1.1, "em"]]})
    tin, tout = slot(i)
    add({"type": "wall", "id": "wl", "slots": ["One", "Two", "Three"], "filled": 1, "now": 2, "fill_at": tin + 0.5})
    tin, tout = slot(i)
    add({"type": "popout", "id": "po", "title": "Popout 3c", "items": [["Item one", tin + 0.4], ["Item two", tin + 0.9]]})
    tin, tout = slot(i)
    add({"type": "flow", "id": "fl", "title": "Flow 30", "source": {"label": "One", "at": tin + 0.3},
         "outputs": [{"label": "Email", "at": tin + 0.7}, {"label": "Shorts", "at": tin + 1.0}],
         "result": {"label": "Subs", "at": tin + 1.6}})
    tin, tout = slot(i)
    add({"type": "dashzoom", "id": "dz", "src": "img/studio.png", "size": [1920, 1080],
         "focus": {"x": 400, "y": 200, "w": 320, "h": 180}, "find_at": tin + 0.8, "lift_at": tin + 1.6,
         "card": {"label": "Views", "value": 1200, "delta": "+12%", "spark": [10, 14, 18, 22, 28]}})
    tin, tout = slot(i)
    add({"type": "lens", "id": "ln", "title": "Lens 32",
         "rows": [["Open", "42%"], ["Click", "8%"]], "stops": [[0, tin + 0.5], [1, tin + 1.2]]})
    tin, tout = slot(i)
    add({"type": "search", "id": "sr", "query": "format catalog", "sound": os.path.isfile(os.path.join(SHARED, "sfx", "typing.mp3")),
         "type_at": tin + 0.3, "cps": 18,
         "results": [{"title": "Result A", "sub": "Subtitle", "color": "cyan", "at": tin + 1.2}]})
    tin, tout = slot(i)
    add({"type": "dock", "id": "dk", "title": "Dock 34",
         "items": [["img/tool.svg", "Tool", tin + 0.4], ["img/logo-a.svg", "App", tin + 0.9]]})
    tin, tout = slot(i)
    add({"type": "masktitle", "id": "mt", "eyebrow": "PART", "text": "Mask title 35", "sub": "subtitle line"})
    tin, tout = slot(i)
    add({"type": "player", "id": "pv", "label": "Watch next 36", "thumb": "img/thumbs/t0.jpg",
         "title": "Next video", "length": 320, "morph_at": tin + 0.6})
    tin, tout = slot(i)
    add({"type": "image", "id": "im", "src": "img/photo.jpg", "reveal_at": tin + 0.5, "label": "Image 37"})
    tin, tout = slot(i)
    add({"type": "imagecard", "id": "ic", "src": "img/photo.jpg", "query": "sunset", "type_at": tin + 0.3,
         "reveal_at": tin + 1.0, "slats": 6})
    tin, tout = slot(i)
    add({"type": "layers", "id": "ly", "title": "Layers 38", "split_at": tin + 0.6,
         "layers": [{"label": "UI"}, {"label": "Logic"}, {"label": "Data"}]})
    tin, tout = slot(i)
    add({"type": "world", "id": "wd", "in": tin, "out": tout + 1.5,
         "nodes": [
             {"id": "a", "kind": "orb", "x": 960, "y": 540, "icon": "shield", "label": "Core", "at": tin + 0.3, "lit": tin + 1.0},
             {"id": "b", "kind": "card", "x": 400, "y": 540, "label": "Left", "at": tin + 0.8},
         ],
         "links": [{"from": "b", "to": "a", "at": tin + 1.2}],
         "cam": [[tin, 960, 540, 1.0], [tin + 1.5, 700, 540, 1.3, 1.0]]})
    i += 1  # world used extra time
    tin, tout = slot(i)
    add({"type": "deck", "id": "dek", "head": "DECK 40", "now": 2, "cards": [{"title": "One", "icon": "user"}, {"title": "Two", "icon": "bolt"}],
         "recap_at": tout - 0.5})
    add({"type": "pills", "id": "pl", "layout": "row",
         "items": [["Tag A", slot(i)[0] + 0.3], {"text": "Risk", "at": slot(i)[0] + 0.7, "tone": "amber", "mark": "x"}]})
    add({"type": "chat", "id": "cf", "frame": "float", "pos": "tr",
         "messages": [["them", "Chat 42?", slot(i)[0] + 0.4], ["me", "Yes.", slot(i)[0] + 0.9]]})
    para = "This paragraph is read aloud on camera for doc format eighteen b."
    tin, tout = slot(i)
    add({"type": "doc", "id": "dc", "domain": "example.com", "title": "Doc read", "paras": [para],
         "marks": [{"text": "read aloud", "at": tin + 0.8}]})
    add({"type": "clip", "id": "cl", "src": "broll/desk.mp4", "label": "Clip 20c", "items": [["B-roll", slot(i)[0] + 0.4]]})

    duration = max(float(b["out"]) for b in beats) + 2.0
    spec = {
        "id": "format-catalog",
        "duration": duration,
        "video": "input-video.mp4",
        "origin": "52% 0%",
        "tag": {"n": 1, "of": 1, "label": "Format catalog", "in": 0.2, "out": min(5.0, duration)},
        "beats": beats,
        "camera": [["creep", 0.5, min(12.0, duration * 0.15), 1.08], ["set", duration * 0.5, 1.0]],
    }
    path = os.path.join(W, "storyboard.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print("wrote", path, "duration=%.1fs beats=%d" % (duration, len(beats)))

    shutil.copy2(clip_mp4, os.path.join(pub, "broll", "desk.mp4"))
    compose = os.path.join(SK, "scripts", "compose.py")
    run([sys.executable, compose, "--spec", path, "--out", pub, "--shared", SHARED])
    shutil.copy2(clip_mp4, os.path.join(pub, "broll", "desk.mp4"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
