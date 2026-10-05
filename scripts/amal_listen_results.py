# -*- coding: utf-8 -*-
"""Amal's listening / checking lists: her answers against the keys. READ-ONLY.

    python scripts/amal_listen_results.py            # every list
    python scripts/amal_listen_results.py --lines    # + every card with her answer
    python scripts/amal_listen_results.py --json

Reads Supabase amal_rules (source 'listen-check'; an undone tap is left out and the latest tap per card wins -
scripts/db.py, AM-17) and the keys under data/lesson-work/ (never published):
  amal-listen-key.json            her own 40 lines (Medi 2026-10-04 "make it for amal"): for 3-of-3 and 2-of-3 Gemini
                                  agreement, ElevenLabs right / Gemini right / both wrong / same or can't tell
  amal-slip-check-key.json        the 27 confirmed slips whose line changed (2026-10-05): said it wrong / right / not
                                  sure, old or new version per card, and the council threshold line
  amal-check-<list>-key.json      own-fix (Medi's typing / an AI run / something else), word-said-N and word-there
                                  (yes / no totals), old-new (old / new), one-or-two (same / different per pair)
Counts only - nothing is written anywhere."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "data" / "lesson-work"
KEY = WORK / "amal-listen-key.json"
INDEX = ROOT / "docs" / "data" / "amal-checks.json"
SOURCE = "listen-check"
COLS = ("elevenlabs", "gemini", "both_wrong", "same", "unanswered")
LABEL = {"elevenlabs": "ElevenLabs right", "gemini": "Gemini right", "both_wrong": "both wrong", "same": "same / can't tell",
         "unanswered": "not answered"}
# the council's rule for the 27 (Codex final approval 2026-10-05): how many "he said it wrong" decide the publish
THRESHOLDS = ((3, "publish"), (7, "remove those overlay rows"), (10 ** 9, "do not publish"))


def latest(rows):
    """{word_key: her latest tap} (rows in id order; undone taps already left out by db.select)."""
    out = {}
    for r in sorted(rows or [], key=lambda r: (r.get("id") or 0, str(r.get("created_at") or ""))):
        if r.get("kind") != "undo" and r.get("word_key"):
            out[r["word_key"]] = r
    return out


def verdict(k, row):
    """elevenlabs | gemini | both_wrong | same | unanswered for one key item and her row (or None)."""
    c = ((row or {}).get("payload") or {}).get("choice")
    if c in ("a", "b"):
        return k[c]
    return c if c in ("both_wrong", "same") else "unanswered"


def tally(key_items, rows):
    ans = latest(rows)
    table = {g: {c: 0 for c in COLS} for g in (3, 2)}
    lines = []
    for k in key_items:
        row = ans.get(k["word_key"])
        v = verdict(k, row)
        table.setdefault(k["agree"], {c: 0 for c in COLS})[v] += 1
        lines.append({"id": k["id"], "agree": k["agree"], "result": v, "elevenlabs": k["elevenlabs"], "gemini": k["gemini"],
                      "typed": ((row or {}).get("payload") or {}).get("typed"), "at": (row or {}).get("created_at")})
    return table, lines


# ---- the lists of docs/data/amal-checks.json ---------------------------------------------------------------------------
def picked(k, p):
    """What her version tap really was: the key's role of that letter (old / new / medi / ai run 1,2 ...), 'other', or None."""
    c = (p or {}).get("choice")
    if not c:
        return None
    return "something else" if c == "other" else (k.get("roles") or {}).get(c, c)


def check_tally(key_items, rows, fields):
    """-> ({field: {answer: n}}, cards). A version tap is counted under what it really was (picked)."""
    ans = latest(rows)
    counts = {f: {} for f in fields}
    cards = []
    for k in key_items:
        p = (ans.get(k["word_key"]) or {}).get("payload") or {}
        got = {}
        for f in fields:
            v = picked(k, p) if f == "choice" else p.get(f)
            v = v or "unanswered"
            if f == "choice" and v.startswith("ai run"):
                v = "an AI run"
            counts[f][v] = counts[f].get(v, 0) + 1
            got[f] = v
        cards.append({"id": k["id"], **got, "typed": p.get("typed"), "key": k})
    return counts, cards


def threshold(wrong):
    return next(what for top, what in THRESHOLDS if wrong <= top)


def threshold_line(counts):
    m = counts.get("mistake") or {}
    wrong, open_ = m.get("yes", 0), m.get("unanswered", 0)
    line = (f"Council threshold (0-3 wrong = publish, 4-7 = remove those overlay rows, 8+ = do not publish): "
            f"{wrong} said wrong -> {threshold(wrong)}")
    if open_:
        hi = wrong + open_
        line += f"  [{open_} not answered yet: could still reach {hi} -> {threshold(hi)}]"
    return line


def fmt(d, order=None):
    keys = [k for k in (order or []) if k in d] + sorted(k for k in d if k not in (order or []))
    return ", ".join(f"{k} {d[k]}" for k in keys) or "-"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    import db
    rows = db.select("amal_rules", {"select": "id,kind,word_key,payload,created_at", "source": f"eq.{SOURCE}", "order": "id.asc"})
    out = {}
    key = json.loads(KEY.read_text(encoding="utf-8"))["items"]
    table, lines = tally(key, rows)
    out["listen"] = {"table": {str(g): t for g, t in table.items()}, "lines": lines}
    index = json.loads(INDEX.read_text(encoding="utf-8"))["lists"] if INDEX.exists() else []
    by_task = {}
    for L in index:
        K = json.loads((WORK / L["key"]).read_text(encoding="utf-8"))
        D = json.loads((ROOT / "docs" / "data" / f"amal-check-{L['list']}.json").read_text(encoding="utf-8"))
        counts, cards = check_tally(K["items"], rows, [q["field"] for q in D["questions"]])
        out[L["list"]] = {"title": L["title"], "counts": counts, "cards": [{k: v for k, v in c.items() if k != "key"} for c in cards]}
        by_task.setdefault(L["task"], []).append((L, counts, cards))
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    print("== Her own 40 lines: which version is right ==")
    for g in (3, 2):
        t = table[g]; n = sum(t.values()); done = n - t["unanswered"]
        print(f"Gemini runs agreed {g} of 3 - {n} lines, {done} answered")
        for c in COLS:
            pct = f"  ({round(100 * t[c] / done)}% of answered)" if done and c != "unanswered" else ""
            print(f"   {LABEL[c]:<18} {t[c]:>3}{pct}")
    if a.lines:
        for x in lines:
            print(f"{x['id']:<16} agree {x['agree']}  {LABEL[x['result']]:<18} EL: {x['elevenlabs']} | GM: {x['gemini']}" + (f" | she typed: {x['typed']}" if x["typed"] else ""))
    YN = ("yes", "no", "not_sure", "unanswered")
    for task, parts in by_task.items():
        total = {}
        for L, counts, cards in parts:
            print(f"\n== {L['title']} ({L['total']}) ==")
            for f, d in counts.items():
                print(f"   {f:<8} {fmt(d, YN + ('same', 'different', 'old', 'new', 'medi', 'an AI run', 'something else'))}")
                for k, v in d.items():
                    total.setdefault(f, {})[k] = total.setdefault(f, {}).get(k, 0) + v
            if task == "slip-check":
                m = counts["mistake"]
                print(f"   said it wrong {m.get('yes', 0)} · said it right {m.get('no', 0)} · not sure {m.get('not_sure', 0)} · not answered {m.get('unanswered', 0)}")
                print("   " + threshold_line(counts))
            if a.lines or task in ("slip-check", "one-or-two"):
                for c in cards:
                    k = c["key"]
                    if task == "slip-check":
                        print(f"   {c['id']:<24} picked {c['choice']:<14} mistake {c['mistake']:<10} {k.get('wrong')} -> {k.get('right')}" + (f" | she typed: {c['typed']}" if c["typed"] else ""))
                    elif task == "one-or-two":
                        print(f"   {c['id']:<40} {c['same']:<10} " + " || ".join(f"{s.get('mmss')} {s.get('wrong')} -> {s.get('right')}" for s in k.get("slips") or []))
                    else:
                        print(f"   {c['id']:<24} " + " ".join(f"{f}={c[f]}" for f in counts) + (f" | {k.get('word')}" if k.get("word") else "") + (f" | she typed: {c['typed']}" if c["typed"] else ""))
        if len(parts) > 1:
            print(f"\n== {task}: all {len(parts)} parts together ==")
            for f, d in total.items():
                print(f"   {f:<8} {fmt(d, YN)}")


if __name__ == "__main__":
    main()
