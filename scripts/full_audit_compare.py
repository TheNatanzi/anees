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
import argparse, json, os, re, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import self_fix_timing as SFT  # noqa: E402  GR-24
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
    # the third reader also SEES the agreed rows (accuracy audit 2026-09-27 item 3): two readers of the same transcript can
    # share a mistake. It may challenge any of them; a challenged row stays in, flagged for an audio or human check.
    L += ["# Agreed rows (both readers found these) - check them too", "",
          "They are kept unless you challenge one: add {\"id\": \"A3\", \"why\": \"...\"} to `challenges` when the transcript "
          "does not support it (not an error, not Medi, pronunciation only, self-fix, wrong label). A challenge does not drop "
          "the row; it sends it to an audio / human check.", ""]
    for i, a in enumerate(out.get("agreed", []), 1):
        a["id"] = f"A{i}"
        L.append(f"- A{i} t={a.get('t')} t_amal={a.get('t_amal')} kind={a.get('kind')} tier={a.get('tier')} bucket={a.get('bucket')} "
                 f"| Medi: {a.get('medi_said')} | Amal: {a.get('amal_said')} | {a.get('wrong')} -> {a.get('right')}")
    open(os.path.join(WORK, f"{date}{tag}.disputes.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


SF_TOL = 10.0


def hand_self_fix(hand_rows, date, pas, did, row, disputes=()):
    """The hand GR-24 ruling (self-fix-rulings.json) for one dispute. The file keys on a dispute NUMBER (date, pass, D<n>),
    and a re-read renumbers the disputes (2026-10-04 re-hear), so the MOMENT decides. A ruling fits a dispute when the
    dispute row's t / t_amal is within SF_TOL s of the ruling's his_t / her_t.
      - a ruling whose own numbered dispute (same pass) still fits its moment applies to that dispute only (as before);
      - a ruling whose number no longer fits (renumbered, or its pass was retired) applies to the dispute of this pass
        CLOSEST to its moment, unless another ruling of the same moment already sits on its own number;
      - a ruling without times keeps the old number-only behaviour."""
    def dist(x, r):
        ts = [sec(x.get(k)) for k in ("his_t", "her_t") if sec(x.get(k)) is not None]
        rt = [sec((r or {}).get(k)) for k in ("t", "t_amal") if sec((r or {}).get(k)) is not None]
        if not ts:
            return None
        return min((abs(a - b) for a in ts for b in rt), default=1e9)
    drow = {d.get("id"): (d.get("r1") or d.get("r2") or {}) for d in disputes}
    mine = [x for x in hand_rows if x.get("date") == date]

    def anchored(x):
        if x.get("pass") != "p%d" % pas:
            return False
        dx = dist(x, drow.get(x.get("ruling"))) if disputes else dist(x, row if x.get("ruling") == did else None)
        return dx is None or dx <= SF_TOL
    moment = lambda x: (x.get("his_t"), x.get("her_t"))
    for x in mine:
        if anchored(x):
            if x.get("ruling") == did:
                return x
            continue
        if not disputes or any(anchored(y) and moment(y) == moment(x) for y in mine if y is not x):
            continue
        dx = dist(x, row)
        if dx is not None and dx <= SF_TOL and dx <= min(dist(x, r) for r in drow.values()):
            return x
    return None


def settle(date, pas=1):
    tag = "" if pas == 1 else f".p{pas}"
    C = json.load(open(os.path.join(WORK, f"{date}{tag}.compare.json"), encoding="utf-8"))
    R = json.load(open(os.path.join(WORK, f"{date}{tag}.r3.json"), encoding="utf-8"))
    rulings = {x["id"]: x for x in R.get("rulings", [])}
    challenges = {x.get("id"): x.get("why") for x in R.get("challenges", []) if str(x.get("id", "")).startswith("A")}
    rows = []
    HAND_SF = (SFT.J(os.path.join(WORK, "self-fix-rulings.json")) or {}).get("rows", [])
    W = SFT.words(date)
    timing = None
    if W:
        D = SFT.J(os.path.join(SFT.REPO, "docs", "data", "lessons", date + ".json")) or {}
        timing = (D.get("turns") or [], W, SFT.offsets(D.get("turns") or [], W))
    for a in C["agreed"]:
        a = dict(a)
        if a.get("id") in challenges:
            a["r3_challenge"] = challenges[a["id"]] or "challenged by the third reader"
        rows.append(a)
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
            # GR-24 (Medi 2026-10-02, 10-02 07:02 سمعت -> صحيت): a "self-fix" drop stands only when his right word came
            # BEFORE hers by the engine's word times; his line starting first is not enough (scripts/self_fix_timing.py)
            row = d.get("r1") or d.get("r2") or {}
            hand = hand_self_fix(HAND_SF, date, pas, d["id"], row, C["disputes"])
            if SFT.SELF_FIX.search(v.get("why") or "") and (timing is not None or hand):
                res = SFT.check(date, row, *timing) if timing is not None else {"verdict": "unknown"}
                if res["verdict"] == "unknown" and hand and hand.get("verdict") == "her-fix":     # the context read decides
                    res = {"verdict": "her-first", "his_t": SFT.sec(hand["his_t"]), "her_t": SFT.sec(hand["her_t"]), "by": "context read: " + hand["why"]}
                if res["verdict"] == "her-first":
                    row = {k: val for k, val in row.items() if not k.startswith("_")}
                    row.update(ids=[x["id"] for x in (d.get("r1"), d.get("r2")) if x], agreed_by="GR-24", rule="GR-24",
                               r3_why=v.get("why"), gr24=res,
                               gr24_why="not a self-fix: Amal said %s at %s, he said it after her at %s (word times)"
                                        % (row.get("right"), SFT.mmss(res["her_t"]), SFT.mmss(res["his_t"])))
                    row.setdefault("id", d["id"])
                    rows.append(row)
                    kept += 1
                    continue
            dropped += 1
    for x in R.get("added", []):
        x = dict(x)
        x["agreed_by"] = "r3-added"
        if any(same_moment(x, r) and (same_piece(x.get("wrong"), r.get("wrong")) or same_piece(x.get("right"), r.get("right"))) for r in rows):
            continue                                # the third reader re-found an agreed row: not a second row
        rows.append(x)
    rows.sort(key=lambda r: (sec(r.get("t")) if sec(r.get("t")) is not None else 1e9))
    for i, r in enumerate(rows, 1):
        r["fid"] = f"{date[5:7]}{date[8:10]}-{i:03d}"
    out = {"date": date, "pass": pas,
           "counts": {**C["counts"], "r3_kept": kept, "r3_dropped": dropped, "r3_unruled": missing,
                      "r3_added": len(R.get("added", [])), "r3_challenged": len(challenges), "final": len(rows)},
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
    out = {"date": date, "pass1": len(P1), "pass2": len(P2), "both": both, "union": union, "agreement_pct": pct}
    json.dump(out, open(os.path.join(WORK, f"{date}.passes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(date, "pass1", len(P1), "pass2", len(P2), "in both", both, "agreement", pct)
    return out


def union_rows(date):
    """Final rows of a lesson = every settled row of pass 1 plus the pass-2 settled rows pass 1 did not have.
    Each row records which passes found it; a row in one pass only is capped at confidence 'medium'."""
    P1p = os.path.join(WORK, f"{date}.settled.json")
    P2p = os.path.join(WORK, f"{date}.p2.settled.json")
    if not os.path.exists(P1p):
        return None
    P1 = json.load(open(P1p, encoding="utf-8"))
    if not os.path.exists(P2p):
        for r in P1["rows"]:
            r["passes"] = [1]
        return P1
    P2 = json.load(open(P2p, encoding="utf-8"))
    used = set()
    for a in P1["rows"]:
        a["passes"] = [1]
        for j, b in enumerate(P2["rows"]):
            if j in used or not same_moment(a, b):
                continue
            if same_piece(a.get("wrong"), b.get("wrong")) or same_piece(a.get("right"), b.get("right")):
                used.add(j)
                a["passes"] = [1, 2]
                a["p2_fid"] = b.get("fid")
                if RANK.get(b.get("confidence"), 0) > RANK.get(a.get("confidence"), 0):
                    a["confidence"] = b["confidence"]
                break
        if a["passes"] == [1] and a.get("confidence") == "high":
            a["confidence"] = "medium"
    extra, repeats = [], 0
    for j, b in enumerate(P2["rows"]):
        if j in used:
            continue
        # Eng audit 2026-09-29: a pass-2 row that repeats a pass-1 row (same moment, same WRONG piece, same kind,
        # same rule) is that pass-1 slip seen twice by pass 2, not a slip pass 1 missed. It used to come through as an
        # "extra" and the slip was counted twice (09-15 1:02:41 A1 FA-950701c8 + FA-950701c8x).
        if any(same_moment(a, b) and kind_class(a.get("kind")) == kind_class(b.get("kind"))
               and (a.get("bucket") or None) == (b.get("bucket") or None)
               and same_piece(a.get("wrong"), b.get("wrong"))
               for a in P1["rows"]):
            repeats += 1
            continue
        b = dict(b)
        b["passes"] = [2]
        if b.get("confidence") == "high":
            b["confidence"] = "medium"
        extra.append(b)
    rows = P1["rows"] + extra
    rows.sort(key=lambda r: (sec(r.get("t")) if sec(r.get("t")) is not None else 1e9))
    for i, r in enumerate(rows, 1):
        r["fid"] = f"{date[5:7]}{date[8:10]}-{i:03d}"
    return {**P1, "rows": rows, "counts": {**P1["counts"], "pass2_final": P2["counts"].get("final"), "in_both_passes": len(used), "pass2_only": len(extra), "pass2_repeats_dropped": repeats},
            "coverage": {**(P1.get("coverage") or {}), "p2": P2.get("coverage")}, "r3_note": (P1.get("r3_note") or "") + (" | p2: " + P2["r3_note"] if P2.get("r3_note") else "")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compare", "settle", "passes"])
    ap.add_argument("date")
    ap.add_argument("--pass", dest="pas", type=int, default=1)
    a = ap.parse_args()
    {"compare": lambda: compare(a.date, a.pas), "settle": lambda: settle(a.date, a.pas), "passes": lambda: passes(a.date)}[a.cmd]()
