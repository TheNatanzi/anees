# -*- coding: utf-8 -*-
"""The rule registry: every correction Medi or Amal made, one entry each (RULES.md S6, Medi 2026-10-02).

    python scripts/rule_registry.py check            # exit 0 = every claim is provable; exit 1 = first line says why
    python scripts/rule_registry.py show [scope|id]  # read the rules before building in a scope (CLAUDE.md / AGENTS.md)
    python scripts/rule_registry.py stats            # one line: counts by status, then the questions for Medi
    python scripts/rule_registry.py plain GR-14 "..." [--topic t]   # the rule in plain words for the rule book (PG-16)

rules/registry.json is the index. It does not replace RULES.md (S1-S6, Medi's own words) or the files that apply a rule
(code, guard tests, the AI readers' briefs, docs/data/ai_rules.json, docs/flashcard-rules.md, memory notes). Each entry
points at them with {path, contains}: the check opens the file and needs the exact text, so a pointer that rots fails
here ("anchor moved: update the entry") instead of silently. Line numbers are never stored.

It fails on (the ESLint "Missing tests for rule X" pattern; design C:/Claude/reports/anees-universal-rules-design-2026-10-02.md):
  - a missing / unknown field, a bad id, a duplicate id, a live alias used twice
  - an enforced entry that is not proven: code/check anchor + a test the publish guard runs (a `def test_` / `test(`
    function, or a BLOCK check id in scripts/check_rules.py), or a brief anchor + a real example moment
  - an enforced not-error rule in word/grammar scoring that the AI readers' brief does not carry
  - an anchor in a file the hourly job regenerates, a missing file, text not found
  - supersede links that disagree, `amend` without `supersedes`, a live conflict where neither side is needs-medi
  - a moment-only entry with neither next_step nor one_off_reason; a needs-medi entry without question + options
  - an S-rule in RULES.md with no entry (alias RULES:Sn); a non-AR id in docs/data/ai_rules.json with no entry
  - a NEW row in a moment-ruling file (its hash not in moment_baseline) without "rule": "<id>" or "one-off: <reason>"
  - a status lower than on origin/master (enforced > written > moment-only), or an entry that disappeared;
    origin/master unreadable (fail closed; --no-origin only for offline runs)
  - a NEW enforced rule whose test does not mention its id (no borrowing an unrelated test)
Optional per entry: `plain` (the statement in plain words, shown by the rule book - scripts/build_rule_book.py, rule
PG-16; it never changes the meaning; `plain_for` = the hash of the statement it was written for, so a changed statement
fails until its plain wording is re-read - use the `plain` command) and `topic` (a short label that keeps related rules together in the book).
Superseded entries keep only their links checked: the code they pointed at may be gone, by design. Nothing is deleted.
"""
from __future__ import annotations

import argparse, hashlib, json, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = "rules/registry.json"
GUARD_CONFIG = "scripts/publish_guard_config.json"
CHECK_RULES = "scripts/check_rules.py"
AI_RULES = "docs/data/ai_rules.json"
MEMORY_DIR = os.environ.get("ANEES_MEMORY_DIR") or "C:/Users/Mahdi/.claude/projects/C--Claude/memory"

SCOPES = {"TR": "transcription", "AZ": "arabizi", "WS": "word-scoring", "GR": "grammar-scoring", "LS": "lessons",
          "AM": "amal-data", "PG": "pages", "AU": "audio", "FC": "flashcards", "PR": "process"}
KINDS = {"error", "not-error", "display", "process", "data"}
STATUSES = {"enforced", "written", "moment-only", "needs-medi", "superseded"}
RANK = {"enforced": 3, "written": 2, "moment-only": 1}
CHANGES = {"new", "amend", "clarify"}
BY = {"medi", "amal", "claude"}
ANCHOR_TYPES = {"code", "check", "brief", "doc", "data", "memory"}
PROVES_CODE = {"code", "check"}
LIVE = {"enforced", "written", "moment-only", "needs-medi"}
ID_RE = re.compile(r"^([A-Z]{2})-(\d{2,3})$")
DATE_RE = re.compile(r"^20\d\d-\d\d-\d\d$")
MIN_ANCHOR = 12
TEST_RE = re.compile(r"^(def test_\w+|test\(\s*['\"])")
CHECK_ID_RE = re.compile(r'^res\("([^"]+)", "block"$')
# files the hourly job regenerates: an anchor there could break on any lesson rebuild and block the publish
REGENERATED = ("docs/data/", "data/full-audit-", "data/accuracy/", "data/accuracy")
REGENERATED_OK = {AI_RULES}
BRIEFS = {"data/lesson-work/full-audit/READER-BRIEF.md", "data/lesson-work/full-audit/THIRD-READER-BRIEF.md",
          "data/lesson-work/full-audit/PATTERN-BRIEF.md"}
MOMENT_FILES = {  # path -> (list key, identity fields)
    "data/lesson-work/full-audit/rejected.json": ("rows", ("date", "t", "wrong")),
    "data/lesson-work/full-audit/duplicates.json": ("pairs", ("date", "keep", "drop")),
    "data/grammar-usage-rulings.json": ("rows", ("date", "t", "bucket")),
}


def load(root=ROOT):
    with open(Path(root) / REGISTRY, encoding="utf-8") as f:
        return json.load(f)


def J(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def guard_tests(root):
    """Test files the publish guard runs: only these count as a rule's test."""
    cfg = J(Path(root) / GUARD_CONFIG)
    out = set()
    for cid in ("tests_py", "tests_node"):
        if cid in (cfg.get("required") or []):
            for a in (cfg.get("commands", {}).get(cid, {}) or {}).get("cmd", []):
                if isinstance(a, str) and a.startswith("tests/"):
                    out.add(a)
    return out, "check_rules" in (cfg.get("required") or [])


def _read(root, rel, cache, memory=False):
    key = ("mem:" if memory else "") + rel
    if key not in cache:
        p = (Path(MEMORY_DIR) / rel) if memory else (Path(root) / rel)
        cache[key] = p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n") if p.is_file() else None
    return cache[key]


def plain_hash(statement):
    """Which statement a `plain` sentence was written for (rule book, PG-16): a changed statement needs a new plain."""
    return hashlib.sha1(str(statement).strip().encode("utf-8")).hexdigest()[:8]


def set_plain(root, rid, text, topic=None):
    """Write `plain` (+ plain_for, optional topic) for one entry, keeping the file's layout. Returns the entry."""
    data = load(root)
    r = next((x for x in data["rules"] if isinstance(x, dict) and x.get("id") == rid), None)
    if r is None:
        raise KeyError(rid)
    items = [(k, v) for k, v in r.items() if k not in ("plain", "plain_for") and not (topic and k == "topic")]
    at = [k for k, _ in items].index("statement") + 1
    items[at:at] = [("plain", text.strip()), ("plain_for", plain_hash(r["statement"]))] + ([("topic", topic)] if topic else [])
    r.clear(); r.update(items)
    with open(Path(root) / REGISTRY, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    return r


def moment_id(row, fields):
    return "|".join(str(row.get(f, "")) for f in fields)


def moment_hash(row):
    """Identity of one moment ruling: the whole row except its "rule" link (Codex audit 2026-10-02: a field-subset id
    could be reused by a different row). Editing an old ruling makes it a new one, which then needs its rule."""
    body = {k: v for k, v in row.items() if k != "rule"}
    return hashlib.sha1(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def check_anchor(root, a, cache, where):
    """One {path, contains} pointer -> list of problems."""
    if not isinstance(a, dict):
        return [f"{where}: pointer must be an object"]
    path, text = a.get("path"), a.get("contains")
    if not isinstance(path, str) or not isinstance(text, str) or not path or not text:
        return [f"{where}: pointer needs path and contains"]
    if a.get("type") and a["type"] not in ANCHOR_TYPES:
        return [f"{where}: unknown pointer type {a['type']!r}"]
    if len(text) < MIN_ANCHOR:
        return [f"{where}: contains {text!r} is shorter than {MIN_ANCHOR} characters (too easy to match by accident)"]
    if a.get("type") == "memory":
        if not Path(MEMORY_DIR).is_dir():            # another PC / CI: memory notes are not there; recorded, not opened
            return []
        body = _read(root, path, cache, memory=True)    # a memory note is never the only anchor (written needs a repo
        if body is None or text not in body:            # one), and notes are renamed often: a stale one is a WARNING,
            cache.setdefault("_warnings", []).append(    # never a blocked publish
                f"{where}: memory note {path} {'not found' if body is None else 'no longer contains ' + repr(text[:50])}")
        return []
    if path.startswith(REGENERATED) and path not in REGENERATED_OK:
        return [f"{where}: {path} is regenerated by the hourly job; point at the code or rules file instead"]
    body = _read(root, path, cache)
    if body is None:
        return [f"{where}: file not found {path}"]
    if text not in body:
        return [f"{where}: anchor moved - {path} no longer contains {text[:60]!r}; update the entry"]
    return []


class OriginUnreadable(Exception):
    pass


def _origin_registry(root):
    """The registry as published (origin/master). None only when origin/master has no registry yet; any other git or
    JSON failure raises (fail closed - Codex audit 2026-10-02: a silent skip would switch the ratchet off)."""
    try:
        r = subprocess.run(["git", "show", f"origin/master:{REGISTRY}"], cwd=str(root), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
    except Exception as e:
        raise OriginUnreadable(f"git show failed ({type(e).__name__}: {e})")
    if r.returncode != 0:
        err = (r.stderr or "").strip()
        if "exists on disk, but not in" in err or "does not exist in" in err:
            return None
        raise OriginUnreadable(err.splitlines()[0] if err else f"git exit {r.returncode}")
    try:
        return json.loads(r.stdout)
    except Exception as e:
        raise OriginUnreadable(f"origin/master {REGISTRY} is not JSON ({e})")


def check_entry(root, r, by_id, cache, tests_run, check_rules_required, origin_ids=None):
    bad = []
    rid = r.get("id") if isinstance(r.get("id"), str) else "?"
    m = ID_RE.match(rid)
    if not m or m.group(1) not in SCOPES:
        bad.append(f"{rid}: id must be <SCOPE>-<nn>, SCOPE one of {sorted(SCOPES)}")
    elif r.get("scope") != SCOPES[m.group(1)]:
        bad.append(f"{rid}: scope {r.get('scope')!r} does not match prefix {m.group(1)} ({SCOPES[m.group(1)]})")
    for f in ("statement", "kind", "status", "change", "source"):
        if not r.get(f):
            bad.append(f"{rid}: missing {f}")
    for f in ("plain", "topic"):                      # optional, for the rule book (PG-16): plain words, same meaning
        if f in r and (not isinstance(r[f], str) or not r[f].strip()):
            bad.append(f"{rid}: {f} must be a non-empty string when present")
    if isinstance(r.get("plain"), str) and isinstance(r.get("statement"), str) and r.get("plain_for") != plain_hash(r["statement"]):
        bad.append(f"{rid}: statement changed after its plain wording was written - re-read it and run: "
                   f"python scripts/rule_registry.py plain {rid} \"<plain words, same meaning>\"")
    st = r.get("status")
    if r.get("kind") and r["kind"] not in KINDS:
        bad.append(f"{rid}: unknown kind {r['kind']!r}")
    if st and st not in STATUSES:
        bad.append(f"{rid}: unknown status {st!r}")
    if r.get("change") and r["change"] not in CHANGES:
        bad.append(f"{rid}: unknown change {r['change']!r}")
    if r.get("change") == "amend" and not r.get("supersedes"):
        bad.append(f"{rid}: change amend must name what it overturns (supersedes)")
    src = r.get("source") if isinstance(r.get("source"), list) else []
    if r.get("source") and not src:
        bad.append(f"{rid}: source must be a list")
    for s in src:
        if not isinstance(s, dict) or s.get("by") not in BY or not DATE_RE.match(str(s.get("date", ""))) or not s.get("quote"):
            bad.append(f"{rid}: each source needs by (medi/amal/claude), date YYYY-MM-DD and quote")
    if src and all(isinstance(s, dict) and s.get("by") == "claude" for s in src) and st == "enforced":
        bad.append(f"{rid}: only Claude is the source - Claude's wording has no authority (precedence 1)")

    # links (checked for every status)
    nxt = r.get("superseded_by")
    if st == "superseded":
        if not nxt or nxt not in by_id:
            bad.append(f"{rid}: superseded_by must name an entry ({nxt!r})")
        elif rid not in (by_id[nxt].get("supersedes") or []):
            bad.append(f"{rid}: superseded_by {nxt}, but {nxt}.supersedes does not list {rid}")
    elif nxt:
        bad.append(f"{rid}: has superseded_by {nxt} but status {st!r} (should be superseded)")
    for old in r.get("supersedes") or []:
        if old not in by_id:
            bad.append(f"{rid}: supersedes unknown {old}")
        elif by_id[old].get("superseded_by") != rid:
            bad.append(f"{rid}: supersedes {old}, but {old}.superseded_by is {by_id[old].get('superseded_by')!r}")
    for other in r.get("conflicts_with") or []:
        o = by_id.get(other)
        if not o:
            bad.append(f"{rid}: conflicts_with unknown {other}")
        elif st in LIVE and o.get("status") in LIVE and "needs-medi" not in (st, o.get("status")):
            bad.append(f"{rid}: live conflict with {other} and neither is needs-medi (precedence 4)")
    if st == "superseded":
        return bad                                     # old anchors may be gone, by design

    enf = r.get("enforcement") if isinstance(r.get("enforcement"), list) else []
    tests = r.get("test") if isinstance(r.get("test"), list) else []
    for i, a in enumerate(enf):
        bad += check_anchor(root, a, cache, f"{rid} enforcement[{i}]")
    for i, a in enumerate(tests):
        where = f"{rid} test[{i}]"
        if not isinstance(a, dict):
            bad.append(f"{where}: must be an object")
            continue
        p, c = a.get("path") or "", a.get("contains") or ""
        if p == CHECK_RULES:
            if not CHECK_ID_RE.match(c):
                bad.append(f'{where}: a check_rules test must read res("<ID>", "block" (a BLOCK check)')
            elif not check_rules_required:
                bad.append(f"{where}: check_rules is not a required publish-guard check")
        elif p.startswith("tests/"):
            if not TEST_RE.match(c):
                bad.append(f"{where}: contains must start with 'def test_' or 'test(' (a test function)")
            if p not in tests_run:
                bad.append(f"{where}: {p} is not run by the publish guard ({GUARD_CONFIG} tests_py / tests_node)")
        else:
            bad.append(f"{where}: a test is a guard test file or a {CHECK_RULES} BLOCK check")
            continue
        bad += check_anchor(root, a, cache, where)
    for i, a in enumerate(r.get("moments") or []):
        bad += check_anchor(root, a, cache, f"{rid} moments[{i}]")

    types = {a.get("type") for a in enf if isinstance(a, dict)}
    if st == "enforced":
        if types & PROVES_CODE:
            if not tests:
                bad.append(f"{rid}: enforced in code but no test the guard runs (planted-mistake test or BLOCK check)")
            elif origin_ids is not None and rid not in origin_ids and not any(
                    isinstance(a, dict) and re.search(rf"(?<![\w-]){re.escape(rid)}(?!\d)", _read(root, a.get("path") or "", cache) or "")
                    for a in tests):
                # Codex audit 2026-10-02: a new rule must not borrow an unrelated test - its test names the rule id
                bad.append(f"{rid}: new rule - its test (or BLOCK check) must mention {rid} so it is provably this rule's test")
        elif "brief" in types:
            ex = r.get("example") or {}
            if not (isinstance(ex, dict) and DATE_RE.match(str(ex.get("date", ""))) and ex.get("note")):
                bad.append(f"{rid}: enforced by a reader brief but no example moment (date + note)")
        else:
            bad.append(f"{rid}: enforced needs a code/check anchor + test, or a brief anchor + example")
        if r.get("kind") == "not-error" and r.get("scope") in ("word-scoring", "grammar-scoring") \
                and not any(isinstance(a, dict) and a.get("path") in BRIEFS for a in enf):
            bad.append(f"{rid}: an enforced not-error rule must also be in the readers' brief (they only see the brief)")
    elif st == "written":
        if not any(isinstance(a, dict) and a.get("type") != "memory" for a in enf):
            bad.append(f"{rid}: written needs a pointer into the repo (a memory note alone is not enough: Codex never reads it)")
    elif st == "moment-only":
        if not (r.get("next_step") or r.get("one_off_reason")):
            bad.append(f"{rid}: moment-only needs next_step (what would enforce it) or one_off_reason")
    elif st == "needs-medi":
        q = r.get("question") or {}
        if not isinstance(q, dict) or not q.get("ask") or not q.get("options"):
            bad.append(f"{rid}: needs-medi needs question.ask and question.options")
    return bad


def check(root=ROOT, data=None, origin=None, use_origin=True, warnings=None):
    """All problems with the registry (empty list = OK)."""
    root = Path(root)
    data = data if data is not None else load(root)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return [f"{REGISTRY}: must be an object with a rules list"]
    rules = [r for r in data["rules"] if isinstance(r, dict)]
    bad = [f"rules[{i}] is not an object" for i, r in enumerate(data["rules"]) if not isinstance(r, dict)]
    cache = {}
    tests_run, cr_required = guard_tests(root)
    ids = Counter(r.get("id") for r in rules)
    bad += [f"{i}: duplicate id ({n}x)" for i, n in ids.items() if n > 1]
    by_id = {r.get("id"): r for r in rules}
    live = [r for r in rules if r.get("status") != "superseded"]
    aliases = Counter(a for r in live for a in (r.get("aliases") or []))
    bad += [f"alias {a} used by {n} live entries" for a, n in aliases.items() if n > 1]

    origin_err = None
    if use_origin and origin is None:
        try:
            origin = _origin_registry(root)
        except OriginUnreadable as e:
            origin_err = str(e)
    if origin_err:
        bad.append(f"ratchet: cannot read origin/master {REGISTRY} ({origin_err}) - fetch origin, or run with --no-origin offline")
    origin_ids = {o.get("id") for o in origin["rules"] if isinstance(o, dict)} if origin and isinstance(origin.get("rules"), list) else None

    for r in rules:
        try:
            bad += check_entry(root, r, by_id, cache, tests_run, cr_required, origin_ids)
        except Exception as e:                        # bad input is a problem line, never a crash or a silent pass
            bad.append(f"{r.get('id', '?')}: entry could not be checked ({type(e).__name__}: {e})")

    # coverage: every standing rule and every non-AR ai_rules id is named by a live entry
    rules_md = _read(root, "RULES.md", cache) or ""
    sids = re.findall(r"^## (S\d+)\s", rules_md, re.M)
    if not sids:
        bad.append("RULES.md: no '## Sn' headings found (format changed?) - coverage cannot be checked")
    for sid in sids:
        if f"RULES:{sid}" not in aliases:
            bad.append(f"RULES.md {sid}: no live registry entry has alias RULES:{sid}")
    try:
        ai = J(root / AI_RULES)
        ai_ids = [x["id"] for g in ai.get("groups", []) for x in g.get("rules", []) if not str(x.get("id", "")).startswith("AR-")]
    except Exception as e:
        ai_ids, _ = [], bad.append(f"{AI_RULES}: unreadable ({type(e).__name__}: {e})")
    for i in ai_ids:
        if f"ai_rules:{i}" not in aliases:
            bad.append(f"{AI_RULES} {i}: no live registry entry has alias ai_rules:{i}")

    # S6 link: every new moment ruling names its rule
    base = data.get("moment_baseline") or {}
    for path, (key, fields) in MOMENT_FILES.items():
        p = root / path
        if not p.is_file():
            continue
        try:
            rows = J(p).get(key) or []
        except Exception as e:
            bad.append(f"{path}: unreadable ({type(e).__name__}: {e})")
            continue
        known = set(base.get(path) or [])
        for row in rows:
            if not isinstance(row, dict) or moment_hash(row) in known:
                continue
            rule = str(row.get("rule") or "")
            if not rule:
                bad.append(f"{path}: new row {moment_id(row, fields)} has no \"rule\" (a registry id or 'one-off: <reason>') - RULES.md S6")
            elif not rule.startswith("one-off:") and rule not in by_id:
                bad.append(f"{path}: row {moment_id(row, fields)} names rule {rule!r}, which is not in the registry")

    # ratchet against origin/master: no entry disappears, no status goes down
    if origin and isinstance(origin.get("rules"), list):
        for o in origin["rules"]:
            if not isinstance(o, dict):
                continue
            cur = by_id.get(o.get("id"))
            if cur is None:
                bad.append(f"{o.get('id')}: entry removed (entries are never deleted; mark it superseded)")
                continue
            a, b = RANK.get(o.get("status")), RANK.get(cur.get("status"))
            if a and b and b < a:
                bad.append(f"{o.get('id')}: status went down {o.get('status')} -> {cur.get('status')} "
                           "(fix the anchor instead; only superseded or needs-medi may replace it)")
    if warnings is not None:
        warnings.extend(cache.get("_warnings", []))
    return bad


def stats(data):
    return Counter(r.get("status") for r in data.get("rules") or [] if isinstance(r, dict))


def stats_line(data):
    c = stats(data)
    rules = [r for r in data.get("rules") or [] if isinstance(r, dict)]
    code = sum(1 for r in rules if r.get("status") == "enforced"
               and any(isinstance(a, dict) and a.get("type") in PROVES_CODE for a in r.get("enforcement") or []))
    return (f"{len(rules)} rules: enforced {c.get('enforced', 0)} (code {code}, brief {c.get('enforced', 0) - code}), "
            f"written {c.get('written', 0)}, moment-only {c.get('moment-only', 0)}, needs Medi {c.get('needs-medi', 0)}, "
            f"superseded {c.get('superseded', 0)}")


def show(data, what=None):
    for r in data.get("rules") or []:
        if what and what not in (r.get("scope"), r.get("id")) and not str(r.get("id", "")).startswith(what):
            continue
        print(f"{r['id']:6} [{r.get('status')}] {r.get('statement')}")
        for a in r.get("enforcement") or []:
            print(f"        {a.get('type', ''):6} {a.get('path')}")
        if r.get("next_step"):
            print(f"        next: {r['next_step']}")
        q = r.get("question") or {}
        if q.get("ask"):
            print(f"        ASK MEDI: {q['ask']}  ({' / '.join(q.get('options') or [])})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["check", "show", "stats", "plain"])
    ap.add_argument("what", nargs="?")
    ap.add_argument("text", nargs="?", help="plain: the rule in plain words (same meaning) for the rule book")
    ap.add_argument("--topic", help="plain: a short topic that keeps related rules together in the rule book")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--no-origin", action="store_true", help="skip the ratchet against origin/master")
    a = ap.parse_args(argv)
    try:
        data = load(a.root)
    except Exception as e:
        print(f"rule_registry: FAIL - {REGISTRY} unreadable ({type(e).__name__}: {e})")
        return 1
    if a.cmd == "plain":
        if not a.what or not a.text:
            print('usage: python scripts/rule_registry.py plain <ID> "<plain words>" [--topic <topic>]')
            return 2
        try:
            r = set_plain(a.root, a.what, a.text, a.topic)
        except KeyError:
            print(f"rule_registry: no entry {a.what}")
            return 1
        print(f"{a.what}: plain = {r['plain']!r} - now run python scripts/build_rule_book.py")
        return 0
    if a.cmd == "show":
        show(data, a.what)
        return 0
    if a.cmd == "stats":
        print(stats_line(data))
        for r in data.get("rules") or []:
            q = r.get("question") or {}
            if r.get("status") == "needs-medi" and q.get("ask"):
                print(f"  {r['id']}: {q['ask']} ({' / '.join(q.get('options') or [])})")
        return 0
    warn = []
    bad = check(a.root, data, use_origin=not a.no_origin, warnings=warn)
    if bad:
        print(f"rule_registry: FAIL {len(bad)} problem(s) - {bad[0]}")
        for b in bad[:60]:
            print("  - " + b)
        return 1
    print(f"rule_registry: OK - {stats_line(data)}" + (f" ({len(warn)} warning(s))" if warn else ""))
    for x in warn[:20]:
        print("  warning: " + x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
