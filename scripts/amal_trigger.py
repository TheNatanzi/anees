# -*- coding: utf-8 -*-
"""Amal trigger: anything Amal does -> re-pull, recalc, log (Medi 2026-09-29, M3: "With anything amal does there should be a
trigger to recalc").

Every source of Amal's input gets a fingerprint (a content hash of her answers, plus the newest timestamp and a count) kept
in data/amal-trigger/state.json. When a fingerprint changes, the trigger re-pulls that source, reruns every builder that
depends on it (in one fixed order), recomputes the headline numbers before/after, and logs the firing:

    data/amal-trigger/log.jsonl       one line per firing (append-only): what changed, steps run, numbers that moved
    docs/data/amal-trigger.json       the same for System Settings: each source's status + the last 30 firings

Publishing is NOT decided here: with --publish the result is committed and pushed through scripts/publish_guard.py
(guarded_push), so the guard decides. A failed step keeps the old fingerprint, so the next run retries (fail closed).

    python scripts/amal_trigger.py                  # check every source; fire on changes (no git)
    python scripts/amal_trigger.py --dry-run        # only say what changed; run nothing, write nothing
    python scripts/amal_trigger.py --publish        # fire, commit, push through the publish guard (the 15-minute task)

Sources (SOURCES below; a new Amal input = one more entry):
  tutor_verify        the "check these moments" list on the Tutor page     amal_rules source=review, word_key verify:*
  pattern_review      slips-by-pattern review                               amal_rules source=review (not verify:*)
  after_links         after-lesson questions                                amal_rules source=after
  plan_links          before-lesson planner                                 amal_rules source=before/plan
  amal_rules_other    any other tap she makes in the app (future inputs)    amal_rules, every other source
  verb_checks         verb check lists 1 and 2                              verb_check_links answers / done_at
  word_review         word review links                                     transcript_review_links payload / done_at
  homework            her homework verdicts                                 homework_answers amal_verdict / amal_fix
  grammar_doc         her grammar-rules Google Doc (1SCYeIEu-...)           ANEES_GRAMMAR_DOC_URL (see below)
  quizlet             her Quizlet sets                                      FIRECRAWL_API_KEY (see below) + the local file

Unreadable unattended (status "not readable" with the exact reason, never a silent pass):
  grammar_doc  the Doc is private: https://docs.google.com/document/d/<id>/export?format=txt answers HTTP 401 without a
               Google sign-in, and this PC has no Google API credentials for scripts. Fix: in the Doc, File > Share >
               Publish to web, then set the User env var ANEES_GRAMMAR_DOC_URL to that published URL (the vocabulary Doc's
               ANEES_DOC_PUBLISHED_URL works the same way). A changed Doc is logged as "needs a read": her notes are
               scoring rulings made by reading each row in context (scripts/amal_grammar_notes.py), not a mechanical copy.
  quizlet      quizlet.com answers HTTP 403 to scripts. With FIRECRAWL_API_KEY set, each of her set pages is re-read at
               most once a day; without it only the imported file (docs/data/quizlet/amal-quizlet-sets.json) is watched.
"""
import argparse, datetime as dt, hashlib, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
STATE_P = ROOT / "data" / "amal-trigger" / "state.json"
LOG_P = ROOT / "data" / "amal-trigger" / "log.jsonl"
PAGE_P = ROOT / "docs" / "data" / "amal-trigger.json"
LOCK_P = ROOT / "data" / "amal-trigger" / ".lock"
NODE = os.environ.get("ANEES_NODE") or (r"C:\dev\tools\node-v24.18.0-win-x64\node.exe"
                                        if os.path.exists(r"C:\dev\tools\node-v24.18.0-win-x64\node.exe") else "node")
GRAMMAR_DOC_ID = "1SCYeIEu-N-wxqGe7Y_M4dKTwAPICQKM-_3SgbF4whME"
LOCK_STALE_S = 3 * 3600
QUIZLET_EVERY_S = 24 * 3600


class Unreadable(Exception):
    """The source cannot be read unattended; the message says exactly why."""


def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def fp_rows(rows, keys, stamp_keys=("created_at", "updated_at", "done_at")):
    """Fingerprint of a set of answer rows: content hash of the fields that carry her answer + count + newest stamp."""
    body = sorted((sha({k: r.get(k) for k in keys}) for r in rows))
    stamps = [str(r.get(k)) for r in rows for k in stamp_keys if r.get(k)]
    # her per-answer times (verb check lists keep one updated_at per answer inside "answers"): the row stamps alone said
    # 09-22 while she answered 876 forms on 2026-09-30
    for r in rows:
        a = r.get("answers")
        if isinstance(a, dict):
            stamps += [str(v.get("updated_at")) for v in a.values() if isinstance(v, dict) and v.get("updated_at")]
    newest = max(stamps, default=None)
    return {"hash": sha(body), "n": len(rows), "newest": newest}


# ------------------------------------------------------------------ sources (fetch = read-only)
def _db():
    import db
    return db


def _amal_rules(pred):
    rows = _db().select("amal_rules", {"select": "id,token,source,kind,word_key,payload,created_at,lesson_date", "order": "id.asc"})
    return [r for r in rows if pred(r) and not str(r.get("source") or "").startswith("test")]


def fetch_tutor_verify():
    return fp_rows(_amal_rules(lambda r: r.get("source") == "review" and str(r.get("word_key") or "").startswith("verify:")),
                   ("id", "kind", "word_key", "payload"))


def fetch_pattern_review():
    return fp_rows(_amal_rules(lambda r: r.get("source") == "review" and not str(r.get("word_key") or "").startswith("verify:")),
                   ("id", "kind", "word_key", "payload"))


def fetch_after():
    return fp_rows(_amal_rules(lambda r: r.get("source") == "after"), ("id", "kind", "word_key", "payload"))


def fetch_plan():
    return fp_rows(_amal_rules(lambda r: r.get("source") in ("before", "plan", "planner")), ("id", "kind", "word_key", "payload"))


KNOWN_RULE_SOURCES = ("review", "after", "before", "plan", "planner", "grammar_notes")
# not Amal: machine flags from flashcard answers, and Medi's own marks
NOT_AMAL_SOURCES = ("flashcards", "medi")


def fetch_grammar_notes():
    """Notes Amal writes under the rules on amal/grammar-rules.html (replaces writing in her Google Doc, 2026-10-01)."""
    return fp_rows(_amal_rules(lambda r: r.get("source") == "grammar_notes"), ("id", "kind", "word_key", "payload"))


def fetch_rules_other():
    return fp_rows(_amal_rules(lambda r: r.get("source") not in KNOWN_RULE_SOURCES + NOT_AMAL_SOURCES), ("id", "source", "kind", "word_key", "payload"))


def fetch_verb_checks():
    rows = _db().select("verb_check_links", {"select": "token,answers,done_at,opened_at,created_at", "order": "created_at.asc"})
    return fp_rows(rows, ("token", "answers", "done_at"))


def fetch_word_review():
    rows = _db().select("transcript_review_links", {"select": "token,payload,done_at,opened_at,created_at", "order": "created_at.asc"})
    return fp_rows([{**r, "answers": (r.get("payload") or {}).get("answers")} for r in rows], ("token", "answers", "done_at"))


def fetch_homework():
    rows = _db().select("homework_answers", {"select": "id,amal_verdict,amal_fix,amal_at", "order": "id.asc"})
    return fp_rows([r for r in rows if r.get("amal_verdict") or r.get("amal_fix")], ("id", "amal_verdict", "amal_fix"), ("amal_at",))


def fetch_grammar_doc():
    url = os.environ.get("ANEES_GRAMMAR_DOC_URL")
    if not url:
        raise Unreadable("her grammar Doc is private (the export URL answers HTTP 401 without a Google sign-in) and this PC "
                         "has no Google API credentials; publish the Doc to the web and set ANEES_GRAMMAR_DOC_URL")
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
    except Exception as e:
        raise Unreadable(f"ANEES_GRAMMAR_DOC_URL could not be read ({type(e).__name__}: {str(e)[:120]})")
    return {"hash": sha(text), "n": len(text), "newest": None}


def fetch_quizlet(state_entry=None):
    local = ROOT / "docs" / "data" / "quizlet" / "amal-quizlet-sets.json"
    sets = json.loads(local.read_text(encoding="utf-8"))["sets"]
    fp = {"hash": sha(sets), "n": len(sets), "newest": None, "remote": "not read"}
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        fp["remote"] = "not read: quizlet.com answers HTTP 403 to scripts and FIRECRAWL_API_KEY is not set"
        return fp
    last = (state_entry or {}).get("remote_checked")
    if last and time.time() - dt.datetime.fromisoformat(last).timestamp() < QUIZLET_EVERY_S:
        fp.update(remote="read less than a day ago", remote_hash=(state_entry or {}).get("fp", {}).get("remote_hash"))
        return fp
    import urllib.request
    texts = []
    for s in sets:
        req = urllib.request.Request("https://api.firecrawl.dev/v1/scrape", method="POST",
                                     data=json.dumps({"url": s["url"], "formats": ["markdown"]}).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            texts.append((s["id"], sha(json.loads(r.read()).get("data", {}).get("markdown", ""))))
    fp.update(remote="read", remote_hash=sha(texts), remote_checked=now_iso())
    return fp


# steps: run in THIS order whatever fired (a builder must see what the ones before it wrote)
STEPS = [
    ("pull_verb_checks", [sys.executable, "scripts/verb_check_links.py", "pull"]),
    ("build_word_bank_catalog", [sys.executable, "scripts/build_word_bank_catalog.py"]),
    ("build_verb_addon_tags", [NODE, "scripts/build_verb_addon_tags.cjs"]),
    ("full_audit_build", [sys.executable, "scripts/full_audit_build.py"]),
    # AFTER full_audit_build: the build rewrites the audit JSON without her rulings (2026-09-30 bug: 134 answers wiped)
    ("apply_amal_audit_rulings", [sys.executable, "scripts/apply_amal_audit_rulings.py"]),
    ("amal_grammar_notes", [sys.executable, "scripts/amal_grammar_notes.py"]),
    ("build_grammar_console", [sys.executable, "scripts/build_grammar_console.py"]),
    ("build_amal_docs", [sys.executable, "scripts/build_amal_docs.py"]),   # her two Google Docs as Anees pages (2026-10-01)
    ("build_amal_grammar_rules", [sys.executable, "scripts/build_amal_grammar_rules.py"]),
    ("build_amal_review", [sys.executable, "scripts/build_amal_review.py"]),
    ("build_lessons_page_data", [sys.executable, "scripts/build_lessons_page_data.py"]),
    ("codex_list", [sys.executable, "scripts/codex_rejudge.py", "--list"]),
    ("accuracy_annotate", [sys.executable, "scripts/accuracy_gates.py", "annotate"]),
    ("build_sentence_ladder", [sys.executable, "scripts/build_sentence_ladder.py"]),
    # new words Amal used that are not on her Doc + her add / later / forget taps (Medi 2026-10-02)
    ("amal_new_words", [sys.executable, "scripts/amal_new_words.py"]),
    ("build_tutor_data", [sys.executable, "scripts/build_tutor_data.py"]),
    ("write_build", [sys.executable, "scripts/write_build.py"]),
]
AUDIT_CHAIN = ["full_audit_build", "apply_amal_audit_rulings", "amal_grammar_notes", "build_grammar_console", "build_amal_docs",
               "build_amal_grammar_rules", "build_amal_review", "build_lessons_page_data", "codex_list", "accuracy_annotate", "build_sentence_ladder", "amal_new_words",
               "build_tutor_data"]

SOURCES = [
    {"id": "tutor_verify", "label": "Tutor page: check these moments", "fetch": fetch_tutor_verify, "steps": AUDIT_CHAIN},
    {"id": "pattern_review", "label": "Slips-by-pattern review", "fetch": fetch_pattern_review, "steps": AUDIT_CHAIN},
    {"id": "after_links", "label": "After-lesson questions", "fetch": fetch_after, "steps": AUDIT_CHAIN},
    {"id": "plan_links", "label": "Before-lesson planner", "fetch": fetch_plan, "steps": ["build_tutor_data"]},
    {"id": "amal_rules_other", "label": "Any other answer she gives in the app", "fetch": fetch_rules_other, "steps": AUDIT_CHAIN},
    {"id": "verb_checks", "label": "Verb check lists 1 and 2", "fetch": fetch_verb_checks,
     "steps": ["pull_verb_checks", "build_word_bank_catalog", "build_verb_addon_tags", "build_sentence_ladder", "build_tutor_data"]},
    {"id": "word_review", "label": "Word review", "fetch": fetch_word_review, "steps": ["build_tutor_data"],
     "note": "her answers are detected and logged; showing them in the Word Bank still needs the Speaking release rebuild (not automated)"},
    {"id": "homework", "label": "Homework verdicts", "fetch": fetch_homework, "steps": ["build_tutor_data"]},
    {"id": "grammar_notes", "label": "Grammar notes she writes on the rules page", "fetch": fetch_grammar_notes,
     "steps": ["build_amal_docs", "build_tutor_data"],
     "note": "like her Doc notes, a note becomes a scoring ruling only after a row-by-row read (amal_grammar_notes.py)"},
    {"id": "grammar_doc", "label": "Her grammar-rules Google Doc", "fetch": fetch_grammar_doc, "steps": [],
     "note": "a change is logged as 'needs a read': Claude re-reads the Doc into data/amal-docs/ with Medi's Drive connector (build_amal_docs.py shows it on the Anees rules page); her notes become scoring rulings only after a row-by-row read"},
    {"id": "quizlet", "label": "Her Quizlet sets", "fetch": fetch_quizlet, "steps": ["write_build"], "pass_state": True},
]


# ------------------------------------------------------------------ numbers before / after
def numbers(root=ROOT):
    """The headline numbers a firing can move (flat dict). Offline; reads the built files + the pages' own math."""
    out = {}
    try:
        L = json.loads((root / "docs/data/lessons.json").read_text(encoding="utf-8"))["lessons"]
        for x in L:
            out[f"{x['date']} Words %"] = (x.get("words") or {}).get("pct")
            out[f"{x['date']} Grammar %"] = (x.get("grammar") or {}).get("pct")
    except Exception:
        pass
    try:
        import check_numbers as C
        names = {"pooled words average": "Words % (all lessons)", "pooled grammar average": "Grammar % (all lessons)",
                 "Word Bank accuracy = status points": "Word Bank accuracy", "Words known = Good + Mastered": "Words known"}
        got, orig = [], C.check
        C.check = lambda name, ok, detail="": (got.append((name, detail)), orig(name, ok, detail))[1]
        try:
            C.run(repo=str(root))
        except SystemExit:
            pass
        finally:
            C.check = orig
        for name, detail in got:
            if name in names:
                try:
                    out[names[name]] = round(float(detail.split(" vs ")[0].split(" but ")[0].split()[-1]), 1)
                except ValueError:
                    pass
    except Exception:
        pass
    try:
        V = json.loads((root / "data/vocab/amal_verb_checks.json").read_text(encoding="utf-8"))["answers"]
        out["verb forms checked by Amal"] = len(V)
    except Exception:
        pass
    try:
        out["rows waiting for Amal"] = len(json.loads((root / "docs/data/amal-verify.json").read_text(encoding="utf-8")).get("rows", []))
    except Exception:
        pass
    return out


def moved(before, after):
    return [{"what": k, "from": before.get(k), "to": after.get(k)} for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]


# ------------------------------------------------------------------ lock (shared with the hourly job)
def acquire(wait_s=0):
    LOCK_P.parent.mkdir(parents=True, exist_ok=True)
    end = time.time() + wait_s
    while True:
        try:
            fd = os.open(str(LOCK_P), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps({"pid": os.getpid(), "at": now_iso()}).encode()); os.close(fd)
            return True
        except FileExistsError:
            try:
                if time.time() - LOCK_P.stat().st_mtime > LOCK_STALE_S:
                    LOCK_P.unlink(); continue
            except FileNotFoundError:
                continue
            if time.time() >= end:
                return False
            time.sleep(10)


def release():
    try:
        LOCK_P.unlink()
    except FileNotFoundError:
        pass


# ------------------------------------------------------------------ run
def _load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def _write(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def detect(state, sources=None):
    """-> (changed [(src, fp)], status {id: {...}}). Pure apart from each source's fetch."""
    changed, status = [], {}
    for s in sources or SOURCES:
        prev = (state.get("sources") or {}).get(s["id"]) or {}
        try:
            fp = s["fetch"](prev) if s.get("pass_state") else s["fetch"]()
        except Unreadable as e:
            status[s["id"]] = {"label": s["label"], "readable": False, "why": str(e), "checked": now_iso()}
            continue
        except Exception as e:
            status[s["id"]] = {"label": s["label"], "readable": False, "why": f"read failed ({type(e).__name__}: {str(e)[:160]})", "checked": now_iso()}
            continue
        key = {k: fp.get(k) for k in ("hash", "remote_hash")}
        old = {k: (prev.get("fp") or {}).get(k) for k in ("hash", "remote_hash")}
        status[s["id"]] = {"label": s["label"], "readable": True, "checked": now_iso(), "n": fp.get("n"), "newest": fp.get("newest"),
                           **({"remote": fp["remote"]} if "remote" in fp else {}), **({"note": s["note"]} if s.get("note") else {})}
        if prev.get("fp") is None:
            status[s["id"]]["baseline"] = True            # first sight: remember, do not fire
            state.setdefault("sources", {})[s["id"]] = {"fp": fp, "since": now_iso()}
        elif key != old:
            changed.append((s, fp))
    return changed, status


def run(publish=False, dry_run=False, runner=subprocess.run, root=ROOT, sources=None, log=print):
    state = _load(STATE_P, {"sources": {}})
    changed, status = detect(state, sources)
    if dry_run:
        log(json.dumps({"changed": [s["id"] for s, _ in changed], "status": status}, ensure_ascii=False, indent=1))
        return {"changed": [s["id"] for s, _ in changed], "fired": False}
    firing = None
    if changed:
        want = {st for s, _ in changed for st in s["steps"]}
        before = numbers(root)
        failures, ran = [], []
        for name, cmd in STEPS:
            if name not in want:
                continue
            r = runner(cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            ran.append(name)
            if getattr(r, "returncode", 0):
                failures.append(f"{name} exit {r.returncode}: {(getattr(r, 'stderr', '') or '')[-200:].strip()}")
        after = numbers(root)
        firing = {"at": now_iso(), "changed": [{"source": s["id"], "label": s["label"], "n": fp.get("n"), "newest": fp.get("newest"),
                                                 **({"note": s["note"]} if s.get("note") else {})} for s, fp in changed],
                  "steps": ran, "failures": failures, "numbers_moved": moved(before, after), "published": None}
        if not failures:                                   # fail closed: a failed step keeps the old fingerprint -> retried next run
            for s, fp in changed:
                state["sources"][s["id"]] = {"fp": fp, "since": now_iso()}
                status[s["id"]]["last_change"] = firing["at"]
        LOG_P.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_P, "a", encoding="utf-8") as f:
            f.write(json.dumps(firing, ensure_ascii=False) + "\n")
        log("amal trigger fired:", ", ".join(c["source"] for c in firing["changed"]), "|", len(firing["numbers_moved"]), "numbers moved",
            ("| FAILED " + "; ".join(failures)) if failures else "")
    for sid, st in status.items():
        prev = (state.get("sources") or {}).get(sid) or {}
        st.setdefault("last_change", prev.get("since"))
    state["checked"] = now_iso()
    _write(STATE_P, state)
    page = _load(PAGE_P, {"firings": []})
    page.update({"about": "Anything Amal does is detected (hash of her answers per source), re-pulled, recalculated, and published "
                          "only if the publish guard passes (scripts/amal_trigger.py; Medi 2026-09-29).",
                 "checked": state["checked"], "sources": [{"id": k, **v} for k, v in status.items()]})
    if firing:
        page["firings"] = ([firing] + page.get("firings", []))[:30]
    _write(PAGE_P, page)
    if firing and publish:
        paths = ["docs", "data/amal-trigger", "data/vocab", "data/full-audit-2026-09-26.json", "data/accuracy",
                 "data/lesson-work/full-audit", "data/amal-grammar-notes-2026-09-29.json"]
        paths = [p for p in paths if (root / p).exists()]
        runner(["git", "add", "-A", *paths], cwd=str(root), capture_output=True, text=True)
        c = runner(["git", "commit", "-q", "-m", "Amal trigger: " + ", ".join(x["source"] for x in firing["changed"]) +
                    " changed -> re-pulled and recalculated\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"],
                   cwd=str(root), capture_output=True, text=True)
        import publish_guard as G
        res = G.guarded_push(root, source="amal trigger", step_failures=firing["failures"], log=lambda *a: log(*a))
        firing["published"] = res.get("outcome")
    return {"changed": [s["id"] for s, _ in changed], "fired": bool(firing), "firing": firing}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait", type=int, default=0, help="seconds to wait for the shared job lock (default: skip if busy)")
    a = ap.parse_args(argv)
    if not a.dry_run and not acquire(a.wait):
        print("amal trigger: another Anees job holds the lock; skipped (the next run checks again)"); return 0
    try:
        r = run(publish=a.publish, dry_run=a.dry_run)
        f = r.get("firing") or {}
        return 1 if f.get("failures") else 0
    finally:
        if not a.dry_run:
            release()


if __name__ == "__main__":
    sys.exit(main())
