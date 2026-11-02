# -*- coding: utf-8 -*-
"""Check Medi's Student-tab homework answers on Medi's Claude plan ($0), from this PC.

Medi 2026-11-02 (his answer showed "The AI check did not run (OpenAI 429: You have no credits remaining)"): the Supabase
`check-homework` function gave the first check of each answer with the paid OpenAI API. His standing rule is plans first
(claude -p / codex exec); a browser page cannot reach a plan, so the page now only saves the answer and says it is checked
within 15 minutes, and this step - run by the 15-minute Amal trigger - checks every reply with no check yet (or only an
'ungraded' placeholder from a check that did not run), with the same prompt, the same 12 real WhatsApp corrections and her
latest 12 overrules. Amal's verdict on her page always overrides it.

    python scripts/grade_homework.py            # check what is waiting
    python scripts/grade_homework.py --dry-run  # list what would be checked
"""
import argparse, datetime, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import db  # noqa: E402

MODEL = "claude-sonnet-5-5"          # on the Claude plan via claude -p; no API key
PAIRS = HERE.parent / "tests" / "fixtures" / "homework_pairs.json"
KIND = {"translate": "translate a sentence", "create": "make a sentence with the given words", "question": "answer a question"}
# placeholders written when a check never ran (budget used up, provider down) - those get a real check now
NOT_RUN = ("budget is used up", "did not run", "could not read")


def waiting(replies):
    out = []
    for r in replies:
        ai = r.get("ai")
        if not ai:
            out.append(r)
        elif ai.get("verdict") == "ungraded" and any(s in str(ai.get("reason") or "") for s in NOT_RUN):
            out.append(r)
    return out


def _in(values):
    return "in.(" + ",".join('"%s"' % str(v).replace('"', "") for v in values) + ")"


def build_prompt(t, r, words, pairs, examples):
    targets = "\n".join(f"{w.get('house_spelling') or w.get('arabizi')} | {w.get('arabic')} | {w.get('english')}" for w in words)
    bar = "\n\n".join(f"Prompt: {p['english']}\nMedi: {p['answer']}\nAmal: {p['amal']}" + (f"  ({p['note']})" if p.get("note") else "") for p in pairs)
    d = t.get("direction")
    direction = ("He translates spoken Palestinian Arabic INTO English." if d == "ar_en"
                 else "He translates the English sentence INTO spoken Palestinian Arabic." if d == "en_ar" else "")
    create = f"Words he must use (Amal's spelling): {', '.join(t.get('words') or [])}" if t["kind"] == "create" else ""
    context = f"Context Amal gave: {t['context']}" if t["kind"] == "question" and t.get("context") else ""
    over = f"\nAmal's earlier overrules of this checker (learn from them):\n{examples}\n" if examples else ""
    return f"""You are Amal, a Palestinian Arabic tutor, giving the FIRST check of one typed homework answer from your adult student Medi.
He writes spoken Palestinian Arabic in Arabizi (6=ط 7=ح 3=ع 2=ء/ق 5=خ 9=ص 8=غ) or in Arabic letters; either is fine. You are terse,
only what needs fixing, never a lecture. Spelling variants of the same sound are NOT errors (kteer/ktir, ma3/ma3a, e/i, o/u);
MSA where he could have said the dialect word is a small note, not wrong. Amal's real verdict comes after yours; her past
overrules below set the bar - follow them.

Task kind: {KIND[t['kind']]}. {direction}
{create}
{context}
Amal's words that may belong here (her spelling | Arabic | English):
{targets or '(none matched)'}

Your real corrections from the chat (the bar you set):
{bar}
{over}
Prompt: {t.get('prompt')}
Medi: {r['answer']}

Return ONLY JSON: {{"verdict": "right" | "close" | "wrong", "reason": "<= 20 words, Amal's voice, say what to fix", "fixed": "<how to say it, in Medi's script (Arabizi or Arabic letters), or the same text when right>"}}
"right" = you would reply Yes / Tmm. "close" = one small fix (a word, an ending, a preposition). "wrong" = the meaning, the main verb or a required word is off."""


def words_for(t):
    src = t.get("words") or [] if t["kind"] == "create" else re.split(r"[^\w'’]+", str(t.get("prompt") or ""))
    want = [w.strip() for w in src if w and w.strip()][:40]
    if not want:
        return []
    ors = ",".join(f"arabizi.ilike.{re.sub(r'[%,()]', '', w)},english.ilike.{re.sub(r'[%,()]', '', w)}" for w in want)
    return db.select("words", {"select": "key,arabizi,arabic,english,house_spelling", "or": f"({ors})", "limit": "40"})


def overrule_examples():
    overs = db.select("homework_verdicts", {"select": "reply_id,verdict,note,fix,created_at", "kind": "eq.verdict", "agrees": "eq.false",
                                            "order": "created_at.desc", "limit": "12"})
    if not overs:
        return ""
    reps = {x["id"]: x for x in db.select("homework_replies", {"select": "id,task_id,answer,ai", "id": _in(o["reply_id"] for o in overs)})}
    tasks = {x["id"]: x for x in db.select("homework_tasks", {"select": "id,kind,prompt,direction,words", "id": _in({r["task_id"] for r in reps.values()})})} if reps else {}
    out = []
    for o in overs:
        rep = reps.get(o["reply_id"]); tk = rep and tasks.get(rep["task_id"])
        if not rep or not tk or tk["kind"] not in KIND:
            continue
        d = f" ({'English to Arabic' if tk['direction'] == 'en_ar' else 'Arabic to English'})" if tk.get("direction") else ""
        w = f" [words: {', '.join(tk.get('words') or [])}]" if tk.get("words") else ""
        fx = f' - say "{o["fix"]}"' if o.get("fix") else ""
        nt = f" ({o['note']})" if o.get("note") else ""
        out.append(f"Task: {KIND[tk['kind']]}{d}: {tk['prompt']}{w}\nMedi: {rep['answer']}\nAI said: {(rep.get('ai') or {}).get('verdict', '?')}. Amal says: {o['verdict']}{fx}{nt}")
    return "\n\n".join(out)


def ask_claude(prompt):
    r = subprocess.run(["claude", "-p", "--model", MODEL, "--output-format", "json",
                        "--disallowedTools", "Bash,Read,Write,Edit,MultiEdit,Glob,Grep,WebFetch,WebSearch,Task,NotebookEdit,TodoWrite"],
                       input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                       shell=(os.name == "nt"))
    try:
        d = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        raise RuntimeError("claude -p: " + (r.stdout or r.stderr)[:300])
    if d.get("is_error"):
        raise RuntimeError("claude -p error: " + str(d.get("result"))[:300])
    return d.get("result") or ""


def parse(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        ai = json.loads(t[t.find("{"):t.rfind("}") + 1])
    except ValueError:
        ai = {"verdict": "ungraded", "reason": "The checker answered in a shape I could not read.", "fixed": ""}
    if ai.get("verdict") not in ("right", "close", "wrong"):
        ai["verdict"] = "ungraded"
    ai["reason"] = str(ai.get("reason") or "")[:300]
    ai["fixed"] = str(ai.get("fixed") or "")[:500]
    return ai


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    replies = db.select("homework_replies", {"select": "id,task_id,answer,ai,created_at", "order": "created_at.desc", "limit": "200"})
    todo = waiting(replies)
    print(f"homework: {len(todo)} answer(s) to check")
    if a.dry_run or not todo:
        for x in todo:
            print("  ", x["id"][:8], x["answer"][:60])
        return 0
    pairs = json.loads(PAIRS.read_text(encoding="utf-8"))
    examples = overrule_examples()
    import track  # noqa: E402
    bad = 0
    for r in todo:
        t = (db.select("homework_tasks", {"select": "*", "id": f"eq.{r['task_id']}"}) or [None])[0]
        if not t or t.get("kind") not in KIND:
            continue
        t0 = time.time()
        try:
            ai = parse(ask_claude(build_prompt(t, r, words_for(t), pairs, examples)))
        except Exception as e:
            bad += 1
            print("  FAILED", r["id"][:8], str(e)[:160])
            track.log_run("homework.check", None, status="failed", provider="claude-plan", model=MODEL, error=str(e)[:300])
            continue
        ai.update(model=MODEL, cost_usd=0, via="claude-plan", examples=examples.count("\nAI said:"))
        db.rest("PATCH", "homework_replies", params={"id": f"eq.{r['id']}"},
                body={"ai": ai, "ai_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}, prefer="return=minimal")
        track.log_run("homework.check", None, provider="claude-plan", model=MODEL, duration_ms=int((time.time() - t0) * 1000),
                      usd=0, note=f"reply {r['id'][:8]}: {ai['verdict']}")
        print("  checked", r["id"][:8], ai["verdict"], "|", r["answer"][:50])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
