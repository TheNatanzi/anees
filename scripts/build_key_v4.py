# -*- coding: utf-8 -*-
"""Answer key v4 for the exam lessons 10-08 / 10-09 / 10-10 (Medi 2026-10-21: "Make v4 and follow amals directions").

v3 (119 slips: the student's key + the 20 Gemini 4 Argon finds he confirmed) is changed ONLY by the tutor's final answers
on her blind cards (AM-33 disputes list, AM-35 judges list), read through AM-36 (build_tutor_more_check.final_answer: an
answer that asked for clarification is replaced by her answer to the re-ask; until then the card is PENDING and v3 stays):
  - 'right' on a v3 slip            -> the slip is removed (her ruling wins over the student's and the AI's)
  - 'mistake' where v3 has no slip  -> a slip is added (src 'tutor <list>'), unless she said it is the same correction as a
                                       slip already in the key (her note 'already flagged') or v3 has the same fix within 60 s
  - 'mistake' on a v3 slip          -> kept; her written correction becomes the slip's right form when she gave one
  - a note giving partial credit ('half a point') -> the slip carries weight 0.5
  - "can't tell" or pending         -> v3 unchanged, listed
Every change is listed in key_versions[-1] with her answer and note. The input v3 files are the frozen exam files of the
reader-90 branch (614c7a2); the output is the grade book's own files on master (PG-46).

    python scripts/build_key_v4.py [--v3-dir DIR]
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_tutor_more_check as MC  # noqa: E402
import build_tutor_dispute_check as DC  # noqa: E402

DATES = ("2026-10-08", "2026-10-09", "2026-10-10")
OUT_DIR = os.path.join(REPO, "data", "lesson-work", "review-grades")
V3_DIR = r"C:\dev\anees\.claude\worktrees\reader-90\data\lesson-work\review-grades"
LISTS = [("AM-33 disputes", os.path.join(REPO, "docs", "data", "amal-check-key-check-disputes.json"),
          os.path.join(REPO, "data", "lesson-work", "tutor-dispute-check", "moments.json")),
         ("AM-35 judges", os.path.join(REPO, "docs", "data", "amal-check-key-check-judges.json"),
          os.path.join(REPO, "data", "lesson-work", "tutor-judge-check", "moments.json"))]
SAME_S, ADD_SAME_FIX_S = 10.0, 60.0
# Where her note re-defines the mistake itself (not only its right form), the right form is written here from her words.
OVERRIDE_AR = {("2026-10-08", "07:44"): "تبدأ"}   # 'he said byebda instead of btebda, because naar is a feminine word'
DUP_RE = re.compile(r"(?i)already flagged|flagged it as a mistake before|same (mistake|correction) as")
HALF_RE = re.compile(r"(?i)half (a )?point|partial (credit|point)")


def J(p):
    return json.load(open(p, encoding="utf-8"))


def secs(s):
    p = [int(x) for x in str(s).split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def mmss(t):
    t = int(round(float(t)))
    return "%d:%02d:%02d" % (t // 3600, t % 3600 // 60, t % 60) if t >= 3600 else "%02d:%02d" % (t // 60, t % 60)


def moment_for(card, moments):
    ms = [m for m in moments if m["date"] == card["date"]]
    return min(ms, key=lambda m: abs((float(m["at"][0]) if m.get("at") else secs(m["time"])) - float(card["t"]))) if ms else {}


def toks(x):
    x = re.sub(r"[\u064B-\u0652\u0670\u0640\u060C,.\u061F?!:;()\-\u2013\u2014\u2026]", " ", str(x or ""))
    x = x.replace("\u0623", "\u0627").replace("\u0625", "\u0627").replace("\u0622", "\u0627").replace("\u0629", "\u0647").lower()
    return {w for w in x.split() if len(w) > 1}


def same_words(a, b):
    """The key slip and the card name the same words (at least one word in common)."""
    return bool(toks(a) & toks(b))


def her_fix(note):
    """Her written right form, when the note gives one ('should be fajer', 'should be with 3indi')."""
    m = re.search(r"(?i)should(?:'ve| have)? be(?:en)?(?: with)? ([^.\n]+)", note or "")
    return m.group(1).strip() if m else None


def build(v3_dir=V3_DIR, out_dir=OUT_DIR, answers=None, log=print):
    if answers is None:
        import db
        rows = db.select("amal_rules", {"select": "id,kind,word_key,payload", "kind": "in.(%s,undo)" % DC.KIND, "order": "id.asc"}, retries=4)
        answers = MC.latest(rows)
    files = {d: J(os.path.join(v3_dir, d + ".json")) for d in DATES}
    slips = {d: [dict(s) for s in files[d]["key"]["slips"]] for d in DATES}
    gone = {d: [] for d in DATES}
    new_slips = {d: [] for d in DATES}
    changes = {d: {"removed": [], "added": [], "kept_fixed": [], "weighted": [], "unchanged_cant_tell": [], "pending": [], "duplicate": []} for d in DATES}
    for name, list_path, mom_path in LISTS:
        cards = (J(list_path).get("items") or [])
        moments = J(mom_path)["moments"]
        for c in cards:
            d = c["date"]
            if d not in slips:
                continue
            fa = MC.final_answer(c["id"], answers)
            first = answers.get("%s:%s" % (DC.PREFIX, c["id"]))
            m = moment_for(c, moments)
            at = float(m["at"][0]) if m.get("at") else (float(m["i"]) if m.get("i") is not None else float(c["t"]))   # the pinned line first
            if name.startswith("AM-33"):          # the disputes list was cut FROM the key: its moments may carry no words to compare
                cand = [s for s in slips[d] if min(abs(float(s["i"]) - at), abs(float(s["i"]) - float(c["t"]))) <= 15.0]
            else:
                cand = [s for s in slips[d] if abs(float(s["i"]) - at) <= SAME_S and same_words(s.get("said"), m.get("said") or c["rows"][0]["ar"])]
            near = [min(cand, key=lambda s: abs(float(s["i"]) - at))] if cand else []      # the ONE slip of this moment
            note = str((fa or {}).get("typed") or "").strip()
            base = {"card": c["id"], "t": c["mmss"], "list": name, "answer": (fa or {}).get("answer"), "note": note}
            if first is None:
                continue                                              # never answered: nothing to apply
            if fa is None:
                changes[d]["pending"].append(base); continue
            ans = fa.get("answer")
            if ans == "cant_tell":
                changes[d]["unchanged_cant_tell"].append(base); continue
            if ans == "right":
                for s in near:
                    slips[d].remove(s); gone[d].append(dict(s))
                    changes[d]["removed"].append(dict(base, slip={"t": s["t"], "said": s.get("said"), "ar": s.get("ar")}))
                continue
            if ans != "mistake":
                continue
            fix = her_fix(note)
            ov = OVERRIDE_AR.get((d, c["mmss"]))
            if near:
                for s in near:
                    if fix or ov:
                        s["tutor_says"] = note                     # her words, kept as she wrote them
                        if ov:
                            s["ar"] = ov
                        elif not (s.get("ar") or "").strip() and m.get("fix_ar"):
                            s["ar"] = m["fix_ar"]
                        changes[d]["kept_fixed"].append(dict(base, slip=s["t"], ar=s.get("ar")))
                    if HALF_RE.search(note):
                        s["weight"] = 0.5; changes[d]["weighted"].append(dict(base, slip=s["t"]))
                continue
            want = {x.strip() for x in (m.get("fix_ar"), fix, ov) if x and x.strip()}
            same_fix = [s for s in slips[d] if abs(float(s["i"]) - at) <= ADD_SAME_FIX_S and (s.get("ar") or "").strip() in want]
            prev = (first or {}).get("typed") or ""
            if DUP_RE.search(prev) or DUP_RE.search(note) or same_fix:
                changes[d]["duplicate"].append(dict(base, why="same correction as a slip already in the key"))
                continue
            new = {"i": "%.2f" % at, "t": mmss(at), "k": m.get("k") or "grammar", "rule": None, "said": m.get("said") or c["rows"][0]["ar"],
                   "ar": ov or m.get("fix_ar") or m.get("ai_right") or fix or "", "src": "tutor ruling (%s, %s)" % (name, "re-asked" if fa is not first else "first answer")}
            if note:
                new["tutor_says"] = note
            if HALF_RE.search(note):
                new["weight"] = 0.5; changes[d]["weighted"].append(dict(base, slip=new["t"]))
            slips[d].append(new); slips[d].sort(key=lambda s: float(s["i"])); new_slips[d].append(new)
            changes[d]["added"].append(dict(base, slip={"t": new["t"], "said": new["said"], "ar": new["ar"]}))
    total = 0
    for d in DATES:
        F = files[d]
        before = len(F["key"]["slips"])
        F["key"]["slips"] = slips[d]
        total += len(slips[d])
        c = changes[d]
        F["key_versions"].append({"version": 4, "date": "2026-10-21",
                                  "why": "the tutor's final answers on her blind cards (AM-33, AM-35), read through AM-36 (re-asked cards use her "
                                         "answer to the re-ask; pending ones leave v3 as it was); Medi 2026-10-21: 'Make v4 and follow amals directions'",
                                  "slips_before": before, "slips_after": len(slips[d]),
                                  # 'added' / 'removed' hold the slips themselves (as in v2 / v3: older keys are replayed by undoing
                                  # them); the record of each of her answers is in 'changes'
                                  "added": new_slips[d], "removed": gone[d], "changes": c})
        os.makedirs(out_dir, exist_ok=True)
        json.dump(F, open(os.path.join(out_dir, d + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log("%s: v3 %d -> v4 %d  (removed %d, added %d, right form from her note %d, half weight %d, duplicates %d, can't tell %d, pending %d)" % (
            d, before, len(slips[d]), len(c["removed"]), len(c["added"]), len(c["kept_fixed"]), len(c["weighted"]), len(c["duplicate"]),
            len(c["unchanged_cant_tell"]), len(c["pending"])))
    log("key v4: %d slips" % total)
    return changes


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--v3-dir", default=V3_DIR)
    a = ap.parse_args()
    build(a.v3_dir)
