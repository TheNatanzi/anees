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


CODE_GLOBS = ('docs/js/**/*.js', 'docs/css/**/*.css', 'docs/*.html', 'docs/amal/*.html')


def code_version():
    """Medi 2026-11-17 ("why do I keep getting out of date refresh alerts when we arent changing anything. We want this
    only for version updates"): a hash of the site's CODE only (scripts, styles, page shells). The hourly job's data
    publishes change the build stamp but not this, so the 'out of date' bar shows only for a real code update; a data-only
    change reloads the page quietly (docs/js/stale.js)."""
    import hashlib
    h = hashlib.sha1()
    files = sorted({p for g in CODE_GLOBS for p in ROOT.glob(g) if p.is_file() and p.name != 'build.js'})
    for p in files:
        h.update(p.relative_to(ROOT).as_posix().encode()); h.update(b'\0')
        h.update(p.read_bytes().replace(b'\r\n', b'\n')); h.update(b'\0')
    return h.hexdigest()[:12]


def write(build=None):
    build = build or stamp()
    (ROOT / 'docs' / 'js').mkdir(parents=True, exist_ok=True); (ROOT / 'docs' / 'data').mkdir(parents=True, exist_ok=True)
    io.open(ROOT / 'docs' / 'js' / 'build.js', 'w', encoding='utf-8').write(f"window.ANEES_BUILD='{build}';\n")
    io.open(ROOT / 'docs' / 'data' / 'build.json', 'w', encoding='utf-8').write(json.dumps({'build': build, 'code': code_version()}))
    return build


if __name__ == '__main__':
    print(write())
