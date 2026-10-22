"""VoiceMagic ASR for youtube-edit scripts (same contract as MCP voicemagic_transcribe_audio)."""
import base64, json, os, subprocess, sys, tempfile, urllib.error, urllib.request

DEFAULT_MCP_URL = "https://voicemagic.demo2easy.com/mcp"
TOKEN_ENV = ("VOICEMAGIC_MCP_TOKEN", "VOICEMAGIC_TOKEN", "X_VOICEMAGIC_MCP_TOKEN")


def token():
    for k in TOKEN_ENV:
        v = os.environ.get(k, "").strip()
        if v:
            return v
    try:
        cfg = json.load(open(os.path.expanduser("~/.cursor/mcp.json")))
        return cfg["mcpServers"]["voicemagic"]["headers"]["x-voicemagic-mcp-token"].strip()
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return ""


def to_transcript_words(resp):
    """Normalize OpenAI verbose_json, VoiceMagic transcript, or MCP tool payload → skill words[]."""
    if isinstance(resp, dict) and "words" in resp and isinstance(resp["words"], list):
        raw = resp["words"]
    elif isinstance(resp, dict) and isinstance(resp.get("transcript"), dict):
        tr = resp["transcript"]
        raw = tr.get("words") or []
        if not raw and tr.get("text") and not tr.get("format"):
            sys.exit("refusing: transcript has text only — word timestamps are required for the cut pipeline.")
    else:
        raw = []
    if not raw:
        sys.exit("refusing: no words[] in the response — set output_format=words (VoiceMagic) or "
                 "timestamp_granularities[]=word (legacy OpenAI). A text-only response cannot feed the cut pipeline.")
    out = []
    for w in raw:
        if not isinstance(w, dict):
            continue
        tx = w.get("text") or w.get("word") or ""
        if "start" not in w or "end" not in w:
            continue
        out.append({"text": tx, "start": float(w["start"]), "end": float(w["end"])})
    if not out:
        sys.exit("refusing: words[] had no usable {text|word,start,end} entries.")
    return {"words": out}


def _parse_mcp_body(raw):
    try:
        outer = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit("bad JSON from VoiceMagic MCP:\n%s" % raw[:500])
    if outer.get("error"):
        sys.exit("VoiceMagic MCP error: %s" % outer["error"])
    result = outer.get("result") or {}
    texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
    if not texts:
        sys.exit("VoiceMagic MCP returned no text content.")
    try:
        payload = json.loads(texts[0])
    except json.JSONDecodeError:
        sys.exit("VoiceMagic MCP text was not JSON:\n%s" % texts[0][:500])
    if payload.get("transcript"):
        return payload
    task = payload.get("task") or {}
    if task.get("status") == "failed":
        sys.exit("VoiceMagic ASR failed: %s" % (task.get("error_message") or task))
    if task.get("result_data"):
        rd = task["result_data"]
        if isinstance(rd, str):
            rd = json.loads(rd)
        if isinstance(rd, dict) and rd.get("transcript"):
            return rd
        if isinstance(rd, dict) and rd.get("words"):
            return rd
    sys.exit("VoiceMagic ASR did not return transcript.words — check membership (words format) and quota.")


def transcribe_file(path, language="zh", engine="auto", mcp_url=DEFAULT_MCP_URL, timeout=600):
    """Upload one audio file; return {"words": [...]} in skill shape."""
    tok = token()
    if not tok:
        sys.exit("no VoiceMagic token — set VOICEMAGIC_MCP_TOKEN (site: 我的 → MCP 令牌, vmpat_…), "
                 "or configure voicemagic in ~/.cursor/mcp.json")
    if not os.path.isfile(path):
        sys.exit("no such audio file: %s" % path)
    mp3 = path
    tmp = None
    if not path.lower().endswith(".mp3"):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", path, "-codec:a", "libmp3lame", "-q:a", "2", tmp.name],
            check=True,
        )
        mp3 = tmp.name
    b64 = base64.b64encode(open(mp3, "rb").read()).decode()
    if tmp:
        os.unlink(tmp.name)
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "voicemagic_transcribe_audio",
            "arguments": {
                "audio_base64": b64,
                "file_name": os.path.basename(mp3) if mp3.endswith(".mp3") else "audio.mp3",
                "output_format": "words",
                "language": language or None,
                "engine": engine,
                "wait_until_complete": True,
            },
        },
    }).encode()
    req = urllib.request.Request(
        mcp_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-voicemagic-mcp-token": tok,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit("cannot reach VoiceMagic at %s — HTTP %s\n%s" % (mcp_url, e.code, e.read()[:500].decode(errors="replace")))
    except urllib.error.URLError as e:
        sys.exit("cannot reach VoiceMagic at %s — %s" % (mcp_url, e.reason))
    return to_transcript_words(_parse_mcp_body(raw))
