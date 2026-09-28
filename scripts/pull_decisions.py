# -*- coding: utf-8 -*-
"""Pull human verdicts into the decisions log (data/decisions/YYYY-MM.jsonl, scripts/decisions.py). Read-only, anon key
from docs/js/config.js (the same public key the pages use). Idempotent: a decision_id is derived from the source row id,
so a re-run adds only rows it has not seen. Runs hourly after the publish (hourly_lessons.py) and by hand:

    python scripts/pull_decisions.py            # pull + append
    python scripts/pull_decisions.py --dry-run  # count only
    python scripts/pull_decisions.py --no-git   # skip the commit-message pass

Sources
  amal_rules_public   Amal's taps on her pages (review -> pattern/word, after -> audit row/homework, planner -> plan) and
                      Medi's 'new' marks. The view hides the token and the payload (so no reason / rows here).
                      source 'flashcards' is skipped: the cards page files it automatically after two misses, not a verdict.
  sentence_labels     Medi's swipes on machine-labelled sentences (may not exist yet: a 404 is fine).
  draft_word_reviews  Medi's verdicts on draft word matches (the row can be updated: a new verdict supersedes the old line).
  git log             commit subjects ending "Medi|Amal YYYY-MM-DD: yes|no" (strict; any other wording is not parsed).
Never logs transcript text: only ids, enums and short Latin values (track.safe hashes Arabic or long text).
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import decisions  # noqa: E402

PAGE = 1000
GIT_DECISION = re.compile(r"\b(Medi|Amal) (\d{4}-\d{2}-\d{2}): ?\"?(yes|no)\"?\.?\)?\s*$", re.I)


def config():
    s = open(os.path.join(REPO, "docs", "js", "config.js"), encoding="utf-8").read()
    return re.search(r"url:\s*'([^']+)'", s).group(1), re.search(r"anon:\s*'([^']+)'", s).group(1)


def http_fetch(table, select="*", order="id.asc"):
    """All rows of a public table/view (paged). None when the table does not exist (404)."""
    import requests
    url, anon = config()
    h = {"apikey": anon, "Authorization": "Bearer " + anon}
    out, off = [], 0
    while True:
        r = requests.get(f"{url}/rest/v1/{table}", params={"select": select, "order": order, "limit": PAGE, "offset": off},
                         headers=h, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        rows = r.json()
        out += rows
        if len(rows) < PAGE:
            return out
        off += PAGE


# ------------------------------------------------------------------ row -> decision (pure, tested)

def from_amal_rule(row):
    """amal_rules_public row -> decision kwargs, or None when it is not a human verdict."""
    src, kind = row.get("source"), row.get("kind")
    if src == "flashcards" or not kind:
        return None
    who = "Medi" if src == "medi" else "Amal"
    wk = row.get("word_key")
    if src == "review":
        about = "pattern" if kind in ("audit_confirm", "audit_skip") else "word"
    elif src == "after":
        about = "audit_row" if kind in ("right", "wrong", "not_medi") else "homework"
    elif src == "planner":
        about = "plan"
    else:
        about = "word"
    about_id = wk if wk else f"{src}:{row.get('lesson_date') or '-'}:{kind}"
    return dict(_key=("amal_rules", src, row.get("lesson_date"), wk) if wk else None, decision_id=f"amal_rules:{row['id']}", ts=row.get("created_at"), who=who,
                channel="app" if who == "Medi" else "tutor_page", about_type=about, about_id=about_id, answer=kind,
                corrected_value=row.get("text") if kind == "edit" else None,
                source_row={"table": "amal_rules", "id": row["id"], "source": src, "lesson_date": row.get("lesson_date")})


def from_sentence_label(row):
    return dict(_key=("sentence_labels", row.get("sentence_id")), decision_id=f"sentence_labels:{row['id']}", ts=row.get("ts") or row.get("created_at"), who="Medi",
                channel="swipe", about_type="label", about_id=row.get("sentence_id"),
                ai_run_id=f"sentence-ladder@{row['machine_version']}" if row.get("machine_version") else None,
                ai_value=row.get("machine_label"), answer=row.get("label"), latency_ms=row.get("answer_ms"),
                source_row={"table": "sentence_labels", "id": row["id"], "lesson_date": row.get("lesson_date"),
                            "side": row.get("side"), "n_words": row.get("n_words"), "played": row.get("played")})


def from_draft_review(row):
    """The row can be updated in place: its id + reviewed_at identify one verdict."""
    return dict(_key=("draft_word_reviews", row["id"]), decision_id=f"draft_word_reviews:{row['id']}@{row.get('reviewed_at')}", ts=row.get("reviewed_at"), who="Medi",
                channel="review_page", about_type="word", about_id=row.get("id"), answer=row.get("verdict"),
                source_row={"table": "draft_word_reviews", "id": row["id"], "lesson_date": row.get("lesson_date"),
                            "word_key": row.get("word_key")})


def git_decisions(repo=REPO, log_text=None):
    """Commit subjects that END with 'Medi|Amal YYYY-MM-DD: yes|no'. log_text (tests) = '<sha>\\x1f<iso>\\x1f<subject>' lines."""
    if log_text is None:
        log_text = subprocess.run(["git", "-C", repo, "log", "--format=%H%x1f%aI%x1f%s"], capture_output=True, text=True,
                                  encoding="utf-8", timeout=60).stdout
    out = []
    for line in log_text.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        sha, iso, subj = parts
        m = GIT_DECISION.search(subj)
        if not m:
            continue
        what = subj[:m.start()].rstrip(" -:;,(")
        out.append(dict(decision_id=f"commit:{sha[:12]}", ts=iso, who=m.group(1).capitalize(), channel="commit",
                        about_type="change", about_id=sha[:12], answer=m.group(3).lower(), reason=what, applied_commit=sha,
                        source_row={"table": "git", "id": sha[:12], "said_on": m.group(2)}))
    return out


# ------------------------------------------------------------------ pull

SOURCES = (("amal_rules_public", "id,created_at,source,lesson_date,kind,word_key,text", "id.asc", from_amal_rule),
           ("sentence_labels", "*", "created_at.asc", from_sentence_label),
           ("draft_word_reviews", "id,lesson_date,word_key,verdict,reviewed_at", "reviewed_at.asc", from_draft_review))


def pull(fetch=http_fetch, directory=None, dry=False, use_git=True, git_log=None):
    """Returns {source: {fetched, new, skipped, error?}}. Appends only decision_ids not yet in the log."""
    have = decisions.known_ids(directory)
    latest = {}                                               # supersede key -> latest decision_id (a re-tap / relabel)
    for x in decisions.read(directory):
        k = (x.get("source_row") or {}).get("key")
        if k:
            latest[k] = x.get("decision_id")
    report, new = {}, []
    for table, select, order, conv in SOURCES:
        st = report.setdefault(table, {"fetched": 0, "new": 0, "skipped": 0})
        try:
            rows = fetch(table, select, order)
        except Exception as e:
            st["error"] = type(e).__name__
            continue
        if rows is None:
            st["error"] = "table missing (404)"
            continue
        st["fetched"] = len(rows)
        for row in rows:
            try:
                kw = conv(row)
            except Exception:
                kw = None
            if not kw or not kw.get("answer"):
                st["skipped"] += 1
                continue
            key = kw.pop("_key", None)
            key = decisions.track.safe("|".join("" if p is None else str(p) for p in key)) if key else None
            if kw["decision_id"] in have:
                continue
            if key:
                kw["source_row"] = {**(kw.get("source_row") or {}), "key": key}
                if latest.get(key) and latest[key] != kw["decision_id"]:
                    kw["supersedes"] = latest[key]
            try:
                line = decisions.make(**kw)
            except ValueError:
                st["skipped"] += 1
                continue
            have.add(kw["decision_id"])
            if key:
                latest[key] = kw["decision_id"]
            new.append(line)
            st["new"] += 1
    if use_git:
        st = report.setdefault("git", {"fetched": 0, "new": 0, "skipped": 0})
        try:
            for kw in git_decisions(log_text=git_log):
                st["fetched"] += 1
                if kw["decision_id"] in have:
                    continue
                new.append(decisions.make(**kw)); have.add(kw["decision_id"]); st["new"] += 1
        except Exception as e:
            st["error"] = type(e).__name__
    if not dry:
        d = directory or decisions.decisions_dir()
        for line in sorted(new, key=lambda x: (x["ts"] or "", x["decision_id"])):
            decisions.track.append_line(d, line["ts"][:7], line)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()
    rep = pull(dry=a.dry_run, use_git=not a.no_git)
    print(json.dumps(rep, indent=1))
    real = [k for k in rep if k != "sentence_labels"]
    return 1 if real and all(rep[k].get("error") for k in real) else 0


if __name__ == "__main__":
    sys.exit(main())
