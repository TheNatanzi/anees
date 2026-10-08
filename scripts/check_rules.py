# -*- coding: utf-8 -*-
"""Standing rules vs the live data - an offline check a publish guard can call (eng audit 2026-09-29, area 5).

    python scripts/check_rules.py                     # exit 0 = no BLOCK rule broken; exit 1 = first line says why
    python scripts/check_rules.py --json out.json     # full results (every check, counts, examples)
    python scripts/check_rules.py --raw <dir>         # raw lessons dir (default C:/dev/anees/data/lessons or ANEES_RAW)

Two levels, printed every run (nothing is hidden):
  BLOCK   a rule the data obeys today. Any violation -> exit 1 and the first stdout line is
          "check_rules: FAIL <id>: <n> violation(s) - <first example>".
  REPORT  a rule the data does NOT fully obey yet, because the rule itself is waiting on Medi (a conflict between two
          rules) or on a code change in a file this audit does not own. Counted and listed every run, never exit 1.
          Each one names what would move it to BLOCK. Moving a check to BLOCK is a tightening; never the reverse.
A check whose input is missing (raw dir not on this machine, node not found) prints SKIP with the reason. SKIP is not
PASS: the JSON keeps status "skip".

Rule sources: RULES.md S1-S5, plan/SESSION-DECISIONS-2026-09-21.md, docs/data/ai_rules.json, the anees-* memory notes
(standing rules), plan/PROMPT-OVERNIGHT-ENGINEERING-AUDIT-2026-09-29.md. The table in plan/ENG-AUDIT-AREA-5-6.md maps
each rule to its check id here.
"""
import argparse, glob, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_RAW = os.environ.get("ANEES_RAW") or "C:/dev/anees/data/lessons"
NODE_FALLBACK = "C:/dev/tools/node-v24.18.0-win-x64/node.exe"

HER_DIGITS = set("2356789")                       # RULES.md S1: 2 3 5 6 7 8 9 are her letters; 0 1 4 are not
EXTRA_METHODS = {"sound", "pieces", "her-chat", "guess", "as-said",           # RULES.md S1 amendment + 09-26 extension
                 "her-list", "filler"}                                        # in the file, not in RULES.md (listed)
GLUE = {'shu', 'bas', 'ai', 'aw', 'em', 'u', 'fi', 'bi', 'min', 'ya3ni', 'iza', 'lama', 'hala', 'ah', 'aha', 'tayeb',
        'tamam', '5alas', 'sa7', 'mashi', 'wala', 'ma', 'ma3', 'la'}           # = understand_lesson.GLUE_KEYS (rule M3)
SCORED = ("Correct", "Partial", "Wrong")
A_KINDS = ("grammar", "vocab-A")
EPISODE_SAYS_ONE = re.compile(r"same episode|count(ed)? once|repetition is practice|restates? |same answer|"
                              r"no new (lexical )?retrieval|one attempt", re.I)
MEDI_EMAIL = "thenatanzi@gmail.com"
# = pipeline_ext.CAPS (rule H4); stop at 90 %. Read from there, not copied: the copy here still said openai 10 after
# the caps were set to openai 40 / gemini 40 on 2026-10-03 (commit d18192d), and had no gemini row at all.
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from pipeline_ext import CAPS
except Exception:  # noqa: BLE001 - never looser than the last known caps if the import fails
    CAPS = {"elevenlabs": 10.0, "openai": 10.0}

# Files that call a paid AI endpoint without scripts/track.py, each with the reason it is allowed (rule: every AI call
# path is logged, AI engineering review 09-27 build #1). A NEW file calling an AI endpoint without track fails AI-logged.
UNTRACKED_AI_OK = {
    "suggest.py": "manual planner path (amal_links.py before), OpenAI gpt-5.5; cost in data/budget.json only; last call 09-05",
    "homework.py": "manual homework path, OpenAI gpt-5.5; cost in data/budget.json only; last call 09-05",
    "miss_kind.py": "optional gpt-5.5 fallback, off in every live caller (use_llm=False)",
    "after_questions.py": "old after-link path, dead since 09-11 (after_from_audit.py replaced it)",
    "lesson_pipeline.py": "retired hourly path (hourly_lessons.py replaced it); Scribe goes through pipeline_ext (tracked)",
    "engine_eleven.py": "09-03 engine bake-off (retired experiment)",
    "engine_openai_chat_audio.py": "09-04 engine bake-off (retired experiment)",
    "engine_openai_clips.py": "09-04 engine bake-off (retired experiment)",
    "engine_openai_recipe1.py": "09-04 engine bake-off (retired experiment)",
    "transcription_experiments.py": "09-07 Codex transcription experiments (retired)",
    "whisper_aug25.py": "08-25 local engine experiment (no paid call)",
    "whisper_hf_aug25.py": "08-25 local engine experiment (no paid call)",
    "dialectal_aug25.py": "08-25 local engine experiment (no paid call)",
    "dialectal_aug25_8s.py": "08-25 local engine experiment (no paid call)",
    "diarize_aug25.py": "08-25 local engine experiment (no paid call)",
    "diarize_words_aug25.py": "08-25 local engine experiment (no paid call)",
    "turns_pyannote_aug25.py": "08-25 local engine experiment (no paid call)",
    "build_engine_report.py": "page builder: names the endpoint in report text, makes no call",
    "lesson_alerts.py": "reads the ElevenLabs credit balance (GET /v1/user/subscription, free, no AI call) for rule LS-04",
}
AI_CALL = re.compile(r"api\.openai\.com|api\.elevenlabs\.io|api\.anthropic\.com|speech-to-text|"
                     r"\[\s*CLAUDE\s*,\s*['\"]-p['\"]|['\"]claude['\"]\s*,\s*['\"]-p['\"]")


# ------------------------------------------------------------------ helpers

def J(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def res(cid, level, rule, source, violations=None, skip=None, note=None, total=None):
    v = list(violations or [])
    if skip:
        status = "skip"
    elif not v:
        status = "pass"
    else:
        status = "fail" if level == "block" else "open"
    return {"id": cid, "level": level, "rule": rule, "source": source, "status": status, "count": len(v),
            "examples": v[:5], "skip": skip, "note": note, "total": total}


def node_bin():
    for c in (os.environ.get("NODE"), shutil.which("node"), NODE_FALLBACK):
        if c and (os.path.exists(c) or shutil.which(c)):
            return c
    return None


def mmss(t):
    try:
        t = float(t)
        return f"{int(t // 60):02d}:{int(t % 60):02d}"
    except Exception:
        return str(t)


def audit_rows(root):
    return J(root / "data" / "full-audit-2026-09-26.json")["rows"]


def wb_audit(root):
    return J(root / "docs" / "data" / "word-bank-audit.json")["events"]


def wb_evidence(root):
    return {e["id"]: e for e in J(root / "docs" / "data" / "word-bank-evidence.json")["events"]}


# ------------------------------------------------------------------ checks (each: root, raw -> result)

def check_s1_guard(root, raw):
    """S1 + anees-arabizi-guard: no Arabic-only word on the Lessons error cards (scripts/arabizi_gaps.cjs prints 0)."""
    n = node_bin()
    rule, src = "Every error-card word has Arabizi (arabizi_gaps.cjs = 0)", "RULES.md S1 (09-26 ext.); anees-arabizi-guard"
    if not n or not (root / "scripts" / "arabizi_gaps.cjs").exists():
        return res("S1-guard", "block", rule, src, skip="node or scripts/arabizi_gaps.cjs not found")
    r = subprocess.run([n, str(root / "scripts" / "arabizi_gaps.cjs")], capture_output=True, text=True, encoding="utf-8",
                       cwd=root)
    bad = [] if r.returncode == 0 else [(r.stdout.strip().splitlines() or ["exit %d" % r.returncode])[0]]
    return res("S1-guard", "block", rule, src, bad)


def check_s1_extra(root, raw):
    """S1 amendment: every built spelling row names its method (and its source unless it is a guess); her letters only."""
    d = J(root / "docs" / "data" / "arabizi-extra.json")
    bad = []
    for w, v in d.get("words", {}).items():
        lat, m = (v.get("latin") or "").strip(), v.get("method")
        if m not in EXTRA_METHODS:
            bad.append(f"{w}: method {m!r} not in {sorted(EXTRA_METHODS)}")
        elif not lat:
            bad.append(f"{w}: no latin")
        elif m != "guess" and not (v.get("from") or "").strip():
            bad.append(f"{w} ({lat}): method {m} but no 'from' (whose spelling it is built from)")
        elif any(c.isdigit() and c not in HER_DIGITS for c in lat):
            bad.append(f"{w} ({lat}): digit outside her letters 2 3 5 6 7 8 9")
        elif not re.fullmatch(r"[A-Za-z0-9' .\-]+", lat):
            bad.append(f"{w} ({lat}): character that is not a Latin letter / her digit")
        elif v.get("scope") not in (None, "lessons"):
            bad.append(f"{w} ({lat}): scope {v.get('scope')!r} is not 'lessons'")
        elif m == "as-said" and str(v.get("added") or "")[:10] >= "2026-10-04" and v.get("scope") != "lessons":
            # Codex final approval 2026-10-05, blocker 7: his own wrong / cut-off / unclear forms are Arabizi only on the
            # Lessons page (S1, AZ-05 / AZ-10); a new as-said row without the scope would show on every page
            bad.append(f"{w} ({lat}): an as-said row added from 2026-10-04 on must carry \"scope\": \"lessons\"")
    return res("S1-extra", "block", "Built Arabizi rows carry method + source; only her letters",
               "RULES.md S1 amendment 2026-09-23", bad, total=len(d.get("words", {})))


def check_s2_raw(root, raw):
    """S2: raw transcripts never edited. Each scribe*.provenance.json holds the response sha256 taken when the engine
    answered; the file on disk must still hash to it. Gap-fill transcripts are checked against the sha in data/runs."""
    rule, src = "Raw transcripts are byte-identical to what the engine returned", "RULES.md S2; ai_rules E1"
    rawp = Path(raw)
    if not rawp.is_dir():
        return res("S2-raw", "block", rule, src, skip=f"raw lessons dir {raw} not on this machine")
    bad, n = [], 0
    for p in sorted(rawp.glob("*/*.provenance.json")):
        try:
            want = J(p).get("response_sha256")
        except Exception as e:
            bad.append(f"{p.parent.name}/{p.name}: unreadable ({e})"); continue
        f = Path(str(p).replace(".provenance.json", ".json"))
        if not want:
            continue
        n += 1
        if not f.exists():
            bad.append(f"{p.parent.name}/{f.name}: raw transcript missing"); continue
        got = sha(f)
        if got != want:
            bad.append(f"{p.parent.name}/{f.name}: sha {got[:12]} != provenance {want[:12]}")
    for rp in sorted((root / "data" / "runs").glob("*.jsonl")):
        for line in open(rp, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("kind") != "ingest":
                continue
            for o in r.get("output_refs") or []:
                pth, want = o.get("path") or "", o.get("sha256")
                if not want or not re.search(r"scribe[^/]*\.json$", pth) or not os.path.exists(pth):
                    continue
                n += 1
                if sha(pth) != want:
                    bad.append(f"{pth}: sha changed since run {r.get('run_id', '')[:8]}")
    return res("S2-raw", "block", rule, src, bad, total=n,
               note=None if n else "no hashed raw transcript found")


def check_s3_signal(root, raw):
    """S3 / M1: a scored slip (audit kind grammar / vocab-A) needs Amal's signal - recast, no, prompt, named rule, chat
    fix, or Medi asking - or her ruling on the review page."""
    bad = []
    for r in audit_rows(root):
        if r.get("kind") not in A_KINDS:
            continue
        s = (r.get("signal") or "").strip().lower()
        if s in ("", "none"):
            bad.append(f"{r.get('uid')} {r.get('date')} {r.get('t')} {r.get('kind')}: no signal")
        elif s == "amal-ruling" and not isinstance(r.get("amal_ruling"), dict):
            bad.append(f"{r.get('uid')}: signal amal-ruling but no stored ruling")
    return res("S3-signal", "block", "A scored slip carries Amal's signal (or her ruling)", "RULES.md S3; ai_rules M1", bad)


def check_s4_pronunciation(root, raw):
    """S4: pronunciation is never a missed word. REPORT: SESSION-DECISIONS 09-21 says a confirmed wrong pronunciation
    scores 0 (8amee2), RULES.md S4 (09-22) says it never reduces a word's score - conflict for Medi. Also lists scored
    audit rows whose own reader note says it may be only pronunciation."""
    bad = []
    for e in wb_audit(root):
        if e.get("status") in ("Wrong", "Partial") and re.search(r"pronunc", e.get("reason") or "", re.I):
            bad.append(f"word bank {e.get('date')} {mmss(e.get('time'))} {e.get('word')}: {e.get('status')} for pronunciation")
    for r in audit_rows(root):
        if r.get("kind") in A_KINDS and re.search(r"(may|might) be (only )?(a )?(pronunciation|only a dropped)|"
                                                   r"pronunciation rather than", r.get("why") or "", re.I):
            bad.append(f"audit {r.get('uid')} {r.get('date')} {r.get('t')} {r.get('kind')}: scored; its note says maybe only pronunciation")
    return res("S4-pron", "report", "Pronunciation never reduces a word's score", "RULES.md S4 vs SESSION-DECISIONS 09-21",
               bad, note="open: Medi decides S4 vs 09-21 '8amee2 = 0'; the audit rows go to the Codex re-judge queue")


def check_s5_pause(root, raw):
    """S5 / M7: a pause is never the reason for a wrong or partial score."""
    bad = [f"word bank {e.get('date')} {mmss(e.get('time'))} {e.get('word')}: {e.get('status')} citing a pause"
           for e in wb_audit(root) if e.get("status") in ("Wrong", "Partial") and re.search(r"\bpaus", e.get("reason") or "", re.I)]
    bad += [f"audit {r.get('uid')}: scored citing a pause" for r in audit_rows(root)
            if r.get("kind") in A_KINDS and re.search(r"\bpaus(e|ed|ing)\b.{0,40}(error|mistake|wrong|slip)", r.get("why") or "", re.I)]
    return res("S5-pause", "block", "A pause is never scored as an error", "RULES.md S5; ai_rules M7; anees-medi-grammar-ykun-and-pauses", bad)


def check_medi_only(root, raw):
    """M11 / anees-only-medi-words-count: only Medi's own recorded speech is scored."""
    ev = wb_evidence(root)
    bad = [f"{e.get('date')} {mmss(e.get('time'))} {e.get('word')}: {e.get('status')} on a {ev[e['id']].get('speaker')!r} line"
           for e in wb_audit(root) if e.get("status") in SCORED and e.get("id") in ev and ev[e["id"]].get("speaker") != "Medi"]
    return res("M11-medi-only", "block", "Only Medi's own speech is scored", "ai_rules M11; anees-only-medi-words-count", bad)


def check_one_episode(root, raw):
    """SESSION-DECISIONS 09-21 'one retrieval episode, one result': two scored uses of one word <= 10 s apart where the
    later one's own note says it is the same episode / a repetition. REPORT: word-bank-review.json is not this audit's
    file; each pair needs a context read (the 15 s rule is a clue)."""
    S = sorted((e for e in wb_audit(root) if e.get("status") in SCORED and e.get("word")),
               key=lambda e: (e["date"], e["word"], float(e.get("time") or 0)))
    bad, clues = [], 0
    for a, b in zip(S, S[1:]):
        if a["date"] == b["date"] and a["word"] == b["word"] and float(b["time"]) - float(a["time"]) <= 10:
            clues += 1
            if EPISODE_SAYS_ONE.search(b.get("reason") or ""):
                bad.append(f"{a['date']} {a['word']} {mmss(a['time'])} {a['status']} + {mmss(b['time'])} {b['status']}"
                           f" (note: {EPISODE_SAYS_ONE.search(b['reason']).group(0)})")
    return res("EP-one-episode", "report", "One retrieval episode, one result", "SESSION-DECISIONS 2026-09-21", bad,
               total=clues, note=f"{clues} same-word pairs <= 10 s apart are clues; listed = the note itself says one episode. "
                                 "Fix = a word-bank-review.json patch per pair (owner: word bank)")


def check_grammar_only(root, raw):
    """SESSION-DECISIONS: grammar-only events are null for vocabulary. REPORT: events the evidence marks grammar_only
    that a later review scored (two reviews disagree; the later one currently wins)."""
    ev = wb_evidence(root)
    bad = [f"{e.get('date')} {mmss(e.get('time'))} {e.get('word')}: evidence grammar_only, word bank {e.get('status')}"
           for e in wb_audit(root) if e.get("status") in SCORED and ev.get(e.get("id"), {}).get("grammar_only")]
    return res("GO-grammar-null", "report", "Grammar-only events score nothing for vocabulary", "SESSION-DECISIONS 2026-09-21",
               bad, note="open: each is a mixed incident per the 09-28 review note; the stale grammar_only flag should be "
                         "cleared or the score dropped (owner: word bank)")


def check_15s_clue(root, raw):
    """anees-15s-rule-is-a-clue: a machine 'Amal said it within 15 s -> helped' flag counts only after a context read."""
    bad = [f"{e.get('date')} {mmss(e.get('time'))} {e.get('word')}: {e.get('status')} from the 15 s rule, no context read"
           for e in wb_audit(root) if e.get("status") in SCORED and re.search(r"within 15 seconds", e.get("reason") or "")
           and not re.search(r"context review|Claude audit|Codex|hand", e.get("reason") or "")]
    return res("15S-clue", "report", "The 15 s rule is a clue: no score from it without a context read",
               "anees-15s-rule-is-a-clue (2026-09-25)", bad,
               note="open: new lessons (09-26, 09-28) get no context read of Word Bank flags; needs a review step in "
                    "review_lesson.py / review_new_lessons.py (not this audit's files)")


def check_glue(root, raw):
    """WS-19 (Medi 2026-10-02: "the glue words should be added to the doc, bring to her attention"; amends ai_rules M3
    "never graded"): a glue word is graded only once it is on Amal's Doc. BLOCK: a graded Word Bank use of a glue word
    that is not on her Doc (docs/data/words.json keys / Arabizi / aliases). Glue words on her Doc keep being graded."""
    import glue_words
    p = root / "docs" / "data" / "words.json"
    keys = glue_words.doc_keys(J(p)) if p.exists() else set()
    graded = [e for e in wb_audit(root) if e.get("status") in SCORED and (e.get("word") or "").lower() in GLUE]
    bad = [f"{e.get('date')} {mmss(e.get('time'))} {e.get('word')}: {e.get('status')} but not on Amal's Doc"
           for e in graded if (e.get("word") or "").lower() not in keys]
    return res("WS19-glue", "block", "A glue word (shu, bas, tamam ...) is graded only once it is on Amal's Doc",
               "WS-19, Medi 2026-10-02 (amends ai_rules M3)", bad,
               note=f"{len(graded) - len(bad)} graded uses of glue words that are on her Doc keep counting; glue words not on her "
                    f"Doc go on her Tutor hub New words card (scripts/glue_words.py)")


def check_new_signal(root, raw):
    """anees-new-bucket-definition: 'new' = only words Amal (or Medi) marked new; nothing inferred."""
    marks = set()
    for p in sorted((root / "data" / "decisions").glob("*.jsonl")):
        for line in open(p, encoding="utf-8"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("who") in ("Amal", "Medi") and str(d.get("answer")).lower() == "new":
                marks.add((str(d.get("about_id")).lower(), (d.get("source_row") or {}).get("lesson_date")))
    keys = {k for k, _ in marks}
    bad = []
    for L in J(root / "docs" / "data" / "lessons.json")["lessons"]:
        for w in L.get("new_words") or []:
            k = str(w.get("key") or "").lower()
            if k not in keys:
                bad.append(f"{L['date']} new word {k!r}: no Amal/Medi 'new' mark in data/decisions")
    return res("NEW-amal-signal", "block", "'New' words come only from an Amal/Medi mark", "anees-new-bucket-definition", bad,
               total=len(marks))


def check_sheet_meaning(root, raw):
    """anees-list-by-meaning: every lesson with vocab rows gets a by-meaning sheet read (data/lesson-work/sheet-verdicts.json).
    REPORT: the hourly review has no sheet-reader step yet, so a new lesson is string-matched only."""
    ver = {v.get("date") for v in J(root / "data" / "lesson-work" / "sheet-verdicts.json")}
    dates = sorted({r["date"] for r in audit_rows(root) if r.get("kind") in ("vocab-A", "vocab-B")})
    bad = [f"{d}: vocab rows but no by-meaning sheet verdicts" for d in dates if d not in ver]
    return res("SHEET-meaning", "report", "List membership judged by meaning (sheet verdicts) for every lesson",
               "anees-list-by-meaning (2026-09-27)", bad,
               note="open: add a sheet-reader step to review_lesson.py (not this audit's file)")


def check_hub_removed(root, raw):
    """Medi 2026-09-28: Amal's Tutor Hub page and every 'Amal's hub' button are gone and must not come back."""
    bad = []
    if (root / "docs" / "amal" / "hub.html").exists():
        bad.append("docs/amal/hub.html exists")
    for p in list((root / "docs").glob("*.html")) + list((root / "docs" / "amal").glob("*.html")) + list((root / "docs" / "js").glob("*.js")):
        s = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"amal/hub\.html|Amal(&#39;|'|’)s hub|Tutor Hub", s):
            ctx = s[max(0, m.start() - 80): m.end() + 80]
            if re.search(r"removed|retired|was removed", ctx, re.I):
                continue                                  # a comment recording the removal is fine
            bad.append(f"{p.relative_to(root).as_posix()}: '{m.group(0)}'")
    return res("HUB-removed", "block", "No Amal's Tutor Hub page or 'Amal's hub' button",
               "Medi 2026-09-28 (17f2e97); PROMPT 09-29 decision 5", bad)


def check_medi_only_email(root, raw):
    """ai_rules A1: code never contacts Amal. The one mail sender hard-codes Medi; nothing else sends mail."""
    bad = []
    s = (root / "scripts" / "send_lesson_email.mjs").read_text(encoding="utf-8")
    m = re.search(r"const TO\s*=\s*'([^']+)'", s)
    if not m or m.group(1) != MEDI_EMAIL:
        bad.append(f"send_lesson_email.mjs TO = {m.group(1) if m else None!r}, not Medi")
    for p in sorted(glob.glob(str(root / "scripts" / "*.*"))) + sorted(glob.glob(str(root / "supabase" / "functions" / "*" / "*.ts"))):
        if p.endswith(("send_lesson_email.mjs", "check_rules.py")) or not p.endswith((".py", ".mjs", ".cjs", ".js", ".ts", ".ps1")):
            continue
        t = open(p, encoding="utf-8", errors="ignore").read()
        if re.search(r"nodemailer|smtplib|Send-MailMessage|api\.twilio|graph\.facebook\.com/.+/messages|api\.resend", t):
            bad.append(f"{os.path.basename(p)}: sends mail/messages outside send_lesson_email.mjs")
    return res("A1-medi-only", "block", "Code never contacts Amal (only Medi is emailed)", "ai_rules A1; PROMPT 09-29", bad)


def check_budget(root, raw):
    """ai_rules H4: paid calls stop at 90 % of each cap."""
    p = root / "data" / "budget.json"
    if not p.exists():
        return res("H4-budget", "block", "Paid calls stop at 90 % of the budget", "ai_rules H4", skip="data/budget.json missing")
    L = J(p)
    bad = [f"{k}: {float(L.get(k, 0)):.2f} of {c:.0f} USD (>= 90 %)" for k, c in CAPS.items() if float(L.get(k, 0) or 0) >= 0.9 * c]
    return res("H4-budget", "block", "Paid calls stop at 90 % of the budget", "ai_rules H4", bad)


def check_rules_json(root, raw):
    """RULES.md is the source; docs/data/standing-rules.json (System Settings) must say the same thing."""
    src = (root / "RULES.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    _, _, rest = src.partition("\n---\n")
    want = {}
    for block in re.split(r"\n(?=## )", "\n" + rest):
        block = block.strip()
        m = re.match(r"## (S\d+)\s+[—-]\s+(.+)\n", block)
        if m:
            want[m.group(1)] = re.sub(r"\n---\s*$", "", block[m.end():].strip()).strip()
    got = {r["id"]: r["body_md"] for r in J(root / "docs" / "data" / "standing-rules.json").get("rules", [])}
    bad = [f"{k}: {'missing on the page' if k not in got else 'page text differs from RULES.md'}"
           for k in sorted(want) if got.get(k) != want[k]]
    bad += [f"{k}: on the page but not in RULES.md" for k in sorted(set(got) - set(want))]
    return res("RULES-json-sync", "block", "System Settings shows RULES.md exactly (run scripts/build_standing_rules.py)",
               "RULES.md header", bad)


def check_ai_logged(root, raw):
    """AI review 09-27 build #1: every AI call path writes a run line (scripts/track.py). A file that calls a paid AI
    endpoint or `claude -p` must import track, or be listed in UNTRACKED_AI_OK with its reason."""
    bad = []
    for p in sorted(glob.glob(str(root / "scripts" / "**" / "*.py"), recursive=True)):
        name = os.path.basename(p)
        if name in ("track.py", "check_rules.py") or name.startswith("test_") or "__pycache__" in p:
            continue
        t = open(p, encoding="utf-8", errors="ignore").read()
        if AI_CALL.search(t) and not re.search(r"^\s*(import track|from track import|import track as)", t, re.M) \
                and "track.run(" not in t and name not in UNTRACKED_AI_OK:
            bad.append(f"scripts/{os.path.relpath(p, root / 'scripts').replace(os.sep, '/')}: calls an AI endpoint without scripts/track.py")
    return res("AI-logged", "block", "Every AI call path logs a run (data/runs)", "AI-ENGINEERING-REVIEW-2026-09-27 #1", bad,
               note=f"{len(UNTRACKED_AI_OK)} untracked files allowed with a reason (manual/retired); see UNTRACKED_AI_OK")


def check_ai_model(root, raw):
    """Every claude inference run records the model that answered; a pinned run must be answered by the pinned model."""
    bad, n = [], 0
    for rp in sorted((root / "data" / "runs").glob("*.jsonl")):
        for line in open(rp, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("kind") != "inference" or r.get("gen_ai.provider.name") != "anthropic" or r.get("status") != "ok":
                continue
            n += 1
            req, resp = r.get("gen_ai.request.model"), r.get("gen_ai.response.model")
            if not resp:
                bad.append(f"{r.get('step')} {r.get('lesson_date')} {r.get('run_id', '')[:8]}: no response model logged")
            elif req and req != resp:
                bad.append(f"{r.get('step')} {r.get('lesson_date')}: asked {req}, answered by {resp}")
    return res("AI-model", "block", "Every Claude run logs its model; pinned runs use the pinned model",
               "AI-ENGINEERING-REVIEW-2026-09-27 #1", bad, total=n)


def check_ai_paid_logged(root, raw):
    """Every paid call in the budget ledger (data/budget.json) since the run log started has its run line (same cost,
    within 14 h - the ledger clock is local, the run log is UTC)."""
    import datetime as dt
    rule, src = "Every paid AI call since 2026-09-28 has a run line", "AI-ENGINEERING-REVIEW-2026-09-27 #1"
    runs = []
    for rp in sorted((root / "data" / "runs").glob("*.jsonl")):
        for line in open(rp, encoding="utf-8"):
            try:
                runs.append(json.loads(line))
            except Exception:
                pass
    bp = root / "data" / "budget.json"
    if not runs or not bp.exists():
        return res("AI-paid-logged", "block", rule, src, skip="no run log or no budget ledger")
    ts = lambda s: dt.datetime.fromisoformat(str(s).replace("Z", "")[:19])
    first = min(ts(r["started_at"]) for r in runs if r.get("started_at"))
    bad, n = [], 0
    for c in J(bp).get("calls", []):
        try:
            t = ts(c["t"])
        except Exception:
            continue
        if t < first - dt.timedelta(hours=12):
            continue
        n += 1
        if not any(r.get("cost_usd") is not None and abs(float(r["cost_usd"]) - float(c.get("usd") or 0)) < 0.00015
                   and abs((ts(r["started_at"]) - t).total_seconds()) < 14 * 3600 for r in runs):
            bad.append(f"{c['t']} {c.get('service')} {c.get('usd')} USD: no run line")
    return res("AI-paid-logged", "block", rule, src, bad, total=n)


AMAL_FILES = ("docs/amal/*.html", "docs/tutor.html", "docs/data/tutor.json", "docs/js/tutor*.js", "docs/js/hub/*.js",
              "docs/js/amal-*.js")
OFFSITE = re.compile(r"https?://(?:[\w-]+\.)*(?:claude\.ai|anthropic\.com|chatgpt\.com|openai\.com|"
                     r"docs\.google\.com|drive\.google\.com|notion\.so)\b[^\s\"'<>)]*", re.I)


def check_amal_onsite(root, raw):
    """Nothing Amal opens leaves Anees: no claude.ai / Google Docs / Drive / login-only link on her pages (Medi 2026-10-01/02)."""
    rule = "Amal's pages and Tutor data link only to Anees itself (no claude.ai, Google Docs/Drive or other login-only site)"
    src = "Medi 2026-10-01 'DOnt make it a different workflow or off site'; registry AM-13"
    bad = []
    for pat in AMAL_FILES:
        for f in sorted(glob.glob(str(root / pat))):
            text = Path(f).read_text(encoding="utf-8", errors="replace")
            for m in OFFSITE.finditer(text):
                bad.append(f"{Path(f).relative_to(root).as_posix()}: {m.group(0)[:80]}")
    return res("AMAL-onsite", "block", rule, src, bad)


CHECKS = [check_s1_guard, check_s1_extra, check_s2_raw, check_s3_signal, check_s4_pronunciation, check_s5_pause,
          check_medi_only, check_one_episode, check_grammar_only, check_15s_clue, check_glue, check_new_signal,
          check_sheet_meaning, check_hub_removed, check_medi_only_email, check_budget, check_rules_json,
          check_ai_logged, check_ai_model, check_ai_paid_logged, check_amal_onsite]


def run_all(root=ROOT, raw=DEFAULT_RAW, only=None):
    out = []
    for fn in CHECKS:
        try:
            r = fn(Path(root), raw)
        except FileNotFoundError as e:
            r = res(fn.__name__.replace("check_", ""), "block", fn.__doc__.strip().splitlines()[0], "", skip=f"input missing: {e.filename}")
        except Exception as e:                        # a crashing check is a failure, never a silent pass
            r = res(fn.__name__.replace("check_", ""), "block", fn.__doc__.strip().splitlines()[0], "", [f"check crashed: {type(e).__name__}: {e}"])
        if only and r["id"] not in only:
            continue
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--raw", default=DEFAULT_RAW)
    ap.add_argument("--json")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    results = run_all(a.root, a.raw, a.only)
    fails = [r for r in results if r["status"] == "fail"]
    if fails:
        f = fails[0]
        print(f"check_rules: FAIL {f['id']}: {f['count']} violation(s) - {f['examples'][0]}")
    else:
        opn = [r for r in results if r["status"] == "open"]
        print(f"check_rules: OK - {sum(r['status'] == 'pass' for r in results)} pass, {len(opn)} open (report only), "
              f"{sum(r['status'] == 'skip' for r in results)} skip")
    for r in results:
        tag = {"pass": "PASS", "fail": "FAIL", "open": "OPEN", "skip": "SKIP"}[r["status"]]
        extra = f" ({r['total']} checked)" if r.get("total") is not None else ""
        print(f"  {tag:4} {r['level']:6} {r['id']:16} {r['count']:4}  {r['rule']}{extra}")
        if r["skip"]:
            print(f"         skip: {r['skip']}")
        for ex in r["examples"][:3]:
            print(f"         - {ex}")
        if r["status"] == "open" and r.get("note"):
            print(f"         {r['note']}")
    if a.json:
        Path(a.json).write_text(json.dumps({"results": results}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
