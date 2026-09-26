# -*- coding: utf-8 -*-
"""Step 5 of the full audit: Amal's review page data (docs/data/amal-review.json).

Every B row (vocab-B / grammar-B = the app thinks Medi slipped and Amal let it pass) is grouped into a PATTERN
(decision C, Medi 2026-09-25: one row per pattern, her ruling once, all examples folded under it). The grouping is
read from data/lesson-work/full-audit/patterns.json (written by the pattern reader; see PATTERN-BRIEF.md) and joined
to the rows of data/full-audit-2026-09-26.json. Rows no pattern claims become one-row patterns so nothing is lost.
Clips are cut from the lesson audio (his line -> her next line, same cutter as the grammar console).

    python scripts/build_amal_review.py [--no-clips]
"""
import hashlib, json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE); DOCS = os.path.join(REPO, "docs")
sys.path.insert(0, HERE)
from full_audit_compare import sec  # noqa: E402
AUDIT = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
PATTERNS = os.path.join(REPO, "data", "lesson-work", "full-audit", "patterns.json")
OUT = os.path.join(DOCS, "data", "amal-review.json")
PRE, POST, GAP = 1.0, 4.0, 20.0


def cut_clip(date, t, t2=None, post=None):
    """His line plus her fix (same shape as build_grammar_console.cut_clip); None when audio or ffmpeg is missing."""
    adir = os.path.join(DOCS, "lessons", date, "audio")
    srcs = [os.path.join(adir, "lesson.mp3")]
    if not os.path.exists(srcs[0]):
        srcs = [os.path.join(adir, f) for f in ("Amal.mp3", "Medi.mp3")]
    if t is None or not all(map(os.path.exists, srcs)) or not shutil.which("ffmpeg"):
        return None
    ts = sorted([t] + ([t2] if isinstance(t2, (int, float)) else []))
    parts = [(max(0.0, ts[0] - PRE), ts[-1] + (POST if post is None else post))] if ts[-1] - ts[0] <= GAP else [(max(0.0, x - PRE), x + 8.0) for x in ts]
    key = "|".join(f"{a:.1f}-{b:.1f}" for a, b in parts)
    name = "gc-" + hashlib.sha1(f"{date}|{key}".encode()).hexdigest()[:16] + ".mp3"
    out = os.path.join(DOCS, "lessons", date, "clips", name)
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
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", chain, "-map", "[o]", "-ac", "1", "-b:a", "48k", tmp], check=True)
            os.replace(tmp, out)
        except Exception:
            return None
    return f"{date}/clips/{name}"


def mmss(t):
    if t is None:
        return ""
    t = int(round(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def main(clips=True):
    A = json.load(open(AUDIT, encoding="utf-8"))
    B = {r["uid"]: r for r in A["rows"] if r.get("kind") in ("vocab-B", "grammar-B")}
    P = json.load(open(PATTERNS, encoding="utf-8")).get("patterns", []) if os.path.exists(PATTERNS) else []
    buckets = {b["id"]: b for b in json.load(open(os.path.join(DOCS, "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]}
    claimed, patterns = set(), []

    def example(r):
        t, t2 = sec(r.get("t")), sec(r.get("t_amal"))
        return {"uid": r["uid"], "date": r["date"], "mmss": r.get("t") or mmss(t), "medi_said": r.get("medi_said"), "amal_said": r.get("amal_said"),
                "chat": r.get("chat"), "english": r.get("english"), "wrong": r.get("wrong"), "right": r.get("right"),
                "confidence": r.get("confidence"), "clip": cut_clip(r["date"], t, t2) if clips else None}

    for p in P:
        rows = [B[u] for u in p.get("rows", []) if u in B and u not in claimed]
        if not rows:
            continue
        claimed.update(r["uid"] for r in rows)
        kind = "vocab" if str(p.get("kind", rows[0]["kind"])).startswith("vocab") else "grammar"
        bucket = p.get("bucket") or (rows[0].get("bucket") if kind == "grammar" else None)
        dates = sorted({r["date"] for r in rows})
        patterns.append({"id": p["id"], "kind": kind, "kind_label": "Word" if kind == "vocab" else "Grammar",
                         "title": p.get("title"), "wrong": p.get("wrong") or rows[0].get("wrong"), "right": p.get("right") or rows[0].get("right"),
                         "wrong_arabic": p.get("wrong_arabic"), "right_arabic": p.get("right_arabic"),
                         "wrong_arabizi": p.get("wrong_arabizi"), "right_arabizi": p.get("right_arabizi"),
                         "why": p.get("why"), "english": p.get("english") or rows[0].get("english"), "bucket": bucket,
                         "bucket_name": buckets.get(bucket, {}).get("name") if bucket else None, "tier": p.get("tier", rows[0].get("tier")),
                         "count": len(rows), "lessons": dates, "lessons_label": (f"{len(dates)} lessons" if len(dates) > 1 else dates[0]),
                         "examples": [example(r) for r in sorted(rows, key=lambda r: (r["date"], sec(r.get("t")) or 0))]})
    for u, r in B.items():                      # anything the pattern reader did not claim: its own pattern
        if u in claimed:
            continue
        kind = "vocab" if r["kind"].startswith("vocab") else "grammar"
        patterns.append({"id": "single-" + u, "kind": kind, "kind_label": "Word" if kind == "vocab" else "Grammar",
                         "title": f"{r.get('wrong')} -> {r.get('right')}", "wrong": r.get("wrong"), "right": r.get("right"),
                         "wrong_arabic": None, "right_arabic": None, "wrong_arabizi": None, "right_arabizi": None,
                         "why": r.get("why"), "english": r.get("english"), "bucket": r.get("bucket") if kind == "grammar" else None,
                         "bucket_name": buckets.get(r.get("bucket"), {}).get("name") if r.get("bucket") else None, "tier": r.get("tier"),
                         "count": 1, "lessons": [r["date"]], "lessons_label": r["date"], "examples": [example(r)]})
    patterns.sort(key=lambda p: (-p["count"], p["kind"], p["id"]))
    out = {"built": A["built"], "lessons": len({r["date"] for r in A["rows"]}), "patterns": patterns,
           "note": "Slips the app thinks Amal let pass (B rows of the 2026-09-26 audit). Nothing is scored until she taps.",
           "counts": {"patterns": len(patterns), "rows": len(B), "vocab": sum(1 for p in patterns if p["kind"] == "vocab"), "grammar": sum(1 for p in patterns if p["kind"] == "grammar")}}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("patterns", out["counts"], "clips", sum(1 for p in patterns for e in p["examples"] if e.get("clip")))


if __name__ == "__main__":
    main(clips="--no-clips" not in sys.argv)
