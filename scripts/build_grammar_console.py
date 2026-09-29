# -*- coding: utf-8 -*-
"""Build docs/data/grammar-console.json from the hand sweep + lesson transcripts.

Corrections (mistakes) come ONLY from the hand sweep data/grammar-sweep-2026-09-24.json
(Medi approved 2026-09-25): every speaking row filed in an approved bucket is one
mistake in `bucket` (bucket2 never adds a second). Listening rows, rejected rows,
pronunciation rows and the unapproved NEW-A12 / NEW-C11 groups never count; NEW-B18
is bucket B18. The machine audit no longer counts. Uses stay machine-counted
(docs/data/grammar-usage.json).

Only real data. Rules with no recorded use are emitted as status "Untested"
with uses=0 so the console can show an honest empty row.
"""
import json, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # this checkout, never the live hourly one (2026-09-29)
DOCS = os.path.join(ROOT, "docs")
LESSONS = r"C:\dev\anees\data\lessons"
OUT = os.path.join(DOCS, "data", "grammar-console.json")

tally = json.load(open(os.path.join(DOCS, "data", "tally.json"), encoding="utf-8"))
buckets = json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]

# The machine audit. These are candidates, never scores: only a human ticking
# one promotes it to a slip. Kept in a separate stream so a guess can never
# move a number on the page.
AUDIT = os.path.join(DOCS, "data", "grammar-audit.json")
audit = json.load(open(AUDIT, encoding="utf-8")) if os.path.exists(AUDIT) else {"events": [], "lessons": []}
USAGE = os.path.join(DOCS, "data", "grammar-usage.json")
usage = json.load(open(USAGE, encoding="utf-8")) if os.path.exists(USAGE) else {"uses": {}, "lessons": {}}
# F1 and F3 match any hard letter / any shadda, so their "use" count is every
# Arabic word Medi says. That is not a rule being exercised - leave them unscored.
NO_USAGE_SCORE = {"F1", "F2", "F3"}

# ---- the hand sweep: the only source of corrections ----
SWEEP_NAME = "grammar-sweep-2026-09-24"
SWEEP = os.path.join(ROOT, "data", SWEEP_NAME + ".json")
# Full audit 2026-09-26 supersedes the sweep: same row shape through its sweep_compat view (see scripts/full_audit_build.py).
AUDIT = os.path.join(ROOT, "data", "full-audit-2026-09-26.json")
if os.path.exists(AUDIT):
    SWEEP_NAME = "full-audit-2026-09-26"
    sweep = json.load(open(AUDIT, encoding="utf-8"))["sweep_compat"]
else:
    sweep = json.load(open(SWEEP, encoding="utf-8"))
BUCKET_IDS = {b["id"] for b in buckets}
APPROVED_NEW = {"NEW-B18": "B18"}          # NEW-A12 / NEW-C11 are not approved buckets
_not_counted = {x["id"] for x in sweep.get("rejected_on_hand_check", []) + sweep.get("pron_from_sweep", [])}


def secs(v):
    if not v:
        return None
    p = [float(x) for x in str(v).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


# Amal's notes (2026-09-27, applied 2026-09-29): some corrections no longer count (her note says it is not a
# mistake), and B14 / B15 are not taught yet. Those rows stay on the page, marked "not counted" with the reason.
import sys as _sys
_sys.path.insert(0, os.path.join(ROOT, "scripts"))
import amal_grammar_notes as AMAL  # noqa: E402

sweep_rows, sweep_left_out, ruled_rows = [], [], []
for r in sweep["rows"] + sweep.get("unfiled", []):
    b = r.get("bucket") or APPROVED_NEW.get(r.get("new_bucket_group"))
    if r.get("mode") != "speaking" or r["id"] in _not_counted or b not in BUCKET_IDS:
        sweep_left_out.append(r["id"])
        continue
    ru = AMAL.ruling(dict(r, bucket=b))
    if ru:
        ruled_rows.append(dict(r, bucket=b, _ruling=ru))
        continue
    sweep_rows.append(dict(r, bucket=b))

# Each candidate gets its own short clip, cut like the word bank's: from just
# before he spoke to a few seconds after her fix. Streaming the hour-long
# lesson.mp3 with a #t= jump left the player at 0:00 on phones.
import hashlib, shutil, subprocess
PRE, POST, GAP = 1.0, 4.0, 20.0


def cut_clip(c, post=None):
    adir = os.path.join(DOCS, "lessons", c["date"], "audio")
    srcs = [os.path.join(adir, "lesson.mp3")]
    if not os.path.exists(srcs[0]):
        # a lesson kept only as per-speaker tracks on one clock (09-10): mix them
        srcs = [os.path.join(adir, f) for f in ("Amal.mp3", "Medi.mp3")]
    if not isinstance(c.get("t"), (int, float)) or not all(map(os.path.exists, srcs)) or not shutil.which("ffmpeg"):
        return None
    ts = sorted([c["t"]] + ([c["recast_t"]] if isinstance(c.get("recast_t"), (int, float)) else []))
    # his line and her fix; if they sit far apart (a typed chat fix), join two short pieces
    parts = [(max(0.0, ts[0] - PRE), ts[-1] + (POST if post is None else post))] if ts[-1] - ts[0] <= GAP         else [(max(0.0, t - PRE), t + 8.0) for t in ts]
    key_ = "|".join(f"{a:.1f}-{b:.1f}" for a, b in parts)
    name = "gc-" + hashlib.sha1(f"{c['date']}|{key_}".encode()).hexdigest()[:16] + ".mp3"
    out = os.path.join(DOCS, "lessons", c["date"], "clips", name)
    if not os.path.exists(out) or not os.path.getsize(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        tmp = out + ".part.mp3"
        chain = ""
        for i, (a, b) in enumerate(parts):
            if len(srcs) == 1:
                chain += f"[0:a]atrim={a:.2f}:{b:.2f},asetpts=PTS-STARTPTS[p{i}];"
            else:
                chain += "".join(f"[{k}:a]atrim={a:.2f}:{b:.2f},asetpts=PTS-STARTPTS[p{i}s{k}];" for k in range(len(srcs)))
                chain += "".join(f"[p{i}s{k}]" for k in range(len(srcs))) + f"amix=inputs={len(srcs)}:normalize=0[p{i}];"
        chain += "".join(f"[p{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[o]"
        ins = [x for f in srcs for x in ("-i", f)]
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", chain, "-map", "[o]",
                        "-ac", "1", "-b:a", "48k", tmp], check=True)
        os.replace(tmp, out)
    return f"{c['date']}/clips/{name}"




# "You used it" entries get the same card: his line with the rule word marked, plus a clip.
import html as _html


def dress_use(u):
    said = u.get("said") or ""
    esc = _html.escape(said)
    hit = u.get("hit")
    if hit and _html.escape(hit) in esc:
        esc = esc.replace(_html.escape(hit), '<mark class="ab-correct">' + _html.escape(hit) + "</mark>", 1)
    u["said_html"] = esc
    u["clip"] = cut_clip({"date": u["date"], "t": u["t"]}, post=6.0)
    return u

# ---- Medi sentence counts per lesson, straight from the transcripts ----
def medi_sentences(date):
    p = os.path.join(LESSONS, date, "transcript.txt")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8", errors="replace").read()
    turns = re.findall(r"\[\d+:\d+\]\s*Medi:\s*([^\n]+)", t)
    n = 0
    for turn in turns:
        turn = re.sub(r"\(pause[^)]*\)", " ", turn)
        for part in re.split(r"[.!?؟]+", turn):
            if len(part.strip()) >= 3:
                n += 1
    return n or None

audit_lessons = {L["date"]: L for L in audit.get("lessons", [])}
lesson_dates = sorted(set(list(tally["lessons"]) + list(usage.get("lessons", {}).keys()) + list(audit_lessons)
                          + [r["date"] for r in sweep_rows]))

import sys
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from lesson_turns import lesson_turns  # noqa: E402
_AUD = {}


def turns_sentences(date):
    """His turns with two or more Arabic words - the auditor's own unit and word test
    (Arabic script or a non-English Latin word), for lessons the auditor never read."""
    if not _AUD:
        src = open(os.path.join(ROOT, "scripts", "audit_grammar_lessons.py"), encoding="utf-8").read()
        _AUD["__file__"] = os.path.join(ROOT, "scripts", "audit_grammar_lessons.py")
        exec(src.split("# ---------------------------------------------------------------- run")[0], _AUD)
    T, _ = lesson_turns(date)
    return sum(1 for x in T if x["speaker"] == "Medi" and len(_AUD["_ar_words"](x["text"])) >= 2) or None
lessons = []
for d in lesson_dates:
    al = audit_lessons.get(d) or {}
    lessons.append({
        "date": d,
        # his turns with two or more Arabic words, in any script - the same unit for every lesson
        "medi_sentences": al.get("medi_sentences") or turns_sentences(d) or medi_sentences(d)
                          or (usage.get("lessons", {}).get(d) or {}).get("medi_arabic_turns"),
        "slips": sum(1 for r in sweep_rows if r["date"] == d),
    })

# ---- roll the tally rules onto buckets ----
by_rule = {r["id"]: r for r in tally["rules"]}

# Reuse the auditor's differ so the hand-verified rows get the same
# underlining as the machine-found ones.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "gaudit", os.path.join(ROOT, "scripts", "audit_grammar_lessons.py"))


def _differ():
    src = open(os.path.join(ROOT, "scripts", "audit_grammar_lessons.py"), encoding="utf-8").read()
    ns = {"__file__": os.path.join(ROOT, "scripts", "audit_grammar_lessons.py")}
    exec(src.split("# ---------------------------------------------------------------- run")[0], ns)
    return ns["diff_spans"]


diff_spans = _differ()

# ---- sweep rows -> console candidates (same shape the JS reads) ----
import difflib, unicodedata

_TASHKEEL = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")


def _n(w):
    w = _TASHKEEL.sub("", unicodedata.normalize("NFC", w)).lower()
    w = re.sub(r"[أإآ]", "ا", w).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[^\w]", "", w)


def mark_piece(text, piece, cls):
    """Wrap the words of `text` that best match `piece` in <mark class=cls>. None if no match."""
    text, piece = text or "", (piece or "").strip()
    if not text or not piece:
        return None
    esc = _html.escape
    if piece in text:
        i = text.index(piece)
        return esc(text[:i]) + f'<mark class="{cls}">' + esc(piece) + "</mark>" + esc(text[i + len(piece):])
    toks = list(re.finditer(r"\S+", text))
    want = [_n(w) for w in piece.split() if _n(w)]
    norm = [_n(m.group(0)) for m in toks]
    if not want or not toks:
        return None
    best, span = 0.0, None
    k = len(want)
    for size in {max(1, k - 1), k, k + 1}:
        for i in range(0, len(toks) - size + 1):
            sc = difflib.SequenceMatcher(a=" ".join(want), b=" ".join(norm[i:i + size]), autojunk=False).ratio()
            if sc > best:
                best, span = sc, (i, i + size)
    if best < 0.7:
        return None
    a, b = toks[span[0]].start(), toks[span[1] - 1].end()
    return esc(text[:a]) + f'<mark class="{cls}">' + esc(text[a:b]) + "</mark>" + esc(text[b:])


mark_stats = {"said": 0, "recast": 0, "fallback": 0, "none": 0}
cands, uncounted = {}, {}
for r in sweep_rows + ruled_rows:
    said, recast = r.get("medi_said") or "", r.get("amal_said") or ""
    sh, rh = mark_piece(said, r.get("wrong"), "ab-wrong"), mark_piece(recast, r.get("right"), "ab-correct")
    if not (sh and rh) and said and recast:
        d = diff_spans(said, recast, wrong_word=r.get("wrong"), fixed_word=r.get("right"))
        if d["wrong"] and d["fixed"]:
            mark_stats["fallback"] += 1
            sh, rh = sh or d["said_html"], rh or d["recast_html"]
    mark_stats["said"] += bool(sh)
    mark_stats["recast"] += bool(rh)
    mark_stats["none"] += not (sh or rh)
    t, ta = secs(r.get("t")), secs(r.get("t_amal"))
    c = {
        "id": r["id"],
        "bucket": r["bucket"],
        "bucket2": r.get("bucket2"),
        "date": r["date"],
        # three 09-23 rows have no time for his line: the card and clip sit on her fix
        "t": t if t is not None else ta,
        "mmss": r.get("t") or r.get("t_amal"),
        "said": said,
        "recast": recast,
        "recast_at": r.get("t_amal"),
        "recast_t": ta,
        "said_html": sh or _html.escape(said),
        "recast_html": rh or _html.escape(recast),
        "wrong": r.get("wrong"),
        "right": r.get("right"),
        "pair_wrong": r.get("wrong") or "",
        "pair_fixed": r.get("right") or "",
        "said_arabizi": r.get("medi_said_arabizi"),
        "recast_arabizi": r.get("amal_said_arabizi"),
        "wrong_arabizi": r.get("wrong_arabizi"),
        "right_arabizi": r.get("right_arabizi"),
        "why": r.get("mistake") or "",
        "signal": r.get("signal"),
        "chat": r.get("chat"),
        "confidence": r.get("confidence") or "medium",
        "confidence_why": r.get("confidence_why"),
        "machine_audit": r.get("machine_audit", False),
        "verified": True,
        "source": "hand-" + SWEEP_NAME,
    }
    clip_at = dict(c) if t is not None else dict(c, t=max(0.0, ta - 6.0))
    c["clip"] = cut_clip(clip_at)
    ru = r.get("_ruling")
    if ru:
        # shown on the page, never counted: Amal's note says it is not a mistake, or its rule is not taught yet
        c.update({"counted": False, "not_counted_kind": ru["kind"], "not_counted_rule": ru["rule"],
                  "not_counted_why": ru["why"]})
        uncounted.setdefault(c["bucket"], []).append(c)
    else:
        cands.setdefault(c["bucket"], []).append(c)
for v in list(cands.values()) + list(uncounted.values()):
    v.sort(key=lambda e: (e["date"], e["t"] or 0), reverse=True)


def event(kind, e):
    said, recast = e.get("said") or "", e.get("recast") or ""
    marks = {}
    # A recast that is a tick or a note, not a re-saying, has nothing to underline.
    if said and recast and not recast.lstrip().startswith(("✓", "✔")):
        d = diff_spans(said, recast)
        if d["wrong"] and d["fixed"]:
            marks = {"said_html": d["said_html"], "recast_html": d["recast_html"]}
    return {
        "kind": kind,                      # slip | right | ask
        "date": e.get("date"),
        "mmss": e.get("mmss"),
        "t": e.get("t"),
        "said": e.get("said"),
        "recast": e.get("recast"),
        "recast_at": e.get("recast_at"),
        "clip": e.get("clip"),
        "offset": e.get("offset"),
        "audio_note": e.get("audio"),
        "verified": e.get("verified", False),
        **marks,
    }

def status(uses, mistakes):
    if not uses:
        return "Untested"
    pct = round(100 * (uses - mistakes) / uses)
    if uses >= 10 and pct >= 95:
        return "Mastered"
    # Medi 2026-09-23: few uses are rated on the score alone (3 of 3 right = Good, not Shaky).
    # Mastered still needs 10+ uses.
    if pct >= 85:
        return "Good"
    if pct >= 65:
        return "Shaky"
    return "Wrong"

import grammar_math  # noqa: E402
GT = grammar_math.table(usage.get("uses", {}), [{"bucket": c["bucket"], "date": c["date"], "t": c["t"]} for v in cands.values() for c in v],
                        [b["id"] for b in buckets], AMAL.not_taught)
rows = []
for b in buckets:
    rid = b.get("tally_rule")
    r = by_rule.get(rid) if rid else None
    events = []
    if r:
        # The tally's slips are not shown or counted any more: the hand sweep re-read
        # those three lessons in full and carries every fix Amal said aloud.
        for e in r.get("rights", []):
            events.append(event("right", e))
        for e in r.get("asks", []):
            events.append(event("ask", e))
    events.sort(key=lambda e: (str(e["date"]), e["t"] if isinstance(e["t"], (int, float)) else 0), reverse=True)

    # How many times he actually used this rule, right or wrong.
    u = [] if b["id"] in NO_USAGE_SCORE else usage.get("uses", {}).get(b["id"], [])
    u = sorted(u, key=lambda x: (x["date"], x["t"]), reverse=True)
    mine = cands.get(b["id"], [])
    asks = sum(1 for e in events if e["kind"] == "ask")

    # A mistake is a correction Amal voiced or typed (full audit; Amal's notes take some out). Uses and mistakes come
    # from scripts/grammar_math.py - the ONE formula the Lessons page uses too (eng audit 2026-09-29): a correction with
    # no counted use within 2 s is itself a use, so mistakes never exceed uses.
    T = GT[b["id"]]
    verified_slips = len(mine)
    auto_slips = 0
    nt = T["not_taught"]
    uses_seen = T["detected"] + T["extra"] if b["id"] not in NO_USAGE_SCORE else 0
    uses, mistakes = T["uses"], T["mistakes"]
    if nt:
        verified_slips = 0
    nc = uncounted.get(b["id"], [])
    rows.append({
        "id": b["id"], "family": b["family"], "name": b["name"],
        "one_line": b["one_line"], "examples": b["examples"],
        "why": b["why"], "more": b["more"],
        "tally_rule": rid,
        "tally_title": r["title"] if r else None,
        "kind": r.get("kind") if r else None,
        "candidates": mine,
        "candidate_count": len(mine),
        "usage": [dress_use(x) for x in u[:40]],
        "usage_total": len(u),
        "last_used": u[0]["date"] if u else None,
        "last_used_mmss": u[0]["mmss"] if u else None,
        "verified_slips": verified_slips,
        "auto_slips": auto_slips,
        "uses": uses, "mistakes": mistakes, "asks": asks,
        # No detector sees his correct uses of this rule, so every use on record is a fix:
        # a % would read 0 for lack of a counter, not for lack of skill. Show it unscored.
        "pct": None if nt or (not u and mistakes) else (round(100 * (uses - mistakes) / uses) if uses else None),
        "status": "NotTaught" if nt else "Unscored" if (not u and mistakes) else status(uses, mistakes),
        "status_label": "Not taught yet" if nt else None,
        "not_taught": nt,
        "not_taught_why": AMAL.NOT_TAUGHT.get(b["id"]),
        "uses_seen": uses_seen,
        # corrections on the page but not in any count (Amal's notes 2026-09-27): not taught yet, or not a mistake
        "not_counted": nc,
        "not_counted_count": len(nc),
        "events": events,
    })

# ---- per-lesson derived series ----
for L in lessons:
    d = L["date"]
    # One tally rule can feed two buckets (R1 -> B2+B3). Count each recorded
    # event once per lesson, keyed by its source rule and timestamp.
    seen, ev, sound = set(), [], []
    for row in rows:
        for e in row["events"]:
            if e["date"] != d:
                continue
            key = (row["tally_rule"], e["kind"], e["t"], e["mmss"])
            if key in seen:
                continue
            seen.add(key)
            # Family F is pronunciation, not grammar (wiki/18 rule M4).
            (sound if row["family"] == "F" else ev).append(e)
    L["slips_counted"] = sum(1 for e in ev if e["kind"] == "slip") + sum(
        1 for row in rows for c in row["candidates"]
        if c["date"] == d)
    L["sound_slips"] = sum(1 for e in sound if e["kind"] == "slip")
    lu = usage.get("lessons", {}).get(d, {})
    # rules Amal has not taught yet (B14, B15) are left out of every total
    nt_uses = sum(v for k, v in (lu.get("by_bucket") or {}).items() if AMAL.not_taught(k))
    nt_rules = sum(1 for k, v in (lu.get("by_bucket") or {}).items() if v and AMAL.not_taught(k))
    L["detected_uses"] = lu.get("uses") - nt_uses if lu.get("uses") is not None else None
    # the same lesson numbers the Lessons page shows (scripts/grammar_math.py)
    _gl = grammar_math.lesson(GT, d)
    L["rule_uses"], L["scored_slips"], L["unscored_slips"], L["grammar_pct"] = _gl["uses"], _gl["scored_mistakes"], _gl["unscored_mistakes"], _gl["pct"]
    L["unique_rules"] = (lu.get("unique_rules") - nt_rules if lu.get("unique_rules") else None) or len(
        {row["id"] for row in rows for e in row["events"] if e["date"] == d})
    L["not_counted"] = sum(1 for row in rows for c in row["not_counted"] if c["date"] == d)
    L["rights"] = sum(1 for e in ev if e["kind"] == "right")
    L["asks_verified"] = sum(1 for e in ev if e["kind"] == "ask")
    # Asks are still found by the audit pass; a lesson it never read has no ask count,
    # so its self-correction rate is unknown, not 0%.
    L["asks_machine"] = (audit_lessons.get(d) or {}).get("asks", 0)
    L["asks"] = L["asks_verified"] + L["asks_machine"]
    L["mistakes_per_sentence"] = (
        round(L["slips_counted"] / L["medi_sentences"], 4) if L["medi_sentences"] else None
    )
    denom = L["slips_counted"] + L["asks"]
    L["self_correction_rate"] = round(100 * L["asks"] / denom) if denom and d in audit_lessons else None

scored = [r for r in rows if r["uses"]]
payload = {
    "updated": "2026-09-29",
    "source": "data/" + SWEEP_NAME + ".json (hand read, rule M1) + transcripts in C:/dev/anees/data/lessons",
    "coverage": {
        "buckets_total": len(rows),
        "buckets_scored": len(scored),
        "lessons_scored": len(lessons),
        "lessons_recorded": len(lesson_dates),
        # eng audit 2026-09-29: the note named the 09-24 sweep (312 fixes) although the counts come from the full audit
        "note": ("Corrections come from the full audit of 2026-09-26: two independent readers per lesson, a third settling "
                 "disagreements, reconciled with the 2026-09-24 hand sweep (a hand check of 20 scored rows found 17 right). "
                 "%d fixes Amal voiced or typed, filed in an approved rule, are counted. Uses are machine-counted: every time "
                 "his Arabic exercises the rule, right or wrong; a fix with no counted use within 2 s counts as a use too, "
                 "so a rule never has more mistakes than uses. Unscored = no counter sees his right uses of the rule, so "
                 "its fixes are listed but no %% is given. Asks: his own questions about a form (rule M1). Untested = he "
                 "never used it in any recorded lesson, or it is a sound (F). Not taught yet = Amal has not taught the rule "
                 "(her notes, 2026-09-27): no score, left out of every total. %d corrections are shown but not counted "
                 "(Amal's notes: not taught yet, or not a mistake - list in data/amal-grammar-notes-2026-09-29.json). "
                 "A score built from a lesson that is not verified yet is marked with ≈ (hover or tap it for why)."
                 % (len(sweep_rows), len(ruled_rows))),
        "not_taught": sorted(AMAL.NOT_TAUGHT),
        "not_counted": len(ruled_rows),
        "not_counted_file": "data/amal-grammar-notes-2026-09-29.json",
    },
    "lessons": lessons,
    "sweep": {
        "file": "data/" + SWEEP_NAME + ".json",
        "counted": len(sweep_rows),
        "buckets_hit": len(cands),
        "lessons": len({r["date"] for r in sweep_rows}),
        "left_out": len(sweep_left_out),
        "clips": sum(1 for v in cands.values() for c in v if c["clip"]),
        "marks": mark_stats,
    },
    # kept for reference only - the machine audit no longer counts anywhere
    "audit": {
        "counted": False,
        "events": sum(1 for e in audit.get("events", []) if e.get("match") != "chat"),
        "lessons": len(audit.get("lessons", [])),
        "method": audit.get("method", ""),
    },
    "rules": rows,
}
json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("wrote", OUT)
print("buckets:", len(rows), "scored:", len(scored))
print("not counted (Amal's notes):", len(ruled_rows))
print("sweep rows counted:", len(sweep_rows), "left out:", len(sweep_left_out),
      "mistakes on page:", sum(r["mistakes"] for r in rows), "clips:", payload["sweep"]["clips"], "marks:", mark_stats)
for L in lessons:
    print(" ", L["date"], "sentences=", L["medi_sentences"], "slips=", L["slips_counted"],
          "asks=", L["asks"], "rights=", L["rights"], "uniq=", L["unique_rules"],
          "m/s=", L["mistakes_per_sentence"], "selfcorr=", L["self_correction_rate"])
from collections import Counter
print(Counter(r["status"] for r in rows))
