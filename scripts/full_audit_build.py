# -*- coding: utf-8 -*-
"""Step 3 of the full audit: reconcile the settled reader rows of all 13 lessons with what already exists
(data/grammar-sweep-2026-09-24.json: 302 grammar rows + 31 unfiled + 147 vocab fixes) and write

    data/full-audit-2026-09-26.json     rows (every error, one source of truth), per-pass counts, per-lesson agreement,
                                        machine-caught / missed, sweep reconciliation
    plan/FULL-AUDIT-2026-09-26.md       per-lesson tables + totals (Medi's reading copy)

Rules: nothing the sweep verified is dropped without a stated reason (a sweep row the readers did not find is KEPT,
tagged source "sweep-2026-09-24", and listed under "sweep rows the readers missed"); everything new is added.
Vocab-B and grammar-B rows are never scored here: they go to Amal's review page (step 5).

    python scripts/full_audit_build.py
"""
import collections, datetime as dt, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from full_audit_compare import sec, same_moment, same_piece, kind_class, norm  # noqa: E402
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
OUT_JSON = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
OUT_MD = os.path.join(REPO, "plan", "FULL-AUDIT-2026-09-26.md")
DATES = sorted(f[:-5] for f in os.listdir(os.path.join(REPO, "docs", "lessons")) if re.fullmatch(r"20\d\d-\d\d-\d\d\.html", f))  # every published lesson page, so a new lesson flows by itself
NOT_COUNTED = ("rejected_on_hand_check", "pron_from_sweep")


def load_settled(date):
    """The lesson's final rows: pass-1 settled rows plus what pass 2 settled and pass 1 did not have (full_audit_compare.union_rows)."""
    from full_audit_compare import union_rows
    return union_rows(date)


def pass_log(date):
    log = []
    for pas, tag in ((1, ""), (2, ".p2")):
        c = os.path.join(WORK, f"{date}{tag}.compare.json")
        s = os.path.join(WORK, f"{date}{tag}.settled.json")
        if os.path.exists(c):
            C = json.load(open(c, encoding="utf-8"))["counts"]
            S = json.load(open(s, encoding="utf-8"))["counts"] if os.path.exists(s) else {}
            log.append({"pass": pas, **C, "r3_kept": S.get("r3_kept"), "r3_dropped": S.get("r3_dropped"), "final": S.get("final")})
    p = os.path.join(WORK, f"{date}.passes.json")
    if os.path.exists(p):
        log.append({"pass": "1 vs 2", **json.load(open(p, encoding="utf-8"))})
    return log


def sweep_rows(sweep):
    """Every sweep row as an audit-shaped row (grammar rows + unfiled + vocab), with what the sweep already knew."""
    dropped = {x["id"] for k in NOT_COUNTED for x in sweep.get(k, [])}
    out = []
    for r in sweep["rows"] + sweep.get("unfiled", []):
        if r["id"] in dropped:
            continue
        b = r.get("bucket") or {"NEW-B18": "B18"}.get(r.get("new_bucket_group") or "")
        out.append({"sweep_id": r["id"], "date": r["date"], "t": r.get("t"), "t_amal": r.get("t_amal"), "medi_said": r.get("medi_said"),
                    "amal_said": r.get("amal_said"), "chat": r.get("chat"), "wrong": r.get("wrong"), "right": r.get("right"),
                    "kind": "grammar", "tier": None, "bucket": b, "bucket2": r.get("bucket2"), "mode": r.get("mode", "speaking"),
                    "signal": r.get("signal"), "confidence": r.get("confidence"), "why": r.get("mistake"),
                    "machine_had": bool(r.get("machine_audit")), "new_bucket_group": r.get("new_bucket_group")})
    for i, v in enumerate(sweep.get("vocab", [])):
        out.append({"sweep_id": f"V{v['date'][5:7]}{v['date'][8:10]}-{i:03d}", "date": v["date"], "t": v.get("t"), "t_amal": None,
                    "medi_said": v.get("medi_said"), "amal_said": v.get("amal_gave"), "chat": None,
                    "wrong": None if v.get("kind") == "didn't-know" else v.get("medi_said"), "right": v.get("amal_gave"),
                    "kind": "vocab-A", "tier": 0 if v.get("kind") == "didn't-know" else 1, "bucket": None, "bucket2": None,
                    "mode": "speaking", "signal": "asked" if v.get("kind") == "didn't-know" else "recast", "confidence": "medium",
                    "why": v.get("english"), "english": v.get("english"), "machine_had": False})
    return out


def match_sweep(row, cands, used):
    for i, s in enumerate(cands):
        if i in used or not same_moment(row, s):
            continue
        if kind_class(row.get("kind")) != kind_class(s.get("kind")):
            continue
        if same_piece(row.get("wrong"), s.get("wrong")) or same_piece(row.get("right"), s.get("right")) \
                or (s.get("kind") == "vocab-A" and same_piece(row.get("right"), s.get("amal_said"))):
            used.add(i)
            return s
    return None


def uid_base(r):
    """What makes a slip one slip: lesson, second of his line, the wrong piece, vocab vs grammar."""
    return f"{r['date']}|{int(sec(r.get('t')) or 0)}|{norm(r.get('wrong'))}|{kind_class(r.get('kind'))}"


def assign_uids(rows):
    """uid is STABLE across rebuilds (patterns.json and Amal's rulings key on it): a hash of date + moment + wrong piece,
    not a position. `n` is the display order. A second row with the same base keeps a suffixed uid (so an old link to it
    still resolves) but is marked a duplicate by mark_duplicates()."""
    import hashlib
    seen_uid = set()
    for i, r in enumerate(rows, 1):
        uid = "FA-" + hashlib.sha1(uid_base(r).encode("utf-8")).hexdigest()[:8]
        while uid in seen_uid:
            uid += "x"
        seen_uid.add(uid)
        r["uid"] = uid
        r["n"] = i
    return rows


def _drop_as_duplicate(r, keep, why):
    if r["kind"] == "rejected":
        return
    r["kind_before_rejection"] = r["kind"]
    r["kind"] = "rejected"
    r["duplicate_of"] = keep["uid"]
    r["rejected_why"] = why
    keep["passes"] = sorted(set(keep.get("passes") or []) | set(r.get("passes") or [])) or keep.get("passes")
    keep.setdefault("duplicates_merged", []).append(r["uid"])


REPEAT_S = 30


def mark_duplicates(rows, hand=()):
    """Same uid base twice -> the later row is the same slip (kind 'rejected', duplicate_of the kept uid, why).
    `hand` = [{"date", "keep", "drop", "why"}] pairs a context read judged to be one slip; keep/drop are uids."""
    first = {}
    for r in rows:
        if r["kind"] == "rejected":
            continue
        b = uid_base(r)
        if b in first:
            _drop_as_duplicate(r, first[b], f"duplicate of {first[b]['uid']}: same lesson, second, wrong piece and kind (eng audit 2026-09-29)")
        else:
            first[b] = r
    # He repeats the same wrong phrase and Amal fixes it once (Medi 2026-10-01: عشرين سجاد at 09-30 09:49 and 10:05 is one
    # slip): same lesson, rule, kind and wrong piece within REPEAT_S seconds -> the later row is the same slip.
    last = {}
    for r in sorted(rows, key=lambda x: (x["date"], sec(x.get("t")) if sec(x.get("t")) is not None else 1e9)):
        if r["kind"] == "rejected" or sec(r.get("t")) is None or not norm(r.get("wrong")):
            continue
        k = (r["date"], r.get("bucket"), r["kind"], norm(r.get("wrong")))
        if k in last and sec(r["t"]) - sec(last[k]["t"]) <= REPEAT_S:
            _drop_as_duplicate(r, last[k], f"duplicate of {last[k]['uid']}: he repeated the same wrong phrase within {REPEAT_S} s, one slip (Medi 2026-10-01)")
        else:
            last[k] = r
    by_uid = {r["uid"]: r for r in rows}
    for h in hand:
        keep, drop = by_uid.get(h["keep"]), by_uid.get(h["drop"])
        if keep is None and drop is None:
            # both rows left with a re-read (2026-10-02: 09-30 re-read when its chat was merged now has ONE row for
            # 'عشرين سجاد', new uid): nothing left to count twice. Only a pair with its repeat still present must resolve.
            continue
        if keep is None:
            raise SystemExit(f"duplicates.json: kept row {h['keep']} is not in the audit rows (uids changed?) - fix the file")
        if drop is None:          # the repeat is already gone (e.g. union_rows no longer lets it through)
            continue
        _drop_as_duplicate(drop, keep, f"duplicate of {keep['uid']}: {h['why']}")
    return rows


SIGNAL_P = os.path.join(WORK, "signal-rulings.json")
CHAT_ONLY_WHY = ("GR-19 (Medi 2026-10-02): typed in the Meet chat only, never voiced - 'if she didnt correct me on voice dont "
                 "factor it as a correction, she might just be cleaning up what I said'")


def apply_chat_rule(rows, signal_rulings=()):
    """GR-19: a fix Amal only TYPED in the chat is not a correction. First the hand re-signals (signal-rulings.json: she
    ALSO voiced the fix, so the row keeps counting with her voiced signal), then every scored row still carrying signal
    'chat-fix' is rejected (kept in the file with the reason, never counted). Returns (resignalled, rejected)."""
    re_n = 0
    for x in signal_rulings:
        for r in rows:
            if r["date"] == x["date"] and same_moment(r, x) and same_piece(r.get("wrong"), x.get("wrong")) and r.get("signal") == "chat-fix"                     and (not x.get("kind") or kind_class(x["kind"]) == kind_class(r["kind"])):
                r["signal_before"] = r["signal"]
                r["signal"] = x["signal"]
                r["signal_why"] = x["why"]
                re_n += 1
                break
    rej = 0
    for r in rows:
        if r.get("signal") == "chat-fix" and r["kind"] in ("grammar", "vocab-A", "grammar-B", "vocab-B"):
            r["kind_before_rejection"] = r["kind"]
            r["kind"] = "rejected"
            r["rejected_why"] = CHAT_ONLY_WHY
            r["rejected_rule"] = "GR-19"
            rej += 1
    return re_n, rej


EL_ONLY = {"ال", "الـ", "ال-", "el", "il", "el-", "il-", "l"}
EL_WHY = ("GR-25 (Medi 2026-10-02 'she corrects me and says el 3ashrah'): her whole reply was 'el' - she prompted the "
          "missing el-, she did not hear a wrong word; the slip is A1 el- (the), voiced")


def apply_el_prompt(rows):
    """GR-25: when Amal's whole voiced reply is 'el' (ال), she prompted the missing el- (A1): the row is re-filed as a
    voiced A1 grammar slip (wrong = his word without el-, right = with it), never a vocab slip. 10-02 07:34: the engine
    wrote على العشاء (dinner) for his على عشرة; readers filed 'dinner for ten' as vocab-B. Returns the re-filed count."""
    n = 0
    for r in rows:
        a = re.sub(r"[.…,،؟?!:;\"“”\s]+", " ", str(r.get("amal_said") or "")).strip().lower()
        if a not in EL_ONLY or r.get("kind") not in ("vocab-A", "vocab-B", "grammar-B"):
            continue
        right = re.sub(r"\s*\([^)]*\)", "", str(r.get("right") or "")).strip()
        if not right.startswith("ال"):
            right = "ال" + right
        r["kind_before_gr25"], r["wrong_before_gr25"], r["right_before_gr25"] = r["kind"], r.get("wrong"), r.get("right")
        r.update(kind="grammar", bucket="A1", signal="prompt-then-fix", wrong=right[2:], right=right, tier=None, rule="GR-25",
                 why=EL_WHY + ". Readers wrote: " + str(r.get("why") or ""))
        n += 1
    return n


DEMONSTR = re.compile(r"^(هاد|هادا|هادي|هاي|هذا|هذه|هدا|هيدا|هيدي|hada|hadi|haada|haadi|hay)$", re.I)
DEM_WHY = ("GR-26 (Medi 2026-10-02 'this should be a grammar error for not using hadi for the morning'): the slip is the "
           "demonstrative (hada / hadi) she took out or changed, so it is grammar A10, not a wrong word")


def apply_demonstrative(rows):
    """GR-26: a vocab row whose wrong phrase starts with a demonstrative (هادا / هادي / هذا ...) that Amal's right form
    drops or changes, with the rest of the phrase kept, is an A10 (hada / hadi) grammar slip. 10-02 08:23 هادي الصباح ->
    الصبح ('We never say هذا الصبح'). Returns the re-filed count."""
    import transcript_marks as TMn
    nz = lambda x: TMn.normalise(re.sub(r"\s*\([^)]*\)", "", str(x or "")))[0].split()
    n = 0
    for r in rows:
        if r.get("kind") not in ("vocab-A", "vocab-B"):
            continue
        w, rt = nz(r.get("wrong")), nz(str(r.get("right") or "").split("/")[0])
        if len(w) < 2 or not DEMONSTR.match(w[0]) or not rt or (rt and DEMONSTR.match(rt[0]) and rt[0] == w[0]):
            continue
        rest = [x for x in rt if not DEMONSTR.match(x)]
        core = lambda x: x.replace("ال", "", 1).replace("ا", "")        # الصبح ~ الصباح (subu7 / sabah): same root
        if not rest or not set(map(core, rest)) & set(map(core, w[1:])):
            continue          # her right form is a different word, not the same phrase without / with another demonstrative
        r["kind_before_gr26"] = r["kind"]
        r.update(kind="grammar" if r["kind"] == "vocab-A" else "grammar-B", bucket="A10", tier=None, rule="GR-26",
                 why=DEM_WHY + ". Readers wrote: " + str(r.get("why") or ""))
        n += 1
    return n


PROPOSE = "PROPOSE"
PROPOSALS_OUT = os.path.join(REPO, "docs", "data", "grammar-proposals.json")


def _counted(r, buckets):
    return (r["kind"] == "grammar" and r.get("bucket") in buckets) or r["kind"] in ("vocab-A", "grammar-B", "vocab-B")


def apply_proposals(rows, hand, buckets):
    """GR-18 (Medi 2026-09-25 "if it doesnt fall into a bucket lets figure out to make one"): a real grammar correction that
    fits no bucket becomes a PROPOSED new bucket for Medi's yes/no - never dropped, never scored until his yes.
      1. hand proposals (data/lesson-work/full-audit/proposed-buckets.json): each row matched by date + moment + wrong
         piece. A matched grammar row with no approved bucket, or a row rejected only because no bucket fits, turns into
         kind 'grammar-propose'; a row already counted under a bucket stays counted (listed as also_counted_as).
      2. every other live grammar / grammar-B row whose bucket is PROPOSE (the readers' brief) or not an approved bucket
         becomes its own proposal (id P-<uid>) with the reader's proposed_rule.
    Returns the proposals for the Grammar Console (docs/data/grammar-proposals.json)."""
    out = []
    taken = set()

    def convert(r, pid, rule):
        r["kind_before_proposal"] = r["kind_before_rejection"] if r["kind"] == "rejected" else r["kind"]
        if r["kind"] == "rejected":
            r["was_rejected_why"] = r.pop("rejected_why", None)
        r["kind"] = "grammar-propose"
        r["bucket_before_proposal"] = r.get("bucket")
        r["bucket"] = PROPOSE
        r["proposal"] = pid
        r["proposed_rule"] = r.get("proposed_rule") or rule
        taken.add(r["uid"])

    def also(r):
        return [{"uid": o["uid"], "kind": o["kind"], "bucket": o.get("bucket")} for o in rows
                if o is not r and o["date"] == r["date"] and _counted(o, buckets) and same_moment(o, r)
                and (same_piece(o.get("wrong"), r.get("wrong")) or sec(o.get("t")) == sec(r.get("t")))]

    def moment(r, extra=None):
        return {"uid": r["uid"], "date": r["date"], "t": r.get("t"), "t_amal": r.get("t_amal"), "medi_said": r.get("medi_said"),
                "amal_said": r.get("amal_said"), "chat": r.get("chat"), "wrong": r.get("wrong"), "right": r.get("right"),
                "kind": r["kind"], "bucket": r.get("bucket"), "confidence": r.get("confidence"), "why": (extra or {}).get("why") or r.get("why"),
                "also_counted_as": also(r)}

    def approve(p, x, cands):
        """Medi said yes (GR-18 -> a real bucket): the moment is scored once, under the new bucket. A grammar twin already
        counted at the moment is refiled to the new bucket and the proposal row becomes its duplicate; otherwise the
        proposal row is scored and a vocab twin counted at the moment becomes its duplicate."""
        new_b = p["bucket"]
        pool = [r for r in rows if r["date"] == x["date"] and same_moment(r, x)]
        live = [r for r in cands if (kind_class(r["kind"]) == "grammar" and r.get("bucket") not in buckets)
                or (r["kind"] == "rejected" and not r.get("duplicate_of") and kind_class(r.get("kind_before_rejection")) == "grammar")]
        ref = live[0] if live else (cands[0] if cands else None)
        if ref is None:
            raise SystemExit(f"proposed-buckets.json {p['id']}: no audit row at {x['date']} {x['t']} {x.get('wrong')} - fix the file")
        near = lambda o: same_piece(o.get("wrong"), ref.get("wrong")) or sec(o.get("t")) == sec(ref.get("t"))
        gtwin = next((o for o in pool if o is not ref and o["kind"] == "grammar" and o.get("bucket") in buckets and near(o)), None)
        if ref["kind"] == "grammar" and ref.get("bucket") in buckets:
            gtwin, ref = ref, None
        if gtwin:
            if gtwin.get("bucket") != new_b:
                gtwin["bucket_before_refile"] = gtwin.get("bucket")
                gtwin["bucket"] = new_b
                gtwin["refiled_by"] = f"{p['id']} approved by Medi (GR-18)"
            if ref is not None:
                _drop_as_duplicate(ref, gtwin, f"same moment as {gtwin['uid']}, filed under {new_b} when Medi approved {p['id']} (GR-18): one slip")
            scored = gtwin
        else:
            r = ref
            if r["kind"] == "rejected":
                r["kind"] = r.pop("kind_before_rejection")
                r["was_rejected_why"] = r.pop("rejected_why", None)
            r["bucket_before_proposal"] = r.get("bucket")
            r["bucket"] = new_b
            r["approved_proposal"] = p["id"]
            for o in pool:
                if o is not r and o["kind"] == "vocab-A" and near(o):
                    _drop_as_duplicate(o, r, f"same moment as {r['uid']}, a grammar slip under {new_b} since Medi approved {p['id']} (GR-18): one slip")
            scored = r
        taken.add(scored["uid"])
        return {**moment(scored, x), "scored_under": new_b}

    for p in hand:
        P = {k: p.get(k) for k in ("id", "name", "proposed_rule", "family", "from", "medi", "bucket")}
        P["moments"] = []
        for x in p.get("rows", []):
            cands = [r for r in rows if r["date"] == x["date"] and same_moment(r, x) and same_piece(r.get("wrong"), x.get("wrong"))]
            if p.get("medi") == "yes" and p.get("bucket") in buckets:
                P["moments"].append(approve(p, x, cands))
                continue
            live = [r for r in cands if (kind_class(r["kind"]) == "grammar" and r.get("bucket") not in buckets)
                    or (r["kind"] == "rejected" and not r.get("duplicate_of") and kind_class(r.get("kind_before_rejection")) == "grammar")]
            if live:
                r = live[0]
                convert(r, p["id"], p["proposed_rule"])
                P["moments"].append(moment(r, x))
            elif cands:                                       # already counted elsewhere: shown, stays counted there
                r = next((c for c in cands if _counted(c, buckets)), cands[0])
                P["moments"].append({**moment(r, x), "already_counted": True})
            else:
                raise SystemExit(f"proposed-buckets.json {p['id']}: no audit row at {x['date']} {x['t']} {x.get('wrong')} - fix the file")
        out.append(P)
    for r in rows:
        if r["uid"] in taken or r["kind"] not in ("grammar", "grammar-B") or r.get("mode", "speaking") != "speaking":
            continue
        if r.get("bucket") == PROPOSE or (r.get("bucket") not in buckets and r.get("new_bucket_group") != "NEW-B18"):
            pid = "P-" + r["uid"]
            convert(r, pid, r.get("why") or "")
            out.append({"id": pid, "name": None, "proposed_rule": r["proposed_rule"], "family": None,
                        "from": f"{r.get('source')} row {r['uid']} (no bucket fits)", "medi": None, "moments": [moment(r)]})
    return out


def compat_entry(r):
    """The sweep-shaped copy of one scored audit row (what build_lessons_page_data / build_grammar_console read), or None."""
    base = {"id": r["uid"], "date": r.get("date"), "t": r.get("t"), "t_amal": r.get("t_amal"), "medi_said": r.get("medi_said"),
            "amal_said": r.get("amal_said"), "chat": r.get("chat"), "wrong": r.get("wrong"), "right": r.get("right"),
            "confidence": r.get("confidence") or "medium", "confidence_why": r.get("r3_why") or r.get("agreed_by"),
            "signal": r.get("signal"), "machine_audit": bool(r.get("machine_had")), "mode": r.get("mode", "speaking"),
            "source": r.get("source"), "uid": r["uid"], "sweep_id": r.get("sweep_id")}
    if r["kind"] == "grammar":
        return {**base, "mistake": r.get("why"), "bucket": r.get("bucket"), "bucket2": r.get("bucket2"), "new_bucket_group": r.get("new_bucket_group")}
    if r["kind"] == "vocab-A":
        return {**base, "amal_gave": r.get("right"), "english": r.get("english") or r.get("why"), "why": r.get("why"),
                "kind": "didn't-know" if r.get("tier") == 0 else "wrong-word", "tier": r.get("tier"),
                "amal_gave_arabizi": r.get("right_arabizi")}
    return None


def sync_compat(A):
    """GR-21 (Medi 2026-10-02 "amals corrections should be counted"): after Amal's rulings flip rows (scripts/
    apply_amal_audit_rulings.py runs AFTER this build), sweep_compat must hold exactly the scored rows: a row she ruled out
    leaves it, a row she CONFIRMED (B -> A) joins it. Before this, a confirm never reached the pages (65 grammar + 12 vocab
    rows on 2026-10-02). A confirmed row at the same lesson second (date + t) as a row already in the copy is the same
    moment, not a second slip: it is marked compat_same_moment_as and left out. Returns (added, removed, same_moment)."""
    sc = A.setdefault("sweep_compat", {})
    kind = {r["uid"]: r["kind"] for r in A["rows"]}
    before = {x.get("uid") or x.get("id") for x in sc.get("rows", []) + sc.get("vocab", [])}
    sc["rows"] = [x for x in sc.get("rows", []) if kind.get(x.get("uid") or x.get("id"), "grammar") == "grammar"]
    sc["vocab"] = [x for x in sc.get("vocab", []) if kind.get(x.get("uid") or x.get("id"), "vocab-A") == "vocab-A"]
    have = {x.get("uid") or x.get("id") for x in sc["rows"] + sc["vocab"]}
    removed = len(before - have)
    added, same = 0, []
    for key, kd in (("rows", "grammar"), ("vocab", "vocab-A")):
        at = {(x.get("date"), x.get("t")): (x.get("uid") or x.get("id")) for x in sc[key] if x.get("t")}
        for r in A["rows"]:
            if r["kind"] != kd or r["uid"] in have:
                continue
            twin = at.get((r.get("date"), r.get("t"))) if r.get("t") else None
            if twin:
                r["compat_same_moment_as"] = twin
                same.append(r["uid"])
                continue
            r.pop("compat_same_moment_as", None)
            sc[key].append(compat_entry(r))
            at.setdefault((r.get("date"), r.get("t")), r["uid"])
            added += 1
        sc[key].sort(key=lambda x: (x.get("date") or "", sec(x.get("t")) if sec(x.get("t")) is not None else 1e9))
    return added, removed, same


def build():
    sweep = json.load(open(os.path.join(REPO, "data", "grammar-sweep-2026-09-24.json"), encoding="utf-8"))
    buckets = {b["id"]: b for b in json.load(open(os.path.join(REPO, "docs", "data", "grammar-buckets.json"), encoding="utf-8"))["buckets"]}
    S = sweep_rows(sweep)
    by_date = collections.defaultdict(list)
    for s in S:
        by_date[s["date"]].append(s)
    rows, per_lesson, missing = [], [], []
    sweep_missed_by_readers = []
    for d in DATES:
        st = load_settled(d)
        if not st:
            missing.append(d)
            continue
        used = set()
        n_new = n_both = 0
        for r in st["rows"]:
            r = dict(r)
            r["date"] = d
            r["source"] = "audit-2026-09-26"
            s = match_sweep(r, by_date[d], used)
            if s:
                r["sweep_id"] = s["sweep_id"]
                r["machine_had"] = s.get("machine_had", False)
                if kind_class(r["kind"]) == "grammar" and not r.get("bucket") and s.get("bucket"):
                    r["bucket"] = s["bucket"]
                n_both += 1
            else:
                r["machine_had"] = False
                n_new += 1
            rows.append(r)
        kept = 0
        for i, s in enumerate(by_date[d]):
            if i in used:
                continue
            # Eng audit 2026-09-29: a sweep row that is the same slip as a reader row already paired with another sweep
            # row (same moment, kind, rule and wrong piece) is not "missed by the readers" - keeping it counted it twice.
            if any(same_moment(r, s) and kind_class(r.get("kind")) == kind_class(s.get("kind"))
                   and (r.get("bucket") or None) == (s.get("bucket") or None)
                   and (same_piece(r.get("wrong"), s.get("wrong")) or same_piece(r.get("right"), s.get("right")))   # match_sweep's own test
                   for r in rows if r["date"] == d and r.get("source") == "audit-2026-09-26"):
                continue
            s = dict(s)
            s["source"] = "sweep-2026-09-24"
            s["agreed_by"] = "sweep (readers did not list it - kept, per the rule that nothing verified is dropped without a reason)"
            s["fid"] = s["sweep_id"]
            rows.append(s)
            sweep_missed_by_readers.append({"date": d, "sweep_id": s["sweep_id"], "kind": s["kind"], "wrong": s.get("wrong"), "right": s.get("right"), "t": s.get("t")})
            kept += 1
        c = st["counts"]
        per_lesson.append({"date": d, "coverage": st.get("coverage"), "r3_note": st.get("r3_note"), "passes": pass_log(d),
                           "agreement_pct": c.get("agreement_pct"), "readers_rows": c.get("final"),
                           "in_sweep_too": n_both, "new_vs_sweep": n_new, "sweep_only_kept": kept})
    # rows a human hand check rejected (data/lesson-work/full-audit/rejected.json): kept in the file, never scored
    rej_p = os.path.join(WORK, "rejected.json")
    if os.path.exists(rej_p):
        for x in json.load(open(rej_p, encoding="utf-8"))["rows"]:
            for r in rows:
                if r["date"] == x["date"] and same_moment(r, x) and same_piece(r.get("wrong"), x.get("wrong")) and r["kind"] != "rejected"                         and (not x.get("kind") or kind_class(x["kind"]) == kind_class(r["kind"])):
                    r["kind_before_rejection"] = r["kind"]
                    r["kind"] = "rejected"
                    r["rejected_why"] = x["why"]
                    if x.get("rule"):
                        r["rejected_rule"] = x["rule"]
                    break
    apply_chat_rule(rows, json.load(open(SIGNAL_P, encoding="utf-8"))["rows"] if os.path.exists(SIGNAL_P) else [])
    apply_el_prompt(rows)
    apply_demonstrative(rows)
    import medi_corrections as MC     # PR-15: Medi's corrections (page table mirror + the ones he gave in chat)
    MC_REPORT = MC.apply_rows(rows)
    # per-row bucket names + a stable order
    for r in rows:
        if r.get("bucket") in buckets:
            r["bucket_name"] = buckets[r["bucket"]]["name"]
    rows.sort(key=lambda r: (r["date"], sec(r.get("t")) if sec(r.get("t")) is not None else 1e9))
    assign_uids(rows)
    # Eng audit 2026-09-29: one slip is one row. Same uid base = same slip (was renamed "<uid>x" and counted twice);
    # plus the hand-read repeats in data/lesson-work/full-audit/duplicates.json. Kept in the file, never counted.
    dup_p = os.path.join(WORK, "duplicates.json")
    mark_duplicates(rows, json.load(open(dup_p, encoding="utf-8"))["pairs"] if os.path.exists(dup_p) else [])
    prop_p = os.path.join(WORK, "proposed-buckets.json")
    proposals = apply_proposals(rows, json.load(open(prop_p, encoding="utf-8"))["proposals"] if os.path.exists(prop_p) else [], buckets)

    def cnt(pred):
        return sum(1 for r in rows if pred(r))
    scored = [r for r in rows if r.get("mode", "speaking") == "speaking" and r.get("kind") in ("grammar", "vocab-A")]
    totals = {
        "rows": len(rows),
        "grammar_A": cnt(lambda r: r["kind"] == "grammar" and r.get("mode", "speaking") == "speaking"),
        "grammar_B": cnt(lambda r: r["kind"] == "grammar-B"),
        "grammar_proposed": cnt(lambda r: r["kind"] == "grammar-propose"),
        "vocab_A": cnt(lambda r: r["kind"] == "vocab-A" and r.get("mode", "speaking") == "speaking"),
        "vocab_A_by_tier": dict(collections.Counter(str(r.get("tier")) for r in rows if r["kind"] == "vocab-A")),
        "vocab_B": cnt(lambda r: r["kind"] == "vocab-B"),
        "vocab_B_by_tier": dict(collections.Counter(str(r.get("tier")) for r in rows if r["kind"] == "vocab-B")),
        "listening": cnt(lambda r: r.get("mode") == "listening"),
        "from_readers": cnt(lambda r: r["source"] == "audit-2026-09-26"),
        "readers_also_in_sweep": cnt(lambda r: r["source"] == "audit-2026-09-26" and r.get("sweep_id")),
        "readers_new": cnt(lambda r: r["source"] == "audit-2026-09-26" and not r.get("sweep_id")),
        "sweep_only_kept": cnt(lambda r: r["source"] == "sweep-2026-09-24"),
        "machine_had": cnt(lambda r: r.get("machine_had")),
        "sweep_before": {"grammar": sweep["totals"].get("speaking_grammar"), "vocab": sweep["totals"].get("vocab")},
        "lesson_pages_before": {"vocab_errors_shown": 23},
    }
    by_bucket = collections.Counter(r.get("bucket") for r in rows if kind_class(r["kind"]) == "grammar" and r.get("mode", "speaking") == "speaking" and r.get("bucket"))
    by_lesson = {}
    for d in DATES:
        L = [r for r in rows if r["date"] == d]
        by_lesson[d] = {"grammar_A": sum(1 for r in L if r["kind"] == "grammar" and r.get("mode", "speaking") == "speaking"),
                        "grammar_B": sum(1 for r in L if r["kind"] == "grammar-B"),
                        "vocab_A": sum(1 for r in L if r["kind"] == "vocab-A" and r.get("mode", "speaking") == "speaking"),
                        "vocab_B": sum(1 for r in L if r["kind"] == "vocab-B"),
                        "listening": sum(1 for r in L if r.get("mode") == "listening"),
                        "sweep_grammar_before": sum(1 for p in sweep["per_lesson"] if p["date"] == d and (p.get("grammar") or 0)) and next(p.get("grammar", 0) + p.get("unfiled", 0) for p in sweep["per_lesson"] if p["date"] == d),
                        "sweep_vocab_before": next((p.get("vocab", 0) for p in sweep["per_lesson"] if p["date"] == d), 0)}
    # sweep-shaped view: scripts/build_lessons_page_data.py and build_grammar_console.py read this instead of the 09-24
    # sweep, so every page shows the audit without changing how the pages are built. Only A rows (Amal's voice / chat)
    # are here; B rows wait for Amal's ruling (scripts/apply_amal_audit_rulings.py flips them).
    compat_rows, compat_vocab = [], []
    for r in rows:
        e = compat_entry(r)
        if e:
            (compat_rows if r["kind"] == "grammar" else compat_vocab).append(e)
    sweep_compat = {"built": "2026-09-26", "method": "full audit 2026-09-26 (two readers + third reader per lesson, reconciled with the 09-24 sweep)",
                    "rows": compat_rows, "unfiled": [], "vocab": compat_vocab,
                    "per_lesson": [{"date": p["date"], "coverage": " / ".join(x for x in [(p.get("coverage") or {}).get("r1"), (p.get("coverage") or {}).get("r2")] if x)} for p in per_lesson],
                    "rejected_on_hand_check": [], "pron_from_sweep": [], "hand_check": {},
                    "totals": {"speaking_grammar": totals["grammar_A"], "vocab": totals["vocab_A"], "machine_caught_speaking": totals["machine_had"]}}
    out = {"built": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "method": __doc__.strip(), "sweep_compat": sweep_compat,
           "decisions": "A counts (every fix Amal voiced; a chat-only fix never counts - GR-19, Medi 2026-10-02); B (she let it pass) is unscored until she rules on Amal's review page; "
                        "tiers 1-3 vocab, tier 0 = she supplied a word he asked for; grammar filed by bucket; listening rows kept apart.",
           "lessons_missing": missing, "totals": totals, "by_bucket": dict(by_bucket.most_common()), "by_lesson": by_lesson,
           "per_lesson": per_lesson, "sweep_rows_readers_missed": sweep_missed_by_readers, "proposals": proposals, "rows": rows}
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # GR-18: the one place Medi sees proposed buckets (Grammar Console); unscored until his yes
    json.dump({"updated": out["built"], "rule": "GR-18",
               "about": "Grammar corrections Amal made that fit no existing rule. Each is a proposed new rule for Medi's yes or no; "
                        "nothing here is scored until he says yes. Built by scripts/full_audit_build.py from the audit rows and "
                        "data/lesson-work/full-audit/proposed-buckets.json.",
               "proposals": proposals}, open(PROPOSALS_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_md(out, buckets)
    print("rows", len(rows), "| grammar A", totals["grammar_A"], "B", totals["grammar_B"], "| vocab A", totals["vocab_A"], "B", totals["vocab_B"],
          "| proposed (GR-18)", totals["grammar_proposed"], "| readers new vs sweep", totals["readers_new"], "| sweep-only kept", totals["sweep_only_kept"], "| missing lessons", missing)
    return out


def az(s):
    return s or ""


def write_md(out, buckets):
    T = out["totals"]
    L = [f"# Full vocab + grammar audit - {out['built'][:10]}", "",
         "Two independent readers per lesson, a third settles disagreements, reconciled with the 2026-09-24 hand sweep. "
         "A = Amal fixed it out loud (scored; a fix she only typed in the chat is not a correction - GR-19). B = she let it pass (unscored until she rules on her review page). "
         "Tier 0 = she supplied a word he asked for. Nothing the sweep verified was dropped.", "",
         "## Totals", "", "| | count |", "|---|---|",
         f"| Grammar fixes Amal voiced (A) | **{T['grammar_A']}** (sweep had {T['sweep_before']['grammar']}) |",
         f"| Grammar she let pass (B, to Amal) | {T['grammar_B']} |",
         f"| Grammar fixes that fit no rule (proposed new rules, unscored until Medi's yes - GR-18) | {T.get('grammar_proposed', 0)} |",
         f"| Vocab fixes Amal voiced (A) | **{T['vocab_A']}** (sweep had {T['sweep_before']['vocab']}; lesson pages showed 23) |",
         f"| - by tier (0 asked / 1 wrong word / 2 wrong form / 3 English-in-Arabic) | {T['vocab_A_by_tier']} |",
         f"| Vocab she let pass (B, to Amal) | **{T['vocab_B']}** by tier {T['vocab_B_by_tier']} |",
         f"| Listening-drill misreads (kept apart) | {T['listening']} |",
         f"| Rows the readers found that the sweep did not have | {T['readers_new']} |",
         f"| Sweep rows the readers did not list (kept) | {T['sweep_only_kept']} |",
         f"| Machine audit already had | {T['machine_had']} |", ""]
    if out["lessons_missing"]:
        L += [f"**Not settled yet:** {', '.join(out['lessons_missing'])}", ""]
    L += ["## Per lesson", "", "| lesson | grammar A | grammar B | vocab A | vocab B | listening | sweep grammar before | sweep vocab before | reader agreement |", "|---|---|---|---|---|---|---|---|---|"]
    pl = {p["date"]: p for p in out["per_lesson"]}
    for d, c in out["by_lesson"].items():
        p = pl.get(d, {})
        L.append(f"| {d} | {c['grammar_A']} | {c['grammar_B']} | {c['vocab_A']} | {c['vocab_B']} | {c['listening']} | {c['sweep_grammar_before']} | {c['sweep_vocab_before']} | {p.get('agreement_pct', '-')} % |")
    L += ["", "## Reader passes (the loop)", ""]
    for p in out["per_lesson"]:
        L.append(f"- **{p['date']}**: " + "; ".join(
            (f"pass {x['pass']}: r1 {x.get('r1')} r2 {x.get('r2')} agreed {x.get('agreed')} disputed {x.get('disputed')} ({x.get('agreement_pct')} %), r3 kept {x.get('r3_kept')} dropped {x.get('r3_dropped')} -> {x.get('final')} rows"
             if x["pass"] in (1, 2) else f"pass 1 vs pass 2: {x.get('agreement_pct')} % of rows in both") for x in p["passes"]))
    L += ["", "## Grammar by bucket (A, speaking)", "", "| bucket | name | fixes |", "|---|---|---|"]
    for b, n in out["by_bucket"].items():
        L.append(f"| {b} | {buckets.get(b, {}).get('name', '?')} | {n} |")
    L += ["", "## Sweep rows the readers did not list (kept, not dropped)", ""]
    for s in out["sweep_rows_readers_missed"][:400]:
        L.append(f"- {s['date']} {s['t']} {s['kind']} {s['sweep_id']}: {az(s.get('wrong'))} -> {az(s.get('right'))}")
    for d in DATES:
        rows = [r for r in out["rows"] if r["date"] == d]
        if not rows:
            continue
        p = pl.get(d, {})
        L += ["", f"### {d}", ""]
        cov = p.get("coverage") or {}
        if cov:
            L.append("_" + (cov.get("r1") or "") + " / " + (cov.get("r2") or "") + "_")
            L.append("")
        L += ["| id | time | kind | tier/bucket | Medi said | Amal said | wrong -> right | why | conf | source |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            tb = r.get("bucket") or (f"tier {r.get('tier')}" if r.get("tier") is not None else "")
            L.append(f"| {r['uid']} | {az(r.get('t'))} | {r['kind']}{' (listening)' if r.get('mode') == 'listening' else ''} | {tb} | {az(r.get('medi_said')).replace('|', '/')} | {az(r.get('amal_said')).replace('|', '/')} | {az(r.get('wrong')).replace('|', '/')} -> {az(r.get('right')).replace('|', '/')} | {az(r.get('why')).replace('|', '/')} | {az(r.get('confidence'))} | {r.get('agreed_by') or r.get('source')} |")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    build()
