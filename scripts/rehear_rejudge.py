# -*- coding: utf-8 -*-
"""Re-judge all lessons on the re-heard transcript without losing anything that hangs on an audit row
(2026-10-04; runbook: plan/REHEAR-REJUDGE-RUNBOOK-2026-10-04.md).

Medi's lines change tonight (transcript-fixes.json rows by "gemini-rehear"), so the three AI readers re-read every
lesson. An audit row's uid is a hash of date + second + wrong piece + kind, so a re-read that moves a slip one second or
words it differently makes a new uid, and Amal's rulings, the verification records, the patterns, duplicates.json and
Medi's corrections silently stop pointing at it. This script keeps them attached. It never calls an AI, never writes to
Supabase, never commits, and nothing here goes to Amal.

    python scripts/rehear_rejudge.py snapshot               # BEFORE anything changes: rehear/rejudge/before.json
    python scripts/rehear_rejudge.py retire-pass2 [--apply] # move the 13 old pass-2 files aside (they read the old text)
    python scripts/rehear_rejudge.py prompts <date>         # the r1 / r2 / r3 prompt text for an agent run
    python scripts/rehear_rejudge.py accept <date> r1|r2|r3 # validate the agent's file + pin its input manifest
    python scripts/rehear_rejudge.py carry                  # old row -> new row of the same moment: full-audit/uid-carry.json
    python scripts/rehear_rejudge.py kept                   # Amal-ruled rows with no new row: kept (confirmed) / listed
    python scripts/rehear_rejudge.py preflight              # every ruling that no longer resolves, BEFORE full_audit_build
    python scripts/rehear_rejudge.py hold                   # rows the re-read created: full-audit/hold-from-amal.json
    python scripts/rehear_rejudge.py report                 # before vs after, per lesson (after build + Amal's rulings)
    python scripts/rehear_rejudge.py amal-diff              # her lists vs origin/master: exit 1 when anything was ADDED

Files: data/lesson-work/rehear/rejudge/ (before.json, prompts/, kept-rows.json, preflight.json, report.json, report.md)
and, read by scripts/full_audit_build.py: data/lesson-work/full-audit/uid-carry.json + preserved-rows.json.
"""
import argparse, collections, datetime as dt, hashlib, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from full_audit_compare import sec, norm, same_moment, same_piece, kind_class  # noqa: E402

WORK = os.path.join(REPO, "data", "lesson-work", "full-audit")
OUTD = os.path.join(REPO, "data", "lesson-work", "rehear", "rejudge")
BEFORE = os.path.join(OUTD, "before.json")
AUDIT = os.path.join(REPO, "data", "full-audit-2026-09-26.json")
SUPERSEDED = os.path.join(WORK, "superseded-2026-10-04")
REPEAT_S = 30
KEPT_MARK = "amal-confirmed; the readers did not write this row on the re-heard text"
RESTORED_MARK = ("first-read slip; the re-read on 2026-10-04 did not write it again and its words are still on the line - "
                 "kept until a person checks it")


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------------------------- what hangs on a uid
def line_at(turns, t, who="Medi"):
    """The text of his line at a row's time (the row's t is the second his line starts)."""
    t = sec(t)
    if t is None:
        return None
    best = None
    for u in turns or []:
        if u.get("who") != who:
            continue
        d = abs(float(u.get("t") or 0) - t)
        if int(float(u.get("t") or 0)) == int(t):
            return u.get("text")
        if d <= 3 and (best is None or d < best[0]):
            best = (d, u.get("text"))
    return best[1] if best else None


def amal_state(row, records=()):
    """'confirmed' | 'rejected' | None: Amal's latest word on a row (her review / after-lesson ruling on the row, or her
    Tutor-page check in the verification ledger; an undone check - 'withdrawn' - is no ruling)."""
    seen = []
    ar = row.get("amal_ruling") or {}
    if ar.get("kind"):
        seen.append((str(ar.get("at") or ""), "confirmed" if ar["kind"] == "confirm" else "rejected"))
    for r in records:
        if r.get("uid") == row.get("uid") and r.get("reviewer") == "Amal":
            seen.append((str(r.get("at") or ""), {"confirmed": "confirmed", "rejected": "rejected"}.get(r.get("verdict"))))
    seen.sort(key=lambda x: x[0])
    return seen[-1][1] if seen else None


def references(repo=REPO):
    """Everything in the repo that points at an audit uid -> {uid: {"amal_ruling", "verifications", "patterns", ...}}."""
    work = os.path.join(repo, "data", "lesson-work", "full-audit")
    ref = collections.defaultdict(dict)
    A = J(os.path.join(repo, "data", "full-audit-2026-09-26.json"), {"rows": []})
    V = (J(os.path.join(repo, "data", "accuracy", "verifications.json"), {}) or {}).get("records", [])
    for r in A["rows"]:
        if r.get("amal_ruling"):
            ref[r["uid"]]["amal_ruling"] = r["amal_ruling"].get("kind")
        if r.get("correction") or r.get("medi_corrections"):
            ref[r["uid"]]["medi_correction_applied"] = True
    for v in V:
        ref[v["uid"]]["verifications"] = ref[v["uid"]].get("verifications", 0) + 1
        if v.get("reviewer") == "Amal":
            ref[v["uid"]]["amal_check"] = v.get("verdict")
    for p in (J(os.path.join(work, "patterns.json"), {}) or {}).get("patterns", []):
        for u in p.get("rows") or []:
            ref[u].setdefault("patterns", []).append(p.get("id"))
    for h in (J(os.path.join(work, "duplicates.json"), {}) or {}).get("pairs", []):
        ref[h["keep"]].setdefault("duplicates", []).append("keep")
        ref[h["drop"]].setdefault("duplicates", []).append("drop")
    for g in (J(os.path.join(repo, "docs", "data", "ai_rules.json"), {}) or {}).get("groups", []):
        for x in g.get("rules", []):
            for u in x.get("rows") or []:
                ref[u].setdefault("ai_rules", []).append(x.get("id"))
    notes = os.path.join(repo, "scripts", "amal_grammar_notes.py")       # rows her notes rule out, hard-coded by uid
    if os.path.exists(notes):
        for u in set(re.findall(r'"(FA-[0-9a-f]{8}x*)"\s*:', open(notes, encoding="utf-8").read())):
            ref[u]["amal_grammar_notes"] = True
    for f in ("medi-corrections.json", "medi-corrections-hand.json"):
        for c in (J(os.path.join(repo, "data", "lesson-work", f), {}) or {}).get("rows", []):
            src = str((c.get("target") or {}).get("src") or "")
            if src.startswith("FA-"):
                ref[src].setdefault("medi_corrections", []).append(c.get("id"))
    return dict(ref)


def hand_matches(rows, repo=REPO):
    """Which rows the moment-matched hand files point at -> {uid: {"rejected.json": [i], ...}} (same tests as the build)."""
    work = os.path.join(repo, "data", "lesson-work", "full-audit")
    out = collections.defaultdict(dict)
    for name, key in (("rejected.json", "rows"), ("signal-rulings.json", "rows")):
        for i, x in enumerate((J(os.path.join(work, name), {}) or {}).get(key, [])):
            for r in rows:
                if r.get("date") == x["date"] and ruling_hits(r, x):
                    out[r["uid"]].setdefault(name, []).append(i)
                    break
    for p in (J(os.path.join(work, "proposed-buckets.json"), {}) or {}).get("proposals", []):
        for x in p.get("rows", []):
            for r in rows:
                if r.get("date") == x["date"] and same_moment(r, x) and any(same_piece(w, x.get("wrong")) for w in pieces(r)):
                    out[r["uid"]].setdefault("proposed-buckets.json", []).append(p.get("id"))
    return dict(out)


def ruling_hits(r, x):
    """The build's test for a rejected.json / signal-rulings.json row, on a row in ANY state (already rejected or not)."""
    return (same_moment(r, x) and any(same_piece(w, x.get("wrong")) for w in (pieces(r) or [r.get("medi_said")]))   # FAB.ruled_piece
            and (not x.get("kind") or kind_class(x["kind"]) in classes(r)))


def headline(lesson):
    w, g = lesson.get("words") or {}, lesson.get("grammar") or {}
    return {"words_pct": w.get("pct"), "words": {k: w.get(k) for k in ("right", "partial", "wrong", "scored", "unique")},
            "grammar_pct": g.get("pct") if isinstance(g, dict) else None,
            "grammar": {k: g.get(k) for k in ("uses", "mistakes")} if isinstance(g, dict) else None,
            "counts": lesson.get("counts"), "release": (lesson.get("release") or {}).get("status")}


def snapshot(repo=REPO, out=None, pin_legacy=True):
    out = out or os.path.join(repo, "data", "lesson-work", "rehear", "rejudge", "before.json")
    if os.path.exists(out):
        raise SystemExit(f"{out} exists - the snapshot is taken ONCE, before the re-read. Not overwritten.")
    work = os.path.join(repo, "data", "lesson-work", "full-audit")
    A = J(os.path.join(repo, "data", "full-audit-2026-09-26.json"))
    V = (J(os.path.join(repo, "data", "accuracy", "verifications.json"), {}) or {}).get("records", [])
    ref, hand = references(repo), hand_matches(A["rows"], repo)
    L = {x["date"]: x for x in (J(os.path.join(repo, "docs", "data", "lessons.json"), {}) or {}).get("lessons", [])}
    lessons = {}
    for d in sorted({r["date"] for r in A["rows"]} | set(L)):
        turns = (J(os.path.join(repo, "docs", "data", "lessons", d + ".json"), {}) or {}).get("turns", [])
        rows = []
        for r in A["rows"]:
            if r["date"] != d:
                continue
            x = dict(r)
            x["line_before"] = line_at(turns, r.get("t"))
            x["refs"] = {**ref.get(r["uid"], {}), **({"hand": hand[r["uid"]]} if r["uid"] in hand else {})}
            x["amal"] = amal_state(r, V)
            rows.append(x)
        files = {}
        for suffix in (".txt", ".r1.json", ".r2.json", ".r3.json", ".settled.json", ".p2.settled.json"):
            p = os.path.join(work, d + suffix)
            if os.path.exists(p):
                files[suffix] = sha_file(p)
        lessons[d] = {"rows": rows, "headline": headline(L[d]) if d in L else None, "files": files}
    known = {r["uid"] for r in A["rows"]}
    doc = {"about": "The audit as it stood BEFORE the 2026-10-04 re-read (scripts/rehear_rejudge.py snapshot). Taken once; never "
                    "overwritten. carry / kept / report compare against it.",
           "taken": now(), "audit_built": A.get("built"), "totals": A.get("totals"),
           "already_orphaned": sorted(u for u in ref if u not in known),      # references that pointed at nothing before tonight
           "lessons": lessons}
    W(out, doc)
    pinned = []
    if pin_legacy:        # what review_lesson.py does before the transcript dump is rewritten: the freshness evidence
        import accuracy_gates as G
        for d in lessons:
            txt = os.path.join(work, d + ".txt")
            for r in ("r1", "r2", "r3"):
                o = os.path.join(work, f"{d}.{r}.json")
                if os.path.exists(o) and os.path.exists(txt) and not os.path.exists(o + ".inputs.json"):
                    G.write_manifest(o, [txt], repo=repo, extra={"legacy": "written before input manifests; this is the transcript it read (pinned by rehear_rejudge snapshot before the 2026-10-04 re-hear)"})
                    pinned.append(os.path.basename(o))
    n = sum(len(x["rows"]) for x in lessons.values())
    print(f"snapshot: {len(lessons)} lessons, {n} rows, {sum(1 for x in lessons.values() for r in x['rows'] if r['amal'])} with Amal's ruling, "
          f"{len(doc['already_orphaned'])} references already pointing at no row | legacy manifests pinned {len(pinned)} -> {out}")
    return doc


# ---------------------------------------------------------------------------------------------- the carry
def classes(r):
    """vocab / grammar classes a row has or had (a row rejected, dropped by Amal, proposed or re-filed keeps its first class)."""
    ks = [r.get("kind"), r.get("kind_before_rejection"), r.get("kind_before_proposal"), r.get("kind_before_gr25"),
          r.get("kind_before_gr26"), r.get("kind_before_medi"), ((r.get("amal_ruling") or {}).get("before") or {}).get("kind")]
    out = {kind_class(k) for k in ks if k} & {"vocab", "grammar"}
    if not out and r.get("kind") == "dropped-by-amal":
        out = {"grammar" if r.get("bucket") else "vocab"}
    return out


def pieces(r):
    return [w for w in (r.get("wrong"), r.get("wrong_before_gr25"), r.get("wrong_before_medi")) if norm(w)]


def _class_ok(o, n):
    a, b = classes(o), classes(n)
    return bool(a & b) or not a or not b


def _dt(o, n):
    a, b = sec(o.get("t")), sec(n.get("t"))
    return abs(a - b) if a is not None and b is not None else 1e9


def _dta(o, n):
    a, b = sec(o.get("t_amal")), sec(n.get("t_amal"))
    return abs(a - b) if a is not None and b is not None else 1e9


def match_rows(old, new):
    """One lesson. old = rows of the snapshot (uid), new = the re-read rows with the uid they would get by themselves.
    -> [(old index, new index, how)], each row used once. Order of trust:
      exact      the new row hashes to the old uid (same second, wrong piece, kind class): nothing to carry
      sweep      both are the same 09-24 sweep row (sweep_id)
      piece      same moment (5 s) + same wrong or right piece + same kind class; the closest in time wins
      repeat     the same wrong piece and kind class within 30 s, one candidate on each side (the build's one-slip rule)
      moment     same moment + same kind class, exactly one candidate on each side (the wording changed)"""
    uo, un, out = set(), set(), []

    def take(i, j, how):
        uo.add(i); un.add(j); out.append((i, j, how))
    by_uid = {n.get("uid"): j for j, n in enumerate(new)}
    for i, o in enumerate(old):
        j = by_uid.get(o.get("uid"))
        if j is not None and j not in un:
            take(i, j, "exact")
    by_sw = {n.get("sweep_id"): j for j, n in enumerate(new) if n.get("sweep_id")}
    for i, o in enumerate(old):
        j = by_sw.get(o.get("sweep_id")) if o.get("sweep_id") else None
        if i not in uo and j is not None and j not in un:
            take(i, j, "sweep")
    for i, o in enumerate(old):
        if i in uo:
            continue
        c = [j for j, n in enumerate(new) if j not in un and same_moment(o, n) and _class_ok(o, n)
             and (any(same_piece(a, b) for a in pieces(o) for b in pieces(n)) or same_piece(o.get("right"), n.get("right")))]
        if c:
            # closest in time; two candidates at the same second (09-17 22:14: his line is untranscribed, both rows quote
            # '[speaking Arabic]') are told apart by the rule, then by when Amal answered
            take(i, min(c, key=lambda j: (_dt(o, new[j]), (o.get("bucket") or None) != (new[j].get("bucket") or None), _dta(o, new[j]))), "piece")

    def unique(test, how):
        co = {i: [j for j, n in enumerate(new) if j not in un and test(o, n)] for i, o in enumerate(old) if i not in uo}
        cn = collections.Counter(j for js in co.values() for j in js)
        for i, js in co.items():
            if len(js) == 1 and cn[js[0]] == 1:
                take(i, js[0], how)
    unique(lambda o, n: _class_ok(o, n) and _dt(o, n) <= REPEAT_S and bool({norm(w) for w in pieces(o)} & {norm(w) for w in pieces(n)}), "repeat")
    unique(lambda o, n: same_moment(o, n) and _class_ok(o, n), "moment")
    return out


def _skel(x):
    """Consonant skeleton of a whole piece (xscript.skel); a Latin piece's written final -h (sawwaah) is not a consonant."""
    import xscript as X
    k = X.skel(re.sub(r"[^\w']+", "", str(x)))
    return k[:-1] if not X.is_ar(str(x)) and len(k) > 1 and k.endswith("h") else k


def _same_consonants(a, b, hold=3):
    """One consonant skeleton equals or holds the other (`hold`+ consonants to hold) - in any two alphabets. Loose on
    purpose (katab and كاتب pass), so it is never enough by itself (same_slip)."""
    if not norm(a) or not norm(b):
        return False
    ka, kb = _skel(a), _skel(b)
    return bool(ka) and bool(kb) and (ka == kb or (min(len(ka), len(kb)) >= hold and (ka in kb or kb in ka)))


def _two_alphabets(a, b, hold=3):
    """The same piece once in Latin letters and once in Arabic script, by consonants alone."""
    import xscript as X
    return bool(norm(a)) and bool(norm(b)) and X.is_ar(a) != X.is_ar(b) and _same_consonants(a, b, hold)


def _same_word_two_alphabets(a, b):
    """The strict cross-alphabet test of lesson_ledger.still_on_line on a whole piece: identical consonants AND vowels that
    agree for sure (a long ا inside the Arabic word must be written long in Latin: katab is كتب, not كاتب)."""
    import xscript as X
    import lesson_ledger as LL
    if not norm(a) or not norm(b) or X.is_ar(a) == X.is_ar(b):
        return False
    lat, ar = (b, a) if X.is_ar(a) else (a, b)
    join = lambda x: "".join(X.TOK.findall(str(x)))  # noqa: E731
    (lc, ls), (ac, as_) = LL._shape(join(lat)), LL._shape(join(ar))
    if bool(lc) and lc == ac and LL._slots_agree(ls, as_):
        return True
    # the same rule word by word (the two alphabets split words differently: 'el akil' / الأكل): every Latin word is on
    # the Arabic piece as the same word (lesson_ledger.still_on_line) AND the whole pieces have identical consonants
    return bool(_skel(lat)) and _skel(lat) == _skel(ar) and LL.still_on_line(str(lat), str(ar))


def sec_mmss(v):
    """mm:ss / h:mm:ss -> the "t" the matchers read (they take the mm:ss string): returned unchanged, None when empty."""
    return v or None


def _no_gloss(x):
    """A piece without the reader's bracketed note ('(my reading)', '(best reading)', '(ba5alli)'): the note is not his
    or her words."""
    return re.sub(r"\([^)]*\)", " ", str(x or ""))


def same_words(a, b):
    """Are two pieces the same WORDS? The same text after the normaliser (every token equal, in order), or - one in
    Latin letters, one in Arabic script - the strict same-word rule (_same_word_two_alphabets: identical consonants AND
    long-vowel letters). A reader's bracketed note is left out first. No overlap count, no substring, no ratio, no threshold."""
    a, b = _no_gloss(a), _no_gloss(b)
    na, nb = norm(a), norm(b)
    return bool(na) and bool(nb) and (na == nb or _same_word_two_alphabets(a, b))


def same_slip(o, n):
    """Is the re-read row n the same CORRECTION as old row o? Codex final approval round 4: the ONLY way is
    wrong == wrong AND right == right by same_words, both pieces and both fixes present. (Two rows that both name no
    wrong piece - he did not know the word - are compared on the fix.) Decides the carry of a uid Amal ruled on, the
    "same correction on another row" removal and the double-count guard of restored rows; the ordinary carry of an
    unruled uid (match_rows) is its own, looser, function and never calls this."""
    if not norm(o.get("right")) or not norm(n.get("right")) or not same_words(o.get("right"), n.get("right")):
        return False
    po, pn = pieces(o), pieces(n)
    if not po and not pn:
        return True
    return any(same_words(a, b) for a in po for b in pn)


def maybe_same_slip_loose(o, n):
    """ONLY for the label "may be counted twice" on the Lessons page - never for a uid, a removal or a score. Two rows of
    one kind class within 30 s whose fixes, or whose wrong pieces, share their consonants (any alphabet), or overlap as
    words."""
    if not _class_ok(o, n) or _dt(o, n) > REPEAT_S:
        return False
    return bool(_same_consonants(o.get("right"), n.get("right")) or same_piece(o.get("right"), n.get("right"))
                or any(_same_consonants(a, b) or same_piece(a, b) for a in pieces(o) for b in pieces(n)))


def has_amals_word(o):
    """Amal ruled on this old row (her review tap) or checked it on her Tutor page."""
    refs = o.get("refs") or {}
    return bool(o.get("amal") or refs.get("amal_ruling") or refs.get("amal_check"))


def new_rows(carry=None, preserved=None):
    """The rows full_audit_build would write now (all rulings applied), each with read_key and its final uid."""
    import full_audit_build as FAB
    G = FAB.gather(carry=carry, preserved=preserved, write_report=False)
    keys = [r.get("read_key") for r in G["rows"]]
    FAB.assign_uids(G["rows"], G["carry"])
    for r, k in zip(G["rows"], keys):
        r["read_key"] = k
    return G


NOT_CARRIED = {}       # {date: [...]} filled by carry_entries: Amal-ruled rows whose moment now holds another slip


def carry_entries(old, new):
    """-> (entries for uid-carry.json, matches). A carry entry is written only when the uid would otherwise change."""
    m = match_rows(old, new)
    out = []
    not_carried = carry_entries.not_carried = []
    for i, j, how in m:
        o, n = old[i], new[j]
        if how == "exact" or not n.get("read_key"):
            continue
        if how != "sweep" and has_amals_word(o) and not same_slip(o, n):
            # Codex final approval 2026-10-05, blocker 6: a uid Amal ruled on or checked followed the MOMENT onto another
            # slip (09-04 26:19: she confirmed 'ashan -> 3an', the uid went to a 'did not know سيء' row; 09-10 12:53 her
            # ykoon confirmation went to 'على بيتي -> في بيتي'; 09-16 her checked 'mashufeta' to 'الأسبوع ماضي'). Her word
            # is about one correction: the uid is not carried, the new row takes its own hash, and `kept` keeps the row
            # she confirmed (an old row she rejected is listed there).
            not_carried.append({"old_uid": o["uid"], "how": how, "amal": o.get("amal"),
                                "old": {"t": o.get("t"), "wrong": o.get("wrong"), "right": o.get("right"), "kind": o.get("kind")},
                                "new": {"t": n.get("t"), "wrong": n.get("wrong"), "right": n.get("right"), "kind": n.get("kind")},
                                "new_uid": n.get("uid")})
            continue
        if str(o["uid"]).endswith("x") and not o.get("refs") and not o.get("amal"):
            # an 'x' uid is the second row of one uid base (a repeat the build rejected as a duplicate). Nothing points at
            # it, so there is nothing to keep attached: the new row takes its own hash (a counted row never ends in x)
            continue
        out.append({"old_uid": o["uid"], "read_key": n["read_key"], "how": how,
                    "new_key": {"date": n.get("date"), "t": n.get("t"), "sec": int(sec(n.get("t")) or 0), "wrong": n.get("wrong"),
                                "wrong_norm": norm(n.get("wrong")), "kind_class": kind_class(n.get("kind"))},
                    "new_uid_without_carry": n.get("uid"),
                    "old": {"t": o.get("t"), "wrong": o.get("wrong"), "right": o.get("right"), "kind": o.get("kind")},
                    "new": {"t": n.get("t"), "wrong": n.get("wrong"), "right": n.get("right"), "kind": n.get("kind")}})
    return out, m


def carry(before=None, out=None):
    import full_audit_build as FAB
    B = J(before or BEFORE)
    if not B:
        raise SystemExit("no before.json - run `snapshot` BEFORE the re-read")
    G = new_rows(carry={}, preserved=[])
    by_date = collections.defaultdict(list)
    for r in G["rows"]:
        by_date[r["date"]].append(r)
    lessons, counts = {}, {}
    for d, x in sorted(B["lessons"].items()):
        ent, m = carry_entries(x["rows"], by_date.get(d, []))
        NOT_CARRIED[d] = list(carry_entries.not_carried)
        if ent:
            lessons[d] = ent
        c = collections.Counter(how for _, _, how in m)
        counts[d] = {"old": len(x["rows"]), "new": len(by_date.get(d, [])), **c,
                     "old_without_new": len(x["rows"]) - len(m), "new_without_old": len(by_date.get(d, [])) - len(m)}
    W(out or FAB.CARRY_P, {"about": "Old audit uid -> the re-read row of the same moment (scripts/rehear_rejudge.py carry, 2026-10-04 re-hear). "
                                    "scripts/full_audit_build.py assign_uids gives the row whose read_key is listed the OLD uid, so Amal's "
                                    "rulings, verification records, patterns, duplicates.json and Medi's corrections keep resolving. "
                                    "read_key = the uid the row would get as the readers wrote it. Generated; re-run after any new settle.",
                           "made": now(), "snapshot": B.get("taken"), "counts": counts,
                           "not_carried_amal_ruled_another_slip": {d: v for d, v in sorted(NOT_CARRIED.items()) if v}, "lessons": lessons})
    tot = collections.Counter()
    for c in counts.values():
        tot.update({k: v for k, v in c.items()})
    print("carry:", dict(tot), "->", out or FAB.CARRY_P)
    return lessons, counts


# ---------------------------------------------------------------------------------------------- kept rows
def restore_before_ruling(r):
    """An old row as it was before Amal's ruling (apply_amal_audit_rulings.py puts the ruling back by uid)."""
    x = {k: v for k, v in r.items() if k not in ("line_before", "refs", "amal", "n", "uid", "compat_same_moment_as")}
    ar = x.pop("amal_ruling", None) or {}
    for k, v in (ar.get("before") or {}).items():
        if k in ("kind", "signal", "confidence"):
            if v is None:
                x.pop(k, None)
            else:
                x[k] = v
    x["uid_keep"] = r["uid"]
    x["kept"] = KEPT_MARK
    x["kept_from"] = "first read (before the 2026-10-04 re-hear)"
    return x


def was_scored(o):
    """A row that counted before the re-read: a grammar slip or an A word slip, said by him."""
    return o.get("kind") in ("grammar", "vocab-A") and o.get("mode", "speaking") == "speaking"


def piece_gone(o, line_after):
    """(a): his line's text changed and the row's wrong piece is no longer on the re-heard line - not as the same text,
    and not as the same words in the other alphabet either (a line that was only re-written in Arabic letters still
    holds the piece: that is no mishearing). None when the row quotes no piece that stood on the old line."""
    import lesson_ledger as LL
    w = norm(o.get("wrong"))
    if not w or w not in norm(o.get("line_before")):
        return None
    if (o.get("line_before") or None) == (line_after or None):
        return False
    return w not in norm(line_after) and not LL.still_on_line(str(o.get("wrong")), str(line_after or ""))


def removal_reason(o, new, line_after):
    """Why an old row that is not in the re-read audit may stay out - (code, detail) - or None when nothing explains it.
      a  his line's text changed and the row's wrong piece is no longer on the re-heard line (the mishearing explanation)
      b  the same slip is still in the audit on another row (same_slip, within REPEAT_S, same kind class)
    (c, a human ruling that rejects it, is a row that was already rejected / dropped before: it never counted.)"""
    twin = next((n for n in new if _class_ok(o, n) and _dt(o, n) <= REPEAT_S and same_slip(o, n)), None)
    if twin is not None:
        return "b", {"same_slip_now_on": twin["uid"], "late_pair_with_sweep_row": bool(twin.get("sweep_paired_late"))}
    if piece_gone(o, line_after):
        return "a", {}
    return None


def restore_first_read(o):
    """A formerly scored row the re-read did not write, as it was: old uid, old scoring state, marked."""
    x = {k: v for k, v in o.items() if k not in ("line_before", "refs", "amal", "n", "uid", "compat_same_moment_as", "date_")}
    x["uid_keep"] = o["uid"]
    x["kept"] = RESTORED_MARK
    x["kept_from"] = "first read (before the 2026-10-04 re-hear)"
    return x


def kept_plan(before_lessons, new_by_date, turns_of=None):
    """-> (preserved rows for the build, listing). new_by_date = the new rows WITH the carry applied and no preserved rows.
    Codex final approval round 2, item 2: besides the rows Amal confirmed, every formerly SCORED row the re-read did not
    write again is restored unless its removal has a reason (removal_reason a / b); 'the readers did not write it' or
    'only the retired second pass had it' is not one. Unscored rows that were not written again are listed."""
    turns_of = turns_of or (lambda d: [])
    preserved, listing = [], {"kept_confirmed": [], "restored_first_read": [], "listed_rejected": [], "listed_human_ruling": [], "line_changed": [],
                              "unscored_not_rewritten": []}
    for d, x in sorted(before_lessons.items()):
        new = new_by_date.get(d, [])
        have = {r["uid"]: r for r in new}
        turns = turns_of(d)
        for o in x["rows"]:
            refs = o.get("refs") or {}
            human = bool(refs.get("hand") or refs.get("medi_corrections") or refs.get("medi_correction_applied") or refs.get("duplicates"))
            after = line_at(turns, o.get("t"))
            item = {"date": d, "uid": o["uid"], "t": o.get("t"), "kind": o.get("kind"), "wrong": o.get("wrong"), "right": o.get("right"),
                    "amal": o.get("amal"), "amal_ruling": o.get("amal_ruling"), "line_before": o.get("line_before"), "line_after": after,
                    "line_changed": (o.get("line_before") or None) != (after or None)}
            n = have.get(o["uid"])
            if n is not None:
                if item["line_changed"] and (o.get("amal") or human):
                    listing["line_changed"].append({**item, "new_row": {"t": n.get("t"), "wrong": n.get("wrong"), "right": n.get("right"), "kind": n.get("kind")}})
                continue
            if o.get("amal") == "confirmed":
                preserved.append(restore_before_ruling(o))
                listing["kept_confirmed"].append({**item, "kept": KEPT_MARK})
                continue
            if o.get("amal") == "rejected":
                listing["listed_rejected"].append({**item, "note": "Amal rejected it and the readers did not write it again: nothing to reject"})
                continue
            if was_scored(o):
                why = removal_reason(dict(o, date=d), new, after)
                if why is None:
                    preserved.append(restore_first_read(dict(o, date=d)))
                    listing["restored_first_read"].append({**item, "passes": o.get("passes"), "kept": RESTORED_MARK})
                    continue
                if human:
                    listing["listed_human_ruling"].append({**item, "refs": refs, "removed_because": why[0], **why[1],
                                                           "note": "a hand ruling pointed at this row; the row left for the reason given"})
                continue
            if human:
                listing["listed_human_ruling"].append({**item, "refs": refs, "note": "a hand ruling pointed at this row and the readers did not write it again"})
            listing["unscored_not_rewritten"].append({k: item[k] for k in ("date", "uid", "t", "kind", "wrong", "right", "line_changed")} | {"passes": o.get("passes")})
    listing["restored_per_lesson"] = dict(sorted(collections.Counter(x["date"] for x in listing["restored_first_read"]).items()))
    return preserved, listing


def kept(before=None):
    import full_audit_build as FAB
    B = J(before or BEFORE)
    if not B:
        raise SystemExit("no before.json - run `snapshot` BEFORE the re-read")
    G = new_rows(preserved=[])
    by_date = collections.defaultdict(list)
    for r in G["rows"]:
        by_date[r["date"]].append(r)
    turns_of = lambda d: (J(os.path.join(REPO, "docs", "data", "lessons", d + ".json"), {}) or {}).get("turns", [])
    preserved, listing = kept_plan(B["lessons"], by_date, turns_of)
    W(FAB.PRESERVED_P, {"about": "Rows Amal CONFIRMED that the readers did not write again on the re-heard text (scripts/rehear_rejudge.py "
                                 "kept). scripts/full_audit_build.py keeps them in the audit under their old uid, marked 'kept', in the state "
                                 "before her ruling; apply_amal_audit_rulings.py puts her ruling back. A row is never deleted (RULES.md S6). "
                                 "Generated; re-run `kept` after any new settle / carry.",
                        "made": now(), "rows": preserved})
    W(os.path.join(OUTD, "kept-rows.json"), {"about": "Amal-ruled and hand-ruled rows after the re-read: kept_confirmed = she confirmed it, no new "
                                                      "row, the old row stays; listed_rejected / listed_human_ruling = no new row, nothing to apply; "
                                                      "line_changed = the row was carried but his line's text changed. Nothing here is asked of Amal.",
                                             "made": now(), "counts": {k: len(v) for k, v in listing.items()}, **listing})
    print("kept:", {k: len(v) for k, v in listing.items()}, "->", FAB.PRESERVED_P, "+", os.path.join(OUTD, "kept-rows.json"))
    return preserved, listing


# ---------------------------------------------------------------------------------------------- preflight
def check_hand_rulings(rows, before_rows=(), work=WORK, disputes_of=None):
    """Every hand ruling against the rows the build would write -> [{"file", "ruling", "status", "severity", "detail"}].
    severity: stop = full_audit_build would raise SystemExit; decide = a ruling of a person no longer lands on a row that
    is still there (fix the data file); info = nothing left to rule on / still fine."""
    out = []
    by_uid = {r["uid"]: r for r in rows}
    old_by_uid = {r["uid"]: r for r in before_rows}

    def add(f, ruling, status, severity, detail=None):
        out.append({"file": f, "ruling": ruling, "status": status, "severity": severity, **({"detail": detail} if detail else {})})

    def near(x):
        return [{"uid": r["uid"], "t": r.get("t"), "wrong": r.get("wrong"), "right": r.get("right"), "kind": r.get("kind")}
                for r in rows if r.get("date") == x["date"] and same_moment(r, x)]

    def was(x):          # the old row this ruling landed on, and where that row is now
        o = next((r for r in before_rows if r.get("date") == x["date"] and ruling_hits(r, x)), None)
        return o, (by_uid.get(o["uid"]) if o else None)

    for name in ("rejected.json", "signal-rulings.json"):
        file_rows = (J(os.path.join(work, name), {}) or {}).get("rows", [])
        for i, x in enumerate(file_rows):
            tag = f"#{i} {x['date']} {x.get('t')} {x.get('wrong')}"
            hit = next((r for r in rows if r.get("date") == x["date"] and ruling_hits(r, x)), None)
            # a ruling a person re-pointed (a later row with repointed_from = this row's t + wrong) is answered by that row
            heir = next((j for j, y in enumerate(file_rows) if y is not x and y.get("date") == x["date"]
                         and (y.get("repointed_from") or {}).get("t") == x.get("t") and (y.get("repointed_from") or {}).get("wrong") == x.get("wrong")
                         and any(r.get("date") == y["date"] and ruling_hits(r, y) for r in rows)), None)
            if hit is None and heir is not None:
                add(name, tag, f"re-pointed: row #{heir} of the file carries this ruling to the row's new t / wrong", "info", {"repointed_to": heir})
                continue
            if hit is not None:
                if name == "signal-rulings.json" and "chat-fix" not in (hit.get("signal"), hit.get("signal_before")):
                    add(name, tag, "moot: the row is there and the readers no longer call it chat-only", "info", {"uid": hit["uid"]})
                else:
                    add(name, tag, "resolves", "ok", {"uid": hit["uid"]})
                continue
            o, n = was(x)
            if n is not None and n.get("kind") != "rejected":
                add(name, tag, "NOT APPLIED: the row it ruled on is still in the audit under another wording - add a row to the file "
                    "with the new t / wrong (keep the old row)", "decide",
                    {"uid": n["uid"], "old_wrong": o.get("wrong"), "new_t": n.get("t"), "new_wrong": n.get("wrong"), "new_kind": n.get("kind")})
            elif near(x):
                add(name, tag, "no row with this wrong piece; other rows sit at the moment - read them", "decide" if before_rows else "info", {"at_the_moment": near(x)})
            else:
                add(name, tag, "nothing to rule on: the readers wrote no row at this moment", "info")
    for p in (J(os.path.join(work, "proposed-buckets.json"), {}) or {}).get("proposals", []):
        for x in p.get("rows", []):
            tag = f"{p['id']} {x['date']} {x.get('t')} {x.get('wrong')}"
            if any(r.get("date") == x["date"] and same_moment(r, x) and same_piece(r.get("wrong"), x.get("wrong")) for r in rows):
                add("proposed-buckets.json", tag, "resolves", "ok")
            else:
                add("proposed-buckets.json", tag, "STOPS THE BUILD (SystemExit 'no audit row at ...'): fix the row's t / wrong, or take the "
                    "row out of the proposal with a note", "stop", {"at_the_moment": near(x)})
    for h in (J(os.path.join(work, "duplicates.json"), {}) or {}).get("pairs", []):
        tag = f"{h.get('date')} keep {h['keep']} drop {h['drop']}"
        k, dr = h["keep"] in by_uid, h["drop"] in by_uid
        if k and dr:
            add("duplicates.json", tag, "resolves", "ok")
        elif not k and dr:
            add("duplicates.json", tag, "STOPS THE BUILD (SystemExit 'kept row ... is not in the audit rows'): the kept row left, its repeat stayed", "stop",
                {"old_keep": {kk: (old_by_uid.get(h["keep"]) or {}).get(kk) for kk in ("t", "wrong", "right")}})
        else:
            add("duplicates.json", tag, "nothing to merge: " + ("both rows" if not k else "the repeat") + " left with the re-read", "info")
    import full_audit_compare as C
    hand = (J(os.path.join(work, "self-fix-rulings.json"), {}) or {}).get("rows", [])
    disputes_of = disputes_of or (lambda d: (J(os.path.join(work, d + ".compare.json"), {}) or {}).get("disputes", []))
    for x in hand:
        tag = f"{x['date']} {x.get('pass')} {x.get('ruling')} (his {x.get('his_t')} / her {x.get('her_t')})"
        D = disputes_of(x["date"])
        on = [d["id"] for d in D if C.hand_self_fix(hand, x["date"], 1, d.get("id"), d.get("r1") or d.get("r2") or {}, D) is x]
        if on:
            add("self-fix-rulings.json", tag, "applies to pass-1 dispute " + ", ".join(on) + ("" if on == [x.get("ruling")] and x.get("pass") == "p1" else " (matched by moment; the number moved)"), "ok")
        else:
            add("self-fix-rulings.json", tag, "idle: no pass-1 dispute at this moment now (the readers agreed, or wrote nothing there). "
                "If the audit no longer has the slip, read the moment", "info")
    return out


def orphans(final_uids, repo=REPO):
    """Every stored reference to a uid that the build would not write."""
    out = collections.defaultdict(list)
    for u, x in references(repo).items():
        if u not in final_uids:
            for k in x:
                out[k].append(u)
    return {k: sorted(set(v)) for k, v in out.items()}


def preflight(before=None):
    import full_audit_build as FAB
    B = J(before or BEFORE) or {"lessons": {}}
    before_rows = [r for x in B["lessons"].values() for r in x["rows"]]
    carry_map = FAB.load_carry()
    G = new_rows()
    rows = G["rows"]
    keys = {r.get("read_key") for r in rows}
    final = {r["uid"] for r in rows}
    problems = check_hand_rulings(rows, before_rows)
    stale = sorted(k for k in carry_map if k not in keys)
    for k in stale:
        problems.append({"file": "uid-carry.json", "ruling": f"{k} -> {carry_map[k]}", "severity": "decide",
                         "status": "stale carry entry: no row has this read_key now (settled rows changed after `carry`) - re-run carry"})
    already = set(B.get("already_orphaned") or [])
    orph = {k: [u for u in v if u not in already] for k, v in orphans(final).items()}
    orph = {k: v for k, v in orph.items() if v}
    ruled_gone = [{"uid": r["uid"], "date": r["date"], "t": r.get("t"), "amal": r.get("amal"), "wrong": r.get("wrong")}
                  for r in before_rows if r.get("amal") and r["uid"] not in final]
    conf_gone = [x for x in ruled_gone if x["amal"] == "confirmed"]
    mc = G.get("mc_report") or {}
    p2 = sorted(f for f in os.listdir(WORK) if ".p2." in f or f.endswith(".passes.json"))
    fresh = {}
    try:
        import review_lesson as R
        for d in FAB.DATES:
            why = R.readers_read_current(d)
            if why:
                fresh[d] = why
    except Exception as e:
        fresh = {"error": f"{type(e).__name__}: {e}"}
    stop = [p for p in problems if p["severity"] == "stop"]
    decide = [p for p in problems if p["severity"] == "decide"]
    doc = {"made": now(), "would_stop_build": stop, "to_decide": decide, "info": [p for p in problems if p["severity"] == "info"],
           "resolves": sum(1 for p in problems if p["severity"] == "ok"),
           "amal_confirmed_rows_without_a_row": conf_gone, "amal_rejected_rows_without_a_row": [x for x in ruled_gone if x["amal"] != "confirmed"],
           "references_orphaned_tonight": orph, "medi_corrections": {k: mc.get(k) for k in ("orphaned", "unmatched", "waiting_for_amal")},
           "pass2_files_still_in_place": p2, "readers_not_on_current_text": fresh, "lessons_missing": G.get("missing")}
    W(os.path.join(OUTD, "preflight.json"), doc)
    print(f"preflight: hand rulings resolving {doc['resolves']} | WOULD STOP THE BUILD {len(stop)} | to decide {len(decide)} | info {len(doc['info'])}")
    for p in stop + decide:
        print("  ", p["severity"].upper(), p["file"], p["ruling"], "-", p["status"])
    if conf_gone:
        print(f"   DECIDE {len(conf_gone)} row(s) Amal CONFIRMED have no row - run `python scripts/rehear_rejudge.py kept`:", [x["uid"] for x in conf_gone])
    for k, v in orph.items():
        print(f"   orphaned tonight - {k}: {len(v)}", v[:8], "..." if len(v) > 8 else "")
    if mc.get("orphaned"):
        print("   Medi corrections orphaned:", mc["orphaned"])
    if p2:
        print(f"   {len(p2)} pass-2 files are still merged into the audit (they read the old text) - `retire-pass2 --apply`")
    if fresh:
        print("   readers not on the current text:", fresh)
    print("->", os.path.join(OUTD, "preflight.json"))
    return 1 if (stop or decide or conf_gone or stale) else 0


# ---------------------------------------------------------------------------------------------- report
def report_lesson(before, after_rows, records=(), patterns=(), after_headline=None):
    """One lesson, before vs after. before = the snapshot's lesson; after_rows = the audit rows now."""
    old = {r["uid"]: r for r in before["rows"]}
    new = {r["uid"]: r for r in after_rows}
    same = [u for u in old if u in new]
    moved = [u for u in same if sec(old[u].get("t")) != sec(new[u].get("t")) or norm(old[u].get("wrong")) != norm(new[u].get("wrong"))]
    kept_rows = [u for u in same if new[u].get("kept") == KEPT_MARK]            # Amal-confirmed, kept
    restored_rows = [u for u in same if new[u].get("kept") == RESTORED_MARK]    # formerly scored, not written again, restored
    scored = lambda r: r.get("kind") in ("grammar", "vocab-A") and r.get("mode", "speaking") == "speaking"
    ruled = [u for u in old if old[u].get("amal")]
    not_back = []
    for u in ruled:
        if u in new and old[u].get("amal_ruling") and (new[u].get("amal_ruling") or {}).get("kind") != old[u]["amal_ruling"].get("kind"):
            not_back.append({"uid": u, "t": new[u].get("t"), "was": old[u]["amal_ruling"].get("kind"), "kind_now": new[u].get("kind"),
                             "why": "her ruling is not on the row now (apply_amal_audit_rulings.py not run yet, or the readers now file "
                                    "the row as an A slip / rejected so her tap does not apply)"})
    rec_u = {r["uid"] for r in records if r.get("date") == before.get("date") or r["uid"] in old}
    pat_u = {u for p in patterns for u in (p.get("rows") or []) if u in old}
    held = [r for u, r in new.items() if u not in old]
    hk = lambda r: "A" if scored(r) else "B" if r.get("kind") in ("vocab-B", "grammar-B") else "other"
    return {"rows_before": len(old), "rows_after": len(new),
            "held_from_amal": {"rows": len(held), **{k: sum(1 for r in held if hk(r) == k) for k in ("A", "B", "other")}},
            "scored_before": sum(1 for r in old.values() if scored(r)), "scored_after": sum(1 for r in new.values() if scored(r)),
            "same_uid": len(same), "moved": len(moved), "added": len([u for u in new if u not in old]), "removed": len([u for u in old if u not in new]),
            "kept": len(kept_rows), "restored": len(restored_rows),
            "amal": {"ruled_before": len(ruled), "on_a_row_after": len([u for u in ruled if u in new]) - len(kept_rows),
                     "kept_from_first_read": len(kept_rows), "no_row_after": sorted(u for u in ruled if u not in new),
                     "ruling_not_back": not_back},
            "verification_records": {"uids": len(rec_u & set(old)), "attached": len(rec_u & set(new)), "orphaned": sorted((rec_u & set(old)) - set(new))},
            "patterns": {"uids": len(pat_u), "attached": len(pat_u & set(new)), "orphaned": sorted(pat_u - set(new))},
            "moved_rows": [{"uid": u, "t": [old[u].get("t"), new[u].get("t")], "wrong": [old[u].get("wrong"), new[u].get("wrong")],
                            "how": "carried" if new[u].get("uid_carried_from") else "same"} for u in moved],
            "added_rows": [{"uid": u, "t": new[u].get("t"), "kind": new[u].get("kind"), "wrong": new[u].get("wrong"), "right": new[u].get("right")} for u in new if u not in old],
            "removed_rows": [{"uid": u, "t": old[u].get("t"), "kind": old[u].get("kind"), "wrong": old[u].get("wrong"), "right": old[u].get("right"),
                              "amal": old[u].get("amal"), "refs": old[u].get("refs") or None} for u in old if u not in new],
            "headline": {"before": before.get("headline"), "after": after_headline}}


def report(before=None):
    B = J(before or BEFORE)
    if not B:
        raise SystemExit("no before.json")
    A = J(AUDIT)
    V = (J(os.path.join(REPO, "data", "accuracy", "verifications.json"), {}) or {}).get("records", [])
    P = (J(os.path.join(WORK, "patterns.json"), {}) or {}).get("patterns", [])
    L = {x["date"]: x for x in (J(os.path.join(REPO, "docs", "data", "lessons.json"), {}) or {}).get("lessons", [])}
    by_date = collections.defaultdict(list)
    for r in A["rows"]:
        by_date[r["date"]].append(r)
    out = {}
    for d in sorted(set(B["lessons"]) | set(by_date)):
        b = dict(B["lessons"].get(d) or {"rows": [], "headline": None}, date=d)
        out[d] = report_lesson(b, by_date.get(d, []), V, P, headline(L[d]) if d in L else None)
    already = set(B.get("already_orphaned") or [])
    orph = {k: [u for u in v if u not in already] for k, v in orphans({r["uid"] for r in A["rows"]}).items()}
    orph = {k: v for k, v in orph.items() if v}
    applied = bool(A.get("rulings_applied"))
    import amal_hold
    H = amal_hold.Hold()
    not_held = sorted(r["uid"] for d, x in out.items() for r in x["added_rows"] if not H.uid(r["uid"]))
    doc = {"made": now(), "snapshot": B.get("taken"), "audit_built": A.get("built"), "amal_rulings_reapplied": applied,
           "hold_file": H.active, "created_rows_not_in_the_hold_file": not_held,
           "totals_before": B.get("totals"), "totals_after": A.get("totals"), "orphaned": orph, "lessons": out}
    W(os.path.join(OUTD, "report.json"), doc)
    M = ["# Re-judge on the re-heard transcript - before vs after", "", f"snapshot {B.get('taken')} | audit built {A.get('built')} | "
         + ("Amal's rulings re-applied" if applied else "**Amal's rulings NOT re-applied yet (run apply_amal_audit_rulings.py)**"), "",
         "| lesson | rows | scored | same uid | moved | added | removed | kept (Amal-confirmed) + restored (first-read slip) | held from Amal (A / B / other) | Amal ruled -> on a row / kept / no row / ruling not back | checks orphaned | patterns orphaned | Words % | Grammar % |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, x in out.items():
        hb, ha = (x["headline"]["before"] or {}), (x["headline"]["after"] or {})
        a = x["amal"]
        M.append(f"| {d} | {x['rows_before']} -> {x['rows_after']} | {x['scored_before']} -> {x['scored_after']} | {x['same_uid']} | {x['moved']} | {x['added']} | "
                 f"{x['removed']} | {x['kept']} + {x['restored']} | {x['held_from_amal']['rows']} ({x['held_from_amal']['A']} / {x['held_from_amal']['B']} / {x['held_from_amal']['other']}) | {a['ruled_before']} -> {a['on_a_row_after']} / {a['kept_from_first_read']} / {len(a['no_row_after'])} / {len(a['ruling_not_back'])} | "
                 f"{len(x['verification_records']['orphaned'])} | {len(x['patterns']['orphaned'])} | {hb.get('words_pct')} -> {ha.get('words_pct')} | {hb.get('grammar_pct')} -> {ha.get('grammar_pct')} |")
    M += ["", "## Orphaned references (must be empty, or each one read)", ""] + ([f"- {k}: {', '.join(v)}" for k, v in orph.items()] or ["none"])
    for d, x in out.items():
        a = x["amal"]
        if a["no_row_after"] or a["ruling_not_back"]:
            M += ["", f"## {d} - Amal's rulings to read", ""] + [f"- no row after: {u}" for u in a["no_row_after"]] \
                + [f"- ruling not back: {y['uid']} {y['t']} was {y['was']}, row is now {y['kind_now']}" for y in a["ruling_not_back"]]
    M += [""] + attribution_md(attribution(before))            # Codex 5: removed / added rows by cause
    disp = J(os.path.join(OUTD, "orphan-dispositions.json"))
    if disp:
        M += ["", "## Orphaned references: one disposition each (orphan-dispositions.json)", ""] + [f"- {k}: {v}" for k, v in (disp.get("counts") or {}).items()]
    orv = J(os.path.join(OUTD, "owner-review.json"))
    if orv:
        M += ["", f"## For the owner, not for Amal: {orv.get('new_rows')} re-read B rows at {orv.get('moments')} moments she already ruled on (owner-review.json)", ""]
        M += [f"- {x['date']} {x['mmss']} earlier {x['earlier']['uid']} (Amal: {x['earlier']['amal']}; {x['earlier']['wrong']} -> {x['earlier']['right']}) | new: "
              + "; ".join(f"{n['uid']} {n['t']} {n['wrong']} -> {n['right']}" for n in x["new_rows"]) for x in orv.get("items") or []]
    mr = J(os.path.join(OUTD, "merge-review.json"))
    if mr:
        M += ["", f"## Late merges re-validated (merge-review.json): {mr.get('merged')} still merged, {mr.get('now_split')} now split", ""]
    open(os.path.join(OUTD, "report.md"), "w", encoding="utf-8", newline="\n").write("\n".join(M) + "\n")
    tot = collections.Counter()
    for x in out.values():
        tot.update({k: x[k] for k in ("rows_before", "rows_after", "scored_before", "scored_after", "same_uid", "moved", "added", "removed", "kept", "restored")})
        tot.update({"amal_no_row": len(x["amal"]["no_row_after"]), "amal_ruling_not_back": len(x["amal"]["ruling_not_back"])})
    if not_held:
        print(f"   !! {len(not_held)} row(s) the re-read created are NOT in hold-from-amal.json - run `hold`, then the Amal-facing builders again")
    print("report:", dict(tot), "| orphaned", {k: len(v) for k, v in orph.items()}, "->", os.path.join(OUTD, "report.md"))
    return doc


# ---------------------------------------------------------------------------------------------- the hold + her lists
HOLD_WHY = "created by the re-read of 2026-10-04 on the re-heard transcript; waits for Medi's OK before Amal sees it"
AMAL_JSON = ("docs/data/amal-review.json", "docs/data/amal-verify.json", "docs/data/amal-ledger.json", "docs/data/amal-new-words.json",
             "docs/data/tutor.json")


def git_show(path, ref="origin/master", repo=REPO):
    """The file as published (her live pages are origin/master:/docs), or None when git has no such file."""
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repo, capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def amal_items(path, doc):
    """What one of her files asks of her -> {key: label}. Only OPEN items: an answered item is not a question."""
    out = {}
    name = os.path.basename(path)
    if not isinstance(doc, dict):
        return out
    if name == "amal-review.json":
        for p in doc.get("patterns", []):
            out["pattern " + str(p.get("id"))] = p.get("title")
            for e in p.get("examples", []):
                out["row " + str(e.get("uid"))] = f"{e.get('date')} {e.get('mmss')} {e.get('wrong')} -> {e.get('right')} (in {p.get('id')})"
        for w in doc.get("new_words", []):
            out["word " + str(w.get("id"))] = w.get("arabic")
            for m in w.get("moments", []):
                out[f"word-moment {w.get('id')} {m.get('date')} {m.get('mmss')}"] = w.get("arabic")
    elif name == "amal-verify.json":
        for x in doc.get("items", []):
            out["verify " + str(x.get("uid"))] = f"{x.get('date')} {x.get('t')} {x.get('wrong')} -> {x.get('right')}"
    elif name == "amal-ledger.json":
        for x in doc.get("items", []):
            out["card " + str(x.get("id"))] = f"{x.get('date')} {x.get('mmss')} {x.get('question')}"
    elif name == "amal-new-words.json":
        for k in ("items", "taught", "promised"):
            for x in doc.get(k) or []:
                if isinstance(x, dict) and x.get("status", "open") == "open" and not x.get("answered_at"):
                    out[f"{k} " + str(x.get("id") or (x.get("date"), x.get("key") or x.get("arabic")))] = f"{x.get('date')} {x.get('arabic')}"
    elif name == "tutor.json":
        for x in doc.get("open", []):
            out["open " + str(x.get("id"))] = x.get("title")
    return out


def amal_diff_docs(before, after):
    """{path: text or None} x 2 -> {"added": [...], "removed": [...], "changed_pages": [...]} (pure; for the test)."""
    added, removed, pages = [], [], []
    for path in sorted(set(before) | set(after)):
        b, a = before.get(path), after.get(path)
        if path.endswith(".json"):
            ib = amal_items(path, json.loads(b) if b else {})
            ia = amal_items(path, json.loads(a) if a else {})
            added += [{"file": path, "item": k, "what": ia[k]} for k in ia if k not in ib]
            removed += [{"file": path, "item": k, "what": ib[k]} for k in ib if k not in ia]
        elif (b or "").replace("\r\n", "\n") != (a or "").replace("\r\n", "\n"):
            pages.append({"file": path, "state": "new page" if b is None else "deleted" if a is None else "changed"})
            if b is None:
                added.append({"file": path, "item": "page", "what": "a page she did not have"})
    return {"added": added, "removed": removed, "changed_pages": pages}


def amal_diff(ref="origin/master", repo=REPO):
    """Her lists in the working tree vs what is published. Exit 1 when anything was ADDED for her."""
    paths = list(AMAL_JSON)
    adir = os.path.join(repo, "docs", "amal")
    paths += sorted("docs/amal/" + f for f in os.listdir(adir) if f.endswith(".html"))
    ls = subprocess.run(["git", "ls-tree", "--name-only", ref, "docs/amal/"], cwd=repo, capture_output=True, text=True)
    if ls.returncode:
        raise SystemExit(f"amal-diff: cannot read {ref} ({ls.stderr.strip()[:200]}) - nothing was compared; do not push")
    paths = sorted(set(paths) | {x for x in ls.stdout.split() if x.endswith(".html")})
    read = lambda p: open(os.path.join(repo, p), encoding="utf-8").read() if os.path.exists(os.path.join(repo, p)) else None
    doc = amal_diff_docs({p: git_show(p, ref, repo) for p in paths}, {p: read(p) for p in paths})
    doc = {"made": now(), "against": ref, **doc}
    W(os.path.join(OUTD, "amal-diff.json"), doc)
    print(f"amal-diff vs {ref}: ADDED for Amal {len(doc['added'])} | removed {len(doc['removed'])} | pages changed {len(doc['changed_pages'])}")
    for x in doc["added"]:
        print("   ADDED  ", x["file"], "|", x["item"], "|", x["what"])
    for x in doc["removed"]:
        print("   removed", x["file"], "|", x["item"], "|", x["what"])
    for x in doc["changed_pages"]:
        print("   page   ", x["file"], x["state"], "(read the diff: `git diff %s -- %s`)" % (ref, x["file"]))
    return 1 if doc["added"] else 0


def hold_doc(before_lessons, audit_rows, published):
    """published = {path: text or None} of her lists as she sees them now (origin/master)."""
    known = {r["uid"] for x in before_lessons.values() for r in x["rows"]}
    rows = [{"uid": r["uid"], "date": r.get("date"), "t": r.get("t"), "kind": r.get("kind"), "wrong": r.get("wrong"), "right": r.get("right"),
             "why": HOLD_WHY} for r in audit_rows if r["uid"] not in known]
    P = {os.path.basename(k): (json.loads(v) if v else None) for k, v in published.items()}
    rv, vf, lg = P.get("amal-review.json"), P.get("amal-verify.json"), P.get("amal-ledger.json")
    before = {
        "review": sorted({e["uid"] for k in ("patterns", "answered") for p in rv.get(k, []) for e in p.get("examples", [])}) if rv else None,
        "new_words": sorted(w["id"] for w in rv.get("new_words", [])) if rv else None,
        "verify": sorted({x["uid"] for k in ("items", "answered") for x in vf.get(k, [])}) if vf else None,
        "ledger": sorted({x["conflict"] for k in ("items", "answered") for x in lg.get(k, []) if x.get("conflict")}) if lg else None}
    return {"about": "Rows the 2026-10-04 re-read created (not in rehear/rejudge/before.json) + what was on Amal's lists before it. While "
                     "this file exists her lists (amal-review.json, amal-verify.json, amal-ledger.json) show only what they showed before "
                     "(scripts/amal_hold.py). The rows count on Medi's own pages as the build decides. Medi's OK = delete this file.",
            "made": now(), "why": HOLD_WHY, "dates": sorted(before_lessons), "uids": [r["uid"] for r in rows], "rows": rows, "before": before}


def hold(before=None, ref="origin/master"):
    import amal_hold
    B = J(before or BEFORE)
    if not B:
        raise SystemExit("no before.json - run `snapshot` BEFORE the re-read")
    pub = {p: git_show(p, ref) for p in AMAL_JSON[:3]}
    missing = [p for p, v in pub.items() if v is None]
    if missing:
        raise SystemExit(f"hold: cannot read {missing} from {ref} - her lists before the re-read are unknown; nothing written")
    # the rows the build WOULD write (in memory, carry + kept rows applied), so the hold exists before the first real build
    doc = hold_doc(B["lessons"], new_rows()["rows"], pub)
    W(amal_hold.HOLD_P, doc)
    c = collections.Counter(r["kind"] for r in doc["rows"])
    print(f"hold: {len(doc['uids'])} rows created by the re-read are held from Amal {dict(c)} | her lists before: "
          + ", ".join(f"{k} {len(v)}" for k, v in doc["before"].items()) + " -> " + amal_hold.HOLD_P)
    return doc


# ---------------------------------------------------------------------------------------------- prompts + accept
AGENT_NOTE = (" You are running as an agent inside this repo, not as `claude -p`: every relative path in this prompt and in the "
              "brief is relative to {repo}. Write ONLY the one JSON file named above ({out}), as UTF-8; create, edit or delete "
              "no other file, run no script, make no commit, call no network service, and send nothing to anyone.")


def reader_inputs(date, reader, repo=REPO):
    """Exactly the input lists scripts/review_lesson.py main() pins (reader_in / third_in)."""
    work = os.path.join(repo, "data", "lesson-work", "full-audit")
    f = lambda name: os.path.join(work, f"{date}{name}")
    common = [os.path.join(work, "buckets.md"), os.path.join(repo, "RULES.md"), os.path.join(repo, "docs", "data", "names.json")]
    if reader == "r3":
        return [f(".txt"), f(".disputes.md"), f(".r1.json"), f(".r2.json"), os.path.join(work, "THIRD-READER-BRIEF.md")] + common
    return [f(".txt"), os.path.join(work, "READER-BRIEF.md"), os.path.join(work, "amal-sheet.txt")] + common


def base_prompt(date, reader):
    import review_lesson as R        # import only: nothing in it runs until claude() is called, and it is never called here
    return R.third_prompt(date) if reader == "r3" else R.reader_prompt(date, reader)


def agent_prompt(date, reader):
    import review_lesson as R
    out = os.path.join(R.WORK, f"{date}.{reader}.json")
    p = base_prompt(date, reader).replace("data/lesson-work/full-audit/", R.WORK + os.sep)
    return p + AGENT_NOTE.format(repo=R.REPO, out=out)


def prompts(date, readers=("r1", "r2", "r3")):
    d = os.path.join(OUTD, "prompts")
    os.makedirs(d, exist_ok=True)
    for r in readers:
        if r == "r3" and not os.path.exists(os.path.join(WORK, f"{date}.disputes.md")):
            print("note: no", f"{date}.disputes.md yet - run `full_audit_compare.py compare {date}` before the r3 agent")
        p = os.path.join(d, f"{date}.{r}.txt")
        open(p, "w", encoding="utf-8", newline="\n").write(agent_prompt(date, r) + "\n")
        print(p)


def accept(date, reader, before=None):
    """Validate an agent-written reader file and pin its manifest the way review_lesson.py does after a claude -p run, so
    review_lesson.cache_decision says 'fresh' and readers_read_current(date) says None."""
    import review_lesson as R, accuracy_gates as G
    out = os.path.join(R.WORK, f"{date}.{reader}.json")
    kind = "third" if reader == "r3" else "reader"
    if not os.path.exists(out):
        print("no file:", out); return 1
    if not R.valid_reader_file(out, date, kind=kind):
        print("NOT accepted - broken reader file (not whole JSON for this lesson, or its list is missing):", out); return 1
    doc = json.load(open(out, encoding="utf-8"))
    if doc.get("reader") not in (None, reader):
        print(f"NOT accepted - the file says reader {doc.get('reader')!r}, expected {reader!r}"); return 1
    was = ((((J(before or BEFORE) or {}).get("lessons") or {}).get(date) or {}).get("files") or {}).get(f".{reader}.json")
    if was and was == sha_file(out):
        print("NOT accepted - this is the file from BEFORE the re-read (same bytes as the snapshot); the agent has not written it"); return 1
    inputs = reader_inputs(date, reader, R.REPO)
    missing = [p for p in inputs if not os.path.exists(p)]
    if missing:
        print("NOT accepted - inputs missing:", missing); return 1
    if reader == "r3":
        C = J(os.path.join(R.WORK, f"{date}.compare.json")) or {}
        ids = {d.get("id") for d in C.get("disputes", [])}
        ruled = {x.get("id") for x in doc.get("rulings", [])}
        if os.path.getmtime(os.path.join(R.WORK, f"{date}.compare.json")) < max(os.path.getmtime(os.path.join(R.WORK, f"{date}.{r}.json")) for r in ("r1", "r2")):
            print("NOT accepted - compare.json is older than r1 / r2: run compare, then the r3 agent again"); return 1
        if ids - ruled:
            print("warning: disputes with no ruling (settle keeps a both-readers row, drops a one-reader row):", sorted(ids - ruled, key=lambda s: int(s[1:]) if s[1:].isdigit() else 0))
        if ruled - ids:
            print("NOT accepted - rulings for disputes that do not exist (it read another disputes file):", sorted(ruled - ids)); return 1
    prompt = base_prompt(date, reader)
    pf = os.path.join(OUTD, "prompts", f"{date}.{reader}.txt")
    G.write_manifest(out, inputs, repo=R.REPO, extra={
        "prompt_sha": R._prompt_sha(prompt),
        "written_by": "a Claude agent given rehear/rejudge/prompts/%s.%s.txt (scripts/rehear_rejudge.py accept), not claude -p" % (date, reader),
        "agent_prompt_sha256": sha_file(pf)})
    st = R.cache_decision(out, inputs, prompt, legacy_ok=False)
    cur = R.readers_read_current(date) if reader == "r1" else None
    n = len(doc.get("rows") or doc.get("rulings") or [])
    print(f"accepted {os.path.basename(out)}: {n} {'rulings' if reader == 'r3' else 'rows'} | cache {st}" + (f" | readers_read_current: {cur or 'current'}" if reader == "r1" else ""))
    return 0 if st == "fresh" and not cur else 1


# ---------------------------------------------------------------------------------------------- pass 2
def pass2_files(work=WORK):
    return sorted(f for f in os.listdir(work) if os.path.isfile(os.path.join(work, f)) and (".p2." in f or f.endswith(".passes.json")))


def retire_pass2(apply=False, work=WORK, dest=None):
    """The 13 older lessons have a second reader pass (<date>.p2.*) that read the transcript as it was on 2026-09-26.
    full_audit_compare.union_rows merges its rows into the audit and accuracy_gates compares the two passes. After the
    re-read pass 1 is on the new text and pass 2 on the old one, so they are moved (never deleted) to
    superseded-2026-10-04/; with the files gone union_rows / pass_log / accuracy_gates.pass_numbers see ONE pass and the
    release status says so ('pass 1 n %; 2 consecutive passes at >= 95 % are needed')."""
    dest = dest or os.path.join(work, os.path.basename(SUPERSEDED))
    files = pass2_files(work)
    print(("moving" if apply else "would move"), len(files), "files ->", dest)
    if not apply:
        for f in files:
            print("  ", f)
        return files
    os.makedirs(dest, exist_ok=True)
    for f in files:
        shutil.move(os.path.join(work, f), os.path.join(dest, f))
    W(os.path.join(dest, "README.json"), {
        "about": "Second reader pass of 13 lessons (2026-09-26 backfill) + the pass-1-vs-pass-2 agreement files. They read the transcript "
                 "BEFORE the 2026-10-04 re-hear, so they are no longer merged into the audit or compared with the re-read pass 1. Kept, "
                 "not deleted. A new second pass on the re-heard text would be written to <date>.p2.* in the folder above.",
        "moved": now(), "files": files})
    return files


# ---------------------------------------------------------------------------------------------- why a row left / came
CAUSES = {
    "1": "existed only in the retired second reader pass (13 older lessons; that pass read the text of 2026-09-26)",
    "2": "his line's text changed at that spot: the second listen removed or changed the quoted wrong piece (a likely false slip from a mishearing)",
    "3": "the line did not change there: the readers simply did not write it this time (reader variance)",
    "4": "not gone: the same slip is still in the audit on another row (merged - late pairing with the 09-24 sweep row, or one slip written once)",
    "c": "a human ruling had rejected it (Amal on her Tutor page) and the readers did not write it again",
}


def attribution(before=None, out=None):
    """Codex final approval 2026-10-05, blocker 5: every row the re-read removed and every row it added, by cause -
    rehear/rejudge/removed-rows-by-cause.json. A removed row gets ONE cause, tested in this order: 4 (its slip is still
    there on another row), 2 (his line changed and the wrong piece is no longer on it), c (a scored row Amal had
    rejected), 1 (retired second pass only), 3 (all the rest: the readers did not write it again). Round 2: causes 1
    and 3 hold no formerly scored row - those are restored by `kept`. Each row also says whether its line changed."""
    B = J(before or BEFORE)
    A = J(AUDIT)
    new_by_date = collections.defaultdict(list)
    for r in A["rows"]:
        new_by_date[r["date"]].append(r)
    turns_of = lambda d: (J(os.path.join(REPO, "docs", "data", "lessons", d + ".json"), {}) or {}).get("turns", [])
    rows_out, added_out, per = [], [], {}

    def turn_at(turns, t, who="Medi"):
        """His line that holds lesson time t (the latest line of his that starts by t + 1 s)."""
        tt = sec(t)
        if tt is None:
            return None
        c = [u for u in turns if u.get("who") == who and float(u["t"]) <= tt + 1.0]
        return max(c, key=lambda u: float(u["t"])) if c else None

    for d, x in sorted(B["lessons"].items()):
        new = new_by_date.get(d, [])
        have = {r["uid"] for r in new}
        turns = turns_of(d)
        c = collections.Counter()
        for o in x["rows"]:
            if o["uid"] in have:
                continue
            after = line_at(turns, o.get("t"))
            line_changed = (o.get("line_before") or None) != (after or None)
            gone = piece_gone(o, after)
            twin = next((n for n in new if n.get("uid") != o["uid"] and _class_ok(o, n) and _dt(o, n) <= REPEAT_S and same_slip(o, n)), None)
            if twin is not None:
                cause, detail = "4", {"same_slip_now_on": twin["uid"], "late_pair_with_sweep_row": bool(twin.get("sweep_paired_late"))}
            elif gone:
                cause, detail = "2", {}
            elif was_scored(o) and o.get("amal") == "rejected":
                cause, detail = "c", {"note": "Amal rejected it on her Tutor page before the re-read; the readers did not write it again"}
            elif o.get("passes") == [2]:
                cause, detail = "1", {"old_line": "changed by the re-hear" if line_changed else "unchanged"}
            else:
                cause, detail = "3", ({"note": "the line changed elsewhere; the quoted piece is still on it"} if line_changed and gone is False
                                      else {"note": "the line changed; the row quotes no piece of his that could be checked on it"} if line_changed else {})
            c[cause] += 1
            if cause == "1":
                c["1_line_changed" if line_changed else "1_line_unchanged"] += 1
            if was_scored(o):
                c["scored_" + cause] += 1
            rows_out.append({"date": d, "uid": o["uid"], "t": o.get("t"), "kind": o.get("kind"), "bucket": o.get("bucket"), "wrong": o.get("wrong"), "was_scored": was_scored(o),
                             "right": o.get("right"), "passes": o.get("passes"), "amal": o.get("amal"), "cause": cause, "line_changed": line_changed,
                             "wrong_piece_gone_from_line": gone, **detail, "old_line": o.get("line_before"), "new_line": after})
        old_u = {o["uid"] for o in x["rows"]}
        for n in new:
            if n["uid"] in old_u:
                continue
            u = turn_at(turns, n.get("t"))
            ch = bool(u and any(str(h.get("by") or "").startswith("gemini") for h in (u.get("heard") or [])))
            c["a" if ch else "b"] += 1
            added_out.append({"date": d, "uid": n["uid"], "t": n.get("t"), "kind": n.get("kind"), "bucket": n.get("bucket"), "wrong": n.get("wrong"),
                              "right": n.get("right"), "on": "a" if ch else "b", "line": u.get("text") if u else None,
                              "engine_line": u.get("engine") if u else None})
        per[d] = {"removed": sum(c[k] for k in "1234c"), **{"cause_" + k: c[k] for k in "1234c"}, **{"scored_cause_" + k: c["scored_" + k] for k in "1234c"},
                  "restored_first_read": sum(1 for n in new if n.get("kept") == RESTORED_MARK), "cause_1_line_unchanged": c["1_line_unchanged"],
                  "cause_1_line_changed": c["1_line_changed"], "added": c["a"] + c["b"], "added_on_changed_line": c["a"], "added_on_unchanged_line": c["b"]}
    tot = collections.Counter()
    for v in per.values():
        tot.update(v)
    doc = {"made": now(), "snapshot": B.get("taken"), "audit_built": A.get("built"),
           "about": "Every audit row the 2026-10-04 re-read removed (old uid no longer in the audit) and every row it added, by cause. "
                    "One cause per removed row, tested in the order 4, 2, c, 1, 3. Added rows: a = on a line the second listen changed, "
                    "b = on a line it did not change.",
           "causes": CAUSES, "added_kinds": {"a": "on a line the second listen changed", "b": "on a line the second listen did not change"},
           "totals": dict(tot), "per_lesson": per, "removed": rows_out, "added": added_out}
    W(out or os.path.join(OUTD, "removed-rows-by-cause.json"), doc)
    print("removed %d: retired pass 2 only %d (line unchanged %d / changed %d) | line changed, piece gone %d | reader variance %d | same slip on another row %d || added %d: on a changed line %d, unchanged %d" % (
        tot["removed"], tot["cause_1"], tot["cause_1_line_unchanged"], tot["cause_1_line_changed"], tot["cause_2"], tot["cause_3"], tot["cause_4"],
        tot["added"], tot["added_on_changed_line"], tot["added_on_unchanged_line"]))
    return doc


def attribution_md(doc):
    """The table for report.md."""
    md = ["## Removed and added rows, by cause (removed-rows-by-cause.json)", "",
          "Removed = an old uid no longer in the audit. One cause per row, tested in this order: 4, 2, c, 1, 3.", "",
          "- 1 = " + CAUSES["1"], "- 2 = " + CAUSES["2"], "- 3 = " + CAUSES["3"], "- 4 = " + CAUSES["4"], "- c = " + CAUSES["c"], "",
          "| lesson | removed | 1 retired pass 2 only (line unchanged / changed) | 2 line changed, piece gone | 3 reader variance | 4 same slip on another row | c ruled out by Amal | added | a on a changed line | b on an unchanged line |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda v: "| %d | %d (%d / %d) | %d | %d | %d | %d | %d | %d | %d |" % (v.get("removed", 0), v.get("cause_1", 0), v.get("cause_1_line_unchanged", 0), v.get("cause_1_line_changed", 0),  # noqa: E731
                                                                      v.get("cause_2", 0), v.get("cause_3", 0), v.get("cause_4", 0), v.get("cause_c", 0), v.get("added", 0),
                                                                      v.get("added_on_changed_line", 0), v.get("added_on_unchanged_line", 0))
    for d, v in sorted(doc["per_lesson"].items()):
        md.append("| %s %s" % (d, f(v)))
    md.append("| **all** %s" % f(doc["totals"]))
    t = doc["totals"]
    md += ["", "Formerly SCORED rows (grammar / vocab-A) among the removed: cause 1: %d, cause 2: %d, cause 3: %d, cause 4: %d, cause c: %d. "
           "Round 2 (2026-10-05): a scored row leaves only for cause 2 (his line changed, the wrong piece is gone), cause 4 (the same "
           "correction is on another row) or cause c (Amal had rejected it); every other one is restored - %d rows kept as 'first-read slip' (kept-rows.json restored_first_read). "
           "Causes 1 and 3 hold only rows that never counted (B rows, rejected, dropped, proposals)." % (
               t.get("scored_cause_1", 0), t.get("scored_cause_2", 0), t.get("scored_cause_3", 0), t.get("scored_cause_4", 0), t.get("scored_cause_c", 0), t.get("restored_first_read", 0))]
    return md


# ---------------------------------------------------------------------------------------------- orphans, one by one
RETIRED_WHY = {
    "c": "retired: Amal had rejected the row on her Tutor page and the readers did not write it again",
    "1": "retired: the row existed only in the retired second reader pass (it read the text of 2026-09-26)",
    "2": "retired: the readers did not write it on the re-heard text - his line changed there and the quoted wrong piece is no longer on it",
    "3": "retired: the readers did not write it on the re-heard text (the line did not change at that piece)",
}
REF_WORDS = {"verifications": "verification record(s) in data/accuracy/verifications.json", "patterns": "pattern row in full-audit/patterns.json",
             "ai_rules": "row list of one of Amal's rules in docs/data/ai_rules.json", "amal_grammar_notes": "uid named in scripts/amal_grammar_notes.py",
             "amal_check": "Amal's Tutor-page check (a human record in verifications.json)", "duplicates": "keep / drop uid in full-audit/duplicates.json"}
# The six hand rulings preflight lists under "to decide" (their wrong piece is on no row; other rows sit at the moment).
# Read one by one on 2026-10-05 against the rows at each moment (Claude; a person may overrule by adding a row to the file).
TO_DECIDE_READ = {
    "rejected.json #25 2026-09-16 23:50 bi il AI": ("retired", "the chat-only fix 'bi il AI -> fi el-AI' was not written again; the row at the moment (23:44 أنا كان -> أنا كنت) is another slip. Nothing to reject."),
    "rejected.json #40 2026-09-21 19:20 أمريكي": ("retired", "the chat-only fix 'أمريكي -> أمريكا' was not written again; the row at the moment (19:26 حكينا -> بنحكي) is another slip. Nothing to reject."),
    "rejected.json #45 2026-09-21 49:00 أساهم": ("retired", "the chat-only fix 'أساهم -> بستعمل' was not written again; the two rows at 49:00 are about المقلاة / الملعقة, another slip. Nothing to reject."),
    "rejected.json #47 2026-09-21 50:29 fi darajat": ("retired", "the chat-only fix 'fi darajat -> bidarjet 7araara' was not written again; the row at 50:29 (قصير -> واطية) is the word she voiced, which the ruling itself says is not the bi- fix. Nothing to reject."),
    "signal-rulings.json #0 2026-09-16 48:52 ili amalti": ("mapped", "the same slip is row FA-8c7f9a21 (48:51 عملتي -> عملت(ي), his 'So ili amalti'); the readers filed it with her VOICED signal 'recast' already, which is all the ruling asks. No new row is needed; if a later read files it as chat-fix, add a row with t 48:51 / wrong عملتي."),
    "signal-rulings.json #3 2026-09-21 52:31 ma'rufin al tahet": ("retired", "the slip 'ma'rufin al tahet' (ma3roofeen bi-) was not written again; the row at the moment (52:26 إحنا إيرانيين -> إحنا الإيرانيين) is another slip. Nothing to re-signal."),
}


def orphan_dispositions(before=None, out=None):
    """Council 5 / Codex 6: every reference that points at a uid the audit no longer holds gets ONE explicit line -
    mapped (the same slip is still in the audit on another row: which, why) or retired (the row is gone: why).
    Nothing is rewritten in the reference files (a ruling row is never deleted); this is the record of what each
    dangling reference now means. Also the six hand rulings preflight lists as 'to decide'. Needs report.json and
    removed-rows-by-cause.json (run `report` first)."""
    B = J(before or BEFORE)
    A = J(AUDIT)
    rep = J(os.path.join(OUTD, "report.json")) or {}
    cause = {(r["date"], r["uid"]): r for r in (J(os.path.join(OUTD, "removed-rows-by-cause.json")) or {}).get("removed", [])}
    old = {r["uid"]: dict(r, date=d) for d, x in B["lessons"].items() for r in x["rows"]}
    new = {r["uid"]: r for r in A["rows"]}
    refs = references()
    rows = []
    for kind, uids in sorted((rep.get("orphaned") or {}).items()):
        for u in uids:
            o = old.get(u)
            base = {"reference": kind, "reference_is": REF_WORDS.get(kind, kind), "uid": u, "what_points_at_it": refs.get(u, {}).get(kind)}
            if o is None:
                rows.append({**base, "disposition": "retired", "why": "retired: this uid was not a row in the snapshot taken before the re-read either"})
                continue
            base.update(date=o["date"], t=o.get("t"), kind=o.get("kind"), wrong=o.get("wrong"), right=o.get("right"), amal=o.get("amal"))
            c = cause.get((o["date"], u))
            if c and c["cause"] == "4":
                n = new[c["same_slip_now_on"]]
                rows.append({**base, "disposition": "mapped", "mapped_to": n["uid"],
                             "why": "mapped: the same slip is still in the audit as %s (%s, %s -> %s%s); the reference keeps its meaning there" % (
                                 n["uid"], n.get("t"), n.get("wrong"), n.get("right"), ", paired late with the 09-24 sweep row" if c.get("late_pair_with_sweep_row") else "")})
            elif c:
                extra = ""
                if o.get("amal") == "rejected":
                    extra = " Amal had rejected it: there is nothing left to reject."
                elif kind in ("patterns", "ai_rules"):
                    extra = " The pattern / rule itself stays; it simply lists one row fewer that exists."
                elif kind == "verifications":
                    extra = " The record stays in the ledger as history; it settles no row now."
                rows.append({**base, "disposition": "retired", "why": RETIRED_WHY[c["cause"]] + "." + extra, "cause": c["cause"]})
            else:
                rows.append({**base, "disposition": "retired", "why": "retired: the row is not in the audit and not in the removed list (a duplicate 'x' uid the build no longer writes)"})
    P = J(os.path.join(OUTD, "preflight.json")) or {}
    decide = []
    for x in P.get("to_decide") or []:
        key = "%s %s" % (x["file"], x["ruling"])
        d, why = TO_DECIDE_READ.get(key, (None, None))
        decide.append({"ruling": key, "rows_at_the_moment": (x.get("detail") or {}).get("at_the_moment"), "disposition": d or "open", "why": why or "not read yet",
                       "read_by": "Claude 2026-10-05 (a person may overrule by adding a row to the ruling file)" if d else None})
    counts = collections.Counter("%s: %s" % (r["reference"], r["disposition"]) for r in rows)
    doc = {"made": now(), "about": "One explicit disposition for every reference that points at an audit uid the re-read removed (report.json "
                                   "'orphaned'), and for the six hand rulings preflight lists as 'to decide'. mapped = the same slip is still in the "
                                   "audit on the row named; retired = the row is gone, with the reason. No reference file was rewritten.",
           "counts": dict(sorted(counts.items())), "hand_rulings_to_decide": decide, "rows": rows}
    W(out or os.path.join(OUTD, "orphan-dispositions.json"), doc)
    print("orphan dispositions: %d references -> %s | to decide: %s" % (len(rows), dict(collections.Counter(r["disposition"] for r in rows)),
                                                                        dict(collections.Counter(x["disposition"] for x in decide))))
    return doc


# ---------------------------------------------------------------------------------------------- spot-check lines taken out
def spot_withheld(out=None):
    """Codex round 2, item 1: the proposed lines the blind spot check judged against are not applied (rehear_apply.plan
    'withheld_by_spot_check'). The readers read the re-heard version of those lines, so an audit row may quote words
    that are no longer on the delivered line. This lists every withheld line and every audit row at its moment whose
    wrong piece, or whose quote of his line, holds a word that only the re-heard version had. Nothing is edited: a slip
    is never invented or removed here."""
    A = J(AUDIT)
    lines, rows = [], []
    for d in sorted(os.listdir(os.path.join(REPO, "data", "lesson-work", "rehear"))):
        P = J(os.path.join(REPO, "data", "lesson-work", "rehear", d, "apply-plan.json")) if re.fullmatch(r"\d{4}-\d\d-\d\d", d) else None
        for x in (P or {}).get("withheld_by_spot_check") or []:
            lines.append({"date": d, "mmss": x["mmss"], "t": x["t"], "old_line_delivered": x["engine"], "reheard_line_not_applied": x["heard"], "votes": x.get("votes")})
            only = set(norm(x["heard"]).split()) - set(norm(x["engine"]).split())
            for r in A["rows"]:
                tt = [v for v in (sec(r.get("t")), sec(r.get("t_amal"))) if v is not None]
                if r["date"] != d or not any(abs(v - x["t"]) <= 12 for v in tt):
                    continue
                in_wrong = bool(only & set(norm(r.get("wrong")).split()))
                in_quote = bool(only & set(norm(r.get("medi_said")).split()))
                if not (in_wrong or in_quote):
                    continue
                rows.append({"date": d, "line": x["mmss"], "uid": r["uid"], "t": r.get("t"), "kind": r.get("kind"), "bucket": r.get("bucket"),
                             "wrong": r.get("wrong"), "right": r.get("right"), "medi_said": r.get("medi_said"),
                             "reheard_only_words": sorted(only), "in_the_wrong_piece": in_wrong, "in_the_quote_of_his_line": in_quote,
                             "how_the_build_treats_it": ("the row stays as the readers wrote it and counts as before (kind %s); nothing in the build "
                                                         "re-checks a row against a line that went back to the engine's text. %s" % (
                                                             r.get("kind"), "Its wrong piece exists only in the re-heard version of the line: it needs Medi's ear "
                                                             "on that line (the 'old or new' card) before it can be trusted." if in_wrong
                                                             else "Only its quote of his line carries the re-heard word; the wrong piece itself is not on the withheld line."))})
    doc = {"made": now(), "about": "Proposed second-listen lines that the blind spot check judged against (verdict 'old text'): not applied, the engine's "
                                   "line is delivered, each waits on Medi's listen page as 'old or new'. And the audit rows that quote a word only the "
                                   "re-heard version had. The readers of these lessons read the re-heard version of these lines (the publish guard's "
                                   "advisory review_freshness says so).",
           "lines": len(lines), "withheld": lines, "audit_rows_quoting_only_the_reheard_text": rows}
    W(out or os.path.join(OUTD, "spot-withheld.json"), doc)
    print("spot-withheld: %d lines; %d audit rows quote a re-heard-only word (%d in the wrong piece)" % (len(lines), len(rows), sum(r["in_the_wrong_piece"] for r in rows)))
    return doc


# ---------------------------------------------------------------------------------------------- repeat-review hold
ALREADY_P = os.path.join(WORK, "amal-already-ruled.json")


def already_ruled_plan(before_lessons, audit_rows, window=5.0):
    """-> [item]: per moment Amal ruled on whose old uid no re-read row carries (the old row is gone, or stays only as a
    kept row), the re-read B rows (a uid that was not in the snapshot) of the same lesson within `window` seconds of it.
    Proximity ONLY: nothing is said here about the rows being the same slip."""
    by = collections.defaultdict(list)
    for r in audit_rows:
        by[r["date"]].append(r)
    old_uids = {r["uid"] for x in before_lessons.values() for r in x["rows"]}
    items = []
    for d, x in sorted(before_lessons.items()):
        now = {r["uid"]: r for r in by.get(d, [])}
        for o in x["rows"]:
            n = now.get(o["uid"])
            if not has_amals_word(o) or (n is not None and not n.get("kept")) or sec(o.get("t")) is None:
                continue                                   # nobody's word on it, or a re-read row carries the uid (her ruling is on it)
            near = [r for r in by.get(d, []) if r["uid"] not in old_uids and r.get("kind") in ("vocab-B", "grammar-B")
                    and sec(r.get("t")) is not None and abs(sec(r["t"]) - sec(o["t"])) <= window]
            if near:
                items.append({"date": d, "mmss": o.get("t"),
                              "earlier": {"uid": o["uid"], "amal": o.get("amal"), "amal_ruling": o.get("amal_ruling"), "kind": o.get("kind"),
                                          "wrong": o.get("wrong"), "right": o.get("right"), "in_the_audit_now": "kept" if n is not None else "no row"},
                              "new_rows": [{"uid": r["uid"], "t": r.get("t"), "kind": r.get("kind"), "bucket": r.get("bucket"), "wrong": r.get("wrong"),
                                            "right": r.get("right"), "medi_said": r.get("medi_said"), "amal_said": r.get("amal_said")} for r in near]})
    return items


def already_ruled(before=None):
    """Codex final approval round 5: the repeat-review hold. Writes full-audit/amal-already-ruled.json (the uids her
    list builders skip, scripts/amal_hold.AlreadyRuled) and rehear/rejudge/owner-review.json (the same moments for the
    owner: lesson, time, the earlier uid + her ruling + its wrong / right, the new rows). Routes review only."""
    B = J(before or BEFORE)
    items = already_ruled_plan(B["lessons"], J(AUDIT)["rows"])
    uids = {}
    for x in items:
        for r in x["new_rows"]:
            uids.setdefault(r["uid"], {"date": x["date"], "t": r["t"], "earlier_uids": []})["earlier_uids"].append(x["earlier"]["uid"])
    W(ALREADY_P, {"about": "Re-read B rows within 5 s, in the same lesson, of a moment Amal already ruled on whose old uid was not carried. "
                           "The builders of her review list, check list and ledger cards skip these uids (scripts/amal_hold.AlreadyRuled); they "
                           "are on the owner's list rehear/rejudge/owner-review.json. Routes review only: no ruling is transferred, no row "
                           "merged, no score changed. Generated by `python scripts/rehear_rejudge.py already-ruled`; delete to release.",
                  "made": now(), "window_s": 5, "uids": dict(sorted(uids.items()))})
    W(os.path.join(OUTD, "owner-review.json"), {"about": "For Medi, not for Amal: questions of the new read that sit at a moment Amal already ruled on. "
                                                         "Is the new row the same slip she ruled on (then her ruling answers it), or another one (then it "
                                                         "may go to her)? Nothing is decided here.",
                                                "made": now(), "moments": len(items), "new_rows": len(uids), "items": items})
    print("already-ruled: %d re-read B rows at %d moments Amal already ruled on -> the owner's list, not hers" % (len(uids), len(items)))
    return items


# ---------------------------------------------------------------------------------------------- late merges, one by one
def _old_late_same(r, s):
    """The rule late_sweep_pairs used until 2026-10-05 (kept here only to name what it merged)."""
    a, b = sec(r.get("t")), sec(s.get("t"))
    if kind_class(r.get("kind")) != kind_class(s.get("kind")) or a is None or b is None or abs(a - b) > REPEAT_S:
        return False
    ra, sa = norm(r.get("medi_said")), norm(s.get("medi_said"))
    if ra and ra == sa and len(ra.split()) >= 3:
        return True
    return kind_class(r.get("kind")) == "vocab" and (same_piece(r.get("right"), s.get("right")) or same_piece(r.get("right"), s.get("amal_said")))


def merge_review(out=None):
    """Codex final approval 2026-10-05, blocker 4: every reader row + 09-24 sweep row pair the OLD late-pairing rule
    merged (the same 3-word line alone was enough), re-validated one by one under the new rule
    (full_audit_build.late_pair_evidence: evidence of the same error). Runs the build in memory; writes
    rehear/rejudge/merge-review.json only."""
    import collections, copy
    import full_audit_build as FAB
    seen = []
    real = FAB.late_sweep_pairs

    def spy(readers, cands, used):
        free = [i for i in range(len(cands)) if i not in used]
        mine = {id(r): [i for i in free if _old_late_same(r, cands[i])] for r in readers}
        taken = collections.Counter(i for v in mine.values() for i in v)
        new = real(readers, cands, used)
        newset = {(id(r), i) for r, i in new}
        for r in readers:
            if len(mine[id(r)]) == 1 and taken[mine[id(r)][0]] == 1:
                i = mine[id(r)][0]
                seen.append({"reader": copy.deepcopy(r), "sweep": copy.deepcopy(cands[i]), "merged_now": (id(r), i) in newset,
                             "evidence": FAB.late_pair_evidence(r, cands[i])})
        for r, i in new:
            if not any(x["reader"].get("t") == r.get("t") and x["reader"].get("wrong") == r.get("wrong") and x["sweep"]["sweep_id"] == cands[i]["sweep_id"] for x in seen):
                seen.append({"reader": copy.deepcopy(r), "sweep": copy.deepcopy(cands[i]), "merged_now": True, "evidence": FAB.late_pair_evidence(r, cands[i]), "new_only": True})
        return new
    FAB.late_sweep_pairs = spy
    try:
        FAB.gather(write_report=False)
    finally:
        FAB.late_sweep_pairs = real
    audit = (J(AUDIT) or {}).get("rows") or []
    by_sweep = {(r["date"], r.get("sweep_id")): r for r in audit if r.get("sweep_id")}
    side = lambda r: {k: r.get(k) for k in ("t", "t_amal", "kind", "bucket", "wrong", "right", "medi_said", "amal_said", "why") if r.get(k) is not None}  # noqa: E731
    hand = (J(os.path.join(OUTD, "merge-review-hand.json")) or {}).get("rows") or {}
    rows = []
    for x in seen:
        r, s = x["reader"], x["sweep"]
        ar = by_sweep.get((r["date"], s["sweep_id"]))
        if x["merged_now"]:
            why = "merged: " + x["evidence"]
        else:
            same_b = r.get("bucket") and r.get("bucket") == s.get("bucket")
            why = ("split: the two rows quote the same line of his but nothing shows the same error - rules %s / %s, wrong pieces %r / %r, right pieces %r / %r; "
                   "the readers' row and the 09-24 sweep's row are two rows again"
                   % (r.get("bucket") or "none", s.get("bucket") or "none", r.get("wrong"), s.get("wrong"), r.get("right"), s.get("right")))
            assert not same_b
        rows.append({"date": r["date"], "mmss": r.get("t"), "sweep_t": s.get("t"), "result": "merged" if x["merged_now"] else "now split", "why": why,
                     "read_by_hand": hand.get("%s|%s" % (r["date"], s["sweep_id"])),
                     "readers_row": side(r), "sweep_row": dict(side(s), sweep_id=s["sweep_id"]),
                     "audit_uid_holding_the_sweep_row": (ar or {}).get("uid"), "audit_row_source": (ar or {}).get("source")})
    rows.sort(key=lambda x: (x["date"], sec(x["mmss"]) or 0))
    doc = {"made": now(), "about": "Every pair the old late-pairing rule merged (same kind class, within 30 s, the same 3-word line of his - or, for "
                                   "word slips, the same word from Amal), re-validated under the rule of 2026-10-05: merge only with evidence of the "
                                   "same error (same rule, or the same wrong / right piece), one partner each.",
           "merged": sum(1 for x in rows if x["result"] == "merged"), "now_split": sum(1 for x in rows if x["result"] == "now split"), "rows": rows}
    W(out or os.path.join(OUTD, "merge-review.json"), doc)
    print("merge review: %d pairs the old rule merged -> %d still merged, %d now split" % (len(rows), doc["merged"], doc["now_split"]))
    for x in rows:
        print("  %s %s (sweep %s) %s - %s" % (x["date"], x["mmss"], x["sweep_t"], x["result"], x["why"][:150]))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("snapshot"); s.add_argument("--no-pin", action="store_true", help="do not write legacy reader manifests")
    s = sp.add_parser("retire-pass2"); s.add_argument("--apply", action="store_true")
    s = sp.add_parser("prompts"); s.add_argument("date"); s.add_argument("readers", nargs="*", default=["r1", "r2", "r3"])
    s = sp.add_parser("accept"); s.add_argument("date"); s.add_argument("reader", choices=["r1", "r2", "r3"])
    for c in ("carry", "kept", "preflight", "report", "hold", "amal-diff", "merge-review", "attribution", "orphans", "spot-withheld", "already-ruled"):
        sp.add_parser(c)
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        snapshot(pin_legacy=not a.no_pin)
    elif a.cmd == "retire-pass2":
        retire_pass2(a.apply)
    elif a.cmd == "prompts":
        prompts(a.date, a.readers)
    elif a.cmd == "accept":
        return accept(a.date, a.reader)
    elif a.cmd == "carry":
        carry()
    elif a.cmd == "kept":
        kept()
    elif a.cmd == "preflight":
        return preflight()
    elif a.cmd == "report":
        report()
    elif a.cmd == "hold":
        hold()
    elif a.cmd == "amal-diff":
        return amal_diff()
    elif a.cmd == "merge-review":
        merge_review()
    elif a.cmd == "attribution":
        attribution()
    elif a.cmd == "orphans":
        orphan_dispositions()
    elif a.cmd == "spot-withheld":
        spot_withheld()
    elif a.cmd == "already-ruled":
        already_ruled()
    return 0


if __name__ == "__main__":
    sys.exit(main())
