# -*- coding: utf-8 -*-
"""TR-32: find the words of his the recording engine misheard, without a person (Medi 2026-10-10: "theres no way we can
address these? can we ask gemini?" / "both all everything do it deploy").

The 2026-10-10 audit of 10-09 fixed 32 misheard words by hand (TR-31): تيني 'fig' was his أعطيني, بيتي 'my house' his
بدي, أعلم his أغلب. Each was proven by the TUTOR's own words - her line right after or the line she typed in the Meet
chat. This file does that for every new lesson, in two steps:

  1 text (Claude, one call): every suspect word of his - 'not on her word list', 'a form the Word Bank does not list',
    a Latin line of his with no mark - goes to one reader with his line, her lines of the 25 s around it and her chat
    lines of the 2 minutes around it. The reader names the word only when her words show it, and quotes them. A fix is
    kept only when the quote really is in her line / chat (checked here) and the word is in the quote or on her list.
  2 audio (Gemini, one short call a word, at most 25 words and $0.50 a lesson): the suspects the text could not settle
    are heard again - his own microphone, the line's clip - with her word list's nearest words as the choices. Kept only
    when Gemini is sure AND picks one of those choices of hers (never a free guess: S1, her words only).

Kept fixes go into data/lesson-work/transcript-fixes.json (the heard-word overlay, S2: the raw text is never edited) with
rule TR-31 / TR-32, by 'claude-misheard' / 'gemini-misheard' and the evidence in 'why'. A word already fixed is never
asked again. From 2026-10-08 on (Medi's scope 2026-10-10). ANEES_MISHEARD=off stops it.

    python scripts/misheard_check.py 2026-10-09             # both steps, write the rows
    python scripts/misheard_check.py 2026-10-09 --dry-run   # list the suspects, call nothing
    python scripts/misheard_check.py 2026-10-09 --no-audio  # text step only
"""
import difflib, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FIXES_P = os.path.join(REPO, "data", "lesson-work", "transcript-fixes.json")
FROM = "2026-10-08"
CLAUDE = os.environ.get("ANEES_CLAUDE", "claude")
GEMINI = "gemini-3.8-flash"
MAX_AUDIO, MAX_USD = 25, 0.50
SUSPECT = re.compile(r"not on her word list|does not list yet|two list words are spelled|second listen changed")
AR = re.compile(r"[؀-ۿ]")

PROMPT = """You check a transcript of an Arabic lesson (Levantine; tutor Amal, student Medi, a Farsi speaker whose ق / غ / ء
sound alike). The recording engine sometimes mishears HIS words (it wrote تيني 'fig' for his أعطيني 'give me', بيتي for
بدي, أعلم for أغلب, 'actor' for أكتر). For each numbered suspect word below you get his line, the tutor's lines around it
and the lines she typed in the chat. Say what he really said ONLY when the tutor's own words show it - she repeats or
corrects it, answers it, or typed his sentence in the chat. Quote her words exactly (copy them). If her words do not show
it, answer null. Never guess from meaning alone. Write the word in Arabic letters as she writes it. Her CORRECTION of
him is not what he said: when she gives him a different form to fix his (his اللابات, her ألعاب), answer null - his
wrong form stays. Her chat often types the corrected sentence: use it only for a word that is clearly the same word
misheard (تيني = أعطيني), never for a form he got wrong.

Answer ONE JSON object and nothing else: {"items": [{"n": <number>, "heard": "<Arabic or null>", "quote": "<her exact
words that show it, or null>"}]}

"""

ASK_AUDIO = """This clip is one line of a learner of Levantine Arabic (a Farsi speaker: his ق, غ and ء sound alike; he
drops ع). The transcript wrote the word «{word}» in his line «{line}». Listen. Which ONE of these words of his teacher's
list did he say there: {choices}? Or did he say «{word}» just as the transcript wrote it? Answer JSON only:
{{"word": "<one of the choices exactly, or AS WRITTEN>", "sure": true|false}}. Answer AS WRITTEN unless you clearly hear
one of the others."""


def track_sha():
    """The prompt is part of the cache key: a changed prompt is a new read."""
    import hashlib
    return "|" + hashlib.sha1(PROMPT.encode("utf-8")).hexdigest()[:10]


def J(p, d=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def mmss(t):
    t = int(float(t or 0))
    return "%02d:%02d" % (t // 60, t % 60)


def suspects(date):
    """[{n, t, word, line, i}] - his words a misheard engine could explain (one per word and line)."""
    import word_coverage as WC
    d = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"), {}) or {}
    T, tm = d.get("turns") or [], d.get("tmarks") or {}
    done = {(r.get("date"), round(float(r.get("t") or 0), 1)) for r in (J(FIXES_P, {}) or {}).get("rows", [])
            if r.get("rule") in ("TR-31", "TR-32", "PR-15") or r.get("by") == "medi"}
    out, seen = [], set()
    for i, u in enumerate(T):
        if u.get("who") != "Medi" or (date, round(float(u["t"]), 1)) in done:
            continue
        for c in (tm.get(str(i)) or {}).get("c", []):
            w = c.get("ar")
            if c.get("s") == "na" and w and not c.get("hide") and SUSPECT.search(c.get("why") or "") and not WC.is_pronoun(w) and (i, w) not in seen:
                seen.add((i, w))
                out.append({"t": float(u["t"]), "end": float(u.get("end") or u["t"]), "word": w, "line": u.get("text") or "", "i": i})
        txt = u.get("text") or ""
        latin = [x for x in re.findall(r"[A-Za-z0-9']{3,}", txt) if arabizi_like(x)]
        if latin and not AR.search(txt) and not (tm.get(str(i)) or {}).get("c"):
            w = " ".join(latin)           # his Arabizi the reader did not read (55:13 'Aqlab asilti', 57:47 'mish vade')
            if (i, w) not in seen:
                seen.add((i, w))
                out.append({"t": float(u["t"]), "end": float(u.get("end") or u["t"]), "word": w, "line": txt, "i": i})
    # the overlay matches the engine's own text: a word that is only on a line some other fix rewrote cannot be fixed here
    out = [s for s in out if s["word"] in (T[s["i"]].get("engine") or T[s["i"]].get("text") or "")]
    for k, s in enumerate(out, 1):
        s["n"] = k
    return out, T


_HERS = None
ENGLISH = set("""the and you that this was with have for not are but what would say she her his him its it's okay yeah yes
right then there here they them from about like just know think want wanna gonna can could should because which when where
who how why one two first second other another more most same different type types game games word words time times day
today favorite mine your my our hold wait sure good great nice sorry thanks thank love laughs echoing shit hey also still
again plural question questions beginning end boring cheap happy beach sea ocean lake mountain mountains ice cream food
tree trees leaf leafs grass paper chat group view prefer enjoy enjoyable became better been have has had did does doing done
make makes made makes said tell told take takes after before over under since some any all every each only even""".split())


def arabizi_like(tok):
    """A Latin word of his that is Arabic written in Latin letters: a number letter (3, 7, 8 ...) or close to a word of
    her list's Arabizi, and no everyday English word."""
    global _HERS
    t = tok.lower().strip("'")
    if t in ENGLISH or len(t) < 3:
        return False
    if re.search(r"[2-9]", t):
        return True
    if _HERS is None:
        rows = (J(os.path.join(REPO, "docs", "data", "words.json"), {}) or {}).get("items", [])
        _HERS = {x.lower() for r in rows for x in re.findall(r"[A-Za-z0-9']{3,}", r.get("arabizi") or "")}
    return t in _HERS or any(difflib.SequenceMatcher(None, t, h).ratio() >= 0.8 for h in _HERS if abs(len(h) - len(t)) <= 2)


def context(T, s, chat):
    t = s["t"]
    her = [u for u in T if u.get("who") == "Amal" and t - 25 <= float(u["t"]) <= t + 25]
    typed = [c for c in chat if t - 120 <= float(c["t"]) <= t + 120]
    return her, typed


def chat_lines(date):
    try:
        import lesson_turns
        return [{"t": float(c.get("t") or c.get("start") or 0), "text": c["text"]} for c in lesson_turns.chat_lines(date)
                if c.get("speaker") == "Amal"]
    except Exception:  # noqa: BLE001
        return []


def ask_claude(date, items, T, chat):
    import track
    body = []
    for s in items:
        her, typed = context(T, s, chat)
        body.append("%d. his line at %s: «%s» - the word: «%s»\n   tutor said: %s\n   tutor typed: %s" % (
            s["n"], mmss(s["t"]), s["line"], s["word"],
            " | ".join("%s «%s»" % (mmss(u["t"]), u["text"]) for u in her) or "-",
            " | ".join("«%s»" % c["text"] for c in typed) or "-"))
    prompt = PROMPT + "\n".join(body)
    cmd = [CLAUDE, "-p", prompt, "--output-format", "json"] + track.claude_model_args()
    try:
        with track.run("misheard_check", date, kind="inference", provider="anthropic", request_model=track.CLAUDE_MODEL,
                       params={"suspects": len(items), "prompt_arg_sha": track.sha256_text(prompt)}) as run:
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=1200)
            parsed = track.parse_claude_output(r.stdout)
            run.claude(parsed)
            txt = parsed.get("text") or ""
    except Exception as e:  # noqa: BLE001
        print("misheard_check: the text reader failed (%s)" % type(e).__name__)
        return {}
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        ans = json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}
    return {int(x["n"]): x for x in ans.get("items") or [] if isinstance(x, dict) and str(x.get("n", "")).isdigit()}


def _norm(s):
    return re.sub(r"[ً-ْــ\s.،,؟?!:;\"'«»()-]+", "", str(s or "")).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")


def proven(s, a, T, chat, keys):
    """Keep the reader's answer only when its quote is really her words near the line and the word is in the quote or a
    word of her list."""
    heard, quote = (a or {}).get("heard"), (a or {}).get("quote")
    if not heard or not quote or not AR.search(str(heard)):
        return None
    heard = clean(heard)
    if guarded(s, heard, T):
        return None
    her, typed = context(T, s, chat)
    q = _norm(quote)
    src = next((u for u in her + typed if q and (q in _norm(u["text"]) or _norm(u["text"]) in q and len(_norm(u["text"])) >= 3)), None)
    if src is None:
        return None
    on_list = keys.lookup(heard)[1] == "one" if keys else False
    if _norm(heard) not in q and not on_list:
        return None
    return {"heard": heard, "quote": quote.strip(), "src": src}


def clean(w):
    """Her letters without vowel marks (ٱسْأِلَة -> اسألة)."""
    return re.sub(r"[\u064B-\u0652\u0670]", "", str(w or "")).replace("ٱ", "ا").strip(" .،,؟?!")


ENGLISH_LINE = re.compile(r"(?:\b[A-Za-z']{2,}\b\W+){3,}")


def guarded(s, heard, T):
    """Never replace his word with a RIGHT form he did not say (his slip would vanish):
    - a counted slip sits on his line: her word there is her fix (10-09 66:04 his اللابات, her ألعاب);
    - he says it himself right after (his own fix of a first try: 24:11 بتتبسط, then 24:16 بتبسط);
    - his word is a place he names inside an English sentence ('the wind is strong in Iran' stays English)."""
    h = _norm(heard)
    if not h:
        return True
    if not AR.search(s["word"]) and ENGLISH_LINE.search(s["line"]) and is_place(heard):
        return True                       # 'the wind is strong in Iran' is English: a place he names in English stays
    if any(s["t"] - 2 <= x <= s["end"] + 2 for x in SLIP_T.get(s.get("date"), ())):
        return True                       # a counted slip on his line: her word there is her fix, not what he said
    for u in T[s["i"] + 1:]:
        if float(u["t"]) - s["end"] > 10:
            break
        if u.get("who") == "Medi" and h in _norm(u.get("text")):
            return True
    return False


def is_place(w):
    try:
        import loanwords
        return bool(loanwords._place_spans(w))
    except Exception:  # noqa: BLE001
        return False


SLIP_T = {}


def load_slips(date):
    d = J(os.path.join(REPO, "docs", "data", "lessons", date + ".json"), {}) or {}
    SLIP_T[date] = [float(g["t"]) for g in (d.get("grammar_errors") or []) + (d.get("vocab_errors") or []) if g.get("t") is not None]


def _fold(x):
    """His sounds folded: ق / غ / ك / ء one letter, ذ / ظ / ض / ز / د one, ط / ت / ث one, ع and long vowels out."""
    return re.sub(r"[عاوىيةه]", "", _norm(x).translate(str.maketrans("قغكءأإآذظضزطث", "كككك" + "ااا" + "دددد" + "تت")))


def choices(keys, word, n=6):
    """Her list's nearest words to his (by letters, with his sounds folded): the only answers Gemini may give."""
    import word_coverage as WC
    w = WC.jsnorm(word)
    fold = lambda x: x.translate(str.maketrans("قغكءأإآذظضزطث", "كككك" + "ااا" + "دددد" + "تت")).replace("ع", "")
    scored = []
    for k, row in keys.words.items():
        a = WC.jsnorm(row.get("arabic") or "")
        if not a or " " in a or len(a) < 2:
            continue
        r = max(difflib.SequenceMatcher(None, w, a).ratio(), difflib.SequenceMatcher(None, fold(w), fold(a)).ratio())
        if r >= 0.5:
            scored.append((r, row.get("arabic")))
    return [a for r, a in sorted(scored, reverse=True)[:n]]


def ask_gemini(date, s, opts, spent):
    import bench_run as BR, rehear_audio as RA, track
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "clip.wav")
        RA.clip(date, "Medi", max(0.0, s["t"] - 0.3), s["end"] + 0.3, wav)
        prompt = ASK_AUDIO.format(word=s["word"], line=s["line"], choices=" / ".join(opts))
        with track.run("misheard_check_audio", date, kind="inference", provider="google", request_model=GEMINI,
                       params={"t": s["t"]}) as run:
            res = BR.gemini(GEMINI, wav, prompt, as_json=True)
            if res.get("usd") is not None:
                run.set(cost_usd=round(res["usd"], 6), cost_basis="tokens")
    raw = res.get("raw") or {}
    return raw, float(res.get("usd") or 0)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date = args[0] if args else None
    if not date or date < FROM or os.environ.get("ANEES_MISHEARD") == "off":
        print("misheard_check: nothing to do (%s)" % (date or "no date"))
        return 0
    import word_coverage as WC
    words = (J(os.path.join(REPO, "docs", "data", "words.json"), {}) or {}).get("items", [])
    keys = WC.Keys(words)
    keys.sound = True
    sus, T = suspects(date)
    load_slips(date)
    for x in sus:
        x["date"] = date
    chat = chat_lines(date)
    print("misheard_check %s: %d suspect words" % (date, len(sus)))
    if "--dry-run" in sys.argv:
        for s in sus:
            print("  %s %s | %s" % (mmss(s["t"]), s["word"], s["line"][:70]))
        return 0
    if not sus:
        return 0
    cache_p = os.path.join(REPO, "data", "lesson-work", "misheard", date + ".json")
    key = json.dumps([[s["t"], s["word"]] for s in sus], ensure_ascii=False)
    cached = J(cache_p, {}) or {}
    key = key + track_sha()
    if cached.get("suspects") == key:
        got = {int(k): v for k, v in (cached.get("answers") or {}).items()}       # never pay twice for the same read
    else:
        got = ask_claude(date, sus, T, chat)
        if got:
            os.makedirs(os.path.dirname(cache_p), exist_ok=True)
            with open(cache_p, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"about": "The misheard-word reader's answers (scripts/misheard_check.py, TR-32), by suspect number.",
                           "suspects": key, "answers": got}, f, ensure_ascii=False, indent=1)
                f.write("\n")
    rows, left = [], []
    for s in sus:
        p = proven(s, got.get(s["n"]), T, chat, keys)
        if p and _norm(p["heard"]) != _norm(s["word"]):
            rows.append({"date": date, "t": s["t"], "who": "Medi", "engine_wrote": s["word"], "heard": p["heard"], "rule": "TR-31",
                         "by": "claude-misheard", "on": __import__("datetime").date.today().isoformat(),
                         "why": "The engine misheard; the tutor's own words show what was said: %s «%s»." % (
                             "her chat" if "who" not in p["src"] else "her line at " + mmss(p["src"]["t"]), p["quote"])})
        else:
            left.append(s)
    spent, asked, heard_again = 0.0, 0, []
    if "--no-audio" not in sys.argv:
        for s in left:
            if asked >= MAX_AUDIO or spent >= MAX_USD or not AR.search(s["word"]):
                continue
            opts = choices(keys, s["word"])
            if not opts:
                continue
            try:
                raw, usd = ask_gemini(date, s, opts, spent)
            except Exception as e:  # noqa: BLE001 - no clip, no key, a timeout: the word stays as it is
                print("  %s %s: not heard again (%s)" % (mmss(s["t"]), s["word"], type(e).__name__))
                continue
            asked += 1
            spent += usd
            pick = raw.get("word")
            if (raw.get("sure") is True and pick in opts and _norm(pick) != _norm(s["word"]) and not guarded(s, pick, T)
                    and difflib.SequenceMatcher(None, _fold(s["word"]), _fold(pick)).ratio() >= 0.6):
                heard_again.append({"t": s["t"], "word": s["word"], "gemini": pick, "choices": opts})
            if False:
                rows.append({"date": date, "t": s["t"], "who": "Medi", "engine_wrote": s["word"], "heard": pick, "rule": "TR-32",
                             "by": "gemini-misheard", "on": __import__("datetime").date.today().isoformat(),
                             "why": "The engine misheard; Gemini listened to his microphone and, given the nearest words of her "
                                    "list (%s), was sure he said «%s»." % (" / ".join(opts), pick)})
    if heard_again:                       # TR-32: Gemini's picks are listed for a person, never applied (2026-10-10 test:
        cache = J(cache_p, {}) or {}      # 7 of its 9 sure picks on 10-09 were wrong - لا -> هلا, عيد -> إيد)
        cache["audio_suggestions"] = heard_again
        os.makedirs(os.path.dirname(cache_p), exist_ok=True)
        with open(cache_p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
            f.write("\n")
        for h in heard_again:
            print("  Gemini suggests %s %s -> %s (not applied)" % (mmss(h["t"]), h["word"], h["gemini"]))
    if rows:
        d = J(FIXES_P)
        have = {(r.get("date"), round(float(r.get("t") or 0), 2), r.get("engine_wrote")) for r in d["rows"]}
        new = [r for r in rows if (r["date"], round(r["t"], 2), r["engine_wrote"]) not in have]
        d["rows"].extend(new)
        with open(FIXES_P, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
            f.write("\n")
        for r in new:
            print("  %s %s -> %s (%s)" % (mmss(r["t"]), r["engine_wrote"], r["heard"], r["by"]))
    print("misheard_check %s: %d fixed (text %d, audio %d), %d heard again for $%.3f" % (
        date, len(rows), sum(r["by"] == "claude-misheard" for r in rows), sum(r["by"] == "gemini-misheard" for r in rows), asked, spent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
