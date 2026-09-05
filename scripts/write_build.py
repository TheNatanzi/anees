"""Stamp the site: docs/js/build.js (window.ANEES_BUILD) + docs/data/build.json. Run by the pre-commit hook (scripts/install_hooks.py)
and by build_report / lesson_pipeline before they publish. The stamp = UTC time + short git hash of HEAD."""
import datetime, io, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def stamp():
    try:
        h = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip() or 'nogit'
    except Exception:
        h = 'nogit'
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + h


def write(build=None):
    build = build or stamp()
    (ROOT / 'docs' / 'js').mkdir(parents=True, exist_ok=True); (ROOT / 'docs' / 'data').mkdir(parents=True, exist_ok=True)
    io.open(ROOT / 'docs' / 'js' / 'build.js', 'w', encoding='utf-8').write(f"window.ANEES_BUILD='{build}';\n")
    io.open(ROOT / 'docs' / 'data' / 'build.json', 'w', encoding='utf-8').write(json.dumps({'build': build}))
    return build


if __name__ == '__main__':
    print(write())
