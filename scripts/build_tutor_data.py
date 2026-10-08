# -*- coding: utf-8 -*-
"""The Tutor page's data (docs/data/tutor.json), built from what is actually open for Amal (Medi 2026-09-26: "wire
everything into the system so it's seamless, part of the menu").

Every unexpired, unfinished link she has - in amal_links (review / after / before), verb_check_links and
transcript_review_links - becomes one card with its total; expired or finished links go to "closed". Cards the
page cannot derive (her grammar Google Doc) are kept from the current file by id. Answered counts stay live in
docs/js/tutor.js (read with each link's own token). Runs every hour from hourly_lessons.py and after every
same-day review (review_lesson.py step 7c); safe to run any time.

    python scripts/build_tutor_data.py            -> rewrites docs/data/tutor.json, prints the open cards
"""
import re, datetime, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE); DOCS = os.path.join(REPO, "docs")
sys.path.insert(0, HERE)
OUT = os.path.join(DOCS, "data", "tutor.json")
# Hand-kept cards: none since 2026-10-01 (her grammar Google Doc card became the Anees grammar-notes card below).
KEEP_KINDS = set()
NOTES = os.path.join(DOCS, "data", "amal-grammar-notes.json")
LISTEN = os.path.join(DOCS, "data", "amal-listen.json")
CHECKS = os.path.join(DOCS, "data", "amal-checks.json")



def screen_words(text):
    """PG-33 (2026-10-07 audit): a question stored in a link payload before the name change still says 'Medi' - on screen it is the student."""
    return str(text).replace("Did Medi ", "Did the student ") if text else text

def day(s):
    return str(s or "")[:10]


def pretty(d):
    try:
        x = datetime.date.fromisoformat(d)
        return x.strftime("%b ") + str(x.day)
    except Exception:
        return d


def pulled_count(payload, repo=REPO):
    """How many of this verb link's answers are IN the app (eng audit 2026-09-29: the page kept a hand-typed 41 while 729
    were pulled). List 1 (verb-forms): answers in data/vocab/amal_verb_checks.json whose form id is one of the link's
    items. List 2 (verb-addons): answers in data/vocab/amal_addon_checks.json for the link's items."""
    payload = payload or {}
    items = set((payload.get("items") or {}).keys())
    vocab = os.path.join(repo, "data", "vocab")
    if payload.get("kind") == "verb-addons":
        p = os.path.join(vocab, "amal_addon_checks.json")
        if not os.path.exists(p):
            return 0
        A = json.load(open(p, encoding="utf-8"))
        if isinstance(A.get("answers"), dict):
            return len(items & set(A["answers"]))
        n = 0
        for verb, e in A.items():
            if isinstance(e, dict):
                keys = (["obj"] if "object" in e else []) + list(e.get("preps_ok") or []) + list(e.get("preps_off") or [])
                n += sum(1 for k in keys if f"{verb}:addon:{k}" in items)
        return n
    p = os.path.join(vocab, "amal_verb_checks.json")
    if not os.path.exists(p):
        return 0
    return len(items & set((json.load(open(p, encoding="utf-8")).get("answers") or {})))


def tap_dates(rules):
    """{(token, word_key or label): latest created_at} from her taps (db.select already leaves undone taps out, AM-17)."""
    out = {}
    for r in rules:
        p = r.get("payload") or {}
        for k in (r.get("word_key"), p.get("audit_uid"), p.get("arabizi"), p.get("english"), p.get("topic") and "topic"):
            if k:
                out[(r.get("token"), str(k))] = max(out.get((r.get("token"), str(k))) or "", r.get("created_at") or "")
    return out


_AUDIT = {}


def audit_rows():
    """uid -> the audit row (his line, her line, what it counts as now)."""
    if not _AUDIT:
        p = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
        if os.path.exists(p):
            _AUDIT.update({x["uid"]: x for x in json.load(open(p, encoding="utf-8")).get("rows", [])})
    return _AUDIT


def mmss(t):
    try:
        t = int(float(t))
    except (TypeError, ValueError):
        return None
    return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


SCORED = ("grammar", "vocab-A")


def clip_for(date, clip, t):
    """A recording that is on the site: the short clip, else the moment in the full lesson (each channel), else None
    (check_pages: no dead play button)."""
    if clip and os.path.exists(os.path.join(DOCS, "lessons", clip)):
        return "lessons/" + clip
    if t is None:
        return None
    for n in ("lesson.mp3", "Medi.mp3", "Amal.mp3"):
        if os.path.exists(os.path.join(DOCS, "lessons", str(date), "audio", n)):
            return f"lessons/{date}/audio/{n}#t={max(0, int(float(t)) - 3)},{int(float(t)) + 12}"
    return None


def effect_after(label, row):
    """What her answer changed (PG-18 'the result'): the audit row's state now when the row is known, else what the tap does."""
    k = (row or {}).get("kind")
    if k in SCORED:
        return "counted as a mistake for the student"
    if k in ("rejected", "dropped-by-amal"):
        return "not counted as a mistake"
    return {"Right": "not counted as a mistake", "Wrong": "counted as a mistake for the student", "Wrong word": "counted as a mistake for the student (wrong word)",
            "Wrong grammar": "counted as a mistake for the student (wrong grammar)", "Not Medi": "dropped - it was not the student", "Skip": "no change"}.get(label, None)


def link_detail(r, dates):
    """Medi 2026-10-02 "can you make these into accodrians so I can see what you are asking": every question a link asked
    and Amal's answer (or not answered), stored here so it stays readable after the link expires."""
    p, a, tok = r.get("payload") or {}, r.get("answers") or {}, r.get("token")
    asked = []

    def when(k):
        return (dates.get((tok, str(k))) or "")[:10] or None

    def pick(m, k):
        m = m or {}
        return m.get(str(k), m.get(k))
    if r.get("kind") == "after":
        rows = audit_rows()
        carried = a.get("carried_from") or {}
        for i, q in enumerate(p.get("questions") or []):
            ans = pick(a.get("q"), i)
            row = rows.get(q.get("audit_uid")) or {}
            t = q.get("t")
            asked.append({"ask": screen_words(q.get("ask")), "word": q.get("arabizi") or q.get("arabic"), "arabic": q.get("arabic"), "english": q.get("english"),
                          "t": mmss(t), "clip": clip_for(r.get("lesson_date"), q.get("clip"), t),
                          "medi": row.get("medi_said"), "amal": row.get("amal_said"),
                          "answer": ans, "at": (when(q.get("audit_uid") or q.get("word_key")) or (a.get("updated") or r.get("done_at") or "")[:10] or None) if ans else None,
                          "result": effect_after(ans, row) if ans else ((a.get("not_asked") or {}).get(str(i)) or None),
                          "carried": str(i) in (carried.get("questions") or {})})
        for i, h in enumerate(p.get("homework") or []):
            ans = pick(a.get("hw"), i)
            asked.append({"ask": "Homework suggestion: keep, drop or edit?", "word": h.get("arabizi"), "english": h.get("english"), "answer": ans,
                          "at": when(h.get("arabizi")) if ans else None})
        for it in p.get("prompts") or []:
            ans = pick(a.get("pr"), it.get("id"))
            asked.append({"ask": "Homework line: keep, drop or edit?", "word": it.get("english"), "answer": ans, "at": when(it.get("english")) if ans else None})
    elif r.get("kind") == "before":
        asked.append({"ask": "What is today's lesson about?", "answer": a.get("topic"), "at": when("topic") if a.get("topic") else None})
        asked.append({"ask": "Words for today", "answer": ", ".join(a.get("repeat") or []) or None})
        for i, x in enumerate(p.get("sentences") or []):
            ans = pick(a.get("sentences"), i)
            asked.append({"ask": "Keep this sentence?", "word": x.get("arabizi"), "english": x.get("english"), "answer": ans, "at": when(x.get("arabizi")) if ans else None})
    elif r.get("kind") == "word_review":
        ans = a.get("answers") or {}
        said = {"yes": "Yes, that is what I hear", "inaudible": "Cannot hear clearly"}
        for it in p.get("items") or []:
            x = ans.get(it.get("id")) or {}
            got = said.get(x.get("choice")) or (("Different: " + (x.get("text") or "")) if x.get("choice") else None)
            asked.append({"ask": "What do you hear?", "word": it.get("proposal"), "answer": got, "at": (x.get("updated_at") or "")[:10] or None})
    elif r.get("kind") == "verb_check":
        ans, items = (a.get("answers") or {}), (p.get("items") or {})
        for iid, x in sorted(ans.items(), key=lambda kv: kv[1].get("updated_at") or ""):
            it = items.get(iid) or {}
            asked.append({"ask": f"{it.get('tense', '')} · {it.get('person', '')}", "word": it.get("word"),
                          "answer": "Right" if x.get("choice") == "yes" else "Fixed: " + str(x.get("word") or ""), "at": (x.get("updated_at") or "")[:10] or None})
    total = len(p.get("items") or {}) if r.get("kind") == "verb_check" else len(asked)
    out = {"answered": sum(1 for x in asked if x.get("answer")), "total": total, "asked": asked}
    if (a.get("carried_from") or {}).get("token"):
        out["carried_from"] = a["carried_from"]["token"]
    return out


def on_screen(text):
    """PG-33 (Medi 2026-10-07): the hub is read by the tutor - she is "you", Medi is "the student". Applied to the hub's
    titles and lines, including ones carried over from an older build or read from docs/data/amal-checks.json; names stay
    in ids, tokens and data keys."""
    if not isinstance(text, str):
        return text
    for a, b in (("Amal answers", "You answer"), ("Amal writes", "You write"), ("link already with her", "link already with you")):
        text = text.replace(a, b)
    text = re.sub(r"(^|[.!?]\s+)Medi\b", lambda m: m.group(1) + "The student", text)
    return re.sub(r"\bMedi\b", "the student", text)


def answered_first(rows):
    """AM-18: a lesson's row shows the link Amal really answered; a link re-made after she answered (and closed with her
    answers carried over) goes inside it as 'made again by mistake'."""
    for x in rows:
        E = x.get("earlier") or []
        src = (x.get("detail") or {}).get("carried_from")
        hit = next((e for e in E if e.get("token") == src), None)
        if not hit:
            continue
        moved = {"why": "made again by the hourly re-review after she had answered; closed with her answers (AM-18)",
                 "token": x.get("token"), "expires": x.get("expires"), "detail": x.get("detail")}
        x["token"], x["expires"], x["detail"], x["why"] = hit["token"], hit["expires"], hit["detail"], hit["why"]
        x["earlier"] = [moved] + [e for e in E if e is not hit]
    return rows


def main():
    import db
    now = datetime.datetime.now(datetime.timezone.utc)
    cur = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"open": [], "closed": []}
    kept = [x for x in cur.get("open", []) if x.get("kind") in KEEP_KINDS]
    open_, closed = [], []
    # review (Amal's slip patterns) + after / before lesson links
    review = json.load(open(os.path.join(DOCS, "data", "amal-review.json"), encoding="utf-8")) if os.path.exists(os.path.join(DOCS, "data", "amal-review.json")) else {}
    seen_review = False
    try:
        dates = tap_dates(db.select("amal_rules", {"select": "token,kind,word_key,payload,created_at", "source": "in.(after,planner)"}))
    except Exception as e:  # noqa: BLE001 - the dates are a nicety; the answers come from the link rows
        print("tap dates not read:", type(e).__name__)
        dates = {}
    for r in db.select("amal_links", {"select": "token,kind,lesson_date,created_at,expires_at,opened_at,done_at,payload,answers", "order": "created_at.desc"}):
        live = r["expires_at"] > now.isoformat() and not r.get("done_at")
        p = r.get("payload") or {}
        if r["kind"] == "review":
            if not live or seen_review:
                continue
            seen_review = True
            open_.append({"id": "slips-review", "title": "The student's mistakes to review", "kind": "review", "token": r["token"],
                          "what": "Mistakes the student made (a wrong word or wrong grammar) that you let pass in the lesson, grouped by kind, with the real moments to play. For each kind you say: yes, count it, or no, he was fine. New lessons add their patterns here the same day.",
                          "who": "You answer · the student sends the link", "url": f"amal/review.html?t={r['token']}",
                          "total": (review.get("counts") or {}).get("patterns", 0), "moments": sum(len(x.get("examples", [])) for x in review.get("patterns", [])),
                          "expires": day(r["expires_at"])})
            # Her grammar notes live on the Anees rules page now, written with this same link's token (Medi 2026-10-01:
            # nothing Amal uses stays in a Google Doc or behind a login). Her Doc notes are shown under each rule.
            notes = json.load(open(NOTES, encoding="utf-8")) if os.path.exists(NOTES) else {"sections": []}
            open_.append({"id": "grammar-notes", "title": "Grammar rules · her notes", "kind": "grammar_notes", "token": r["token"],
                          "what": "The student's 57 grammar rules. Under each rule: her notes from her Doc (" + str(len(notes.get("sections", [])))
                                  + " notes) and a box to write a new one - no Google Doc needed. Each note she saves reaches the app.",
                          "who": "You write · the student sends the link", "url": f"amal/grammar-rules.html?t={r['token']}",
                          "doc_notes": len(notes.get("sections", [])), "expires": day(r["expires_at"])})
            open_.append({"id": "materials", "title": "Arabic Materials", "kind": "materials", "token": None,
                          "what": "Her explanations: prepositions, possession, adjectives, time, kul, the b- prefix and the pointer rule, copied word for word from her Doc.",
                          "who": "To read · no answers needed", "url": "amal/materials.html"})
            # Her listening check (Medi 2026-10-04 "put anything that needs to be checked in the tutor portal"): her own
            # lines, two versions each. Saved with this same link's token (amal_rules source 'listen-check').
            n_listen = len(json.load(open(LISTEN, encoding="utf-8")).get("items") or []) if os.path.exists(LISTEN) else 0
            if n_listen:
                open_.append({"id": "listen-check", "title": "Listen: which version is right?", "kind": "listen", "token": r["token"],
                              "what": f"{n_listen} of your own lines from two lessons, each written two ways. Play your clip and tap the one that is right. About 10 minutes.",
                              "who": "You answer · on your Tutor page", "url": f"amal/listen-check.html?t={r['token']}",
                              "total": n_listen, "expires": day(r["expires_at"])})
            # Her other listening / checking lists (Medi 2026-10-05 "have amal do the 27 line check too", "did you put the
            # 108 on amals list", "5 send to amal"): one row per list of docs/data/amal-checks.json, same token, same saving.
            for c in (json.load(open(CHECKS, encoding="utf-8")).get("lists") or []) if os.path.exists(CHECKS) else []:
                if c.get("total"):
                    open_.append({"id": "check-" + c["list"], "title": c["title"], "kind": "check", "list": c["list"], "token": r["token"],
                                  "what": c["what"], "who": "You answer · on your Tutor page", "url": f"amal/check.html?list={c['list']}&t={r['token']}",
                                  "total": c["total"], "unit": c.get("unit") or "items", "min_each": round(c.get("mins", 5) / c["total"], 3),
                                  "expires": day(r["expires_at"])})
        elif r["kind"] in ("after", "before"):
            title = ("After the lesson · " if r["kind"] == "after" else "Before the lesson · ") + pretty(r.get("lesson_date") or "")
            n = len(p.get("questions") or []) + len(p.get("homework") or []) + len(p.get("prompts") or []) if r["kind"] == "after" else len(p.get("suggestions") or p.get("items") or [])
            if live:
                if any(x["kind"] == r["kind"] and x.get("lesson_date") == r.get("lesson_date") for x in open_):
                    continue                                   # one card per lesson: the newest link wins
                open_.append({"id": f"{r['kind']}-{r.get('lesson_date')}", "title": title, "kind": r["kind"], "token": r["token"], "lesson_date": r.get("lesson_date"),
                              "what": ("3-5 moments from this lesson the app was least sure about: was he right here? One tap each, with the clip." if r["kind"] == "after"
                                       else "Words to bring back and sentences to try in this lesson. Keep or drop."),
                              "who": "You answer · the student sends the link", "url": f"amal/{'after' if r['kind'] == 'after' else 'plan'}.html?t={r['token']}",
                              "total": n, "expires": day(r["expires_at"]), "detail": link_detail(r, dates)})
            elif day(r["expires_at"]) >= day((now - datetime.timedelta(days=21)).isoformat()):
                why = "answered" if r.get("done_at") else f"link expired {day(r['expires_at'])}"
                row = {"id": f"{r['kind']}-{r.get('lesson_date')}", "title": title, "why": why, "kind": r["kind"], "lesson_date": r.get("lesson_date"),
                       "token": r["token"], "expires": day(r["expires_at"]), "detail": link_detail(r, dates)}
                # 2026-10-02: a lesson can have two links (a newer one replaced the first). The older one is shown INSIDE
                # the lesson's row as "an earlier link", never as a second row with the same title.
                newer = next((x for x in open_ + closed if x.get("kind") == r["kind"] and x.get("lesson_date") == r.get("lesson_date")), None)
                if newer:
                    newer.setdefault("earlier", []).append({"why": why, "token": r["token"], "expires": row["expires"], "detail": row["detail"]})
                else:
                    closed.append(row)
    # verb checks (two lists) and word reviews
    for table, kind, page, title in (("verb_check_links", "verb_check", "verb-check", "Verb check"), ("transcript_review_links", "word_review", "word-review", "Word review")):
        try:
            rows = db.select(table, {"select": "token,created_at,expires_at,opened_at,done_at,payload,answers", "order": "created_at.asc"})
        except Exception as e:
            print("skip", table, e)
            continue
        n_open = 0
        for r in rows:
            p = r.get("payload") or {}
            items = p.get("items") or []
            total = len(items)
            live = r["expires_at"] > now.isoformat() and not r.get("done_at")
            if live:
                n_open += 1
                lvl = " · list 2 (endings and prepositions)" if p.get("kind") == "verb-addons" else (" · list 1" if kind == "verb_check" else "")
                old = next((x for x in cur.get("open", []) if x.get("token") == r["token"]), {})
                open_.append({"id": f"{kind}-{n_open}", "title": title + lvl + (f" · {pretty(p.get('lesson'))}" if p.get("lesson") else ""), "kind": kind, "token": r["token"],
                              "what": old.get("what") or p.get("what") or ("Every person of every verb she taught, filled in by the app. She taps right, or fixes the spelling." if kind == "verb_check"
                                                            else "Transcript lines where the app is not sure what the student said. Confirm the wording or type what you heard."),
                              "who": old.get("who") or "You answer · the student sends the link", "url": f"amal/{page}.html?t={r['token']}",
                              "total": total, "pulled": pulled_count(p) if kind == "verb_check" else old.get("pulled", 0),
                              "expires": day(r["expires_at"])})
            elif day(r["expires_at"]) >= day((now - datetime.timedelta(days=21)).isoformat()):
                closed.append({"id": f"{kind}-{r['token'][:6]}", "title": title + (f" ({pretty(p.get('lesson'))})" if p.get("lesson") else ""),
                               "why": "answered" if r.get("done_at") else f"link expired {day(r['expires_at'])}", "kind": kind,
                               "token": r["token"], "expires": day(r["expires_at"]), "detail": link_detail({**r, "kind": kind}, {})})
    answered_first(closed)
    for x in kept + open_ + closed:
        for k in ("title", "what", "who"):
            if k in x:
                x[k] = on_screen(x[k])
    # keep the old stamp when nothing changed, so the hourly job does not commit a new file every hour
    same = cur.get("open") == kept + open_ and cur.get("closed") == closed
    out = {"updated": cur.get("updated") if same and cur.get("updated") else now.astimezone().isoformat(timespec="seconds"),
           "note": "What Amal needs to check right now. Rebuilt by scripts/build_tutor_data.py every hour and after every same-day lesson review; "
                   "answered counts are read live from Supabase with each link's own token. Medi sends every link himself; the app never contacts Amal.",
           "open": kept + open_, "closed": closed}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for x in out["open"]:
        print(f"open   {x['id']:22} {x.get('total', x.get('done', '')):>5}  {x['title']}")
    for x in closed:
        print(f"closed {x['id']:22}        {x['title']} - {x['why']}")


if __name__ == "__main__":
    main()
