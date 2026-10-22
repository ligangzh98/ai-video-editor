"""prompt_window.py: format 13 — dark prompt window, dictated typing (display:none per char, not opacity)."""
import html as _h


def prompt_css():
    return """
  .pw-cut { position:absolute; inset:0; }
  .pw-win { position:absolute; left:260px; top:120px; width:1400px; height:720px; border-radius:20px; overflow:hidden;
    background:#14161c; box-shadow: 0 40px 100px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.08); }
  .pw-bar { height:52px; background:#1c1f28; display:flex; align-items:center; gap:10px; padding:0 20px; }
  .pw-bar .d { width:14px; height:14px; border-radius:50%; } .pw-bar .r { background:#ff5f57; } .pw-bar .y { background:#febc2e; } .pw-bar .g { background:#28c840; }
  .pw-title { margin-left:12px; font-size:22px; font-weight:500; color:rgba(255,255,255,.55); }
  .pw-body { padding:48px 56px; }
  .pw-dict { display:flex; align-items:center; gap:14px; font-size:28px; font-weight:500; color:rgba(43,255,136,.95); margin-bottom:28px; }
  .pw-dict svg { width:32px; height:32px; flex:none; }
  .pw-text { font-size:44px; line-height:1.45; color:#f4f4f5; min-height:120px; }
  .pw-text .ch { display:none; }
  .pw-caret { display:inline-block; width:3px; height:48px; background:#fff; vertical-align:-8px; margin-left:4px; }
"""


def prompt_scene(p, text, t_in, t_out, type_t0, type_t1):
    """Returns (html, js_lines). Composition times in seconds."""
    chars = "".join('<span class="ch">%s</span>' % _h.escape(c) for c in text)
    mic = ('<svg viewBox="0 0 24 24" fill="none"><path d="M12 15a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3z" stroke="currentColor" stroke-width="2"/>'
             '<path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>')
    html = ('<div class="cut pw-cut"><div class="gridbg"></div><div class="pw-win" id="%s-win">'
            '<div class="pw-bar"><span class="d r"></span><span class="d y"></span><span class="d g"></span>'
            '<span class="pw-title">Voice prompt</span></div>'
            '<div class="pw-body"><div class="pw-dict">%s<span>Dictated</span></div>'
            '<div class="pw-text" id="%s-text">%s<span class="pw-caret" id="%s-caret"></span></div></div></div></div>'
            % (p, mic, p, chars, p))
    j = []
    j.append("tl.fromTo('#%s-win', { opacity: 0, y: 24, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: 'power3.out' }, %.3f);" % (p, t_in))
    j.append("(function(){ const cs = document.querySelectorAll('#%s-text .ch'); const n = cs.length; const t0 = %.3f, t1 = %.3f;"
             " for (let i = 0; i < n; i++) tl.set(cs[i], { display: 'inline' }, t0 + (t1 - t0) * i / Math.max(1, n - 1)); })();" % (p, type_t0, type_t1))
    j.append("tl.fromTo('#%s-caret', { opacity: 1 }, { opacity: 0, duration: 0.2, ease: 'steps(1)', yoyo: true, repeat: %d }, %.3f);"
             % (p, max(1, int((type_t1 - type_t0) / 0.22)), type_t0))
    j.append("tl.to('#%s-win', { opacity: 0, y: -20, duration: 0.35, ease: 'power2.in' }, %.3f);" % (p, t_out - 0.4))
    return html, j
