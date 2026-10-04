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
    python scripts/rehear_rejudge.py report                 # before vs after, per lesson (after build + Amal's rulings)

Files: data/lesson-work/rehear/rejudge/ (before.json, prompts/, kept-rows.json, preflight.json, report.json, report.md)
and, read by scripts/full_audit_build.py: data/lesson-work/full-audit/uid-carry.json + preserved-rows.json.
"""
import argparse, collections, datetime as dt, hashlib, json, os, shutil, sys

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
    return (same_moment(r, x) and any(same_piece(w, x.get("wrong")) for w in pieces(r))
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
            take(i, min(c, key=lambda j: _dt(o, new[j])), "piece")

    def unique(test, how):
        co = {i: [j for j, n in enumerate(new) if j not in un and test(o, n)] for i, o in enumerate(old) if i not in uo}
        cn = collections.Counter(j for js in co.values() for j in js)
        for i, js in co.items():
            if len(js) == 1 and cn[js[0]] == 1:
                take(i, js[0], how)
    unique(lambda o, n: _class_ok(o, n) and _dt(o, n) <= REPEAT_S and bool({norm(w) for w in pieces(o)} & {norm(w) for w in pieces(n)}), "repeat")
    unique(lambda o, n: same_moment(o, n) and _class_ok(o, n), "moment")
    return out


def new_rows(carry=None, preserved=None):
    """The rows full_audit_build would write now (all rulings applied), each with read_key and its final uid."""
    import full_audit_build as FAB
    G = FAB.gather(carry=carry, preserved=preserved, write_report=False)
    keys = [r.get("read_key") for r in G["rows"]]
    FAB.assign_uids(G["rows"], G["carry"])
    for r, k in zip(G["rows"], keys):
        r["read_key"] = k
    return G


def carry_entries(old, new):
    """-> (entries for uid-carry.json, matches). A carry entry is written only when the uid would otherwise change."""
    m = match_rows(old, new)
    out = []
    for i, j, how in m:
        o, n = old[i], new[j]
        if how == "exact" or not n.get("read_key"):
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
        if ent:
            lessons[d] = ent
        c = collections.Counter(how for _, _, how in m)
        counts[d] = {"old": len(x["rows"]), "new": len(by_date.get(d, [])), **c,
                     "old_without_new": len(x["rows"]) - len(m), "new_without_old": len(by_date.get(d, [])) - len(m)}
    W(out or FAB.CARRY_P, {"about": "Old audit uid -> the re-read row of the same moment (scripts/rehear_rejudge.py carry, 2026-10-04 re-hear). "
                                    "scripts/full_audit_build.py assign_uids gives the row whose read_key is listed the OLD uid, so Amal's "
                                    "rulings, verification records, patterns, duplicates.json and Medi's corrections keep resolving. "
                                    "read_key = the uid the row would get as the readers wrote it. Generated; re-run after any new settle.",
                           "made": now(), "snapshot": B.get("taken"), "counts": counts, "lessons": lessons})
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


def kept_plan(before_lessons, new_by_date, turns_of=None):
    """-> (preserved rows for the build, listing). new_by_date = the new rows WITH the carry applied and no preserved rows."""
    turns_of = turns_of or (lambda d: [])
    preserved, listing = [], {"kept_confirmed": [], "listed_rejected": [], "listed_human_ruling": [], "line_changed": []}
    for d, x in sorted(before_lessons.items()):
        have = {r["uid"]: r for r in new_by_date.get(d, [])}
        turns = turns_of(d)
        for o in x["rows"]:
            refs = o.get("refs") or {}
            human = bool(refs.get("hand") or refs.get("medi_corrections") or refs.get("medi_correction_applied") or refs.get("duplicates"))
            if not o.get("amal") and not human:
                continue
            after = line_at(turns, o.get("t"))
            item = {"date": d, "uid": o["uid"], "t": o.get("t"), "kind": o.get("kind"), "wrong": o.get("wrong"), "right": o.get("right"),
                    "amal": o.get("amal"), "amal_ruling": o.get("amal_ruling"), "line_before": o.get("line_before"), "line_after": after,
                    "line_changed": (o.get("line_before") or None) != (after or None)}
            n = have.get(o["uid"])
            if n is not None:
                if item["line_changed"]:
                    listing["line_changed"].append({**item, "new_row": {"t": n.get("t"), "wrong": n.get("wrong"), "right": n.get("right"), "kind": n.get("kind")}})
                continue
            if o.get("amal") == "confirmed":
                preserved.append(restore_before_ruling(o))
                listing["kept_confirmed"].append({**item, "kept": KEPT_MARK})
            elif o.get("amal") == "rejected":
                listing["listed_rejected"].append({**item, "note": "Amal rejected it and the readers did not write it again: nothing to reject"})
            else:
                listing["listed_human_ruling"].append({**item, "refs": refs, "note": "a hand ruling pointed at this row and the readers did not write it again"})
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
        for i, x in enumerate((J(os.path.join(work, name), {}) or {}).get("rows", [])):
            tag = f"#{i} {x['date']} {x.get('t')} {x.get('wrong')}"
            hit = next((r for r in rows if r.get("date") == x["date"] and ruling_hits(r, x)), None)
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
    kept_rows = [u for u in same if new[u].get("kept")]
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
    return {"rows_before": len(old), "rows_after": len(new),
            "scored_before": sum(1 for r in old.values() if scored(r)), "scored_after": sum(1 for r in new.values() if scored(r)),
            "same_uid": len(same), "moved": len(moved), "added": len([u for u in new if u not in old]), "removed": len([u for u in old if u not in new]),
            "kept": len(kept_rows),
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
    doc = {"made": now(), "snapshot": B.get("taken"), "audit_built": A.get("built"), "amal_rulings_reapplied": applied,
           "totals_before": B.get("totals"), "totals_after": A.get("totals"), "orphaned": orph, "lessons": out}
    W(os.path.join(OUTD, "report.json"), doc)
    M = ["# Re-judge on the re-heard transcript - before vs after", "", f"snapshot {B.get('taken')} | audit built {A.get('built')} | "
         + ("Amal's rulings re-applied" if applied else "**Amal's rulings NOT re-applied yet (run apply_amal_audit_rulings.py)**"), "",
         "| lesson | rows | scored | same uid | moved | added | removed | kept | Amal ruled -> on a row / kept / no row / ruling not back | checks orphaned | patterns orphaned | Words % | Grammar % |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, x in out.items():
        hb, ha = (x["headline"]["before"] or {}), (x["headline"]["after"] or {})
        a = x["amal"]
        M.append(f"| {d} | {x['rows_before']} -> {x['rows_after']} | {x['scored_before']} -> {x['scored_after']} | {x['same_uid']} | {x['moved']} | {x['added']} | "
                 f"{x['removed']} | {x['kept']} | {a['ruled_before']} -> {a['on_a_row_after']} / {a['kept_from_first_read']} / {len(a['no_row_after'])} / {len(a['ruling_not_back'])} | "
                 f"{len(x['verification_records']['orphaned'])} | {len(x['patterns']['orphaned'])} | {hb.get('words_pct')} -> {ha.get('words_pct')} | {hb.get('grammar_pct')} -> {ha.get('grammar_pct')} |")
    M += ["", "## Orphaned references (must be empty, or each one read)", ""] + ([f"- {k}: {', '.join(v)}" for k, v in orph.items()] or ["none"])
    for d, x in out.items():
        a = x["amal"]
        if a["no_row_after"] or a["ruling_not_back"]:
            M += ["", f"## {d} - Amal's rulings to read", ""] + [f"- no row after: {u}" for u in a["no_row_after"]] \
                + [f"- ruling not back: {y['uid']} {y['t']} was {y['was']}, row is now {y['kind_now']}" for y in a["ruling_not_back"]]
    open(os.path.join(OUTD, "report.md"), "w", encoding="utf-8", newline="\n").write("\n".join(M) + "\n")
    tot = collections.Counter()
    for x in out.values():
        tot.update({k: x[k] for k in ("rows_before", "rows_after", "same_uid", "moved", "added", "removed", "kept")})
        tot.update({"amal_no_row": len(x["amal"]["no_row_after"]), "amal_ruling_not_back": len(x["amal"]["ruling_not_back"])})
    print("report:", dict(tot), "| orphaned", {k: len(v) for k, v in orph.items()}, "->", os.path.join(OUTD, "report.md"))
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("snapshot"); s.add_argument("--no-pin", action="store_true", help="do not write legacy reader manifests")
    s = sp.add_parser("retire-pass2"); s.add_argument("--apply", action="store_true")
    s = sp.add_parser("prompts"); s.add_argument("date"); s.add_argument("readers", nargs="*", default=["r1", "r2", "r3"])
    s = sp.add_parser("accept"); s.add_argument("date"); s.add_argument("reader", choices=["r1", "r2", "r3"])
    for c in ("carry", "kept", "preflight", "report"):
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
