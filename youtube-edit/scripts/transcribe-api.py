#!/usr/bin/env python3
"""transcribe-api.py: word-level transcript.json via VoiceMagic ASR (MCP HTTP, same as voicemagic_transcribe_audio).

The video language defaults to CHINESE. Ask the user before ever using another language — never assume one.

  python3 transcribe-api.py --audio W/audio.wav --out W/transcript.json
  python3 transcribe-api.py --from-json saved.json --out W/transcript.json
  python3 transcribe-api.py --dry-run

Token: VOICEMAGIC_MCP_TOKEN (vmpat_… from the site), or voicemagic in ~/.cursor/mcp.json.
"""
import argparse, json, os, sys

from voicemagic_asr import DEFAULT_MCP_URL, to_transcript_words, transcribe_file

ap = argparse.ArgumentParser()
ap.add_argument("--audio", help="WAV/MP3/other (non-MP3 is converted locally with ffmpeg)")
ap.add_argument("--from-json", help="saved VoiceMagic MCP payload or transcript object")
ap.add_argument("--out", help="where to write transcript.json")
ap.add_argument("--mcp-url", default=os.environ.get("VOICEMAGIC_MCP_URL", DEFAULT_MCP_URL))
ap.add_argument("--language", default="zh", help="ISO code; default zh — ask the user before using another")
ap.add_argument("--engine", default="auto", help="VoiceMagic engine: auto | local | qwen-audio-3.1-asr-flash-filetrans")
ap.add_argument("--dry-run", action="store_true", help="print the request fields as JSON and exit")
args = ap.parse_args()

if args.dry_run:
    print(json.dumps({
        "service": "voicemagic",
        "mcp_url": args.mcp_url,
        "tool": "voicemagic_transcribe_audio",
        "language": args.language,
        "engine": args.engine,
        "output_format": "words",
        "token_env": ["VOICEMAGIC_MCP_TOKEN", "VOICEMAGIC_TOKEN"],
    }, ensure_ascii=False))
    sys.exit(0)

if args.from_json:
    resp = json.load(open(args.from_json))
    t = to_transcript_words(resp)
elif args.audio and args.out:
    t = transcribe_file(args.audio, language=args.language, engine=args.engine, mcp_url=args.mcp_url)
else:
    sys.exit("need --audio and --out (or --from-json / --dry-run)")

json.dump(t, open(args.out, "w"), ensure_ascii=False, indent=1)
print("wrote %s (%d words)" % (args.out, len(t["words"])))
