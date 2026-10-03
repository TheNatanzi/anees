# -*- coding: utf-8 -*-
"""TR-22 context listening (Medi 2026-10-03: "Maybe you can figure out a process to go through the transcript and try and
actually figure out what I am saying using judgement and context. this is awful as is.").

For one of Medi's lines an audio model LISTENS to his own microphone for that line, with the engine's text of the 40 s
around it (both speakers) and Amal's chat lines as context, and writes what he actually said - his mistakes kept, the
engine's mishearings fixed. A second listen of the same audio with NO context confirms it: an Arabic word the first
listen changed must also be heard in the bare audio, or the change is rejected (the context pulling his slip toward
Amal's correction). The engine text it gets is the RAW engine text (never our overlay), so the benchmark is fair.

    python scripts/context_transcribe.py bench [MODEL]    # Medi's own corrections of 10-02 = the answer key
    python scripts/context_transcribe.py falses [MODEL]   # his unflagged lines 07:00-11:40: how many get changed
    python scripts/context_transcribe.py lesson DATE      # every Medi line -> data/lesson-work/context-heard/<date>.json
"""
import base64, json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
MODEL = os.environ.get("ANEES_CONTEXT_MODEL", "gemini-3.8-flash")
USD_PER_CALL = 0.004          # estimate per call (short clip + ~2k tokens), logged to data/budget.json under 'gemini'
FFMPEG = "ffmpeg"
RAW = r"C:\dev\anees\data\lessons"

PROMPT = """You are transcribing a recorded online Arabic lesson. Medi is an American learner of Levantine (Palestinian/Jordanian)
Arabic; he mixes English and Arabic and makes learner mistakes. Amal is his teacher (native Levantine). A speech engine
wrote the transcript below; it often MISHEARS Medi's Arabic as a different Arabic word, or as English look-alike words.

The audio clip is ONLY Medi's microphone for the target line. Context (engine text of the lines around it; seconds
before (-) / after (+) the target line):
{context}
Amal's typed chat lines near this moment (she often types the sentence Medi was trying to say, in her Arabizi; her typed
version may be CORRECTED, so it shows what he meant, not always what he said): {chat}

TARGET: Medi's line that the engine wrote as: «{target}».

How to use the context (general, true of these lessons):
- Medi often REPEATS Amal's previous sentence with small changes (her "you woke up late" -> his "I woke up late"): if his
  line sounds like hers, expect her words in it.
- An answer must fit the question just before it (asked "what time?", he answers with a time).
- Amal's next reaction shows what she heard: if she only fixes one small piece, the rest was right as she heard it.
- The engine prefers common words; a common word that makes the sentence nonsense is probably a mishearing.
- Amal's correction AFTER his line is what he should have said, not what he said: never put her fix into his line.

Write exactly what MEDI said in the target line:
- keep his mistakes, wrong words, wrong endings, wrong vowels and false starts exactly as he said them (do NOT correct his Arabic);
- fix only what the engine misheard;
- if he spoke English, write the English.
Answer JSON only: {{"arabic": "his words in Arabic script (English words stay English)", "arabizi": "his words in Latin letters with 2 3 5 6 7 8 9 for ء ع خ ط ح غ ص", "engine_was_wrong": true|false, "changes": [{{"engine": "...", "said": "..."}}], "confidence": "high"|"medium"|"low", "why": "one short reason"}}"""

CONFIRM = """Audio of ONE speaker: Medi, an American learner of Levantine Arabic who mixes English and Arabic and makes learner
mistakes. Write exactly what he says, keeping his mistakes (do not correct his Arabic). Answer JSON only:
{"arabic": "his words in Arabic script (English stays English)", "arabizi": "Latin letters with 2 3 5 6 7 8 9"}"""


def J(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def key():
    k = os.environ.get("GEMINI_API_KEY")
    if not k:
        import winreg
        k = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment"), "GEMINI_API_KEY")[0]
    return k


def clip(mp3, a, b):
    out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", "%.2f" % a, "-to", "%.2f" % b, "-i", mp3, "-ac", "1", "-ar", "16000", "-b:a", "48k", out], check=True)
    data = open(out, "rb").read()
    os.unlink(out)
    return data


def raw(u):
    return u.get("engine") or u["text"]


_OFF = {}


def track_clip(date, who, a, b):
    """His own recording (no Amal on it) for lesson-clock [a, b]. Per-speaker tracks sit on the lesson clock by their own
    offset (self_fix_timing.offsets); a lesson with one mixed recording uses lesson.mp3."""
    import self_fix_timing as SFT
    tr = os.path.join(RAW, date, "tracks")
    files = [f for f in (os.listdir(tr) if os.path.isdir(tr) else []) if f.lower().endswith(".mp3") and f.lower().startswith(who.lower()[:4])]
    if date not in _OFF:
        W = SFT.words(date)
        _OFF[date] = SFT.offsets(J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"))["turns"], W) if W else {}
    off = (_OFF[date] or {}).get(who)
    if len(files) == 1 and off is not None:
        return clip(os.path.join(tr, files[0]), max(0.0, a - off), b - off), "own track"
    return clip(os.path.join(REPO, "docs", "lessons", date, "audio", "lesson.mp3"), a, b), "lesson mix"


def _oai(model, audio, text):
    """OpenAI audio model (gpt-audio*): same contract as _gem."""
    import requests
    import pipeline_ext as PE
    k = os.environ.get("OPENAI_API_KEY")
    if not k:
        import winreg
        k = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment"), "OPENAI_API_KEY")[0]
    body = {"model": model, "modalities": ["text"], "temperature": 0.2,
            "messages": [{"role": "user", "content": [{"type": "text", "text": text},
                                                      {"type": "input_audio", "input_audio": {"data": base64.b64encode(audio).decode(), "format": "mp3"}}]}]}
    if not PE.budget_ok("openai", USD_PER_CALL):
        raise SystemExit("openai budget cap")
    r = None
    for n in range(4):
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": "Bearer " + k}, json=body, timeout=300)
        except requests.exceptions.RequestException:
            time.sleep(10 * (n + 1))
            continue
        if r.status_code == 200:
            break
        time.sleep(5 * (n + 1))
    if r is None or r.status_code != 200:
        return {"error": "no answer (%s) %s" % (r.status_code if r is not None else "timeout", (r.text[:200] if r is not None else ""))}
    _runline("openai", model)
    PE.spend("openai", USD_PER_CALL, "TR-22 context listening " + model)
    try:
        txt = r.json()["choices"][0]["message"]["content"]
        return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:
        return {"error": str(e)[:200]}


def _runline(service, model):
    """Every paid call has a run line (check_rules AI-paid-logged)."""
    import track
    track.log_run("context.listen", None, kind="inference", provider="google" if service == "gemini" else "openai",
                  request_model=model, response_model=model, cost_usd=USD_PER_CALL, params={"rule": "TR-22"})


def _call(model, audio, text):
    return _oai(model, audio, text) if model.startswith("gpt") else _gem(model, audio, text)


def _gem(model, audio, text):
    import requests
    import pipeline_ext as PE
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(audio).decode()}}, {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    if not PE.budget_ok("gemini", USD_PER_CALL):
        raise SystemExit("gemini budget cap")
    r = None
    for k in range(4):
        try:
            r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (model, key()), json=body, timeout=420)
        except requests.exceptions.RequestException:
            time.sleep(10 * (k + 1))
            continue
        if r.status_code == 200:
            break
        time.sleep(5 * (k + 1))
    if r is None or r.status_code != 200:
        return {"error": "no answer (%s)" % (r.status_code if r is not None else "timeout")}
    _runline("gemini", model)
    PE.spend("gemini", USD_PER_CALL, "TR-22 context listening")
    try:
        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:
        return {"error": str(e)[:200]}


DIAC = re.compile("[\u064B-\u0652\u0670]")
FILL = {"اا", "ااا", "اممم", "امم", "ام", "ا", "اه", "ممم", "مم"}


def words_ar(x):
    x = DIAC.sub("", x or "")
    x = re.sub("[آأإ]", "ا", x).replace("ة", "ه").replace("ى", "ي")
    return [w for w in re.sub("[^\u0621-\u064A ]", " ", x).split() if w not in FILL]


def ask(date, turns, i, model=MODEL, ctx_s=40.0, confirm=True):
    """One Medi line -> listen 1 (his track + context) and listen 2 (bare). accepted = every Arabic word listen 1 changed
    from the engine is also in listen 2."""
    u = turns[i]
    end = u.get("end") or u["t"] + 2
    audio, src = track_clip(date, "Medi", max(0.0, u["t"] - 0.6), end + 0.6)
    ctx = "\n".join("%+.1f s %s: %s" % (v["t"] - u["t"], v["who"], raw(v)) for v in turns
                    if u["t"] - ctx_s <= v["t"] <= u["t"] + ctx_s and v["who"] != "chat" and v is not u)
    chat = " | ".join(v["text"] for v in turns if v["who"] == "chat" and u["t"] - 20 <= v["t"] <= u["t"] + 60) or "(none)"
    r1 = _call(model, audio, PROMPT.format(context=ctx, chat=chat, target=raw(u)))
    r2 = _call(model, audio, CONFIRM) if confirm else {}
    eng, h1, h2 = words_ar(raw(u)), words_ar(r1.get("arabic")), set(words_ar(r2.get("arabic")))
    changed = [w for w in h1 if w not in eng]
    unsupported = [w for w in changed if w not in h2] if confirm else []
    return dict(r1, t=u["t"], engine=raw(u), model=model, audio=src, confirm=r2.get("arabic"),
                changed=changed, unsupported=unsupported, accepted=not unsupported and not r1.get("error"))


# Medi's own corrections of 10-02 (his words in chat, 2026-10-02/03) = the answer key. 'want' = a piece that must be in
# the accepted Arabic/Arabizi (any one); 'gone' = an engine word that must be gone.
BENCH = [
    (421.64, ["سمعت"], [], "kept: he really said sme3et (his slip)"),
    (454.02, ["عشر"], ["العشاء", "عشاء"], "3ala 3ashra"),
    (457.84, ["عشر"], ["العشاء", "عشاء"], "3ala el-3ashra"),
    (502.9, ["هادي", "هاد", "هذا"], ["عادي"], "hadi el-subu7"),
    (519.4, ["صحيت"], ["صرت"], "ana s7eet mit2a55er"),
    (533.84, ["هادي", "هاد", "هذا"], ["عادي"], "hadi el-subu7 (2nd)"),
    (570.62, ["لسه", "لسا", "لسة"], ["suck"], "lissa"),
    (578.26, ["عطل"], ["أطلع", "اطلع"], "3otle"),
    (584.14, ["عطل"], ["أطلع", "اطلع"], "aa5ud 3otle w safar"),
    (609.44, ["كمان"], [], "kaman marra"),
    (642.88, ["خطط", "5otatet", "5utatet"], [], "5otatet (vowel slip; Medi: understandable to miss)"),
    (683.96, ["عموي"], ["عمي"], "kept: his 3ammwi slip (Amal fixed it to 3ammi)"),
    (562.94, ["شجاع"], [], "kept: his شجاع slip (Amal fixed it to mitshajje3)"),
]


def bench(model=MODEL):
    date = "2026-10-02"
    turns = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"))["turns"]
    idx = {round(u["t"], 2): k for k, u in enumerate(turns)}
    rows, hit = [], 0
    for t, want, gone, note in BENCH:
        r = ask(date, turns, idx[round(t, 2)], model)
        heard = (r.get("arabic") or "") + " " + (r.get("arabizi") or "") if r.get("accepted") else r.get("engine")
        a = DIAC.sub("", heard or "")
        ok = any(w in a for w in want) and not any(g in a for g in gone)
        hit += ok
        rows.append(dict(r, ok=ok, note=note))
        print(("OK  " if ok else "MISS"), "%.0f" % t, note, "|", r.get("arabic"), "| bare:", r.get("confirm"),
              "| accepted" if r.get("accepted") else "| REJECTED %s" % r.get("unsupported"), flush=True)
    print("%d of %d right (engine alone: 3 of %d)" % (hit, len(BENCH), len(BENCH)))
    p = os.path.join(REPO, "data", "lesson-work", "context-heard", "bench-%s.json" % model)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump({"model": model, "score": [hit, len(BENCH)], "rows": rows}, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return hit


def falses(model=MODEL, lo=420.0, hi=700.0):
    """His Arabic lines in 10-02 07:00-11:40 that Medi read and did NOT flag (taken as right): how many get changed."""
    date = "2026-10-02"
    turns = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"))["turns"]
    flagged = {round(t, 2) for t, *_ in BENCH} | {round(u["t"], 2) for u in turns if u.get("engine")}
    rows = []
    for i, u in enumerate(turns):
        if u["who"] != "Medi" or not (lo <= u["t"] <= hi) or round(u["t"], 2) in flagged or not re.search("[\u0621-\u064A]", raw(u)):
            continue
        r = ask(date, turns, i, model)
        changed = bool(r.get("accepted") and r.get("changed"))
        rows.append(dict(r, changed_accepted=changed))
        print(("CHANGED" if changed else "same   "), "%.0f" % u["t"], raw(u), "->", r.get("arabic"), "| bare:", r.get("confirm"),
              "|", "accepted" if r.get("accepted") else "rejected %s" % r.get("unsupported"), flush=True)
    n = sum(x["changed_accepted"] for x in rows)
    print("%d of %d unflagged lines changed (after the bare-audio check)" % (n, len(rows)))
    json.dump({"model": model, "changed": [n, len(rows)], "rows": rows},
              open(os.path.join(REPO, "data", "lesson-work", "context-heard", "falses-%s.json" % model), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return n, len(rows)


def lesson(date, model=MODEL):
    turns = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"))["turns"]
    p = os.path.join(REPO, "data", "lesson-work", "context-heard", date + ".json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    done = {round(x["t"], 2): x for x in (J(p) or {}).get("rows", []) if not x.get("error")}
    todo = [i for i, u in enumerate(turns) if u["who"] == "Medi" and round(u["t"], 2) not in done
            and (re.search("[\u0621-\u064A]", raw(u)) or len(raw(u).split()) <= 6)]
    for n, i in enumerate(todo):
        try:
            done[round(turns[i]["t"], 2)] = ask(date, turns, i, model)
        except SystemExit:
            raise
        except Exception as e:
            done[round(turns[i]["t"], 2)] = {"t": turns[i]["t"], "engine": raw(turns[i]), "error": str(e)[:200]}
        if n % 10 == 9:
            json.dump({"date": date, "model": model, "rows": sorted(done.values(), key=lambda x: x["t"])}, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"date": date, "model": model, "rows": sorted(done.values(), key=lambda x: x["t"])}, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return done


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "bench":
        bench(sys.argv[2] if len(sys.argv) > 2 else MODEL)
    elif cmd == "falses":
        falses(sys.argv[2] if len(sys.argv) > 2 else MODEL)
    elif cmd == "lesson":
        lesson(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else MODEL)
