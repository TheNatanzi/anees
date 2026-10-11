# -*- coding: utf-8 -*-
"""AM-29 - the tutor's half of an exam lesson's answer key (Medi 2026-10-11: "mix 30-20", after "Put it in the tutor
panel I will have amal work on it as well"; plan/PIPELINE-TEST-PROTOCOL.md section 2.4: whether a moment of the
student's line is right is checked by the tutor too, blind, on her own page).

    python scripts/build_tutor_key_check.py                 # build the card list(s) (default: every exam in EXAMS)
    python scripts/build_tutor_key_check.py pull            # her answers -> data/lesson-work/review-grades/tutor-check-answers.json
    python scripts/build_tutor_key_check.py 2026-10-09      # one lesson

The 50 moments of one exam lesson: 30 lines of tier 1 (unsure) + 20 lines of tiers 2 and 3, both drawn from
docs/data/review-pick/<date>.json (scripts/review_picker.py) by a hash of the date and the line time (stable: the same
date always gives the same lines; once written, the selection is read back from the key file and never moves), shown
in time order. BLIND: the card data carries no chip, no robot mark, no tier, no reason and no student answer - only the
student's clip (the lesson page's clip of the line, else the lesson audio from 1 s before it), his line as the transcript
has it (Arabizi first, the Arabic small after - RULES.md S1 / PG-44 - and the English under it, PG-48) and the tutor's
own line just before and just after it. The tiers stay in the key, outside docs/.

Writes
  docs/data/amal-check-key-check-<date>.json   the list (the Tutor page's check-list module, docs/js/hub/check-task.js:
                                               one options question with four plain sentences, AM-23 / PG-33)
  data/lesson-work/review-grades/tutor-check-<date>-key.json   which line is which tier (never published)
Her taps are amal_rules rows (source 'listen-check', kind 'key_check', word_key 'keycheck:<item id>', her review link's
token - the table and kind her other checking lists already use; no migration). `pull` mirrors them read-only into
data/; scripts/review_grades.py compares them with the student's fast-review keys on the same line and adds
amal_check to the grade book row. Her answers are a measurement only: nothing here or there changes a lesson page.
No AI call; nothing is written to Supabase."""
import hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

EXAMS = ["2026-10-09"]                 # the exam lessons whose key the tutor checks (protocol section 1b: 10-09 is the first)
N_UNSURE, N_REST = 30, 20              # Medi 2026-10-11 "mix 30-20"
SECS_EACH = 14.4                       # 50 moments in about 12 minutes (AM-05: short, one tap each)
KIND, PREFIX, SOURCE = "key_check", "keycheck", "listen-check"
CONTEXT_S = 30.0                       # her line before / after: within 30 s of his line
QUOTE = "mix 30-20"

QUESTION = {"field": "answer", "ask": "Listen to the student. Which is true?", "type": "options",
            "options": [{"v": "right", "label": "The words are right and the student said it right"},
                        {"v": "words", "label": "The words are not what the student said",
                         "box": "What did the student really say? (Arabic or Arabizi)"},
                        {"v": "mistake", "label": "The student made a mistake here",
                         "box": "How should it be said? (optional)"},
                        {"v": "cant_tell", "label": "Can't tell from the recording"}]}
ANSWERS = [o["v"] for o in QUESTION["options"]]
# the student's fast-review keys (PG-50, docs/js/review-mode.js) as the same sentence: 1 heard right, 2 wrong word,
# 3 mistake; key 4 ('not a mistake' about a robot chip) says nothing about the words, so it is never compared
HIS_KEY = {1: "right", 2: "words", 3: "mistake"}
COMPARED = ("right", "words", "mistake")       # her "Can't tell" is never compared


def J(p, d=None):
    if not p or not os.path.exists(p):
        return d
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


def list_name(date):
    return "key-check-" + date


def data_path(date, repo=REPO):
    return os.path.join(repo, "docs", "data", "amal-check-%s.json" % list_name(date))


def key_path(date, repo=REPO):
    return os.path.join(repo, "data", "lesson-work", "review-grades", "tutor-check-%s-key.json" % date)


ANSWERS_P = os.path.join(REPO, "data", "lesson-work", "review-grades", "tutor-check-answers.json")


def mmss(t):
    t = int(max(0, float(t or 0)))
    return "%d:%02d:%02d" % (t // 3600, t // 60 % 60, t % 60) if t >= 3600 else "%02d:%02d" % (t // 60, t % 60)


def pretty(d):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)$", str(d or ""))
    return ("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[int(m.group(2)) - 1] + " " + str(int(m.group(3)))) if m else str(d or "")


def item_id(date, t):
    return "%s:t%d" % (date, int(round(float(t) * 100)))


# ------------------------------------------------------------------ the 50 moments
def _rank(date, t):
    return hashlib.sha1(("keycheck|%s|%.2f" % (date, float(t))).encode("utf-8")).hexdigest()


def select(pick, date, n_unsure=N_UNSURE, n_rest=N_REST):
    """-> [{t, end, tier}] in time order: n_unsure tier-1 lines + n_rest tier-2/3 lines, each group ranked by a hash of
    the date and the line time (the same date always picks the same lines)."""
    lines = [x for x in (pick or {}).get("lines") or [] if x.get("t") is not None]
    t1 = sorted((x for x in lines if x.get("tier") == 1), key=lambda x: _rank(date, x["t"]))[:n_unsure]
    rest = sorted((x for x in lines if x.get("tier") in (2, 3)), key=lambda x: _rank(date, x["t"]))[:n_rest]
    return sorted(({"t": round(float(x["t"]), 2), "end": round(float(x.get("end") if x.get("end") is not None else x["t"]), 2),
                    "tier": x["tier"]} for x in t1 + rest), key=lambda x: x["t"])


def _arabizi(texts):
    """[Arabizi or None] through the shared renderer (node); None for every line when node is missing."""
    if not texts:
        return []
    try:
        r = subprocess.run(["node", os.path.join(HERE, "tutor_key_check_arabizi.cjs")], input=json.dumps(texts, ensure_ascii=False),
                           capture_output=True, text=True, encoding="utf-8", timeout=120, cwd=REPO)
        out = json.loads(r.stdout or "[]")
        return [(o or {}).get("text") for o in out] if len(out) == len(texts) else [None] * len(texts)
    except Exception as e:  # noqa: BLE001 - no Arabizi = the Arabic alone (S1: never a guessed spelling)
        print("arabizi: not rendered (%s)" % type(e).__name__)
        return [None] * len(texts)


def _line(turns, idx):
    text = " ".join(str(turns[i].get("text") or "").strip() for i in idx).strip()
    en = " ".join(str(turns[i].get("en") or "").strip() for i in idx if turns[i].get("en")).strip()
    return text, en or None


def _clip(page, t, end):
    """The lesson page's clip of the line (the review mode's own pick), else None."""
    for v in (page.get("vocab_errors") or []) + (page.get("vocab_correct") or []):
        c = v.get("clip")
        if c and v.get("t") is not None and t - 1 <= float(v["t"]) <= end + 1:
            return re.sub(r"^lessons/", "", c.split("#")[0])
    return None


def cards(date, chosen, page, render=_arabizi):
    """The blind card for each chosen line (see the module doc). render(texts) -> Arabizi per text."""
    turns = page.get("turns") or []
    built, texts = [], []
    for c in chosen:
        t, end = c["t"], c["end"]
        idx = [i for i, u in enumerate(turns) if u.get("who") == "Medi" and t - 0.05 <= float(u.get("t") or 0) <= end + 0.05]
        if not idx:
            continue
        text, en = _line(turns, idx)
        before = next((i for i in range(idx[0] - 1, -1, -1) if turns[i].get("who") == "Amal" and t - float(turns[i].get("t") or 0) <= CONTEXT_S
                       and str(turns[i].get("text") or "").strip()), None)
        after = next((i for i in range(idx[-1] + 1, len(turns)) if turns[i].get("who") == "Amal" and float(turns[i].get("t") or 0) - end <= CONTEXT_S
                      and str(turns[i].get("text") or "").strip()), None)
        win = "%s/audio/lesson.mp3#t=%.2f,%.2f" % (date, max(0.0, t - 1), end + 0.8)
        clip = _clip(page, t, end)
        x = {"id": item_id(date, t), "date": date, "mmss": mmss(t), "t": t, "end": end,
             "clips": [{"label": "The student", "src": clip or win, "fallback": win}],
             "line": {"label": "The student", "ar": text, "en": en}, "rows": []}
        texts.append(text)
        for lab, i in (("You, just before", before), ("You, just after", after)):
            if i is not None:
                tx, e = _line(turns, [i])
                x["rows"].append({"label": "%s · %s" % (lab, mmss(turns[i]["t"])), "ar": tx, "en": e})
                texts.append(tx)
        built.append(x)
    az = render(texts)
    k = 0
    for x in built:
        for part in [x["line"]] + x["rows"]:
            a = az[k] if k < len(az) else None
            k += 1
            part["az"] = a if a and a.strip() and a.strip() != part["ar"].strip() else None
    return built


def doc(date, items):
    n = len(items)
    mins = max(1, round(n * SECS_EACH / 60))
    title = "Check %d moments of the %s lesson (about %d minutes)" % (n, pretty(date), mins)
    return {"set": "tutor-key-check", "list": list_name(date), "kind": KIND, "prefix": PREFIX, "date": date,
            "title": title, "unit": "moments", "mins": mins,
            "intro": "Short clips of the student from the %s lesson, each with his line as the transcript has it. Listen, then "
                     "tap what is true. One tap each; Undo is next to every answer." % pretty(date),
            "what": "Short clips of the student from the %s lesson, with his line as the transcript has it and your line just "
                    "before and after. One tap each. About %d minutes." % (pretty(date), mins),
            "questions": [QUESTION], "n": n, "items": items}


def build(date, repo=REPO, render=_arabizi, log=print):
    pick = J(os.path.join(repo, "docs", "data", "review-pick", date + ".json"))
    page = J(os.path.join(repo, "docs", "data", "lessons", date + ".json"))
    if not pick or not page:
        log("tutor key check %s: no review pick or lesson page yet - skipped" % date)
        return None
    kp = key_path(date, repo)
    key = J(kp) or {}
    chosen = key.get("items") if key.get("date") == date and key.get("items") else select(pick, date)
    items = cards(date, chosen, page, render)
    D = doc(date, items)
    old = J(data_path(date, repo)) or {}
    if old.get("tutor_from"):
        D["tutor_from"] = old["tutor_from"]              # tutor_scope.scope_all stamps it; kept so a rebuild is a no-op
    if old.get("paused"):
        D["paused"] = old["paused"]
    W(data_path(date, repo), D)
    if not key.get("items"):
        W(kp, {"about": "AM-29: which of the tutor's %d key-check moments of %s is which tier (1 unsure, 2 changed, 3 confident; "
                        "docs/data/review-pick/%s.json at the first build). Frozen at the first build so the selection never moves; "
                        "never published (her cards are blind)." % (len(chosen), date, date),
                "date": date, "rule": "AM-29", "quote": QUOTE, "built": time.strftime("%Y-%m-%d"),
                "items": [{"id": item_id(date, c["t"]), "word_key": PREFIX + ":" + item_id(date, c["t"]), "t": c["t"], "end": c["end"], "tier": c["tier"]}
                          for c in chosen]})
    log("tutor key check %s: %d moments (%d unsure + %d others), about %d min" % (
        date, len(items), sum(1 for c in chosen if c["tier"] == 1), sum(1 for c in chosen if c["tier"] != 1), D["mins"]))
    return D


def build_all(repo=REPO, render=_arabizi, log=print):
    return [build(d, repo, render, log) for d in EXAMS]


# ------------------------------------------------------------------ her answers (read-only mirror) + the agreement
def pull(path=ANSWERS_P, fetch=None, log=print):
    """amal_rules source listen-check, word_key keycheck:* -> data/ (db.select leaves undone taps out, AM-17). The
    stamp moves only when the rows do, so the hourly job does not commit an unchanged file."""
    if fetch is None:
        import db
        fetch = lambda: db.select("amal_rules", {"select": "id,kind,word_key,payload,created_at", "source": "eq." + SOURCE,
                                                 "word_key": "like.%s:*" % PREFIX, "order": "id.asc"})
    rows = fetch()
    old = J(path) or {}
    if old.get("rows") == rows:
        log("tutor key check: %d answer rows, unchanged" % len(rows))
        return rows
    W(path, {"about": "AM-29: the tutor's key-check taps (amal_rules source listen-check, word_key keycheck:*), pulled read-only "
                      "by scripts/build_tutor_key_check.py pull. Undone taps are left out (AM-17); the latest tap per moment wins. "
                      "A measurement only: nothing is changed by it.",
             "pulled": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": rows})
    log("tutor key check: pulled %d answer rows" % len(rows))
    return rows


def her_answers(rows):
    """{word_key: answer} - her latest tap per moment (an undo as the latest row = no answer)."""
    out = {}
    for r in sorted(rows or [], key=lambda r: (r.get("id") or 0, str(r.get("created_at") or ""))):
        k = r.get("word_key")
        if not k:
            continue
        a = (r.get("payload") or {}).get("answer")
        if r.get("kind") == "undo" or a not in ANSWERS:
            out.pop(k, None)
        else:
            out[k] = a
    return out


def his_key(r):
    p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
    k = p.get("key")
    if k is None:
        k = {"rule-answer": 1, "text": 2, "add": 3, "not-slip": 4}.get(r.get("kind"))
    try:
        return int(k)
    except (TypeError, ValueError):
        return None


def agreement(key_items, her_rows, his_rows):
    """The grade book's amal_check: her answer vs the student's fast-review answer on the same line, when both exist.
    key_items = the key file's items; her_rows = her pulled rows; his_rows = his fast-mode rows still standing (undone ones
    out), any order - his latest answer on a line counts."""
    hers = her_answers(her_rows)
    his = {}
    for r in sorted(his_rows or [], key=lambda r: str(r.get("ts") or r.get("created_at") or "")):
        p = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        if p.get("relisten"):
            continue
        try:
            t = float(r.get("turn_t") if r.get("turn_t") is not None else p.get("t"))
        except (TypeError, ValueError):
            continue
        for it in key_items or []:
            if it["t"] - 0.6 <= t <= it["end"] + 0.6:
                his[it["word_key"]] = his_key(r)
    answered = sum(1 for it in key_items or [] if it["word_key"] in hers)
    pairs = [(hers[it["word_key"]], HIS_KEY.get(his.get(it["word_key"]))) for it in key_items or []
             if hers.get(it["word_key"]) in COMPARED and HIS_KEY.get(his.get(it["word_key"]))]
    agree = sum(1 for a, b in pairs if a == b)
    return {"total": len(key_items or []), "answered": answered, "compared_n": len(pairs), "agree_with_student_n": agree,
            "agreement_pct": round(100.0 * agree / len(pairs), 1) if pairs else None}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["pull"]:
        try:
            pull()
        except Exception as e:  # noqa: BLE001 - fail open: the grade book keeps the last mirror
            print("tutor key check: answers not pulled (%s)" % type(e).__name__)
        return 0
    for d in (argv or EXAMS):
        build(d)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
