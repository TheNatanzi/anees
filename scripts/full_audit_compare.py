# -*- coding: utf-8 -*-
"""Step 2 of the full audit: compare two independent readers of one lesson, list disputes for the third reader,
merge the third reader's rulings, and score agreement.

    python scripts/full_audit_compare.py compare 2026-09-14 [--pass 1]
        reads  data/lesson-work/full-audit/<date>.r1.json + .r2.json  (pass 2: .p2.r1.json + .p2.r2.json)
        writes <date>.compare.json  (agreed / disputed rows, agreement %)  and  <date>.disputes.md  (for the third reader)
    python scripts/full_audit_compare.py settle 2026-09-14 [--pass 1]
        reads  <date>.compare.json + <date>.r3.json (third reader's rulings)  ->  <date>.settled.json
    python scripts/full_audit_compare.py passes 2026-09-14
        agreement between pass-1 settled and pass-2 settled rows (the loop's exit test, >= 95 %)

Match rule (plan step 2): same moment (t within 5 s, or t_amal within 5 s) AND the same wrong piece
(normalised Arabic / lower-case Latin; one containing the other, or >= half the tokens shared).
Rows that match on the moment but not on the piece, or on the piece but with a different kind, are disputes too.
"""
import argparse, json, os, re, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
TOL = 5.0
ALEF = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"}


def sec(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    p = str(s).strip().split(":")
    try:
        p = [float(x) for x in p]
    except ValueError:
        return None
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def norm(s):
    s = unicodedata.normalize("NFC", str(s or ""))
    s = re.sub(r"[ً-ٰٟـؐ-ؚۖ-ۭ]", "", s)
    s = "".join(ALEF.get(c, c) for c in s)
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def toks(s):
    return set(norm(s).split())


def same_piece(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    ta, tb = toks(a), toks(b)
    return len(ta & tb) >= max(1, min(len(ta), len(tb)) / 2)


def same_moment(a, b):
    for ka in ("t", "t_amal"):
        for kb in ("t", "t_amal"):
            x, y = sec(a.get(ka)), sec(b.get(kb))
            if x is not None and y is not None and abs(x - y) <= TOL:
                return True
    return False


def kind_class(k):
    k = str(k or "")
    return "vocab" if k.startswith("vocab") else ("grammar" if k.startswith("grammar") else k)


def load(date, reader, pas=1):
    p = os.path.join(WORK, f"{date}.{'' if pas == 1 else f'p{pas}.'}{reader}.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    for i, r in enumerate(d.get("rows", [])):
        r.setdefault("id", f"{reader}-{i+1}")
        r["_reader"] = reader
    return d


RANK = {"high": 3, "medium": 2, "low": 1}


def merge(a, b):
    """One row from two agreeing rows: the more confident reader's wording, both ids kept."""
    hi, lo = (a, b) if RANK.get(a.get("confidence"), 0) >= RANK.get(b.get("confidence"), 0) else (b, a)
    m = {k: v for k, v in hi.items() if not k.startswith("_")}
    for k in ("chat", "t_amal", "amal_said", "english", "bucket2"):
        if not m.get(k) and lo.get(k):
            m[k] = lo[k]
    m["ids"] = [a["id"], b["id"]]
    m["agreed_by"] = "r1+r2"
    return m


def compare(date, pas=1):
    A, B = load(date, "r1", pas), load(date, "r2", pas)
    if not A or not B:
        raise SystemExit(f"missing reader file for {date} pass {pas}")
    ra, rb = A["rows"], B["rows"]
    used_b, agreed, disputes = set(), [], []
    for a in ra:
        best = None
        for j, b in enumerate(rb):
            if j in used_b or not same_moment(a, b):
                continue
            if same_piece(a.get("wrong"), b.get("wrong")) or same_piece(a.get("right"), b.get("right")):
                best = j
                break
        if best is None:
            # same moment, same class, pieces differ -> dispute (they saw the same slip, described it differently)
            for j, b in enumerate(rb):
                if j in used_b or not same_moment(a, b) or kind_class(a.get("kind")) != kind_class(b.get("kind")):
                    continue
                used_b.add(j)
                disputes.append({"why": "same moment, different piece", "r1": a, "r2": b})
                break
            else:
                disputes.append({"why": "only r1 found it", "r1": a, "r2": None})
            continue
        used_b.add(best)
        b = rb[best]
        diff = []
        if kind_class(a.get("kind")) != kind_class(b.get("kind")):
            diff.append("kind")
        elif a.get("kind") != b.get("kind"):
            diff.append("A/B")
        if kind_class(a.get("kind")) == "grammar":
            ab, bb = a.get("bucket") or "", b.get("bucket") or ""
            if ab != bb and ab != (b.get("bucket2") or "") and bb != (a.get("bucket2") or ""):
                diff.append("bucket")
        if kind_class(a.get("kind")) == "vocab" and a.get("tier") != b.get("tier"):
            diff.append("tier")
        if a.get("mode", "speaking") != b.get("mode", "speaking"):
            diff.append("mode")
        if diff:
            disputes.append({"why": "matched but differ on " + ", ".join(diff), "r1": a, "r2": b})
        else:
            agreed.append(merge(a, b))
    for j, b in enumerate(rb):
        if j not in used_b:
            disputes.append({"why": "only r2 found it", "r1": None, "r2": b})
    total = len(agreed) + len(disputes)
    out = {"date": date, "pass": pas,
           "counts": {"r1": len(ra), "r2": len(rb), "agreed": len(agreed), "disputed": len(disputes),
                      "agreement_pct": round(100.0 * len(agreed) / total, 1) if total else None},
           "coverage": {"r1": A.get("coverage_note"), "r2": B.get("coverage_note")}, "agreed": agreed, "disputes": disputes}
    tag = "" if pas == 1 else f".p{pas}"
    write_disputes_md(date, out, tag)
    json.dump(out, open(os.path.join(WORK, f"{date}{tag}.compare.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(date, "pass", pas, out["counts"])
    return out


def write_disputes_md(date, out, tag=""):
    L = [f"# Disputes {date} (pass {out['pass']}) - third reader rules with the transcript open", "",
         f"agreed {out['counts']['agreed']} - disputed {out['counts']['disputed']} - agreement {out['counts']['agreement_pct']} %", "",
         "For each D-row answer in the r3 file: {\"id\": \"D1\", \"verdict\": \"keep|drop\", \"row\": {...final row...}, \"why\": \"...\"}.",
         "keep = it IS an error (write the final row: kind, tier/bucket, wrong, right, t, t_amal, medi_said, amal_said, signal, confidence, why).",
         "drop = not an error / pronunciation (S4) / pause (S5) / self-fix / not Medi / duplicate of another row. Say which.", ""]
    for i, d in enumerate(out["disputes"], 1):
        d["id"] = f"D{i}"
        L.append(f"## D{i} - {d['why']}")
        for k in ("r1", "r2"):
            r = d.get(k)
            if not r:
                L.append(f"- {k}: (nothing)")
                continue
            L.append(f"- {k} [{r.get('id')}] t={r.get('t')} t_amal={r.get('t_amal')} kind={r.get('kind')} tier={r.get('tier')} "
                     f"bucket={r.get('bucket')} mode={r.get('mode', 'speaking')} conf={r.get('confidence')} signal={r.get('signal')}")
            L.append(f"  - Medi: {r.get('medi_said')}")
            L.append(f"  - Amal: {r.get('amal_said')}" + (f"  | chat: {r.get('chat')}" if r.get("chat") else ""))
            L.append(f"  - wrong -> right: {r.get('wrong')} -> {r.get('right')}")
            L.append(f"  - why: {r.get('why')}")
        L.append("")
    open(os.path.join(WORK, f"{date}{tag}.disputes.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def settle(date, pas=1):
    tag = "" if pas == 1 else f".p{pas}"
    C = json.load(open(os.path.join(WORK, f"{date}{tag}.compare.json"), encoding="utf-8"))
    R = json.load(open(os.path.join(WORK, f"{date}{tag}.r3.json"), encoding="utf-8"))
    rulings = {x["id"]: x for x in R.get("rulings", [])}
    rows = list(C["agreed"])
    kept = dropped = missing = 0
    for d in C["disputes"]:
        v = rulings.get(d["id"])
        if not v:
            missing += 1
            if d.get("r1") and d.get("r2"):        # both saw it, r3 silent: keep the merged row, flagged
                m = merge(d["r1"], d["r2"])
                m["agreed_by"] = "r1+r2 (r3 silent)"
                rows.append(m)
            continue
        if v.get("verdict") == "keep":
            row = dict(v.get("row") or (d.get("r1") or d.get("r2")))
            row = {k: val for k, val in row.items() if not k.startswith("_")}
            row["ids"] = [x["id"] for x in (d.get("r1"), d.get("r2")) if x]
            row["agreed_by"] = "r3"
            row["r3_why"] = v.get("why")
            row.setdefault("id", d["id"])
            rows.append(row)
            kept += 1
        else:
            dropped += 1
    for x in R.get("added", []):
        x = dict(x)
        x["agreed_by"] = "r3-added"
        rows.append(x)
    rows.sort(key=lambda r: (sec(r.get("t")) if sec(r.get("t")) is not None else 1e9))
    for i, r in enumerate(rows, 1):
        r["fid"] = f"{date[5:7]}{date[8:10]}-{i:03d}"
    out = {"date": date, "pass": pas,
           "counts": {**C["counts"], "r3_kept": kept, "r3_dropped": dropped, "r3_unruled": missing,
                      "r3_added": len(R.get("added", [])), "final": len(rows)},
           "coverage": C["coverage"], "r3_note": R.get("note"), "rows": rows}
    json.dump(out, open(os.path.join(WORK, f"{date}{tag}.settled.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(date, "pass", pas, "settled", out["counts"])
    return out


def passes(date):
    P1 = json.load(open(os.path.join(WORK, f"{date}.settled.json"), encoding="utf-8"))["rows"]
    P2 = json.load(open(os.path.join(WORK, f"{date}.p2.settled.json"), encoding="utf-8"))["rows"]
    used, both = set(), 0
    for a in P1:
        for j, b in enumerate(P2):
            if j in used or not same_moment(a, b):
                continue
            if same_piece(a.get("wrong"), b.get("wrong")) or same_piece(a.get("right"), b.get("right")):
                used.add(j)
                both += 1
                break
    union = len(P1) + len(P2) - both
    pct = round(100.0 * both / union, 1) if union else None
    print(date, "pass1", len(P1), "pass2", len(P2), "in both", both, "agreement", pct)
    return {"date": date, "pass1": len(P1), "pass2": len(P2), "both": both, "agreement_pct": pct}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compare", "settle", "passes"])
    ap.add_argument("date")
    ap.add_argument("--pass", dest="pas", type=int, default=1)
    a = ap.parse_args()
    {"compare": lambda: compare(a.date, a.pas), "settle": lambda: settle(a.date, a.pas), "passes": lambda: passes(a.date)}[a.cmd]()
