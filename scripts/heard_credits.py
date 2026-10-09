# -*- coding: utf-8 -*-
"""Credit for the words he really said (WS-29, Medi 2026-10-09 on the 10-08 lesson: "I should get credit for knowing
'alayhi salmik'", "Merhaba should count as a vocab", "99% of the words said should come from amals arabic list").

The Word Bank matcher (scripts/speaking_evidence.py) reads the engine's raw words. When the engine misheard him
('Defect' for كيفك, 'alayhi salmik' for الله يسلمك) his own correction (a heard-word row, scripts/medi_corrections.py
text_rows, by medi) only ever REMOVED a credit (TR-18 in scripts/lesson_ledger.py): the word he said was never matched,
so a corrected lesson scored lower than the right transcript would. This file matches her Doc words in the HEARD text of
his own rows, with the same StrictMatcher, and adds them as Word Bank events through the review overlay's `additions`
(docs/data/word-bank-review.json - the overlay that already carries hand-made events; the raw evidence is never touched,
RULES.md S2).

Only his own rows (by medi): a machine listen (the Gemini re-hear) is not his word and never adds a credit here.
The context decides like the matcher's own assess(): Amal said the same Doc word in the 15 s before = helped (practice,
not independent); a correction cue from her in the 8 s after (no / لا / مش / instead / wrong) = left unresolved for the
readers; otherwise independent. Rebuilt every build (every addition it made before is replaced; others are kept).

    python scripts/heard_credits.py            # rebuild the additions, print one line per credit
"""
import hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
REVIEW_P = os.path.join(REPO, "docs", "data", "word-bank-review.json")
EVID_P = os.path.join(REPO, "docs", "data", "word-bank-evidence.json")
WORDS_P = os.path.join(REPO, "docs", "data", "words.json")
LESSONS_DIR = os.path.join(REPO, "docs", "data", "lessons")
BY = "heard-credit"
CUE = re.compile(r"\b(no|instead|wrong|pronounce|correction)\b|(?:^|\s)(لا|مش)(?:\s|[.،؟?]|$)", re.I)


def J(p, d=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def sha(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def find_words(text, matcher, prefer=None):
    """[(start token, end token, key, method, words)] - longest Doc phrase first, one key only (an ambiguous form is skipped
    unless his row names the key: كيفك is keefak (m) or keefek (f), his row says which he said)."""
    import speaking_evidence as se
    toks = [t for t in str(text or "").split() if t.strip()]
    out, pos = [], 0
    while pos < len(toks):
        hit = None
        for n in matcher.lengths:
            part = toks[pos:pos + n]
            if len(part) != n:
                continue
            m = matcher.match(" ".join(part))
            if len(m) > 1:
                m = se.contextual_match(m, " ".join(toks[pos + n:pos + n + 1]))
            if len(m) > 1 and prefer in m:
                m = {prefer: m[prefer]}
            if len(m) == 1:
                k = next(iter(m))
                hit = (pos, pos + n, k, m[k], " ".join(part))
                break
        if hit:
            out.append(hit)
            pos = hit[1]
        else:
            pos += 1
    return out


def assess(key, t0, t1, turns, matcher):
    """(assessment, reason) from the lesson around the word, the matcher's own rules in short."""
    before = [u for u in turns if u.get("who") == "Amal" and 0 <= t0 - float(u["t"]) <= 15
              and any(h[2] == key for h in find_words(u.get("text"), matcher, key))]
    if before:
        return "helped", "Same vocabulary supplied by Amal within 15 seconds; repetition is practice, not independent credit"
    after = [u for u in turns if u.get("who") == "Amal" and 0 <= float(u["t"]) - t1 <= 8]
    if any(CUE.search(u.get("text") or "") for u in after):
        return "unresolved", "A correction cue from Amal right after; the readers decide"
    return "independent", "Word he said, written by his own correction (the recording engine misheard it)"


def build(rows=None, words=None, evidence=None, lessons=None):
    """[addition] for every Doc word in the heard text of his own rows."""
    import speaking_evidence as se
    import medi_corrections as MC
    rows = MC.text_rows() if rows is None else rows
    words = (J(WORDS_P, {}) or {}).get("items", []) if words is None else words
    matcher = se.StrictMatcher(words)
    events = (J(EVID_P, {}) or {}).get("events", []) if evidence is None else evidence
    anchors = {}
    for e in events:
        if e.get("speaker") == "Medi" and e.get("lesson_date") and e["lesson_date"] not in anchors:
            anchors[e["lesson_date"]] = e
    out = []
    for r in rows:
        if r.get("by") != "medi" or r.get("who") != "Medi" or not r.get("heard") or r.get("set_who") or r.get("set_t") is not None:
            continue
        if r.get("credit") == "none":
            continue                      # WS-30: his own 'no credit' on this line (10-08 00:42 keefak, fixed by him to keefek)
        d = str(r["date"])
        a = anchors.get(d)
        if not a:
            continue
        turns = (lessons or {}).get(d)
        if turns is None:
            turns = (J(os.path.join(LESSONS_DIR, d + ".json"), {}) or {}).get("turns", [])
        t0 = float(r["t"])
        t1 = max(t0, float(r.get("turn_end") or t0))
        engine_keys = {h[2] for h in find_words(r.get("engine_wrote"), matcher)}
        for i, (s, e_, key, method, said) in enumerate(find_words(r["heard"], matcher, r.get("word_key"))):
            if key in engine_keys:
                # the engine already had this word: the matcher made its event. His "should count" (credit) rules on
                # that event through a patch (patches()); without it, no second credit
                continue
            ass, why = assess(key, t0, t1, turns, matcher)
            if r.get("credit") in ("independent", "helped") and r.get("word_key") == key:
                ass, why = r["credit"], "His own ruling on this moment (%s)" % (r.get("quote") or "his correction")
            off = float(a.get("t_start") or 0) - float(a.get("local_start") or 0)     # the anchor's own track offset
            rid = "heard:" + str(r.get("correction") or "")
            ev = {"id": sha([BY, d, r.get("correction") or "", i, key]), "lesson_date": d, "word_key": key,
                  "local_start": round(t0 - off, 3), "local_end": round(t1 - off, 3),
                  "candidate_keys": [key], "source_id": a.get("source_id"), "source_sha256": a.get("source_sha256"),
                  "row_id": rid, "item_ids": [], "t_start": t0, "t_end": t1,
                  "speaker": "Medi", "speaker_basis": a.get("speaker_basis"), "text": said, "original_text": r.get("engine_wrote") or "",
                  "match_method": method, "assessment": ass, "assessment_status": "provisional", "spoken": True,
                  "wording_status": "human_reviewed", "review_ids": [], "version": a.get("version"),
                  # his corrected line is the event's own row (the Word Bank card shows it and plays its clip)
                  "context": [{"row_id": rid, "speaker": "Medi", "text": r["heard"], "timeline_start": t0, "timeline_end": t1}],
                  "reason": "%s (WS-29: the engine wrote %s; he said %s)" % (why, r.get("engine_wrote") or "nothing", said),
                  # 'correction' is the Word Bank's word for a tutor fix (an event carrying one needs a classification),
                  # so his row id goes in medi_correction; the credit is a word (lexical), with its points spelled out
                  "heard_credit": True, "medi_correction": r.get("correction"), "rule": "WS-29", "classification": "lexical",
                  **({"vocab_points": {"independent": 1, "helped": 0.5}[ass]} if ass in ("independent", "helped") else {})}
            out.append({"anchor_id": a["id"], "expected_source": a.get("source_sha256"), "event": ev, "by": BY})
    return out


def patches(rows=None, evidence=None):
    """{event id: patch} - his "should count" on a word the matcher already found (a confirming row, engine_wrote ==
    heard, with credit): that Word Bank event of his, on that line, becomes his ruling (10-08 0:10 مرحبا)."""
    import medi_corrections as MC
    rows = MC.text_rows() if rows is None else rows
    events = (J(EVID_P, {}) or {}).get("events", []) if evidence is None else evidence
    out = {}
    for r in rows:
        if r.get("by") != "medi" or r.get("who") != "Medi" or r.get("credit") not in ("independent", "helped") or r.get("engine_wrote") != r.get("heard"):
            continue
        t0 = float(r["t"]) - 1.0
        t1 = max(float(r["t"]), float(r.get("turn_end") or r["t"])) + 1.0
        for e in events:
            if (e.get("lesson_date") == str(r["date"]) and e.get("speaker") == "Medi" and t0 <= float(e.get("t_start") or -9) <= t1
                    and (not r.get("word_key") or e.get("word_key") == r["word_key"]) and e.get("word_key")
                    and _norm(e.get("text")) and _norm(e.get("text")) in _norm(r["heard"])):
                out[e["id"]] = {"expected": {k: e.get(k) for k in ["source_sha256", "row_id", "word_key", "text", "t_start", "t_end", "assessment", "reason"]},
                                "changes": {"assessment": r["credit"], "reason": "His own ruling (WS-29): %s" % (r.get("quote") or "should count"),
                                            "medi_ruling": True, "by": BY, "medi_correction": r.get("correction"),
                                            "classification": "lexical", "vocab_points": {"independent": 1, "helped": 0.5}[r["credit"]]}}
    return out


def _norm(s):
    return re.sub(r"[^ء-يa-z0-9]", "", str(s or "").lower())


def refresh(path=REVIEW_P, log=print, **kw):
    review = J(path)
    if review is None:
        return {"status": "no review overlay"}
    keep = [x for x in review.get("additions") or [] if x.get("by") != BY]
    new = build(**kw)
    old = [x for x in review.get("additions") or [] if x.get("by") == BY]
    P = review.setdefault("patches", {})
    pold = {k: v for k, v in P.items() if (v.get("changes") or {}).get("by") == BY}
    pnew = patches(rows=kw.get("rows"), evidence=kw.get("evidence"))
    pnew = {k: v for k, v in pnew.items() if k not in P or (P[k].get("changes") or {}).get("by") == BY or (P[k].get("changes") or {}).get("audit_created")}
    if old != new or pold != pnew:
        for k in pold:
            P.pop(k, None)
        P.update(pnew)
        review["additions"] = keep + new
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(review, f, ensure_ascii=False, indent=2)
            f.write("\n")
    n = sum(x["event"]["assessment"] == "independent" for x in new)
    log("heard_credits: %d of his own 'should count' rulings on words the matcher had" % len(pnew))
    log("heard_credits: %d Doc words in his own corrections (%d independent, %d helped, %d for the readers)"
        % (len(new), n, sum(x["event"]["assessment"] == "helped" for x in new), sum(x["event"]["assessment"] == "unresolved" for x in new)))
    return {"status": "ok", "n": len(new), "independent": n}


if __name__ == "__main__":
    res = refresh()
    for x in build():
        e = x["event"]
        print(e["lesson_date"], "%d:%02d" % divmod(int(e["t_start"]), 60), e["word_key"], e["text"], e["assessment"])
