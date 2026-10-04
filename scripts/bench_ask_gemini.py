# -*- coding: utf-8 -*-
"""Ask Gemini itself why the listener prompt misses what it misses (PR-18; Medi 2026-10-04 "Should we be asking gemini
itself too?" - yes, as an idea source, never as a judge). One text-only call: the frozen prompt template, the results
of the variables test and the baseline's misses. The answer is saved, not acted on: any wording it suggests is one more
variable to test (3 runs) and to confirm on a second corrected lesson.

    python scripts/bench_ask_gemini.py 2026-10-02
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402
import bench_run as BR  # noqa: E402
import bench_vars as BV  # noqa: E402

MODEL = "gemini-3.8-flash"
ASK = """You are Gemini 3.8 Flash. Below is a prompt that is sent to YOU, with a short audio clip, about 470 times per lesson: you re-hear one
line of a learner's speech and write what he actually said. I ran it 3 times on a lesson the learner corrected by hand and scored it.
I want your honest view of why you miss what you miss, and what to change. Be concrete and short; do not flatter the prompt.

=== THE PROMPT TEMPLATE ({{context}}, {{chat}}, {{target}} are filled per line) ===
{template}

=== RESULTS (heard right of 63 corrected moments / his slips hidden of 24 / untouched lines with a word changed of 519) ===
{results}

=== THE MOMENTS THE BASELINE MISSES (what he said -> what you wrote in runs 1, 2, 3, with your own reason from run 1) ===
{misses}

=== SLIPS YOU HID (you wrote the teacher's correct form where he said the wrong one) ===
{hidden}

Questions:
1. For each missed moment: is it something you cannot hear in a clip like this, or something the prompt's wording pushes you to do
   (finish a cut-off word, tidy the grammar, copy the teacher, prefer a standard spelling)? One line each.
2. Which sentences of the prompt work against "write exactly what he said"? Quote them and give a better wording.
3. Several ideas made no difference or hurt (asking for evidence, confidence, a second guess, an accent note, a word list, vowel
   marks, more output fields). Why would more fields lower your accuracy, and what does that say about how to ask you?
4. Give at most 5 changes, ranked, that you expect to raise the score or cut the changed untouched lines WITHOUT hiding more slips:
   prompt wording, what audio to send (longer clip, both microphones, the teacher's line too), settings, or a second pass.
5. What in your answers to 1-4 are you least sure of?
Answer in plain text with those five numbered parts."""


def main(date):
    import requests
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    R = BC.J(os.path.join(BV.vdir(date), "results.json"))
    M = {m["id"]: m for m in truth["moments"]}
    L = {ln["i"]: ln for ln in truth["lines"]}
    run1 = BC.J(os.path.join(d, BV.BASE, "line-run1.json"))["lines"]
    b = R["baseline"]
    res = ["%s: %d / %d / %d" % (r["name"], r["heard_right"], r["hidden_slips"], r["lines_words_changed"]) for r in [b] + R["variables"]]
    miss = []
    for p in b["per_moment"]:
        if p["final"] == "hit":
            continue
        m = M[p["id"]]
        why = ((run1.get(str(m["i"])) or {}).get("raw") or {}).get("why")
        miss.append("- he said: «%s» | the speech engine wrote: «%s» | you wrote: %s | your reason: %s" % (L[m["i"]]["truth"], L[m["i"]]["engine"], " / ".join("«%s»" % h for h in p["heard"]), why))
    hid = ["- he said «%s», the teacher's form is «%s»; you wrote «%s»" % (h["wrong"], h["right"], h["heard"]) for h in b["hidden_rows"]]
    prompt = ASK.format(template=BC.J(os.path.join(d, "prompts.json"))["template"], results="\n".join(res), misses="\n".join(miss), hidden="\n".join(hid) or "(none)")
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 1, "maxOutputTokens": 8192}}
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL, params={"key": BR.key("GEMINI_API_KEY")}, json=body, timeout=420)
    if r.status_code != 200:
        raise SystemExit("%d %s" % (r.status_code, r.text[:300].replace(BR.key("GEMINI_API_KEY"), "***")))
    j = r.json()
    u = j.get("usageMetadata") or {}
    tin, tout = u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    p = BR.PRICE[MODEL]
    usd = (tin * p[0] + tout * p[2]) / 1e6
    os.environ["ANEES_RUNS_DIR"] = os.path.join(d, "runs", "gemini-self-review")
    BR.paid(date, "gemini-self-review", "text", 1, MODEL, usd, None, provider="google")
    text = "".join(x.get("text", "") for x in j["candidates"][0]["content"]["parts"])
    BC.W(os.path.join(BV.vdir(date), "gemini-self-review.json"), {"model": MODEL, "asked": prompt, "answer": text, "tokens": [tin, tout], "usd": round(usd, 5),
                                                                  "note": "an idea source, not a judge: nothing here is applied without its own 3-run test"})
    print(text)
    print("\n$%.4f" % usd)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
