"""The format table in FORMATS.md and compose.py's beat types stay the same list.

「手工搭建」/「尚未构建」rows have no type. `tag` is a storyboard field, not a beat type.
"""
import os, re, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(ROOT, "FORMATS.md")
COMPOSE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "compose.py")


def table_types(md):
    start = md.index("## 格式库")
    end = md.index("### 两种格式打架时")
    found = set()
    for line in md[start:end].splitlines():
        if not line.startswith("|") or line.startswith("| #") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        kind = cells[3]
        if "手工搭建" in kind or "尚未构建" in kind or kind.startswith("`formats/"):
            continue
        found.update(re.findall(r"`([a-z][a-z0-9]*)`", kind))
    return found


def beat_types(src):
    return set(re.findall(r'(?:if|elif) t == "([a-z0-9]+)"', src))


class FormatTable(unittest.TestCase):
    def test_table_types_are_implemented(self):
        with open(SKILL, encoding="utf-8") as f:
            md = f.read()
        with open(COMPOSE, encoding="utf-8") as f:
            src = f.read()
        table, beats = table_types(md), beat_types(src)
        storyboard_fields = {"tag"}
        missing = table - beats - storyboard_fields
        self.assertFalse(missing, "SKILL format table names a type compose.py does not build: %s" % sorted(missing))
        undocumented = beats - table
        self.assertFalse(undocumented, "compose.py beat type missing from the SKILL format table: %s" % sorted(undocumented))
        self.assertIn("tag", table)
        self.assertIn('S.get("tag")', src)


if __name__ == "__main__":
    unittest.main()
