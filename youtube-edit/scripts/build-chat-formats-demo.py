#!/usr/bin/env python3
"""Demo video: format 13 (prompt), 13b (claude_chat), 42 (chat window)."""
import json, os, shutil, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SK = os.path.join(ROOT, "youtube-edit")
W = os.path.join(ROOT, "videos", "chat-formats-demo")
SHARED = os.path.join(W, "_shared")


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def main():
    os.makedirs(os.path.join(W, "public"), exist_ok=True)
    os.makedirs(os.path.join(SHARED, "img"), exist_ok=True)
    pub = os.path.join(W, "public")
    inp = os.path.join(pub, "input-video.mp4")
    if not os.path.isfile(inp):
        run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=0x5a5a62:s=1920x1080:r=30:d=50",
            "-f", "lavfi", "-i", "testsrc2=s=420x520:r=30:d=50",
            "-f", "lavfi", "-i", "sine=f=180:sample_rate=48000:d=50",
            "-filter_complex",
            "[1]hue=s=0.25[h];[0][h]overlay=x='960-210+90*sin(2*PI*t/5)':y='280+25*sin(2*PI*t/4)'[v]",
            "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", inp,
        ])
    claude_svg = os.path.join(SHARED, "img", "claude.svg")
    if not os.path.isfile(claude_svg):
        open(claude_svg, "w").write(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="#D97757"/>'
            '<path d="M20 38c8-14 24-14 24-14s-6 10-24 14z" fill="#FAF9F5"/></svg>'
        )
    spec = {
        "id": "chat-formats-demo",
        "duration": 42.0,
        "video": "input-video.mp4",
        "origin": "52% 0%",
        "beats": [
            {"type": "line", "id": "t1", "text": "Format 13 Prompt window", "em": [1], "in": 0.15, "out": 2.8, "anchor": "-"},
            {"type": "prompt", "id": "pr", "text": "帮我写一段产品介绍，语气专业但口语化，大约一百字",
             "in": 0.5, "out": 12.5, "type_at": 1.2, "type_end": 6.5, "anchor": "-"},
            {"type": "line", "id": "t2", "text": "Format 13b Claude chat", "em": [1], "in": 12.6, "out": 14.5, "anchor": "-"},
            {"type": "claude_chat", "id": "cc",
             "prompt": "Write a short product intro in a friendly professional tone",
             "in": 13.0, "out": 27.0, "type_t0": 14.0, "type_t1": 17.2, "send": 17.6, "think_end": 18.8,
             "head": "Here is a draft structure", "items": [["Hook", "one punchy line"], ["Body", "three benefits"], ["CTA", "try it today"]],
             "item_t0": 19.2, "anchor": "-"},
            {"type": "line", "id": "t3", "text": "Format 42 Chat window", "em": [1, 2], "in": 27.1, "out": 29.0, "anchor": "-"},
            {"type": "chat", "id": "ch", "frame": "window", "name": "Product team", "icon": "user", "in": 28.5, "out": 41.5, "anchor": "-",
             "messages": [
                 ["them", "Can we ship this Friday?", 29.2],
                 ["me", "Yes, if QA finishes by Thursday.", 31.0],
                 ["them", "I'll lock the release notes.", 33.5],
             ]},
        ],
        "camera": [["set", 0.0, 1.0]],
    }
    path = os.path.join(W, "storyboard.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    compose = os.path.join(SK, "scripts", "compose.py")
    run([sys.executable, compose, "--spec", path, "--out", pub, "--shared", SHARED])
    print("wrote", pub, "→ render:", os.path.join(W, "output-chat-formats-1080p.mp4"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
