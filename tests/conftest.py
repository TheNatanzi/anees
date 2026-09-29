import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


# ---- Live-database gate (engineering audit 2026-09-29) --------------------------------------------------------------
# Some end-to-end tests write into the LIVE Supabase project (card_results, amal_links, amal_rules, homework_*,
# word_events). On 2026-09-29 full-suite runs left ~90 fake answers in Medi's real flashcard history (2 fake leeches,
# the day's new-card room used up). Those tests now run ONLY when ANEES_E2E_LIVE=1 is set on purpose.
import inspect as _inspect
import re as _re
import pytest as _pytest

LIVE_WRITE = _re.compile(r"amal_links\.create\(|db\.upsert\(|db\.rest\(\s*'(POST|PATCH|DELETE)'|delete from |insert into |"
                         r"card_results")


def live_writer(fn):
    """True when a test function's own source writes to (or drives a page that writes to) the live database."""
    try:
        src = _inspect.getsource(fn)
    except (OSError, TypeError):
        return False
    return bool(LIVE_WRITE.search(src)) and ("sync_playwright" in src or "db." in src or "amal_links" in src)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("ANEES_E2E_LIVE") == "1":
        return
    skip = _pytest.mark.skip(reason="writes to the LIVE database; set ANEES_E2E_LIVE=1 to run on purpose")
    for it in items:
        fn = getattr(it, "function", None)
        if fn is not None and live_writer(fn):
            it.add_marker(skip)


@_pytest.fixture(autouse=True)
def _no_env_leak():
    """hourly_lessons.main() sets ANEES_STRICT / ANEES_TRIGGER with os.environ.setdefault in-process; restore them after
    every test so one test's hourly run cannot switch a later test into strict mode (eng audit 2026-09-29)."""
    keep = {k: os.environ.get(k) for k in ("ANEES_STRICT", "ANEES_TRIGGER")}
    yield
    for k, v in keep.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@_pytest.fixture(autouse=True)
def _amal_trigger_sandbox(tmp_path_factory, monkeypatch, request):
    """scripts/amal_trigger.py keeps state, a log, a page file and the shared job lock in the repo; hourly_lessons.main()
    calls it. In tests they live in a temp folder, and the real DB-reading run is replaced by a no-op unless a test uses
    amal_trigger directly (it then sets its own paths)."""
    try:
        import amal_trigger as T
    except Exception:
        yield; return
    d = tmp_path_factory.mktemp("amal-trigger")
    for k, name in (("STATE_P", "state.json"), ("LOG_P", "log.jsonl"), ("PAGE_P", "amal-trigger.json"), ("LOCK_P", ".lock")):
        monkeypatch.setattr(T, k, d / name)
    if "test_amal_trigger" not in str(getattr(request.node, "fspath", "")):
        monkeypatch.setattr(T, "SOURCES", [])
    yield
