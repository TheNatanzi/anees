# -*- coding: utf-8 -*-
"""Codex re-judges the uncertain rows against the AUDIO (Medi's decision 5, 2026-09-29).

Every row in data/accuracy/verification-queue.json (a scored row the Claude readers were unsure of) gets:
  1. clips cut with ffmpeg from the RAW recordings (C:\\dev\\anees\\data\\lessons\\<date>): each person's own track for
     listen_from..listen_to, plus the mixed lesson recording (mixed-only lessons: that is the only audio)
  2. an independent, non-Claude transcription of every clip: local faster-whisper large-v3 AND the Levantine dialect
     whisper (C:\\dev\\anees\\models\\dialect-ct2), language ar, NO prompt (a prompt would bias it toward the right form)
  3. Codex (gpt-5.5, `codex exec -m gpt-5.5`, never a Claude model) reads the Claude readers' row, the transcript lines
     around it, and both independent transcriptions, and rules: confirmed / changed / rejected / unsure + reason
  4. one append-only record per row in data/accuracy/verifications.json (reviewer "codex gpt-5.5", role second-judge,
     method audio, evidence = window, clip hashes, the independent transcription, the quote Codex relied on)

scripts/accuracy_gates.py then treats: Codex confirmed/changed = the row stands (eligible); Codex rejected/unsure =
the two AIs disagree -> the row stays pending and goes to Amal's list on the Tutor page (docs/data/amal-verify.json);
only her answer (or Medi's) settles it.

    python scripts/codex_rejudge.py                 # every queue row without a Codex record (resumable)
    python scripts/codex_rejudge.py --limit 16      # the first 16 of those
    python scripts/codex_rejudge.py --asr-only      # cut clips + transcribe, no Codex calls
    python scripts/codex_rejudge.py --list          # just (re)build docs/data/amal-verify.json from the ledger

Cost: $0 in API fees (local ASR; Codex runs on the ChatGPT plan). Every Codex call is logged to data/runs (track.py).
"""
import argparse, datetime as dt, hashlib, json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import accuracy_gates as G  # noqa: E402
import source_audit as S  # noqa: E402

QUEUE_P = os.path.join(REPO, "data", "accuracy", "verification-queue.json")
LEDGER_P = os.path.join(REPO, "data", "accuracy", "verifications.json")
ASR_P = os.path.join(REPO, "data", "accuracy", "asr-evidence.json")
CLIPS = os.path.join(REPO, "data", "accuracy", "clips")              # *.mp3 is git-ignored; hashes go in the ledger
AMAL_LIST_P = os.path.join(REPO, "docs", "data", "amal-verify.json")
DIALECT = os.environ.get("ANEES_DIALECT_CT2", r"C:\dev\anees\models\dialect-ct2")
CODEX_MODEL = "gpt-5.5"
REVIEWER = f"codex {CODEX_MODEL}"
BATCH = 6
VERDICTS = ("confirmed", "changed", "rejected", "unsure")


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def W(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, p)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ clips
def window(q):
    a, b = G.sec(q.get("listen_from")), G.sec(q.get("listen_to"))
    if a is None or b is None or b <= a:
        t = G.sec(q.get("t")) or G.sec(q.get("t_amal")) or 0
        a, b = max(0, t - 10), t + 25
    return max(0.0, a), min(b, a + 60.0)                  # at most 60 s: a longer clip loses the moment


def audio_sources(date, attribution):
    """[(label, file, offset_on_lesson_clock)] - own tracks when the transcript came from them, and the mixed lesson."""
    out = []
    segs = S.segments(date)
    if segs and attribution == "per-speaker-tracks":
        for p in S.PEOPLE:
            for s in segs[p]:
                if s["status"] != "lost" and os.path.exists(s["file"]):
                    out.append((p, s["file"], s["offset"], s["duration_s"]))
    mixed = S.MIXED_AUDIO.get(date) or os.path.join(REPO, "docs", "lessons", date, "audio", "lesson.mp3")
    if os.path.exists(mixed):
        out.append(("mixed", mixed, 0.0, 1e9))
    return out


def cut(src, off, a, b, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    ss = max(0.0, a - off)
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.2f}", "-t", f"{b - a:.2f}", "-i", src, "-ac", "1", "-ar", "16000",
                        "-b:a", "48k", dest], capture_output=True, timeout=120)
    return dest if r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1000 else None


def clips_for(q, lesson):
    a, b = window(q)
    out = []
    for label, src, off, dur in audio_sources(q["date"], (lesson.get("source") or {}).get("attribution")):
        if not (off - 1 <= a and b <= off + dur + 1) and label != "mixed":
            if b < off or a > off + dur:
                continue                                     # this segment does not cover the window
        dest = os.path.join(CLIPS, q["date"], f"{q['uid']}_{label}_{os.path.splitext(os.path.basename(src))[0][:24]}.mp3")
        c = cut(src, off, max(a, off), min(b, off + dur), dest)
        if c:
            out.append({"who": label, "file": os.path.relpath(c, REPO).replace("\\", "/"), "sha256": sha(c),
                        "from": round(max(a, off), 2), "to": round(min(b, off + dur), 2), "source": os.path.basename(src)})
    return out


# ------------------------------------------------------------------------------------------------ ASR
_models = {}


def model(name):
    if name not in _models:
        import torch                                        # its lib folder holds cublas64_12.dll that CTranslate2 needs
        os.add_dll_directory(os.path.join(os.path.dirname(torch.__file__), "lib"))
        from faster_whisper import WhisperModel
        path = "large-v3" if name == "large-v3" else DIALECT
        _models[name] = WhisperModel(path, device="cuda", compute_type="float16")
    return _models[name]


def transcribe(path, name, t0):
    segs, _ = model(name).transcribe(os.path.join(REPO, path), language="ar", beam_size=5, vad_filter=False,
                                     condition_on_previous_text=False, temperature=0.0)
    return [{"t": G.mmss(t0 + s.start), "text": s.text.strip()} for s in segs if s.text.strip()]


def asr_for(q, lesson, cache):
    key = q["uid"]
    if key in cache and cache[key].get("clips"):
        return cache[key]
    clips = clips_for(q, lesson)
    for c in clips:
        c["asr"] = {}
        for name in ("large-v3", "dialect"):
            try:
                c["asr"][name] = transcribe(c["file"], name, c["from"])
            except Exception as e:                           # a missing model is recorded, never guessed around
                c["asr"][name] = {"error": str(e)[:200]}
    cache[key] = {"uid": key, "date": q["date"], "window": [round(x, 2) for x in window(q)], "clips": clips,
                  "asr_models": {"large-v3": "Systran/faster-whisper-large-v3 (local, fp16, language ar, no prompt)",
                                 "dialect": "oddadmix/whisper-large-v3-turbo-arabic-dialectal (local CTranslate2, no prompt)"},
                  "at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    return cache[key]


# ------------------------------------------------------------------------------------------------ Codex
BRIEF = """You are an independent second judge (not the AI that wrote these rows) checking an Arabic-lesson audit.
Medi is an adult learner of Palestinian Levantine Arabic; Amal is his tutor. Two AI readers read the lesson TRANSCRIPT
(ElevenLabs Scribe v2 speech-to-text, one transcript per person's own microphone) and wrote each row below as a mistake
Medi made that Amal signalled (corrected, recast, said no, supplied the word, or prompted until he fixed it). They were
unsure about these rows. You get, per row: their claim, the transcript lines around it (lesson clock mm:ss), and an
INDEPENDENT transcription of the actual audio of each person's own track for that window by two other speech models
(whisper large-v3 and a Levantine-dialect whisper; no prompt). Rule on each row from this evidence.

How to weigh the evidence:
- Speech models tend to AUTO-CORRECT a learner (they write the correct form he meant). So an independent transcription
  that shows the right form is WEAK evidence against the row. Strong evidence FOR: Amal right afterwards corrects,
  recasts, says la/no, gives the form, or he repeats her form. Strong evidence AGAINST: the line is Amal's not Medi's;
  nothing like it was said at that time in either transcription; Amal did not react as a correction at all (she was just
  talking, or confirming); the only difference is pronunciation of one sound (dropped ع/ط/ق, a root letter slip) or a
  pause/restart/self-fix before she helped - those are NOT errors; spelling variants are NOT errors.
- The readers' quotes and reasons are their reading of the same transcript and can be wrong. Decide from the transcript
  lines and the independent transcriptions yourself; if those do not show the correction, do not confirm on the readers' word.
- When Amal echoes what he said, her echo shows what he really said (it beats the transcript).
- "tier 0 / signal asked" rows are words he did not know and she supplied: confirm them if she really supplied the word
  he asked for or reached for.
- Latin letters in a transcript line are the engine writing Arabic sounds in Latin; read them as Arabic.

Verdicts (exactly one per row):
- confirmed : the mistake happened as described and Amal signalled it.
- changed   : Medi made a mistake at that moment that Amal signalled, but the wrong or right piece is different - give yours.
- rejected  : no such mistake (say which: not Medi / no correction / pronunciation only / self-fix / not said / other).
- unsure    : the audio evidence cannot decide (e.g. both transcriptions are garbled there).
Be strict and honest; do not confirm to be agreeable. Keep reason to one or two sentences, in English, quoting the
Arabic you relied on.

Return ONLY a JSON object: {"rulings": [{"uid": "...", "verdict": "...", "confidence": "high|medium|low",
"reason": "...", "quote": "the words (from either source) that decide it", "wrong": "only for changed", "right": "only for changed"}]}
with one ruling for every uid below, nothing else.
"""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["rulings"],
          "properties": {"rulings": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                                 "required": ["uid", "verdict", "confidence", "reason", "quote", "wrong", "right"],
                                                                 "properties": {"uid": {"type": "string"}, "verdict": {"type": "string", "enum": list(VERDICTS)},
                                                                                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                                                                                "reason": {"type": "string"}, "quote": {"type": "string"},
                                                                                "wrong": {"type": ["string", "null"]}, "right": {"type": ["string", "null"]}}}}}}


def context_lines(detail, a, b):
    out = []
    for t in detail.get("turns", []):
        if a - 15 <= t.get("t", -1) <= b + 15:
            out.append(f"[{G.mmss(t['t'])}] {t.get('who')}: {t.get('text')}")
    return out


def row_block(q, audit_row, detail, ev, bucket_names):
    a, b = window(q)
    r = audit_row or {}
    kind = q.get("kind")
    lab = (f"grammar rule {q.get('bucket')} ({bucket_names.get(q.get('bucket'), '')})" if kind == "grammar"
           else f"vocabulary, tier {q.get('tier')} (0 = did not know, 1 = wrong word, 2 = wrong form, 3 = English word for an Arabic word on her sheet)")
    L = [f"### uid {q['uid']}  lesson {q['date']}  Medi's line at {q.get('t')}  Amal's fix at {q.get('t_amal')}",
         f"Claim ({lab}; signal {r.get('signal')}; readers' confidence {r.get('confidence')}): Medi said WRONG «{q.get('wrong')}» where the right form is «{q.get('right')}».",
         f"Readers' reason: {r.get('why') or r.get('mistake') or ''}",
         f"Readers quoted Medi: «{q.get('medi_said')}»   Amal: «{q.get('amal_said')}»" + (f"   Amal typed in chat: «{r.get('chat')}»" if r.get("chat") else ""),
         f"Why it was flagged for a check: {'; '.join(q.get('why_check') or [])}",
         f"Transcript {G.mmss(a - 15)}-{G.mmss(b + 15)}:"]
    L += ["  " + x for x in context_lines(detail, a, b)] or ["  (no transcript lines)"]
    for c in ev.get("clips", []):
        who = {"Medi": "Medi's own microphone", "Amal": "Amal's own microphone", "mixed": "the mixed recording (both voices)"}[c["who"]]
        for name, lines in (c.get("asr") or {}).items():
            if isinstance(lines, dict):
                continue
            L.append(f"Independent transcription, {who}, {G.mmss(c['from'])}-{G.mmss(c['to'])}, model {name}:")
            L += [f"  [{x['t']}] {x['text']}" for x in lines] or ["  (nothing heard)"]
    return "\n".join(L)


def codex(prompt, workdir):
    schema = os.path.join(workdir, "schema.json")
    out = os.path.join(workdir, f"out-{int(time.time() * 1000)}.json")
    with open(schema, "w", encoding="utf-8") as f:
        json.dump(SCHEMA, f)
    import shutil
    exe = shutil.which("codex") or shutil.which("codex.cmd") or "codex"      # codex.cmd on Windows
    r = subprocess.run([exe, "exec", "-m", CODEX_MODEL, "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
                        "-C", workdir, "--output-schema", schema, "-o", out, "-"], input=prompt.encode("utf-8"),
                       capture_output=True, timeout=900)
    txt = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
    m = re.search(r"\{.*\}", txt, re.S)
    if r.returncode or not m:
        raise RuntimeError(f"codex exit {r.returncode}: {r.stderr.decode('utf-8', 'replace')[-400:]} | {txt[:200]}")
    tok = re.search(rb"tokens used\s*\n?\s*([\d,]+)", r.stdout + r.stderr)
    return json.loads(m.group(0)), (int(tok.group(1).replace(b",", b"")) if tok else None)


# ------------------------------------------------------------------------------------------------ ledger
def codex_done(ledger):
    return {r["uid"] for r in ledger.get("records", []) if r.get("reviewer") == REVIEWER}


def record(q, ev, ruling, run_id):
    a, b = window(q)
    heard = {}
    for c in ev.get("clips", []):
        v = (c.get("asr") or {}).get("large-v3")
        if isinstance(v, list):
            heard[c["who"]] = " ".join(x["text"] for x in v)[:400]
    rec = {"uid": q["uid"], "date": q["date"], "kind": q.get("kind"), "method": "audio",
           "method_detail": "independent ASR of the raw clip (faster-whisper large-v3 + Levantine dialect whisper, no prompt) + the transcript lines, judged by Codex",
           "reviewer": REVIEWER, "role": "second-judge", "verdict": ruling["verdict"], "confidence": ruling.get("confidence") or "low",
           "reason": ruling.get("reason"),
           "evidence": {"t_start": round(a, 2), "t_end": round(b, 2), "quote": ruling.get("quote"),
                        "clips": [{k: c[k] for k in ("who", "file", "sha256", "source")} for c in ev.get("clips", [])],
                        "independent_asr_large_v3": heard},
           "claim": {"wrong": q.get("wrong"), "right": q.get("right"), "bucket": q.get("bucket"), "tier": q.get("tier")},
           "at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "run_id": run_id}
    if ruling["verdict"] == "changed":
        rec["changed_to"] = {"wrong": ruling.get("wrong"), "right": ruling.get("right")}
    return rec


def append_records(recs):
    L = J(LEDGER_P, None) or {"about": LEDGER_ABOUT, "records": []}
    L.setdefault("about", LEDGER_ABOUT)
    L["records"].extend(recs)
    W(LEDGER_P, L)


LEDGER_ABOUT = ("Append-only verification ledger (scripts/accuracy_gates.py reads it). One record per check of one audit row: uid, "
                "method audio|human, reviewer, role (second-judge = Codex re-judging against the audio; human = Amal or Medi), "
                "verdict confirmed|changed|rejected|unsure, confidence, reason, evidence {t_start, t_end, quote, clips + hashes}, at. "
                "A later record never edits an earlier one; the latest HUMAN record settles a row, else the latest second-judge record.")


# ------------------------------------------------------------------------------------------------ Amal's list
def amal_list(queue_rows=None, ledger=None, audit=None, repo=REPO, hold=None):
    """Rows where Codex (audio) and the Claude readers disagree and no human has ruled -> docs/data/amal-verify.json.
    Same card pattern as her review page: 'Correction is correct' / 'Reason not to correct' + a box."""
    ledger = ledger if ledger is not None else J(LEDGER_P, {"records": []})
    audit = audit if audit is not None else J(os.path.join(repo, "data", "full-audit-2026-09-26.json"))
    rows = {r["uid"]: r for r in audit.get("rows", [])}
    st = G.ledger_state(ledger)
    items, answered = [], []
    import amal_hold
    if hold is None:                     # the hold (scripts/amal_hold.py); no hold file = nothing is skipped
        hold = amal_hold.Hold()
    for uid, s in st.items():
        h = s.get("human")
        # AM-17: a moment Amal answered on the Tutor page stays listed as answered (with her answer and Undo); any other
        # human ruling takes it off her list
        mine = bool(h) and h.get("reviewer") == "Amal" and "Tutor page" in str(h.get("source") or "")
        if h and not mine:
            continue
        c = s.get("second_judge")
        if not c or c["verdict"] not in ("rejected", "unsure"):
            continue
        r = rows.get(uid) or {}
        if r.get("kind") not in G.SCORED_KINDS:
            continue
        if not mine and amal_hold.AlreadyRuled().uid(uid):       # a re-read row at a moment she already ruled on: the owner's list (round 5)
            continue
        if not mine and hold.blocks("verify", uid, uid=uid, date=r.get("date")):     # created or changed by the 2026-10-04 re-read: not asked of Amal until Medi's OK
            continue
        t = G.sec(r.get("t")) or G.sec(r.get("t_amal")) or c["evidence"]["t_start"]
        (answered if mine else items).append({"id": "verify:" + uid, "uid": uid, "date": c.get("date") or r.get("date"), "t": r.get("t"), "t_amal": r.get("t_amal"),
                      "kind": r.get("kind"), "bucket": r.get("bucket"), "tier": r.get("tier"),
                      "medi_said": r.get("medi_said"), "amal_said": r.get("amal_said"), "chat": r.get("chat"),
                      "wrong": r.get("wrong"), "right": r.get("right"), "english": r.get("english"),
                      "readers_say": r.get("why") or r.get("mistake"), "codex_says": c.get("reason"), "codex_verdict": c["verdict"],
                      "audio": (f"lessons/{c.get('date') or r.get('date')}/audio/lesson.mp3#t={max(0, int(c['evidence']['t_start']))},{int(c['evidence']['t_end']) + 1}"
                                if os.path.exists(os.path.join(repo, "docs", "lessons", c.get("date") or r.get("date") or "-", "audio", "lesson.mp3")) else None),
                      "sec": t, **({"answered": {"kind": "audit_confirm" if h["verdict"] == "confirmed" else "audit_skip",
                                                 "reason": None if h["verdict"] == "confirmed" else h.get("reason"), "at": h.get("at")}}
                                   if mine else {})})
    items.sort(key=lambda x: (x["date"] or "", x["sec"] or 0))
    answered.sort(key=lambda x: (x["date"] or "", x["sec"] or 0))
    return {"about": "Rows two AIs disagree on (Claude readers: a mistake Amal signalled; Codex, listening to an independent transcription "
                     "of the audio: not so, or cannot tell). Built by scripts/codex_rejudge.py. Amal answers on the Tutor page; her "
                     "'Correction is correct' makes the row a scored mistake, her reason drops it (scripts/apply_amal_audit_rulings.py).",
            "built": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "count": len(items), "items": items,
            "answered": answered}


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--asr-only", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--batch", type=int, default=BATCH)
    a = ap.parse_args(argv)
    if a.list:
        L = amal_list()
        W(AMAL_LIST_P, L)
        print("Amal's list:", L["count"], "rows")
        return 0
    Q = J(QUEUE_P)["rows"]
    ledger = J(LEDGER_P, {"records": []})
    done = codex_done(ledger)
    todo = [q for q in Q if q["uid"] not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"queue {len(Q)} | already re-judged by Codex {len(done & {q['uid'] for q in Q})} | to do now {len(todo)}")
    lessons = {L["date"]: L for L in J(os.path.join(REPO, "docs", "data", "lessons.json"))["lessons"]}
    audit = J(os.path.join(REPO, "data", "full-audit-2026-09-26.json"))
    rows = {r["uid"]: r for r in audit["rows"]}
    bnames = {b["id"]: b.get("name") or b.get("title") or "" for b in J(os.path.join(REPO, "docs", "data", "grammar-buckets.json"))["buckets"]}
    cache = J(ASR_P, {"about": "Independent (non-Claude) transcriptions of the clips behind each checked row (scripts/codex_rejudge.py).", "rows": {}})
    details = {}
    for i, q in enumerate(todo, 1):
        asr_for(q, lessons[q["date"]], cache["rows"])
        if i % 10 == 0 or i == len(todo):
            W(ASR_P, cache)
            print(f"  asr {i}/{len(todo)}", flush=True)
    W(ASR_P, cache)
    if a.asr_only:
        return 0
    import track
    work = tempfile.mkdtemp(prefix="anees-codex-")
    n_ok = n_fail = 0
    for k in range(0, len(todo), a.batch):
        chunk = todo[k: k + a.batch]
        blocks = []
        for q in chunk:
            if q["date"] not in details:
                details[q["date"]] = J(os.path.join(REPO, "docs", "data", "lessons", q["date"] + ".json"))
            blocks.append(row_block(q, rows.get(q["uid"]), details[q["date"]], cache["rows"][q["uid"]], bnames))
        prompt = BRIEF + "\n\n" + "\n\n".join(blocks)
        with track.run("accuracy.codex_rejudge", lesson_date=chunk[0]["date"], kind="inference", role="second-judge",
                       provider="openai-codex", request_model=CODEX_MODEL, prompt_sha=hashlib.sha256(BRIEF.encode()).hexdigest(),
                       inputs=[QUEUE_P, ASR_P], outputs=[LEDGER_P], params={"rows": len(chunk)}) as run:
            try:
                out, toks = codex(prompt, work)
                run.set(status="ok", usage={"total_tokens": toks}, cost_usd=0.0, cost_basis="ChatGPT plan (codex exec), no API fee")
            except Exception as e:
                run.set(status="error", error_type=type(e).__name__)
                print("  !! codex failed on", [q["uid"] for q in chunk], str(e)[:300], flush=True)
                n_fail += len(chunk)
                continue
            rid = run.get("run_id") if hasattr(run, "get") else None
        by = {x.get("uid"): x for x in out.get("rulings", [])}
        recs = []
        for q in chunk:
            x = by.get(q["uid"])
            if not x or x.get("verdict") not in VERDICTS:
                n_fail += 1
                print("  !! no ruling for", q["uid"])
                continue
            recs.append(record(q, cache["rows"][q["uid"]], x, rid))
        append_records(recs)
        n_ok += len(recs)
        print(f"  codex {k + len(chunk)}/{len(todo)}: " + " ".join(f"{r['uid'][-4:]}={r['verdict'][:4]}" for r in recs), flush=True)
    L = amal_list()
    W(AMAL_LIST_P, L)
    print(f"done: {n_ok} ruled, {n_fail} failed | Amal's list {L['count']}")
    return 0 if not n_fail else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
