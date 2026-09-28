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
import datetime, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE); DOCS = os.path.join(REPO, "docs")
sys.path.insert(0, HERE)
OUT = os.path.join(DOCS, "data", "tutor.json")
KEEP_KINDS = {"doc"}


def day(s):
    return str(s or "")[:10]


def pretty(d):
    try:
        x = datetime.date.fromisoformat(d)
        return x.strftime("%b ") + str(x.day)
    except Exception:
        return d


def main():
    import db
    now = datetime.datetime.now(datetime.timezone.utc)
    cur = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"open": [], "closed": []}
    kept = [x for x in cur.get("open", []) if x.get("kind") in KEEP_KINDS]
    open_, closed = [], []
    # review (Amal's slip patterns) + after / before lesson links
    review = json.load(open(os.path.join(DOCS, "data", "amal-review.json"), encoding="utf-8")) if os.path.exists(os.path.join(DOCS, "data", "amal-review.json")) else {}
    seen_review = False
    for r in db.select("amal_links", {"select": "token,kind,lesson_date,created_at,expires_at,opened_at,done_at,payload", "order": "created_at.desc"}):
        live = r["expires_at"] > now.isoformat() and not r.get("done_at")
        p = r.get("payload") or {}
        if r["kind"] == "review":
            if not live or seen_review:
                continue
            seen_review = True
            open_.append({"id": "slips-review", "title": "Review Medi's slips", "kind": "review", "token": r["token"],
                          "what": "Slips she let pass, grouped by pattern with the real moments to play. Per pattern she says: correct him, or a reason not to. New lessons add their patterns here the same day.",
                          "who": "Amal answers · Medi sends the link", "url": f"amal/review.html?t={r['token']}",
                          "total": (review.get("counts") or {}).get("patterns", 0), "moments": sum(len(x.get("examples", [])) for x in review.get("patterns", [])),
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
                              "who": "Amal answers · Medi sends the link", "url": f"amal/{'after' if r['kind'] == 'after' else 'plan'}.html?t={r['token']}",
                              "total": n, "expires": day(r["expires_at"])})
            elif day(r["expires_at"]) >= day((now - datetime.timedelta(days=21)).isoformat()) and not any(c.get("id") == f"{r['kind']}-{r.get('lesson_date')}" for c in closed):
                closed.append({"id": f"{r['kind']}-{r.get('lesson_date')}", "title": title, "why": ("answered" if r.get("done_at") else f"link expired {day(r['expires_at'])}")})
    # verb checks (two lists) and word reviews
    for table, kind, page, title in (("verb_check_links", "verb_check", "verb-check", "Verb check"), ("transcript_review_links", "word_review", "word-review", "Word review")):
        try:
            rows = db.select(table, {"select": "token,created_at,expires_at,opened_at,done_at,payload", "order": "created_at.asc"})
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
                              "what": old.get("what") or ("Every person of every verb she taught, filled in by the app. She taps right, or fixes the spelling." if kind == "verb_check"
                                                            else "Transcript lines where the app is not sure what Medi said. Confirm the wording or type what you heard."),
                              "who": old.get("who") or "Amal answers · Medi sends the link", "url": f"amal/{page}.html?t={r['token']}",
                              "total": total, "pulled": old.get("pulled", 0), "expires": day(r["expires_at"])})
            elif day(r["expires_at"]) >= day((now - datetime.timedelta(days=21)).isoformat()):
                closed.append({"id": f"{kind}-{r['token'][:6]}", "title": title + (f" ({pretty(p.get('lesson'))})" if p.get("lesson") else ""),
                               "why": "answered" if r.get("done_at") else f"link expired {day(r['expires_at'])}"})
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
