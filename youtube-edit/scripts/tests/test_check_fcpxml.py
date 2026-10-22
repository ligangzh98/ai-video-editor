"""check-fcpxml.py: the import-failure pre-flight. Each case is one real incident.

The bug this file exists for: a camera file's embedded start timecode (09:15:30:00) is
not zero, FCP positions media by that timecode, and an XML that declares asset start="0s"
with 0-based in-points puts every clip before frame 1 — FCP then reports
"未包含相应媒体的无效编辑" once per ENABLED clip (disabled ones are not validated, which is
the diagnostic: warnings only on the odd-numbered spine elements means this, not a bad cut).
"""
import os, unittest
from .helpers import run, scratch, write, needs_ffmpeg, ffmpeg

# A 2 s 24 fps CFR clip, optionally carrying a start timecode, plus a 2 s audio file.
def _media(d, tc=None, fps=24, seconds=2):
    p = os.path.join(d, "clip-%s.mov" % (tc or "none"))
    args = ["-f", "lavfi", "-i", "testsrc=size=192x108:rate=%d:duration=%d" % (fps, seconds)]
    if tc:
        args += ["-timecode", tc]
    ffmpeg(*args, "-c:v", "libx264", "-pix_fmt", "yuv420p", p)
    return p


def _xml(media, asset_start="0s", asset_dur="48/24s", clip_start="24/24s", dur="24/24s",
         enabled="1", marker=None):
    mark = ('<marker start="%s" duration="1/24s" value="保留" note="x"/>' % marker) if marker else ""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
    <format id="r1" name="FFVideoFormat1080p24" frameDuration="1/24s" width="1920" height="1080"/>
    <asset id="r2" name="clip" start="%s" duration="%s" hasVideo="1" hasAudio="1" format="r1">
      <media-rep kind="original-media" src="file://%s"/>
    </asset>
  </resources>
  <library location="file:///tmp/">
    <event name="t"><project name="p">
      <sequence format="r1" duration="%s" tcStart="0s" tcFormat="NDF">
        <spine>
          <asset-clip ref="r2" name="c" offset="0/24s" start="%s" duration="%s" format="r1" tcFormat="NDF" enabled="%s">%s</asset-clip>
        </spine>
      </sequence>
    </project></event>
  </library>
</fcpxml>
""" % (asset_start, asset_dur, media, dur, clip_start, dur, enabled, mark)


@needs_ffmpeg
class CheckFcpxml(unittest.TestCase):
    def check(self, xml):
        d = scratch(self)
        p = write(os.path.join(d, "t.fcpxml"), xml)
        return run("check-fcpxml.py", p)

    def test_clean_file_passes(self):
        d = scratch(self)
        m = _media(d)
        r = self.check(_xml(m))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 problem(s)", r.stdout)

    def test_asset_start_that_ignores_the_timecode_fails(self):
        """The 261007 incident: asset start="0s" but the media starts at 01:00:00:00."""
        d = scratch(self)
        m = _media(d, tc="01:00:00:00")
        r = self.check(_xml(m, asset_start="0s"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("TIMECODE MISMATCH", r.stdout)
        self.assertIn("3600", r.stdout)

    def test_timecode_aware_file_passes(self):
        d = scratch(self)
        m = _media(d, tc="01:00:00:00")
        r = self.check(_xml(m, asset_start="86400/24s", clip_start="86424/24s", marker="86424/24s"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_clip_past_the_asset_end_fails(self):
        d = scratch(self)
        m = _media(d)                                   # 48 frames = 2 s
        r = self.check(_xml(m, clip_start="0/24s", dur="96/24s"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("INVALID EDIT", r.stdout)

    def test_disabled_overrun_is_a_note_not_a_failure(self):
        """261003's one over-report sits on an enabled="0" clip and never warned on import."""
        d = scratch(self)
        m = _media(d)
        r = self.check(_xml(m, clip_start="0/24s", dur="96/24s", enabled="0"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("NOTE:", r.stdout)

    def test_asset_duration_past_the_last_frame_fails(self):
        d = scratch(self)
        m = _media(d)                                   # exactly 48 frames
        r = self.check(_xml(m, asset_dur="49/24s"))      # one frame past the media
        self.assertEqual(r.returncode, 1)
        self.assertIn("ASSET OVER-REPORT", r.stdout)

    def test_off_grid_clip_fails(self):
        d = scratch(self)
        m = _media(d)
        r = self.check(_xml(m, clip_start="24/24s", dur="24/25s"))   # 24/25 s is not a frame multiple
        self.assertEqual(r.returncode, 1)
        self.assertIn("UNALIGNED EDIT", r.stdout)

    def test_missing_media_fails(self):
        r = self.check(_xml("/nonexistent/clip.mov"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("MEDIA MISSING", r.stdout)

    def test_connected_clip_after_a_marker_fails(self):
        """The DTD orders connected clips before markers; FCP rejects the reverse."""
        d = scratch(self)
        m = _media(d)
        xml = _xml(m, marker="24/24s").replace(
            "</asset-clip>", '<asset-clip ref="r2" name="k" offset="0/24s" start="0/24s" duration="1/24s" lane="2"/></asset-clip>')
        r = self.check(xml)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ORDER", r.stdout)

    def test_malformed_xml_fails(self):
        r = self.check("<fcpxml><unclosed>")
        self.assertEqual(r.returncode, 1)
        self.assertIn("NOT WELL-FORMED", r.stdout)
