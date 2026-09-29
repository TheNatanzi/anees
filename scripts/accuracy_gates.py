# -*- coding: utf-8 -*-
"""Accuracy gates (Medi 2026-09-27, plan/PROMPT-SYSTEMIC-ACCURACY-AUDIT-2026-09-27.md): what makes a score VERIFIED.

A lesson score is only "verified" when all of these hold; otherwise it stays on the page, labelled "not verified" with the
specific reasons, and it is left out of every verified total:

  1 agreement   two consecutive reader passes, each with reader 1 vs reader 2 >= 95 %, and the two passes' settled rows
                >= 95 % alike (docs/data/accuracy-policy.json; lowering the number is a rule change, not a fix)
  2 coverage    both people transcribed for the whole lesson: no stretch where one side has no transcript while the other
                talks, no "[speaking Arabic]" holes, speakers from separate tracks (not guessed by pitch / diarization),
                and the speech recognition reviewed
  3 checks      no scored row that needs an audio or human check (low confidence, one reviewer only, the two passes
                disagree it exists, kept only from the old sweep, disputed transcript) without a recorded check
                (data/accuracy/verifications.json: who checked, how, evidence, verdict - append-only)
  7 grammar     the grammar % additionally needs a valid denominator: every corrected slip must sit where the usage
                counter could have counted it (Arabic-script turn, a bucket the counter detects)

    python scripts/accuracy_gates.py annotate      # adds release / coverage / eligible-excluded-pending to docs/data/lessons.json,
                                                   # writes docs/data/accuracy-release.json + data/accuracy/verification-queue.json
    python scripts/accuracy_gates.py check         # fail-closed validation before anything is published (exit 1 on a problem)
    python scripts/accuracy_gates.py agreement D   # the reader-agreement decision for one lesson

Nothing here edits a transcript (RULES.md S2) or a reader file; it only reads them and writes the release layer.
"""
import argparse, collections, datetime as dt, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
POLICY_P = os.path.join(REPO, "docs", "data", "accuracy-policy.json")
LEDGER_P = os.path.join(REPO, "data", "accuracy", "verifications.json")
RELEASE_P = os.path.join(REPO, "docs", "data", "accuracy-release.json")
QUEUE_P = os.path.join(REPO, "data", "accuracy", "verification-queue.json")
AUDIT_P = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
LESSONS_P = os.path.join(REPO, "docs", "data", "lessons.json")
SCORED_KINDS = ("grammar", "vocab-A")
AR = re.compile(r"[ء-ي]")


def J(p):
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def W(p, obj, indent=1):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def load_policy(path=POLICY_P):
    return J(path)


def sec(s):
    """'mm:ss' / 'h:mm:ss' / number -> seconds; anything else -> None."""
    if s is None or s == "":
        return None
    if isinstance(s, (int, float)):
        return float(s)
    p = str(s).strip().split(":")
    try:
        p = [float(x) for x in p]
    except ValueError:
        return None
    return sum(v * 60 ** i for i, v in enumerate(reversed(p)))


def mmss(t):
    if t is None:
        return "?"
    t = int(round(t))
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


# ====================================================================== 1 reader agreement
def pass_numbers(date, work=WORK):
    """Reader passes that were compared for this lesson: 1 = <date>.compare.json, n = <date>.p<n>.compare.json."""
    out = []
    if os.path.exists(os.path.join(work, f"{date}.compare.json")):
        out.append(1)
    for f in os.listdir(work) if os.path.isdir(work) else []:
        m = re.fullmatch(re.escape(date) + r"\.p(\d+)\.compare\.json", f)
        if m:
            out.append(int(m.group(1)))
    return sorted(set(out))


def _tag(n):
    return "" if n == 1 else f".p{n}"


def within_pass(date, n, work=WORK):
    p = os.path.join(work, f"{date}{_tag(n)}.compare.json")
    if not os.path.exists(p):
        return None
    c = J(p)["counts"]
    return {"pass": n, "r1": c.get("r1"), "r2": c.get("r2"), "agreed": c.get("agreed"), "disputed": c.get("disputed"),
            "agreement_pct": c.get("agreement_pct")}


def between_passes(date, a, b, work=WORK):
    """Settled rows of pass a vs pass b: rows in both / union (the same matching as full_audit_compare.passes)."""
    sys.path.insert(0, HERE)
    from full_audit_compare import same_moment, same_piece
    pa, pb = (os.path.join(work, f"{date}{_tag(n)}.settled.json") for n in (a, b))
    if not (os.path.exists(pa) and os.path.exists(pb)):
        return None
    A, B = J(pa)["rows"], J(pb)["rows"]
    used, both = set(), 0
    for x in A:
        for j, y in enumerate(B):
            if j in used or not same_moment(x, y):
                continue
            if same_piece(x.get("wrong"), y.get("wrong")) or same_piece(x.get("right"), y.get("right")):
                used.add(j)
                both += 1
                break
    union = len(A) + len(B) - both
    return {"passes": [a, b], "both": both, "union": union, "agreement_pct": round(100.0 * both / union, 1) if union else None}


def release_decision(within, between, policy):
    """within = {pass_n: pct}, between = {(a, b): pct}. Released only when the two LATEST consecutive passes each reach the
    threshold between reader 1 and reader 2 AND agree with each other at the threshold (both readings of the rule)."""
    T = float(policy["release_threshold_pct"])
    need = int(policy.get("consecutive_passes_required", 2))
    ns = sorted(within)
    reasons = []
    if len(ns) < need:
        got = ", ".join(f"pass {n} {within[n]} %" for n in ns) or "no reader pass"
        reasons.append(f"reader agreement: {got}; {need} consecutive passes at >= {T:g} % are needed")
        return {"status": "withheld", "reasons": reasons, "threshold_pct": T}
    last = ns[-need:]
    if last != list(range(last[0], last[0] + need)):
        reasons.append(f"reader agreement: passes {last} are not consecutive")
    for n in last:
        v = within[n]
        if v is None or v < T:
            reasons.append(f"reader agreement: pass {n} readers agree on {v} % of rows (>= {T:g} % needed)")
    applied = (policy.get("agreement_readings") or {}).get("applied", "both")
    if applied in ("both", "between_passes"):
        for a, b in zip(last, last[1:]):
            v = between.get((a, b))
            if v is None or v < T:
                reasons.append(f"reader agreement: pass {a} vs pass {b} settled rows agree on {v} % (>= {T:g} % needed)")
    return {"status": "withheld" if reasons else "released", "reasons": reasons, "threshold_pct": T, "basis": last}


def agreement(date, policy, work=WORK):
    ns = pass_numbers(date, work)
    within = {n: (within_pass(date, n, work) or {}).get("agreement_pct") for n in ns}
    between = {}
    for a, b in zip(ns, ns[1:]):
        x = between_passes(date, a, b, work)
        between[(a, b)] = x["agreement_pct"] if x else None
    d = release_decision(within, between, policy)
    d["passes"] = [within_pass(date, n, work) for n in ns]
    d["between"] = [{"passes": [a, b], "agreement_pct": v} for (a, b), v in between.items()]
    return d


def next_reader_action(decision, n_passes, policy):
    """What review_lesson.py does next: 'released', 'run pass <n>' or 'withheld' (the pass budget is spent)."""
    if decision["status"] == "released":
        return "released"
    if n_passes < int(policy.get("max_reader_passes", 2)):
        return f"run pass {n_passes + 1}"
    return "withheld"


# ====================================================================== 2 source coverage
def hole_re(policy):
    return re.compile(policy.get("hole_markers") or r"\[[^\]]*speaking[^\]]*\]", re.I)


def participant_coverage(turns, duration, policy, people=("Medi", "Amal")):
    """Per person: stretches with NO transcript while the other person talks (missing), and turns the engine heard but wrote
    as a marker such as '[speaking Arabic]' (holes). turns = docs/data/lessons/<date>.json turns (who, t, end, text)."""
    H = hole_re(policy)
    gap = float(policy.get("missing_interval_min_s", 120))
    spoken = [t for t in turns if t.get("who") in people]
    end_all = max([duration or 0] + [(t.get("end") or t["t"]) for t in spoken]) if spoken else (duration or 0)
    out = {}
    for p in people:
        mine = sorted(t["t"] for t in spoken if t["who"] == p)
        other = sorted(t["t"] for t in spoken if t["who"] != p)
        missing = []
        bounds = [0.0] + mine + [end_all]
        for a, b in zip(bounds, bounds[1:]):
            if b - a < gap:
                continue
            talk = [x for x in other if a < x < b]
            if len(talk) >= 5:                          # the other person kept talking: this side is not in the transcript
                lo = a if a == 0.0 else a + 1
                missing.append([round(lo, 2), round(b, 2), f"no transcript for {p} while the other person talks"])
        holes = []
        for t in spoken:
            if t["who"] == p and H.search(t.get("text") or ""):
                holes.append([round(t["t"], 2), round(max(t.get("end") or t["t"], t["t"] + 1.0), 2),
                              "engine heard speech but wrote a marker, not words"])
        miss_s = sum(b - a for a, b, _ in missing)
        hole_s = sum(b - a for a, b, _ in holes)
        out[p] = {"first_t": mine[0] if mine else None, "last_t": mine[-1] if mine else None, "missing": missing, "holes": holes,
                  "missing_s": round(miss_s, 1), "hole_s": round(hole_s, 1),
                  "covered_pct": round(100 * (1 - miss_s / end_all), 1) if end_all else None}
    return out


def source_quality(lesson):
    """How the speakers and the timings were obtained (build_lessons_page_data.py writes `source`; older files: its notes)."""
    s = lesson.get("source") or {}
    if s.get("attribution") and s.get("timing"):
        return s
    notes = " ".join(lesson.get("notes") or [])
    if "voice pitch" in notes:
        attribution = "pitch-guess"
    elif "diarization" in notes:
        attribution = "diarized-mixed"
    else:
        attribution = "per-speaker-tracks"
    if "silence detection" in notes:
        timing = "estimated"
    elif "no word-level timings" in notes:
        timing = "none"
    else:
        timing = "engine"
    return {"attribution": attribution, "timing": timing}


ATTRIBUTION_TEXT = {"pitch-guess": "speakers guessed by voice pitch on one mixed recording",
                    "diarized-mixed": "speakers split by the engine's diarization of one mixed recording (labels can swap)"}


def in_iv(t, ivs):
    return t is not None and any(a <= t <= b for a, b, *_ in ivs)


# ====================================================================== 3 row checks + the verification ledger
def row_times(row):
    return sec(row.get("t")), sec(row.get("t_amal"))


def row_scoreability(row, cov, policy):
    """('scoreable', None) or ('unscoreable', reason) for one audit row, from the lesson's source coverage."""
    H = hole_re(policy)
    t, ta = row_times(row)
    t = t if t is not None else ta
    medi, amal = cov.get("Medi", {}), cov.get("Amal", {})
    if H.search(row.get("medi_said") or ""):
        return "unscoreable", f"his line at {mmss(t)} is not in the transcript ({(row.get('medi_said') or '')[:40]}); evidence rests on Amal's side only"
    if in_iv(t, medi.get("missing", [])):
        return "unscoreable", f"Medi not transcribed at {mmss(t)}"
    if in_iv(t, medi.get("holes", [])) and not AR.search(re.sub(H, "", row.get("medi_said") or "")):
        return "unscoreable", f"Medi's speech at {mmss(t)} is an untranscribed stretch"
    fix_t = ta if ta is not None else t
    if in_iv(fix_t, amal.get("missing", [])) and not row.get("chat"):
        return "unscoreable", f"Amal not transcribed at {mmss(fix_t)}: her correction or reaction cannot be read"
    return "scoreable", None


def check_reasons(row, n_passes):
    """Why a scored row needs an independent audio or human check (empty list = it does not)."""
    out = []
    if row.get("kind") not in SCORED_KINDS or row.get("mode", "speaking") != "speaking":
        return out
    if row.get("confidence") == "low":
        out.append("reader confidence low")
    ab = row.get("agreed_by") or ""
    passes = row.get("passes") or []
    if ab == "r3-added":
        out.append("added by the third reader alone")
    elif ab.startswith("r3") and len(passes) <= 1:
        out.append("decided by the third reader alone, in one pass only")
    if n_passes >= 2 and len(passes) == 1:
        out.append(f"found in pass {passes[0]} only (the other pass did not list it)")
    if row.get("r3_challenge"):
        out.append("both readers found it but the third reader challenged it")
    if row.get("source") == "sweep-2026-09-24":
        out.append("kept from the 09-24 sweep; neither reader pass listed it")
    if row.get("transcript_note") or "engine wrote" in (row.get("why") or ""):
        out.append("the transcript under it is disputed (engine wrote something else)")
    return out


def load_ledger(path=LEDGER_P):
    if not os.path.exists(path):
        return {"records": []}
    return J(path)


LEDGER_FIELDS = ("uid", "method", "reviewer", "verdict", "evidence", "confidence", "at")
LEDGER_VERDICTS = ("confirmed", "rejected", "changed", "unsure")
ROLES = ("second-judge", "human")


def record_role(r):
    """'human' (Amal / Medi listened) or 'second-judge' (a different AI re-judged against the audio). Old records without a
    role: method human = human, anything else = second-judge."""
    return r.get("role") or ("human" if r.get("method") == "human" else "second-judge")


def ledger_problems(ledger):
    """Every record must say who checked, how, on what evidence, with what confidence, and when (item 6). The second judge
    must not be a Claude model (Medi 2026-09-29: the readers are Claude; the check has to come from a different AI)."""
    probs = []
    seen = set()
    for i, r in enumerate(ledger.get("records", [])):
        miss = [k for k in LEDGER_FIELDS if not r.get(k)]
        if miss:
            probs.append(f"verification record {i} missing {miss}")
        if r.get("method") not in ("audio", "human"):
            probs.append(f"verification record {i}: method must be audio or human")
        if r.get("verdict") not in LEDGER_VERDICTS:
            probs.append(f"verification record {i}: verdict must be one of {'/'.join(LEDGER_VERDICTS)}")
        if record_role(r) not in ROLES:
            probs.append(f"verification record {i}: role must be second-judge or human")
        if record_role(r) == "second-judge" and "claude" in str(r.get("reviewer") or "").lower():
            probs.append(f"verification record {i}: a Claude model cannot be the second judge of Claude readers")
        ev = r.get("evidence") or {}
        if not (ev.get("t_start") is not None and ev.get("t_end") is not None):
            probs.append(f"verification record {i}: evidence needs t_start and t_end")
        key = (r.get("uid"), r.get("reviewer"), r.get("at"), r.get("verdict"))
        if key in seen:
            probs.append(f"verification record {i}: exact duplicate of an earlier record")
        seen.add(key)
    return probs


def ledger_state(ledger):
    """uid -> {latest, revisions, human, second_judge}. Records are append-only; a later record of the same role
    supersedes an earlier one (= revision history). The latest HUMAN record settles a row; without one, the latest
    second-judge record does."""
    out = {}
    for r in sorted(ledger.get("records", []), key=lambda r: r.get("at") or ""):
        out.setdefault(r["uid"], []).append(r)
    st = {}
    for u, v in out.items():
        hum = [r for r in v if record_role(r) == "human"]
        sj = [r for r in v if record_role(r) == "second-judge"]
        st[u] = {"latest": v[-1], "revisions": len(v), "human": hum[-1] if hum else None, "second_judge": sj[-1] if sj else None}
    return st


def check_outcome(s):
    """What the ledger says about one row that needed a check: ('eligible'|'excluded'|'pending', why).
    Human: confirmed/changed = eligible, rejected = excluded, unsure = pending. Second judge alone: confirmed/changed =
    eligible (two different AIs agree, one of them on the audio); rejected/unsure = pending - the AIs disagree, so the
    row waits for Amal on the Tutor page and is never counted as right or dropped on one AI's word."""
    if not s:
        return None
    h, c = s.get("human"), s.get("second_judge")
    if h:
        if h["verdict"] in ("confirmed", "changed"):
            return "eligible", None
        if h["verdict"] == "rejected":
            return "excluded", f"rejected on a human check by {h['reviewer']}"
        return "pending", f"{h['reviewer']} could not tell"
    if c:
        if c["verdict"] in ("confirmed", "changed"):
            return "eligible", None
        return "pending", f"{c['reviewer']} (audio) {'disagrees with' if c['verdict'] == 'rejected' else 'cannot confirm'} the Claude readers; waiting for Amal (Tutor page)"
    return None


# ====================================================================== 7 grammar denominator
def grammar_denominator(slips, usage_lesson):
    """Is `uses` (machine-counted rule uses) a valid denominator for these corrected slips? Each slip must be one the
    counter could have counted: his line in Arabic script and a bucket the counter found at least as often."""
    usage_lesson = usage_lesson or {}
    uses = usage_lesson.get("uses")
    by = usage_lesson.get("by_bucket") or {}
    latin = [s for s in slips if not AR.search(s.get("said") or s.get("medi_said") or "")]
    zero = [s for s in slips if not by.get(s.get("bucket"))]
    per = collections.Counter(s.get("bucket") for s in slips)
    over = sorted(b for b, n in per.items() if n > (by.get(b) or 0))
    reasons = []
    if uses is None:
        reasons.append("no machine-counted uses for this lesson")
    else:
        if uses < len(slips):
            reasons.append(f"fewer counted uses ({uses}) than corrected slips ({len(slips)})")
        if latin:
            reasons.append(f"{len(latin)} of {len(slips)} slips are in turns the engine wrote in Latin letters, which the usage counter skips")
        if zero:
            reasons.append(f"{len(zero)} slips are in rules the counter found 0 uses of in this lesson")
        if over:
            reasons.append(f"{len(over)} rules have more slips than counted uses ({', '.join(over[:8])})")
    return {"valid": not reasons, "reasons": reasons, "uses": uses, "slips": len(slips), "slips_latin": len(latin),
            "slips_in_zero_use_rules": len(zero), "rules_slips_over_uses": over}


# ====================================================================== ASR review
def asr_review(date, lesson_s, wb_checks, evidence_dates):
    """Seconds of this lesson whose speech recognition was compared against a second model (docs/data/
    word-bank-transcription-checks.json). No lesson has a human listening pass."""
    ivs = [(c["start"], c["end"]) for c in (wb_checks or {}).get("comparisons", []) if evidence_dates.get(c.get("event_id")) == date]
    s = sum(b - a for a, b in ivs)
    return {"model_compared_excerpts": len(ivs), "model_compared_s": round(s, 1), "lesson_s": round(lesson_s or 0, 1),
            "human_listened_s": 0, "reviewed": False}


# ====================================================================== annotate
def _eligible_counts(items):
    right = sum(1 for x in items if x["p"] == 1)
    part = sum(1 for x in items if x["p"] == .5)
    wrong = sum(1 for x in items if x["p"] == 0)
    n = right + part + wrong
    return {"right": right, "partial": part, "wrong": wrong, "scored": n,
            "pct": round(100 * (right + .5 * part) / n, 1) if n else None}


def apply_source_audit(cov, sa):
    """Merge the raw-audio source audit (scripts/source_audit.py, data/accuracy/source-audit.json) into the coverage:
    speech on a person's own track with no transcript line, and recordings that were never saved, become 'missing'
    intervals (rows there are unscoreable); every flag becomes a release reason. Returns the reasons."""
    reasons = []
    if not sa:
        return ["coverage: no source audit of the raw audio for this lesson (run scripts/source_audit.py)"]
    for f in sa.get("flags", []):
        p = f.get("who")
        if f["kind"] in ("untranscribed", "audio-lost") and p in cov:
            cov[p]["missing"].append([f["from"], f["to"], f["text"]])
            cov[p]["missing_s"] = round(cov[p]["missing_s"] + (f["to"] - f["from"]), 1)
        reasons.append("coverage: " + f["text"])
    return reasons


def annotate(lessons_doc, details, audit, usage, policy, ledger, work=WORK, wb_checks=None, evidence_dates=None, source_audit=None):
    """Adds `release`, `coverage`, `source`, words/grammar `eligible|excluded|pending` + `verified_pct` to every lesson.
    The displayed `pct` stays as the builder computed it (standing decisions unchanged); only verified figures and the
    labels are new. Returns (lessons_doc, release_doc, queue)."""
    rows_by_uid = {r["uid"]: r for r in audit.get("rows", [])}
    state = ledger_state(ledger)
    queue, lessons_out, queued = [], [], set()
    T = float(policy["release_threshold_pct"])
    for L in lessons_doc["lessons"]:
        d = L["date"]
        D = details.get(d) or {}
        cov = participant_coverage(D.get("turns", []), (L.get("duration_min") or 0) * 60, policy)
        src = source_quality(L)
        agr = agreement(d, policy, work)
        n_passes = len(agr["passes"])
        reasons = list(agr["reasons"])
        for p in ("Medi", "Amal"):
            for a, b, why in cov[p]["missing"]:
                reasons.append(f"coverage: {p} not transcribed {mmss(a)}-{mmss(b)} while the other person talks")
            if cov[p]["holes"]:
                reasons.append(f"coverage: {len(cov[p]['holes'])} stretches of {p}'s speech written as '[speaking ...]' markers ({mmss(cov[p]['hole_s'])} in all)")
        if src["attribution"] in ATTRIBUTION_TEXT:
            reasons.append("coverage: " + ATTRIBUTION_TEXT[src["attribution"]])
        reasons += apply_source_audit(cov, ((source_audit or {}).get("lessons") or {}).get(d))
        asr = asr_review(d, (L.get("duration_min") or 0) * 60, wb_checks, evidence_dates or {})
        if policy.get("asr_review_required_for_verified", True) and not asr["reviewed"]:
            reasons.append(f"speech recognition not reviewed: nobody listened; {asr['model_compared_excerpts']} excerpts "
                           f"({asr['model_compared_s']:.0f} s of {asr['lesson_s']:.0f} s) compared with a second model")

        def judge(uid, t, t_amal, medi_said, chat):
            r = rows_by_uid.get(uid) if uid else None
            probe = r or {"t": t, "t_amal": t_amal, "medi_said": medi_said, "chat": chat}
            st, why = row_scoreability(probe, cov, policy)
            if st == "unscoreable":
                return "excluded", why
            chk = check_reasons(r, n_passes) if r else []
            s = state.get(uid) if uid else None
            oc = check_outcome(s)
            if oc and oc[0] == "excluded":
                return oc
            if chk and oc and oc[0] == "eligible":
                return "eligible", None
            if chk:
                if r and uid not in queued:
                    queued.add(uid)
                    queue.append({"uid": uid, "date": d, "t": r.get("t"), "t_amal": r.get("t_amal"), "kind": r.get("kind"),
                                  "tier": r.get("tier"), "bucket": r.get("bucket"), "medi_said": r.get("medi_said"),
                                  "amal_said": r.get("amal_said"), "wrong": r.get("wrong"), "right": r.get("right"),
                                  "why_check": chk, "check": "audio" if any("transcri" in c or "engine" in c for c in chk) else "audio or human",
                                  "stage": "waiting for Amal (the two AIs disagree)" if oc else "needs the second judge (audio)",
                                  "second_judge": ({k: (s.get("second_judge") or {}).get(k) for k in ("reviewer", "verdict", "reason")} if oc else None),
                                  "listen_from": mmss(max(0, (sec(r.get("t")) or sec(r.get("t_amal")) or 0) - 10)),
                                  "listen_to": mmss((sec(r.get("t_amal")) or sec(r.get("t")) or 0) + 20)})
                return "pending", (oc[1] if oc else "; ".join(chk))
            return "eligible", None

        # ---- words: every scored use on the page (Word Bank + the audit's slips on the sheet)
        items = []
        for e in D.get("vocab_correct", []):
            items.append({"p": 1 if e["kind"] == "correct" else .5, "uid": None, "t": e["t"], "src": "word-bank"})
        for e in D.get("vocab_errors", []):
            if e.get("on_sheet") is False:
                continue
            items.append({"p": .5 if e["kind"] in ("asked", "partial") else 0, "uid": e.get("audit_uid"), "t": e["t"],
                          "src": "audit" if e.get("source") == "audit-2026-09-26" else "word-bank", "said": e.get("said")})
        ex_w, pend_w, elig_w = [], [], []
        for x in items:
            st, why = judge(x["uid"], x["t"], None, x.get("said") if x["src"] == "audit" else "x", None)
            x["why"] = why
            (elig_w if st == "eligible" else pend_w if st == "pending" else ex_w).append(x)
        wv = L["words"]
        ec = _eligible_counts(elig_w + pend_w)
        vc = _eligible_counts(elig_w)
        wv.update({"eligible": len(elig_w) + len(pend_w), "excluded": len(ex_w), "pending": len(pend_w),
                   "eligible_pct": ec["pct"],
                   "excluded_why": dict(collections.Counter(x["why"].split(" at ")[0] if " at " in (x["why"] or "") else x["why"] for x in ex_w))})
        # ---- grammar: every slip on the page
        gitems = []
        for g in D.get("grammar_errors", []):
            st, why = judge(g.get("id"), g.get("t"), g.get("t_fix"), g.get("said"), g.get("chat"))
            gitems.append((st, why, g))
        gv = L["grammar"]
        den = grammar_denominator([{"said": g.get("said"), "bucket": g.get("bucket")} for _, _, g in gitems], (usage.get("lessons") or {}).get(d))
        g_ex = [x for x in gitems if x[0] == "excluded"]
        g_pe = [x for x in gitems if x[0] == "pending"]
        gv.update({"eligible": len(gitems) - len(g_ex), "excluded": len(g_ex), "pending": len(g_pe), "denominator": den})
        pend_reason = []
        if pend_w or g_pe:
            pend_reason.append(f"checks: {len(pend_w) + len(g_pe)} scored rows need an audio or human check "
                               f"({len(pend_w)} words, {len(g_pe)} grammar)")
        released = not reasons and not pend_reason
        rel = {"status": "verified" if released else "not verified", "reasons": reasons + pend_reason,
               "agreement": {k: agr[k] for k in ("status", "passes", "between", "threshold_pct")}, "asr": asr}
        wv["verified_pct"] = vc["pct"] if released else None
        gv["verified_pct"] = (round(100 * (1 - (len(gitems) - len(g_ex) - len(g_pe)) / den["uses"]), 1)
                              if released and den["valid"] and den["uses"] else None)
        L["release"], L["coverage_by_person"], L["source"] = rel, cov, src
        lessons_out.append({"date": d, "release": rel["status"], "reasons": rel["reasons"],
                            "words": {k: wv.get(k) for k in ("pct", "eligible_pct", "verified_pct", "scored", "eligible", "excluded", "pending", "excluded_why")},
                            "grammar": {k: gv.get(k) for k in ("pct", "verified_pct", "mistakes", "uses", "eligible", "excluded", "pending", "estimate")} | {"denominator_valid": den["valid"], "denominator_reasons": den["reasons"]},
                            "coverage": {p: {k: cov[p][k] for k in ("covered_pct", "missing_s", "hole_s")} for p in cov},
                            "source": src, "agreement": [p["agreement_pct"] for p in agr["passes"]],
                            "between_passes": [b["agreement_pct"] for b in agr["between"]]})
    ver = [x for x in lessons_out if x["release"] == "verified"]
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    totals = {
        "lessons": len(lessons_out), "verified_lessons": len(ver), "threshold_pct": T,
        "words": {"verified_avg_pct": avg([x["words"]["verified_pct"] for x in ver if x["words"]["verified_pct"] is not None]),
                  "unverified_avg_pct": avg([x["words"]["pct"] for x in lessons_out if x["words"]["pct"] is not None]),
                  "eligible": sum(x["words"]["eligible"] for x in lessons_out), "excluded": sum(x["words"]["excluded"] for x in lessons_out),
                  "pending": sum(x["words"]["pending"] for x in lessons_out)},
        "grammar": {"verified_avg_pct": avg([x["grammar"]["verified_pct"] for x in ver if x["grammar"]["verified_pct"] is not None]),
                    "unverified_avg_pct": avg([x["grammar"]["pct"] for x in lessons_out if x["grammar"]["pct"] is not None]),
                    "denominator_valid_lessons": sum(1 for x in lessons_out if x["grammar"]["denominator_valid"]),
                    "eligible": sum(x["grammar"]["eligible"] for x in lessons_out), "excluded": sum(x["grammar"]["excluded"] for x in lessons_out),
                    "pending": sum(x["grammar"]["pending"] for x in lessons_out)},
        "verification_queue": len(queue),
    }
    release_doc = {"about": "Release layer over docs/data/lessons.json (scripts/accuracy_gates.py). A number is verified only when "
                            "every gate in docs/data/accuracy-policy.json holds; the rest stay visible, labelled, and out of verified totals.",
                   "policy": {k: policy[k] for k in ("release_threshold_pct", "consecutive_passes_required", "max_reader_passes")},
                   "totals": totals, "lessons": lessons_out}
    return lessons_doc, release_doc, sorted(queue, key=lambda q: (q["date"], sec(q["t"]) or sec(q["t_amal"]) or 0))


def evidence_date_index(repo=REPO):
    p = os.path.join(repo, "docs", "data", "word-bank-evidence.json")
    if not os.path.exists(p):
        return {}
    E = J(p)
    return {e["id"]: e.get("lesson_date") for e in (E.get("events") if isinstance(E, dict) else E)}


def run_annotate(repo=REPO, write=True):
    policy = load_policy(os.path.join(repo, "docs", "data", "accuracy-policy.json"))
    lessons_p = os.path.join(repo, "docs", "data", "lessons.json")
    doc = J(lessons_p)
    details = {L["date"]: J(os.path.join(repo, "docs", "data", "lessons", L["date"] + ".json")) for L in doc["lessons"]}
    audit = J(os.path.join(repo, "data", "full-audit-2026-09-26.json"))
    up = os.path.join(repo, "docs", "data", "grammar-usage.json")
    usage = J(up) if os.path.exists(up) else {"lessons": {}}
    ledger = load_ledger(os.path.join(repo, "data", "accuracy", "verifications.json"))
    cp = os.path.join(repo, "docs", "data", "word-bank-transcription-checks.json")
    wb_checks = J(cp) if os.path.exists(cp) else None
    sp = os.path.join(repo, "data", "accuracy", "source-audit.json")
    doc, rel, queue = annotate(doc, details, audit, usage, policy, ledger, os.path.join(repo, "data", "lesson-work", "full-audit"),
                               wb_checks, evidence_date_index(repo), J(sp) if os.path.exists(sp) else None)
    if write:
        W(lessons_p, doc)
        W(os.path.join(repo, "docs", "data", "accuracy-release.json"), rel)
        W(os.path.join(repo, "data", "accuracy", "verification-queue.json"),
          {"about": "Scored rows that need an independent audio or human check before they count in any verified total. "
                    "Record each check in data/accuracy/verifications.json (append-only: uid, method audio|human, reviewer, "
                    "verdict confirmed|rejected|changed, evidence {t_start, t_end, quote}, confidence, at).",
           "count": len(queue), "by_date": dict(collections.Counter(q["date"] for q in queue)), "rows": queue})
    return doc, rel, queue


# ====================================================================== 4 cache manifests (fail closed on stale inputs)
def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def input_hashes(paths, repo=REPO):
    out = {}
    for p in paths:
        full = p if os.path.isabs(p) else os.path.join(repo, p)
        out[os.path.relpath(full, repo).replace("\\", "/")] = sha_file(full) if os.path.exists(full) else None
    return out


def manifest_path(output):
    return output + ".inputs.json"


def write_manifest(output, inputs, repo=REPO, extra=None):
    W(manifest_path(output), {"output": os.path.relpath(output, repo).replace("\\", "/"), "output_sha256": sha_file(output),
                              "inputs": input_hashes(inputs, repo), "written": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                              **(extra or {})})


def cache_state(output, inputs, repo=REPO):
    """'missing' | 'fresh' | 'stale: <why>'. An output is reused only when it exists, has a manifest, is unchanged since
    the manifest, and every input (transcript, briefs, rules, vocabulary, buckets) still has the recorded hash."""
    if not os.path.exists(output):
        return "missing"
    mp = manifest_path(output)
    if not os.path.exists(mp):
        return "stale: no input manifest (written before 2026-09-27 or by hand)"
    M = J(mp)
    if M.get("output_sha256") != sha_file(output):
        return "stale: the output was edited after it was written"
    now = input_hashes(inputs, repo)
    changed = [k for k, v in now.items() if M.get("inputs", {}).get(k) != v]
    if changed:
        return "stale: inputs changed since it was written: " + ", ".join(changed)
    return "fresh"


# ====================================================================== 5 validation before publishing
def validate(repo=REPO):
    """Fail-closed checks on the data the pages read. Returns a list of problems (empty = publishable)."""
    probs = []
    policy = load_policy(os.path.join(repo, "docs", "data", "accuracy-policy.json"))
    if float(policy.get("release_threshold_pct", 0)) < 95.0:
        probs.append("policy: release threshold lowered below 95 % (a rule change only Medi makes)")
    lessons = J(os.path.join(repo, "docs", "data", "lessons.json"))["lessons"]
    audit = J(os.path.join(repo, "data", "full-audit-2026-09-26.json"))
    buckets = {b["id"] for b in J(os.path.join(repo, "docs", "data", "grammar-buckets.json"))["buckets"]}
    wb = J(os.path.join(repo, "docs", "data", "word-bank-audit.json"))
    wbc = collections.Counter((e["date"], e["status"]) for e in wb.get("events", []))
    ledger = load_ledger(os.path.join(repo, "data", "accuracy", "verifications.json"))
    probs += ledger_problems(ledger)
    # schema: full-audit rows
    kinds = {"grammar", "grammar-B", "vocab-A", "vocab-B", "rejected"}
    uids = set()
    for r in audit["rows"]:
        if r.get("kind") not in kinds:
            probs.append(f"audit row {r.get('uid')}: kind {r.get('kind')!r} unknown")
        if not r.get("uid") or r["uid"] in uids:
            probs.append(f"audit row {r.get('uid')}: missing or duplicate uid")
        uids.add(r.get("uid"))
        if sec(r.get("t")) is None and sec(r.get("t_amal")) is None:
            probs.append(f"audit row {r.get('uid')}: no time")
        # a speaking grammar row must sit in an approved bucket, or in a named group waiting for approval (NEW-A12 /
        # NEW-C11 are not approved, so they count nowhere; NEW-B18 was approved as B18 on 2026-09-24)
        if r.get("kind") == "grammar" and r.get("mode", "speaking") == "speaking" and r.get("bucket") not in buckets \
                and not str(r.get("new_bucket_group") or "").startswith("NEW-"):
            probs.append(f"audit row {r.get('uid')}: grammar row in unknown bucket {r.get('bucket')!r}")
    for L in lessons:
        d = L["date"]
        for k in ("words", "grammar", "release", "coverage_by_person", "source"):
            if k not in L:
                probs.append(f"{d}: lessons.json has no {k!r} (run scripts/accuracy_gates.py annotate)")
        if "release" not in L:
            continue
        dp = os.path.join(repo, "docs", "data", "lessons", d + ".json")
        if not os.path.exists(dp):
            probs.append(f"{d}: detail file missing")
            continue
        D = J(dp)
        w = L["words"]
        # scoring invariants
        if w["right"] + w["wrong"] + w["partial"] != w["scored"]:
            probs.append(f"{d}: words right+wrong+partial {w['right']}+{w['wrong']}+{w['partial']} != scored {w['scored']}")
        exp = round(100 * (w["right"] + .5 * w["partial"]) / w["scored"], 1) if w["scored"] else None
        if w.get("pct") != exp:
            probs.append(f"{d}: words pct {w.get('pct')} != (right + half partial) / scored = {exp}")
        if w.get("eligible", 0) + w.get("excluded", 0) != w["scored"]:
            probs.append(f"{d}: words eligible {w.get('eligible')} + excluded {w.get('excluded')} != scored {w['scored']}")
        if w.get("pending", 0) > w.get("eligible", 0):
            probs.append(f"{d}: more pending than eligible word uses")
        g = L["grammar"]
        if g.get("eligible", 0) + g.get("excluded", 0) != g["mistakes"]:
            probs.append(f"{d}: grammar eligible + excluded != mistakes")
        # release consistency: nothing verified that fails a gate
        rel = L["release"]
        if rel["status"] == "verified" and rel["reasons"]:
            probs.append(f"{d}: verified with open reasons")
        if rel["status"] != "verified" and (w.get("verified_pct") is not None or g.get("verified_pct") is not None):
            probs.append(f"{d}: a verified % is shown for a lesson that is not verified")
        if rel["status"] == "verified":
            T = float(policy["release_threshold_pct"])
            ag = rel["agreement"]
            if len(ag["passes"]) < 2 or any((p["agreement_pct"] or 0) < T for p in ag["passes"][-2:]):
                probs.append(f"{d}: verified below the agreement threshold")
            if not g.get("denominator", {}).get("valid") and g.get("verified_pct") is not None:
                probs.append(f"{d}: verified grammar % with an invalid denominator")
        # reconciliation: Lessons summary = lesson detail = Word Bank ledger = audit
        ve = [e for e in D.get("vocab_errors", []) if e.get("on_sheet") is not False]
        vc = D.get("vocab_correct", [])
        calc = {"right": sum(1 for e in vc if e["kind"] == "correct"),
                "partial": sum(1 for e in vc if e["kind"] == "partial") + sum(1 for e in ve if e["kind"] in ("asked", "partial")),
                "wrong": sum(1 for e in ve if e["kind"] == "wrong")}
        for k, v in calc.items():
            if w[k] != v:
                probs.append(f"{d}: Lessons summary words.{k}={w[k]} but the lesson detail has {v}")
        if w["right"] != wbc[(d, "Correct")]:
            probs.append(f"{d}: Lessons words.right={w['right']} but the Word Bank audit has {wbc[(d, 'Correct')]} Correct")
        # one Word Bank event can be two wrong attempts (a wrong substitution scores the said AND the intended word -
        # SESSION-DECISIONS 2026-09-21, e.g. 09-16 safra/safar), so events are compared, not cards
        wb_wrong = len({e.get("event_id") for e in ve if e["kind"] == "wrong" and e.get("source") != "audit-2026-09-26"})
        if wb_wrong > wbc[(d, "Wrong")]:
            probs.append(f"{d}: {wb_wrong} Word Bank wrong events on the Lessons page but the Word Bank audit has {wbc[(d, 'Wrong')]} Wrong")
        if g["mistakes"] != len(D.get("grammar_errors", [])):
            probs.append(f"{d}: grammar.mistakes {g['mistakes']} != {len(D.get('grammar_errors', []))} grammar cards")
        a_rows = [r for r in audit["sweep_compat"]["rows"] if r["date"] == d and r.get("mode") == "speaking"
                  and ((r.get("bucket") in buckets) or r.get("new_bucket_group") == "NEW-B18")]
        # every speaking grammar row of the audit is on the page exactly once: a counted card, or a card Amal's rule notes
        # set apart (grammar_not_counted: not taught yet / dropped, 2026-09-29) - by uid, not by count
        a_uids = {r["uid"] for r in a_rows}
        shown = [x.get("id") for x in D.get("grammar_errors", [])] + [x.get("id") for x in D.get("grammar_not_counted", [])]
        dup = sorted({u for u in shown if shown.count(u) > 1})
        lost = sorted(a_uids - set(shown))
        extra = sorted(set(shown) - a_uids)
        if dup or lost or extra:
            probs.append(f"{d}: grammar cards do not match the full audit: {len(lost)} audit rows missing {lost[:4]}, "
                         f"{len(extra)} cards not in the audit {extra[:4]}, {len(dup)} shown twice {dup[:4]}")
    # the release layer must be what the gates give TODAY (a new ledger record, source audit or reader pass changes it)
    try:
        doc2, rel2, q2 = run_annotate(repo, write=False)
        fresh = {L["date"]: L for L in doc2["lessons"]}
        for L in lessons:
            F = fresh.get(L["date"]) or {}
            if (L.get("release") or {}).get("status") != (F.get("release") or {}).get("status")                     or (L.get("release") or {}).get("reasons") != (F.get("release") or {}).get("reasons"):
                probs.append(f"{L['date']}: the release layer in lessons.json is stale (run scripts/accuracy_gates.py annotate)")
            for k in ("eligible", "excluded", "pending", "verified_pct"):
                if L["words"].get(k) != F["words"].get(k) or L["grammar"].get(k) != F["grammar"].get(k):
                    probs.append(f"{L['date']}: {k} counts in lessons.json are stale (run scripts/accuracy_gates.py annotate)")
                    break
        qp = os.path.join(repo, "data", "accuracy", "verification-queue.json")
        if os.path.exists(qp) and J(qp).get("count") != len(q2):
            probs.append(f"verification queue is stale: file has {J(qp).get('count')} rows, the gates give {len(q2)}")
    except Exception as e:                                   # fail closed: a gate that cannot run blocks publishing
        probs.append(f"the release layer could not be recomputed: {type(e).__name__}: {e}")
    rp = os.path.join(repo, "docs", "data", "accuracy-release.json")
    if not os.path.exists(rp):
        probs.append("docs/data/accuracy-release.json missing")
    else:
        R = J(rp)
        if R["totals"]["verified_lessons"] != sum(1 for L in lessons if (L.get("release") or {}).get("status") == "verified"):
            probs.append("accuracy-release.json verified_lessons disagrees with lessons.json")
    gc = os.path.join(repo, "docs", "data", "grammar-console.json")
    if os.path.exists(gc):
        G = J(gc)
        n_console = sum(int(b.get("mistakes") or 0) for b in G.get("buckets", G.get("rules", [])) if isinstance(b, dict))
        n_lessons = sum(L["grammar"]["mistakes"] for L in lessons)
        if n_console and n_console != n_lessons:
            probs.append(f"Grammar console counts {n_console} slips but the Lessons page counts {n_lessons}")
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["annotate", "check", "agreement"])
    ap.add_argument("date", nargs="?")
    a = ap.parse_args(argv)
    if a.cmd == "annotate":
        _, rel, q = run_annotate()
        t = rel["totals"]
        print(f"lessons {t['lessons']} verified {t['verified_lessons']} | words eligible {t['words']['eligible']} excluded "
              f"{t['words']['excluded']} pending {t['words']['pending']} | grammar denominator valid in "
              f"{t['grammar']['denominator_valid_lessons']} | verification queue {len(q)}")
        return 0
    if a.cmd == "agreement":
        print(json.dumps(agreement(a.date, load_policy()), ensure_ascii=False, indent=1))
        return 0
    try:
        probs = validate()
    except Exception as e:                                   # fail closed: an exception is a problem, never a pass
        probs = [f"the accuracy check itself failed: {type(e).__name__}: {e}"]
    for p in probs:
        print("PROBLEM", p)
    # last line = one plain sentence the publish guard can show (hourly log, System Settings)
    print("accuracy check: OK" if not probs else f"accuracy check: {len(probs)} problem(s) - do not publish. First: {probs[0]}")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
