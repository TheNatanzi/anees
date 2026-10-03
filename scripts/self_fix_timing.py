# -*- coding: utf-8 -*-
"""GR-24 self-fix by word time (Medi 2026-10-02: "this is clearly a correction. I said Sme3et instead of s7eet. Why did we
skip this? lets figure out systematically what went wrong here so we can create a rule to catch other issues").

What went wrong at 10-02 07:02: he said أنا سمعت (I heard) for "I woke up"; Amal said صحيت; he repeated صحيت and said
"That's right". The third reader dropped the slip as "self-fix before help" because his LINE started at 07:04, before
her line at 07:06. But his line ran 07:04-07:08 and the word صحيت in it was said at 07:07 - 1.7 s AFTER hers. A line's
start time is not the time of every word in it.

The rule: a self-fix counts only when his right word comes BEFORE Amal's right word, by the engine's word times (each
track on the lesson clock). His right word after hers - even inside one line - is her recast, and the slip counts.

    python scripts/self_fix_timing.py scan          # every reader 'self-fix' drop, checked by word time
    python scripts/self_fix_timing.py scan --json   # the same, machine-readable (data/lesson-work/self-fix-timing.json)

Used by scripts/full_audit_build.py: a self-fix drop that this check overturns ('her-first') is put back as a slip with
rule GR-24 (the moment stays visible with both times).
"""
import glob, json, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import transcript_marks as TM  # noqa: E402

WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
RAW = r"C:\dev\anees\data\lessons"
OUT = os.path.join(REPO, "data", "lesson-work", "self-fix-timing.json")
SELF_FIX = re.compile(r"self[- ]?fix|fixe[sd] (it )?himself|corrected himself|self-correct", re.I)
MARGIN = 0.3        # s: closer than this is "the same moment", left to the reader


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def sec(s):
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return float(s)
    p = [float(x) for x in str(s).split(":")]
    return p[-1] + 60 * p[-2] + (3600 * p[0] if len(p) == 3 else 0)


def mmss(t):
    t = int(t)
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def key(s):
    """A word for matching: no punctuation, no Arabizi gloss in brackets, normalised letters."""
    s = re.sub(r"\([^)]*\)", " ", str(s or ""))
    return TM.normalise(re.sub(r"[.…,،؟?!:;\"“”\-]+", " ", s))[0].strip()


def words(date, raw=RAW):
    """{speaker: [(text key, start on the track)]} from the engine's word files (two-track lessons only)."""
    out = {}
    for who in ("Medi", "Amal"):
        p = os.path.join(raw, date, "scribe_%s.json" % who)
        W = (J(p) or {}).get("words") or []
        out[who] = [(key(w["text"]), w["start"]) for w in W if w.get("type", "word") == "word" and w.get("start") is not None]
    return out if out.get("Medi") and out.get("Amal") else None


def offsets(turns, W):
    """Each track's offset onto the lesson clock: median of (page line start - start of the same first word on the track)."""
    off = {}
    for who, ws in W.items():
        d = []
        for u in turns:
            if u["who"] != who:
                continue
            k = (key(u["text"]).split() or [""])[0]
            if not k:
                continue
            near = [s for t, s in ws if t == k and abs(s - u["t"]) < 60]
            if near:
                d.append(u["t"] - min(near, key=lambda s: abs(s - u["t"])))
        off[who] = statistics.median(d) if d else None
    return off


def _strip(t):
    return re.sub(r"^(ال|وال|و|ب|el-?|il-?|w)", "", t) or t


def same(a, b):
    """One word against another: equal, or the same after a leading el- / w- / b-, or one letter apart (ratio >= .8)."""
    import difflib
    if a == b:
        return True
    a, b = _strip(a), _strip(b)
    return a == b or (min(len(a), len(b)) >= 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.8)


def first_after(ws, needle, lo, hi, off):
    """Lesson-clock time of the first word of ws inside [lo, hi] that matches the needle's longest word (several right
    words, e.g. 'عشرة تسعة', are matched on the longest; alternatives 'a / b' on any)."""
    alts = [a.split() for a in re.split(r"\s*/\s*", needle) if a.split()]
    if not alts:
        return None
    cores = [max(a, key=len) for a in alts]
    for t, s in ws:
        c = s + off
        if lo <= c <= hi and any(same(t, k) for k in cores):
            return round(c, 2)
    return None


def check(date, row, turns, W, off):
    """'her-first' (her right word came first: not a self-fix), 'his-first' (a real self-fix), or 'unknown' with why."""
    right = key(row.get("right"))
    t = sec(row.get("t"))
    if not right or t is None:
        return {"verdict": "unknown", "why": "no right word or time on the row"}
    if off.get("Medi") is None or off.get("Amal") is None:
        return {"verdict": "unknown", "why": "track offsets not found"}
    lo, hi = t - 3, t + 40
    his = first_after(W["Medi"], right, lo, hi, off["Medi"])
    hers = first_after(W["Amal"], right, lo, hi, off["Amal"])
    if his is None or hers is None:
        return {"verdict": "unknown", "why": "right word not found on %s track" % ("his" if his is None else "her"),
                "his_t": his, "her_t": hers}
    if his + MARGIN < hers:
        return {"verdict": "his-first", "his_t": his, "her_t": hers}
    if hers + MARGIN < his:
        return {"verdict": "her-first", "his_t": his, "her_t": hers}
    return {"verdict": "unknown", "why": "said at the same moment", "his_t": his, "her_t": hers}


def scan(work=WORK, repo=REPO, raw=RAW):
    """Every reader-3 'drop' whose reason is a self-fix, with the disputed row and the word-time check."""
    out = []
    for p in sorted(glob.glob(os.path.join(work, "20??-??-??*.r3.json"))):
        base = os.path.basename(p)[:-len(".r3.json")]
        date = base[:10]
        r3, cmp_ = J(p) or {}, J(os.path.join(work, base + ".compare.json")) or {}
        disputes = {d["id"]: d for d in cmp_.get("disputes") or []}
        detail = J(os.path.join(repo, "docs", "data", "lessons", date + ".json")) or {}
        W = words(date, raw)
        off = offsets(detail.get("turns") or [], W) if W else {}
        for r in r3.get("rulings") or []:
            if r.get("verdict") != "drop" or not SELF_FIX.search(r.get("why") or ""):
                continue
            d = disputes.get(r["id"]) or {}
            row = d.get("r1") or d.get("r2") or {}
            res = check(date, row, detail.get("turns") or [], W, off) if W else {"verdict": "unknown", "why": "one mixed recording: no per-speaker word times"}
            out.append({"date": date, "pass": base[11:] or "p1", "ruling": r["id"], "t": row.get("t"), "wrong": row.get("wrong"),
                        "right": row.get("right"), "kind": row.get("kind"), "r3_why": r.get("why"), **res})
    return out


def overturned(work=WORK, repo=REPO, raw=RAW):
    """{(date, pass, ruling id)} the word times overturn (her right word came first)."""
    data = J(OUT) if os.path.exists(OUT) else None
    rows = data["rows"] if data else scan(work, repo, raw)
    return {(x["date"], x["pass"], x["ruling"]) for x in rows if x["verdict"] == "her-first"}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    rows = scan()
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"about": "GR-24: every reader-3 self-fix drop checked by word time (scripts/self_fix_timing.py). Generated.",
                   "rows": rows}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for x in rows:
        print(f"{x['date']} {x['pass']:3} {x['ruling']:4} {x['t'] or '?':>7} {x['verdict']:9} his {x.get('his_t')} her {x.get('her_t')} "
              f"{x.get('wrong')} -> {x.get('right')} {x.get('why') or ''}")
    n = sum(1 for x in rows if x["verdict"] == "her-first")
    print(f"{len(rows)} self-fix drops: {n} her word came first (not a self-fix), "
          f"{sum(1 for x in rows if x['verdict'] == 'his-first')} his came first, {sum(1 for x in rows if x['verdict'] == 'unknown')} unknown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
