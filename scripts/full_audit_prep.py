# -*- coding: utf-8 -*-
"""Step 1 prep for the full vocab+grammar audit (plan/PROMPT-OVERNIGHT-FULL-AUDIT-2026-09-26.md).

    python scripts/full_audit_prep.py            -> data/lesson-work/full-audit/<date>.txt (readable transcript, lesson clock)
                                                    data/lesson-work/full-audit/READER-BRIEF.md (what a reader does + schema)
                                                    data/lesson-work/full-audit/amal-sheet.txt (her Doc words, for tier 3)

Transcripts come from docs/data/lessons/<date>.json (turns already on the lesson-page clock, chat merged).
Nothing is re-transcribed. Rule S2: the text is printed as the engine wrote it.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "data", "lesson-work", "full-audit")
DATES = sorted(f[:-5] for f in os.listdir(os.path.join(REPO, "docs", "lessons")) if re.fullmatch(r"20\d\d-\d\d-\d\d\.html", f))  # every published lesson page, so a new lesson flows by itself

def mmss(t):
    t = int(round(t)); h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return (f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")

def main():
    os.makedirs(OUT, exist_ok=True)
    for d in DATES:
        L = json.load(open(os.path.join(REPO, "docs", "data", "lessons", d + ".json"), encoding="utf-8"))
        lines = [f"# Lesson {d} - {len(L['turns'])} turns on the lesson clock (mm:ss = seconds on the page audio)", ""]
        for t in L["turns"]:
            who = t["who"]
            tag = f"CHAT {t.get('typed_by','')}".strip() if who == "chat" else who
            lines.append(f"[{mmss(t['t'])}] {tag}: {t['text']}")
        open(os.path.join(OUT, d + ".txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    W = json.load(open(os.path.join(REPO, "docs", "data", "words.json"), encoding="utf-8"))["items"]
    rows = sorted({(w.get("arabic") or "").strip(), (w.get("arabizi") or "").strip(), (w.get("english") or "").strip(), w["key"]} and
                  ((w.get("english") or "").strip().lower(), (w.get("arabizi") or "").strip(), (w.get("arabic") or "").strip(), w["key"]) for w in W)
    open(os.path.join(OUT, "amal-sheet.txt"), "w", encoding="utf-8").write(
        "# Amal's vocabulary Doc (docs/data/words.json) - english | her arabizi | arabic | key\n" +
        "\n".join(f"{e} | {a} | {ar} | {k}" for e, a, ar, k in rows) + "\n")
    B = json.load(open(os.path.join(REPO, "docs", "data", "grammar-buckets.json"), encoding="utf-8"))
    fam = B["families"]
    blines = []
    for b in B["buckets"]:
        one = b.get("one_line") or b.get("rule") or b.get("short") or ""
        blines.append(f"- **{b['id']}** {b.get('name','')} ({fam.get(b['id'][0],'')}): {one}"
                      + (" **NOT TAUGHT YET - file it, it is shown but never counted.**" if b.get("taught") == "not-yet" else ""))
        # Amal's own notes on the rule (2026-09-27): what is and is not a mistake, so readers file by her rulings
        blines += [f"  - {m}" for m in b.get("more", []) if "(Amal" in m]
    open(os.path.join(OUT, "buckets.md"), "w", encoding="utf-8").write("# Grammar buckets (docs/data/grammar-buckets.json)\n\n" + "\n".join(blines) + "\n")
    print("wrote", len(DATES), "transcripts,", len(rows), "sheet words,", len(B["buckets"]), "buckets ->", OUT)

if __name__ == "__main__":
    main()
