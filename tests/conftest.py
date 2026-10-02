import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


# ---- Live-database gate (engineering audit 2026-09-29; FC-08 tightened 2026-10-02) ---------------------------------
# Some end-to-end tests write into the LIVE Supabase project (card_results, amal_links, amal_rules, homework_*,
# word_events). On 2026-09-29 full-suite runs left 108 fake answers in Medi's real flashcard history, and a test's
# buckets.recompute_and_store() froze 90 of them into word_stats, where they still scored his words on 2026-10-02.
# FC-08: no test writes to Medi's project, ever.
#   1. A test whose source writes to the live database runs only against a NON-Medi project:
#      ANEES_E2E_LIVE=1 *and* ANEES_SUPABASE_URL pointing somewhere else. ANEES_E2E_LIVE=1 alone is no longer enough.
#   2. Runtime net: every Python request that would write to Medi's project (PostgREST POST/PATCH/PUT/DELETE, or a
#      management-API query with INSERT/UPDATE/DELETE/...) raises LiveWriteBlocked; every Playwright browser context
#      gets a route that answers write requests to Medi's host locally instead of sending them.
#   3. Browser tests that grade cards use the `rest_stub` fixture and assert on the rows the page tried to send.
import inspect as _inspect
import re as _re
import pytest as _pytest

MEDI_REF = 'yljcbdxvnkfrwvelypfu'          # Medi's live Anees project (scripts/anees_env.py default)
MEDI_HOST = f'{MEDI_REF}.supabase.co'
READ_METHODS = {'GET', 'HEAD', 'OPTIONS'}
WRITE_SQL = _re.compile(r"\b(insert|update|delete|upsert|merge|truncate|alter|drop|create|grant|revoke|copy|comment|vacuum)\b", _re.I)

PY_WRITE = r"amal_links\.create\(|db\.upsert\(|db\.rest\(\s*'(POST|PATCH|DELETE)'|delete from |insert into |recompute_and_store\("
LIVE_WRITE = _re.compile(PY_WRITE + r"|card_results")
PY_LIVE_WRITE = _re.compile(PY_WRITE)


class LiveWriteBlocked(RuntimeError):
    """A test tried to write to Medi's live Supabase project (rule FC-08)."""


def live_target_ok():
    """True only when a run was switched on for live tests AND points at a project that is not Medi's."""
    import anees_env as E
    return os.environ.get("ANEES_E2E_LIVE") == "1" and E.SUPABASE_REF != MEDI_REF


def live_writer(fn):
    """True when a test function's own source writes to (or drives a page that writes to) the live database."""
    try:
        src = _inspect.getsource(fn)
    except (OSError, TypeError):
        return False
    if "rest_stub" in src:          # the page's writes go to the stub; only a direct Python write still counts
        return bool(PY_LIVE_WRITE.search(src))
    return bool(LIVE_WRITE.search(src)) and ("sync_playwright" in src or "db." in src or "amal_links" in src)


def is_live_write(method, url, body=None):
    """FC-08: would this HTTP call change data in Medi's project?"""
    from urllib.parse import urlsplit
    u = urlsplit(str(url))
    m = str(method or 'GET').upper()
    if u.hostname == MEDI_HOST:
        return m not in READ_METHODS
    if u.hostname == 'api.supabase.com' and f'/projects/{MEDI_REF}/' in u.path:
        if m in READ_METHODS:
            return False
        q = body.get('query', '') if isinstance(body, dict) else str(body or '')
        return not u.path.endswith('/database/query') or bool(WRITE_SQL.search(q))
    return False


def pytest_configure(config):
    config.addinivalue_line("markers", "live_db: writes to the live database through a helper the source scan cannot see "
                                       "(FC-08: runs only against a non-Medi project)")


def pytest_collection_modifyitems(config, items):
    if live_target_ok():
        return
    skip = _pytest.mark.skip(reason="writes to the live database; runs only with ANEES_E2E_LIVE=1 and a non-Medi "
                                    "ANEES_SUPABASE_URL (FC-08)")
    for it in items:
        fn = getattr(it, "function", None)
        if it.get_closest_marker("live_db") or (fn is not None and live_writer(fn)):
            it.add_marker(skip)


def _route_writes(ctx, record=None, offline=lambda: False):
    """Answer every write to Medi's host inside this browser context locally (201, nothing sent)."""
    def handle(route):
        req = route.request
        if offline():
            return route.abort('internetdisconnected')
        cors = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS'}
        if req.method.upper() == 'OPTIONS':
            return route.fulfill(status=204, headers=cors, body='')
        if req.method.upper() in READ_METHODS:
            return route.continue_()
        if record is not None:
            record.append({'method': req.method.upper(), 'url': req.url, 'body': req.post_data,
                           'prefer': (req.headers or {}).get('prefer', '')})
        return route.fulfill(status=201 if req.method.upper() == 'POST' else 204, headers=cors, body='')
    ctx.route(_re.compile(r'https://' + _re.escape(MEDI_HOST) + r'/.*'), handle)


@_pytest.fixture(autouse=True)
def _fc08_no_live_writes(monkeypatch):
    """FC-08 runtime net: no test can write to Medi's project, from Python or from a Playwright page."""
    if live_target_ok():
        yield; return
    import requests.sessions as _rs
    real = _rs.Session.request

    def guarded(self, method, url, *a, **kw):
        if is_live_write(method, url, kw.get('json') if kw.get('json') is not None else kw.get('data')):
            raise LiveWriteBlocked(f"FC-08: test tried {str(method).upper()} {url} on Medi's live project")
        return real(self, method, url, *a, **kw)
    monkeypatch.setattr(_rs.Session, 'request', guarded)
    try:
        from playwright.sync_api import Browser
    except Exception:
        yield; return
    new_ctx, new_page = Browser.new_context, Browser.new_page

    def ctx_wrap(self, *a, **kw):
        ctx = new_ctx(self, *a, **kw); _route_writes(ctx); return ctx

    def page_wrap(self, *a, **kw):
        pg = new_page(self, *a, **kw); _route_writes(pg.context); return pg
    monkeypatch.setattr(Browser, 'new_context', ctx_wrap)
    monkeypatch.setattr(Browser, 'new_page', page_wrap)
    yield


class RestStub:
    """What a page tried to write. rows(table) = the POSTed rows, de-duplicated by id like on_conflict=id ignore."""
    def __init__(self):
        self.calls, self.offline = [], False

    def attach(self, ctx):
        _route_writes(ctx, self.calls, lambda: self.offline)
        return self

    def rows(self, table):
        import json as _json
        out = {}
        for c in self.calls:
            if c['method'] == 'POST' and f'/rest/v1/{table}' in c['url'] and c['body']:
                body = _json.loads(c['body'])
                for r in (body if isinstance(body, list) else [body]):
                    out.setdefault(r.get('id') or len(out), r)
        return list(out.values())


@_pytest.fixture
def rest_stub():
    """FC-08: a page under test writes into this stub, never into Medi's card history."""
    return RestStub()


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
