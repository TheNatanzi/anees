"""RULES.md -> docs/data/standing-rules.json for the System Settings page.

Each "## Sn — Title" section becomes one row. The body is copied verbatim as
Markdown (never paraphrased); the page renders it. Re-run after editing RULES.md:

    python scripts/build_standing_rules.py
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "RULES.md"
OUT = ROOT / "docs" / "data" / "standing-rules.json"


def main():
    text = SRC.read_text(encoding="utf-8").replace("\r\n", "\n")
    head, _, rest = text.partition("\n---\n")
    intro = "\n".join(l for l in head.splitlines() if not l.startswith("# ")).strip()
    rules = []
    for block in re.split(r"\n(?=## )", "\n" + rest):
        block = block.strip()
        m = re.match(r"## (S\d+)\s+[—-]\s+(.+)\n", block)
        if not m:
            continue
        body = block[m.end():].strip()
        body = re.sub(r"\n---\s*$", "", body).strip()
        rules.append({"id": m.group(1), "title": m.group(2).strip(), "body_md": body})
    try:
        updated = subprocess.run(["git", "log", "-1", "--format=%cs", "--", "RULES.md"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        updated = ""
    OUT.write_text(json.dumps({"updated": updated, "source": "RULES.md", "intro_md": intro, "rules": rules},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rules)} standing rules -> {OUT.relative_to(ROOT)} (RULES.md updated {updated})")


if __name__ == "__main__":
    main()
