#!/usr/bin/env python3
"""Build the "listen pages": self-contained HTML pages on which Medi taps what he really said.

Two kinds of moments from the second listen (scripts/rehear_apply.py writes them to apply-plan.json):
  his-correction  a correction HE typed that none of Gemini's 3 runs heard (his text stays; who is right?)
  held            Gemini wanted to add a word Amal says in the next 15 s and the two-clip check did not
                  confirm he said it himself (the line keeps its old text)

Each card: the lesson date + mm:ss, a one-line question, two players (his microphone only; both speakers
6 s before to 8 s after), what each one wrote, answer buttons. The bottom of the page holds his answers as
plain lines to copy and paste back.

2026-10-05 (council / Codex final approval), two more kinds:
  spot            --spot: a spot-check line where the blind listen preferred the OLD text
                  (rehear/<date>/spot.json verdict "old text"): "Old line / New line - which did you say?"
                  A third section on the listen pages.
  council         --council: an Amal-confirmed slip whose line changed in the second listen so that the slip is no
                  longer on it (rehear/rejudge/kept-rows.json kept_confirmed: line_changed and the wrong piece gone).
                  Old line, new line, what Amal corrected; "I said it wrong (her fix was needed)" / "I said it right" /
                  "Not sure". Written to its own pages, council-check-<n>.html.

The audio is embedded as base64 data: URIs (mono MP3, his clip 24 kbps, both speakers 16 kbps), the cards
are split over pages so each page stays under 12 MB (an Artifact page may be 16 MB).

  python scripts/rehear_listen_page.py [dates...] [--max-held N] [--spot] [--out DIR]
  python scripts/rehear_listen_page.py --council [--out DIR]

Default: every lesson that has data/lesson-work/rehear/<date>/apply-plan.json.
Writes C:/Claude/reports/anees-listen-2026-10-04/listen-page-<n>.html. No network, no AI calls: only ffmpeg.

The pages are written in the Artifact page shape (title + style + content, no <html>/<body> wrapper: the
publish step adds it). --standalone wraps them in a full document for opening the file straight from disk.
"""
import argparse
import base64
import difflib
import glob
import html
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REHEAR = os.path.join(ROOT, "data", "lesson-work", "rehear")
LESSONS = os.path.join(ROOT, "docs", "lessons")
OUT_DIR = r"C:\Claude\reports\anees-listen-2026-10-04"
PAGE_LIMIT = 12 * 1000 * 1000          # bytes per page, base64 audio included
BEFORE, AFTER, BOTH_CAP = 6.0, 8.0, 30.0
STORE_KEY = "anees-listen-2026-10-04"
REJUDGE = os.path.join(REHEAR, "rejudge")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def J(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mmss(t):
    t = int(float(t))
    return "%d:%02d" % (t // 60, t % 60)


# ---------------------------------------------------------------- audio

def ffmpeg(args):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin"] + args + ["-f", "mp3", "pipe:1"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(p.stderr.decode("utf-8", "replace").strip()[:300] or "ffmpeg wrote nothing")
    return p.stdout


def own_mp3(wav):
    return ffmpeg(["-i", wav, "-ac", "1", "-ar", "16000", "-b:a", "24k"])


def both_sources(date):
    a = os.path.join(LESSONS, date, "audio")
    one = os.path.join(a, "lesson.mp3")
    if os.path.exists(one):
        return [one]
    two = [os.path.join(a, n) for n in ("Amal.mp3", "Medi.mp3")]
    if all(os.path.exists(p) for p in two):
        return two
    return []


def both_mp3(srcs, t, end):
    start = max(0.0, float(t) - BEFORE)
    dur = min(BOTH_CAP, float(end) + AFTER - start)
    args = []
    for s in srcs:
        args += ["-ss", "%.2f" % start, "-t", "%.2f" % dur, "-i", s]
    if len(srcs) > 1:
        args += ["-filter_complex", "amix=inputs=%d:duration=longest:normalize=0" % len(srcs)]
    return ffmpeg(args + ["-ac", "1", "-ar", "16000", "-b:a", "16k"])


def data_uri(mp3):
    return "data:audio/mpeg;base64," + base64.b64encode(mp3).decode("ascii")


# ---------------------------------------------------------------- text helpers

_PUNCT = re.compile(r"[\s\.,;:!\?\u060C\u061B\u061F\"'\u2018\u2019\u201C\u201D\(\)\[\]\u2026\-\u2013\u2014]+")


def norm(s):
    return _PUNCT.sub(" ", (s or "").lower()).strip()


def toks(s):
    return (s or "").split()


def spot(engine_line, engine_wrote, run_text):
    """What a run wrote at the place where the engine wrote `engine_wrote`. None = cannot place it."""
    et, rt = toks(engine_line), toks(run_text)
    en, rn = [norm(x) for x in et], [norm(x) for x in rt]
    wn = [x for x in (norm(w) for w in toks(engine_wrote)) if x]
    if not wn or not rt:
        return None
    a = next((k for k in range(len(en) - len(wn) + 1) if en[k:k + len(wn)] == wn), None)
    if a is None:
        return None
    b = a + len(wn)
    lo = hi = None
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, en, rn, autojunk=False).get_opcodes():
        if i2 <= a or i1 >= b or tag == "insert":
            continue
        if tag == "equal":
            x, y = j1 + max(a, i1) - i1, j1 + min(b, i2) - i1
        else:
            x, y = j1, j2
        lo = x if lo is None else min(lo, x)
        hi = y if hi is None else max(hi, y)
    if lo is None:
        return None
    return " ".join(rt[lo:hi]).strip(" .,;:!?\u060C\u061F\u2026")


def group_runs(runs):
    """[(text or None, [run numbers])] in first-seen order, identical texts merged."""
    out = []
    for n, r in enumerate(runs or [], 1):
        r = (r.get("text") if isinstance(r, dict) else r) or None
        for g in out:
            if (g[0] is None and r is None) or (g[0] is not None and r is not None and g[0].strip() == r.strip()):
                g[1].append(n)
                break
        else:
            out.append([r, [n]])
    return out


def E(s):
    return html.escape(s if s is not None else "", quote=True)


def bdi(s):
    return '<bdi dir="auto">%s</bdi>' % E(s)


def words(v):
    if not v:
        return []
    if isinstance(v, str):
        return [v]
    out = []
    for x in v:
        x = x.get("text") if isinstance(x, dict) else x
        if x and str(x) not in out:
            out.append(str(x))
    return out


# ---------------------------------------------------------------- cards

def table(rows):
    h = ['<table class="wrote"><tbody>']
    for who, text in rows:
        cell = E(text) if text else '<span class="none">nothing</span>'
        h.append('<tr><th scope="row">%s</th><td dir="auto">%s</td></tr>' % (E(who), cell))
    h.append("</tbody></table>")
    return "".join(h)


def run_rows(runs):
    total = len(runs or [])
    return [("Gemini (%d of %d)" % (len(ns), total), text) for text, ns in group_runs(runs)]


def player(label, uri, missing):
    if not uri:
        return '<div class="player"><span class="plabel">%s</span><span class="none">%s</span></div>' % (E(label), E(missing))
    return ('<div class="player"><span class="plabel">%s</span>'
            '<audio controls preload="none" src="%s"></audio></div>' % (E(label), uri))


def btn(ans, label_html, extra=""):
    return '<button type="button" class="ans" aria-pressed="false" data-ans="%s"%s>%s</button>' % (E(ans), extra, label_html)


def card_html(c):
    cid = "%s-%s-%s" % (c["date"], c["i"], c["type"])
    prefix = "%s %s line %s %s" % (c["date"], c["mmss"], c["i"], c["type"])
    if c["type"] == "council":
        cid, prefix = "%s-%s-council" % (c["date"], c["uid"]), "%s %s %s council" % (c["date"], c["mmss"], c["uid"])
        q = "Did you say it wrong here?"
        sub = "Amal confirmed this slip. The second listen wrote your line another way, and the slip is not on it any more."
        rows = [("Old line", c.get("line_before")), ("New line", c.get("line_after")),
                ("Amal corrected", "%s \u2192 %s" % (c.get("wrong") or "", c.get("right") or ""))]
        buttons = [btn("I said it wrong (her fix was needed)", "I said it wrong (her fix was needed)"),
                   btn("I said it right", "I said it right"), btn("not sure", "Not sure")]
        tag = "Amal's fix"
    elif c["type"] == "spot":
        q = "Old line / New line - which did you say?"
        sub = "A blind listen by the AI preferred the old line here. The transcript now shows the new one."
        rows = [("Old line", c.get("engine")), ("New line", c.get("heard"))]
        buttons = [btn("the old line (%s)" % (c.get("engine") or ""), "The old line: %s" % bdi(c.get("engine") or "")),
                   btn("the new line (%s)" % (c.get("heard") or ""), "The new line: %s" % bdi(c.get("heard") or "")),
                   btn("neither", "Neither. I'll type it", ' data-type="1"'),
                   '<input class="typed" id="typed-%s" type="text" dir="auto" autocomplete="off" autocapitalize="off" '
                   'placeholder="Type what you said" aria-label="Type what you said" hidden>' % E(cid),
                   btn("not sure", "Not sure")]
        tag = "Old or new"
    elif c["type"] == "his-correction":
        his, wrote = c.get("his") or "", c.get("engine_wrote") or ""
        q = "Did you say %s?" % bdi(his)
        sub = "The old engine wrote %s. You fixed it to %s. Gemini did not hear that." % (bdi(wrote), bdi(his))
        rows = [("Old engine", c.get("engine_line"))]
        if c.get("line_now") and c.get("line_now") != c.get("engine_line"):
            rows.append(("With your fix", c.get("line_now")))
        else:
            rows.append(("Your fix", "%s \u2192 %s" % (wrote, his)))
        rows += run_rows(c.get("runs"))
        buttons = [btn("what I typed (%s)" % his, "What I typed: %s" % bdi(his))]
        seen = []
        for text, ns in group_runs(c.get("runs")):
            if not text:                                   # a run that returned no line is not "heard nothing"
                continue
            s = spot(c.get("engine_line"), wrote, text)
            label = (text if s is None else s) or ""
            if norm(label) in [norm(x) for x in seen]:
                continue
            seen.append(label)
            if label:
                buttons.append(btn("Gemini (%s)" % label, "Gemini heard: %s" % bdi(label)))
            else:
                buttons.append(btn("Gemini (no word there)", "Gemini heard: no word there"))
        buttons.append(btn("neither", "Neither. I'll type it", ' data-type="1"'))
        buttons.append('<input class="typed" id="typed-%s" type="text" dir="auto" autocomplete="off" autocapitalize="off" '
                       'placeholder="Type what you said" aria-label="Type what you said" hidden>' % E(cid))
        tag = "Your fix"
    else:
        hw = words(c.get("her_words"))
        w = " ".join(hw) if hw else ""
        q = ("Did you say %s?" % bdi(w)) if w else "Did you say the extra word?"
        sub = "Amal says it right after. Gemini thinks you said it too."
        rows = [("Old engine", c.get("engine")), ("Gemini wants", c.get("heard"))]
        rr = run_rows(c.get("runs"))
        if not (len(rr) == 1 and (rr[0][1] or "").strip() == (c.get("heard") or "").strip()):
            rows += rr
        else:
            rows[1] = ("Gemini wants (%s)" % rr[0][0][8:-1], c.get("heard"))
        if w:
            rows.append(("Amal, right after", w))
        said = ("Yes, I said %s: Gemini's line is right" % bdi(w)) if w else "Yes, I said it: Gemini's line is right"
        buttons = [btn("yes, I said it (%s): Gemini's line is right" % w if w else "yes, I said it: Gemini's line is right", said),
                   btn("no, I did not say it: keep the old line", "No, I did not say it: keep the old line"),
                   btn("not sure", "Not sure")]
        tag = "Extra word"
    return ('<article class="card" data-id="%s" data-prefix="%s">'
            '<p class="when"><span class="tag">%s</span> <span class="date">%s</span> at <span class="time">%s</span></p>'
            '<h2>%s</h2><p class="sub">%s</p>'
            '<div class="players">%s%s</div>'
            '%s<div class="answers">%s</div></article>') % (
        E(cid), E(prefix), E(tag), E(c["date"]), E(c["mmss"]), q, sub,
        player("Your microphone only", c.get("own_uri"), "This clip is missing."),
        player("You and Amal, 6 seconds before to 8 after", c.get("both_uri"), "No recording of both of you for this lesson."),
        table(rows), "".join(buttons))


# ---------------------------------------------------------------- page

CSS = r"""
/* layout: one narrow column of question cards; sticky count on top; answers box at the bottom */
:root{
  --bg:#f2f6f0; --card:#fbfdf9; --ink:#1b2a21; --muted:#56675c; --line:#d3dcd1;
  --accent:#1c774a; --accent-ink:#ffffff; --accent-soft:#e0f0e5;
  --font:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans","Noto Naskh Arabic","Geeza Pro",Tahoma,sans-serif;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#111812; --card:#18211b; --ink:#e5eee7; --muted:#9bb0a2; --line:#2c3b31;
    --accent:#5fc891; --accent-ink:#0b1a11; --accent-soft:#1d3527; color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#111812; --card:#18211b; --ink:#e5eee7; --muted:#9bb0a2; --line:#2c3b31;
  --accent:#5fc891; --accent-ink:#0b1a11; --accent-soft:#1d3527; color-scheme:dark;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--font);font-size:17px;line-height:1.45;margin:0}
.wrap{max-width:34rem;margin:0 auto;padding-inline:16px;padding-block:20px 40px;display:flex;flex-direction:column;gap:20px}
h1{font-size:1.5rem;line-height:1.2;margin:0;text-wrap:balance}
.lead{margin:6px 0 0;color:var(--muted)}
.progress{position:sticky;top:env(safe-area-inset-top,0px);z-index:2;background:var(--bg);padding-block:10px;
  border-bottom:2px solid var(--accent);font-weight:700;font-variant-numeric:tabular-nums;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.progress .pg{font-weight:400;color:var(--muted)}
.cards{display:flex;flex-direction:column;gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:14px;min-width:0}
.card.done{border-color:var(--accent)}
.when{margin:0;color:var(--muted);font-size:.9rem;font-variant-numeric:tabular-nums}
.tag{display:inline-block;background:var(--accent-soft);color:var(--ink);border-radius:4px;padding:1px 8px;margin-inline-end:4px;font-weight:600}
.time{font-weight:700;color:var(--ink)}
h2{font-size:1.3rem;line-height:1.3;margin:0;text-wrap:balance;overflow-wrap:anywhere}
.sub{margin:-8px 0 0;color:var(--muted);overflow-wrap:anywhere}
.players{display:flex;flex-direction:column;gap:12px}
.player{display:flex;flex-direction:column;gap:4px;min-width:0}
.plabel{font-weight:600;font-size:.95rem}
audio{width:100%;max-width:100%;height:44px;display:block}
.wrote{width:100%;table-layout:fixed;border-collapse:collapse;font-size:.95rem}
.wrote th,.wrote td{padding:7px 0;border-top:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}
.wrote th{width:7.2em;padding-inline-end:10px;text-align:start;font-weight:600;color:var(--muted);font-size:.85rem}
.wrote td{unicode-bidi:plaintext}
.none{color:var(--muted);font-style:italic}
.answers{display:flex;flex-direction:column;gap:10px}
.ans{font:inherit;font-weight:600;text-align:start;min-height:56px;padding:12px 14px;border-radius:10px;cursor:pointer;
  background:var(--card);color:var(--ink);border:2px solid var(--line);overflow-wrap:anywhere;width:100%}
.ans:hover{border-color:var(--accent)}
.ans[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.ans[aria-pressed="true"]::before{content:"\2713\00a0\00a0"}
.typed{font:inherit;width:100%;min-height:52px;padding:10px 12px;border-radius:10px;border:2px solid var(--accent);background:var(--bg);color:var(--ink)}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.out{display:flex;flex-direction:column;gap:12px}
.out h2{font-size:1.2rem}
#answers-box{font:inherit;font-size:.9rem;width:100%;min-height:9.5em;padding:10px 12px;border-radius:10px;border:1px solid var(--line);
  background:var(--card);color:var(--ink);resize:vertical}
#copy-btn{font:inherit;font-size:1.15rem;font-weight:700;min-height:64px;border-radius:10px;border:0;cursor:pointer;
  background:var(--accent);color:var(--accent-ink);width:100%;padding:12px 14px}
#copy-msg{margin:0;color:var(--muted);min-height:1.45em}
"""

JS = r"""
(function(){
  var KEY=%(key)s, state={};
  try{ state=JSON.parse(localStorage.getItem(KEY)||"{}")||{}; }catch(e){ state={}; }
  var cards=[].slice.call(document.querySelectorAll(".card"));
  var box=document.getElementById("answers-box"), count=document.getElementById("count"), msg=document.getElementById("copy-msg");
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify(state)); }catch(e){} }
  function answer(card){
    var s=state[card.dataset.id]; if(!s) return null;
    var b=card.querySelectorAll(".ans")[s.b]; if(!b) return null;
    if(b.dataset.type) return "neither, I said: "+((s.typed||"").trim()||"(not typed yet)");
    return b.dataset.ans;
  }
  function render(){
    var lines=[], n=0;
    cards.forEach(function(card){
      var s=state[card.dataset.id], btns=card.querySelectorAll(".ans"), inp=card.querySelector(".typed"), a=answer(card);
      for(var i=0;i<btns.length;i++) btns[i].setAttribute("aria-pressed", s&&s.b===i?"true":"false");
      if(inp){ var on=!!(s&&btns[s.b]&&btns[s.b].dataset.type); inp.hidden=!on; if(on&&inp.value!==(s.typed||"")&&document.activeElement!==inp) inp.value=s.typed||""; }
      card.classList.toggle("done", !!a);
      if(a){ n++; lines.push(card.dataset.prefix+": "+a); }
    });
    box.value=lines.join("\n");
    count.textContent=n+" of "+cards.length+" answered";
  }
  cards.forEach(function(card){
    var btns=[].slice.call(card.querySelectorAll(".ans")), inp=card.querySelector(".typed"), id=card.dataset.id;
    btns.forEach(function(b,i){
      b.addEventListener("click",function(){
        if(state[id]&&state[id].b===i){ delete state[id]; }
        else{ state[id]={b:i,typed:(state[id]&&state[id].typed)||""}; }
        save(); render();
        if(b.dataset.type&&state[id]&&inp){ inp.focus(); }
      });
    });
    if(inp) inp.addEventListener("input",function(){ if(state[id]){ state[id].typed=inp.value; save(); render(); } });
  });
  document.getElementById("copy-btn").addEventListener("click",function(){
    var text=box.value;
    if(!text){ msg.textContent="Nothing to copy yet. Tap an answer first."; return; }
    function fallback(){
      box.focus(); box.select();
      var ok=false; try{ ok=document.execCommand("copy"); }catch(e){}
      msg.textContent=ok?"Copied. Now paste it to Claude.":"The text is selected. Press copy, then paste it to Claude.";
    }
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){ msg.textContent="Copied. Now paste it to Claude."; },fallback);
    } else fallback();
  });
  document.addEventListener("play",function(e){
    [].forEach.call(document.querySelectorAll("audio"),function(a){ if(a!==e.target) a.pause(); });
  },true);
  render();
})();
"""


def page_shell(n, total):
    head = ('<title>Listen and tap</title>\n<style>%s</style>\n<div class="wrap">\n'
            '<header><h1>Listen and tap</h1><p class="lead">Play the sound. Tap what you said.</p></header>\n'
            '<div class="progress" role="status"><span id="count">0 answered</span><span class="pg">Page %d of %d</span></div>\n'
            '<main class="cards">\n' % (CSS, n, total))
    tail = ('\n</main>\n<section class="out"><h2>Your answers</h2>'
            '<textarea id="answers-box" readonly aria-label="Your answers" placeholder="Your answers show up here."></textarea>'
            '<button type="button" id="copy-btn">Copy my answers</button><p id="copy-msg" role="status"></p></section>\n'
            '</div>\n<script>%s</script>\n' % (JS % {"key": json.dumps(STORE_KEY)}))
    return head, tail


def standalone(body):
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>\n'
            + body + "</body></html>\n")


# ---------------------------------------------------------------- collect + pack

def collect(date, plan_root, max_held):
    plan_path = os.path.join(plan_root, date, "apply-plan.json")
    if not os.path.exists(plan_path):
        return None
    plan = J(plan_path)
    d = os.path.join(REHEAR, date)
    by_i = {ln["i"]: ln for ln in J(os.path.join(d, "lines.json"))["lines"]}
    cards = []
    for r in plan.get("listen") or []:
        if r.get("type", "his-correction") == "his-correction":
            cards.append(dict(r, type="his-correction", date=date))
    held = sorted(plan.get("held") or [], key=lambda r: r["t"])
    if max_held is not None:
        held = held[:max_held]
    cards += [dict(r, type="held", date=date) for r in held]
    for c in cards:
        ln = by_i.get(c["i"]) or {}
        c.setdefault("mmss", mmss(c["t"]))
        c["end"] = ln.get("end", float(c["t"]) + 3.0)
        c["clip_path"] = os.path.join(d, ln["clip"]) if ln.get("clip") else None
    return cards


def spot_cards(date):
    """The spot-check lines of one lesson where the blind listen preferred the old text (rehear/<date>/spot.json)."""
    p = os.path.join(REHEAR, date, "spot.json")
    if not os.path.exists(p):
        return []
    d = os.path.join(REHEAR, date)
    by_i = {ln["i"]: ln for ln in J(os.path.join(d, "lines.json"))["lines"]}
    out = []
    for i, r in sorted(J(p)["lines"].items(), key=lambda kv: int(kv[0])):
        if r.get("verdict") != "old text":
            continue
        ln = by_i.get(int(i)) or {}
        if "t" not in ln:
            continue
        out.append({"type": "spot", "date": date, "i": int(i), "t": ln["t"], "end": ln.get("end", ln["t"] + 3.0), "mmss": mmss(ln["t"]),
                    "engine": r.get("engine"), "heard": r.get("heard"), "votes": r.get("votes"),
                    "clip_path": os.path.join(d, ln["clip"]) if ln.get("clip") else None})
    return out


def _secs(v):
    n = 0.0
    for x in str(v).split(":"):
        n = n * 60 + float(x)
    return n


def _gone(wrong, line):
    return bool(norm(wrong)) and norm(wrong) not in norm(line)


def council_cards(kept_path=None):
    """Amal-confirmed slips whose line the second listen changed so that the slip is no longer on it
    (rejudge/kept-rows.json kept_confirmed: line_changed and the wrong piece is not in the new line). The line is his
    line of the lesson that holds the slip's time; its microphone clip is the re-hear's own cut when that line was
    re-heard, else it is cut from his track now (scripts/rehear_audio.clip)."""
    K = J(kept_path or os.path.join(REJUDGE, "kept-rows.json"))
    out = []
    for x in K.get("kept_confirmed") or []:
        if not x.get("line_changed") or not _gone(x.get("wrong"), x.get("line_after")):
            continue
        d = os.path.join(REHEAR, x["date"])
        lines = J(os.path.join(d, "lines.json"))["lines"] if os.path.exists(os.path.join(d, "lines.json")) else []
        t = _secs(x["t"])
        cand = [ln for ln in lines if ln["t"] <= t + 1.0] or lines[:1]
        ln = max(cand, key=lambda l: l["t"]) if cand else {"i": -1, "t": t, "end": t + 3.0}
        out.append({"type": "council", "date": x["date"], "uid": x["uid"], "i": ln["i"], "t": ln["t"], "end": ln.get("end", ln["t"] + 3.0),
                    "mmss": mmss(ln["t"]), "wrong": x.get("wrong"), "right": x.get("right"), "line_before": x.get("line_before"),
                    "line_after": x.get("line_after"), "clip_path": os.path.join(d, ln["clip"]) if ln.get("clip") else None,
                    "cut_own": not ln.get("clip")})
    return out


def cut_own(c):
    """His microphone for a line the re-hear did not cut: a fresh cut from his track (rehear_audio.clip), 0.6 s around."""
    import tempfile
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rehear_audio as RA
    out = os.path.join(tempfile.gettempdir(), "anees-listen-%s-%s.wav" % (c["date"], c["i"]))
    src = RA.clip(c["date"], "Medi", max(0.0, float(c["t"]) - 0.6), float(c["end"]) + 0.6, out)
    return out, src


def encode(c, srcs):
    warn = []
    c["own_uri"] = c["both_uri"] = None
    if c.get("cut_own"):
        try:
            c["clip_path"], src = cut_own(c)
            if src != "own":
                warn.append("no separate microphone track here: the first player is the recording of both of you")
        except (SystemExit, Exception) as e:  # noqa: BLE001
            warn.append("his clip could not be cut: %s" % e)
    if c["clip_path"] and os.path.exists(c["clip_path"]):
        try:
            c["own_uri"] = data_uri(own_mp3(c["clip_path"]))
        except RuntimeError as e:
            warn.append("his clip: %s" % e)
    else:
        warn.append("his clip is missing")
    if srcs:
        try:
            c["both_uri"] = data_uri(both_mp3(srcs, c["t"], c["end"]))
        except RuntimeError as e:
            warn.append("both-speakers cut: %s" % e)
    else:
        warn.append("no both-speakers recording")
    c["html"] = card_html(c)
    c["bytes"] = len(c["html"].encode("utf-8")) + 1
    return ["%s line %s (%s): %s" % (c["date"], c["i"], c["mmss"], w) for w in warn]


def pack(groups, overhead):
    """groups: lists of cards kept together when they fit on one page. Greedy, in order."""
    pages, cur, size = [], [], overhead
    for g in groups:
        gsize = sum(c["bytes"] for c in g)
        if cur and size + gsize > PAGE_LIMIT and overhead + gsize <= PAGE_LIMIT:
            pages.append(cur)
            cur, size = [], overhead
        for c in g:
            if cur and size + c["bytes"] > PAGE_LIMIT:
                pages.append(cur)
                cur, size = [], overhead
            cur.append(c)
            size += c["bytes"]
    if cur:
        pages.append(cur)
    return pages


def main():
    ap = argparse.ArgumentParser(description="Build the listen pages for the second-listen moments that need Medi's ear.")
    ap.add_argument("dates", nargs="*", help="lesson dates (default: every lesson with an apply-plan.json)")
    ap.add_argument("--max-held", type=int, default=None, metavar="N", help="at most N held cards per lesson (default: all)")
    ap.add_argument("--out", default=OUT_DIR, help="where the pages go (default: %s)" % OUT_DIR)
    ap.add_argument("--plan-root", default=REHEAR, help="read <plan-root>/<date>/apply-plan.json (testing; audio and lines.json still come from the repo)")
    ap.add_argument("--standalone", action="store_true", help="wrap each page in a full HTML document (for opening the file from disk; do not publish these)")
    ap.add_argument("--spot", action="store_true", help="add a third section: the spot-check lines where the blind listen preferred the old text")
    ap.add_argument("--council", action="store_true", help="write only the council check pages (council-check-<n>.html): Amal-confirmed slips whose line changed")
    a = ap.parse_args()
    if a.council:
        return council_main(a)

    dates = a.dates or sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(a.plan_root, "*", "apply-plan.json")))
    dates = sorted((d for d in dates if DATE_RE.match(d)), reverse=True)          # newest lesson first
    per = {}
    for date in dates:
        cards = collect(date, a.plan_root, a.max_held)
        if cards is None:
            print("%s: no apply-plan.json yet - left out" % date)
            continue
        per[date] = cards
    spots = {d: spot_cards(d) for d in per} if a.spot else {}
    for d in per:
        per[d] = per[d] + spots.get(d, [])
    todo = [c for d in per for c in per[d]]
    if not todo:
        print("No cards: no lesson here has an apply-plan.json with listen or held moments. Nothing written.")
        return 0

    srcs = {d: both_sources(d) for d in per}
    with ThreadPoolExecutor(max_workers=6) as ex:
        warns = [w for ws in ex.map(lambda c: encode(c, srcs[c["date"]]), todo) for w in ws]

    groups = [[c for d in per for c in per[d] if c["type"] == "his-correction"]]
    groups += [[c for c in per[d] if c["type"] == "held"] for d in per]
    groups += [[c for d in per for c in per[d] if c["type"] == "spot"]]
    groups = [g for g in groups if g]
    head, tail = page_shell(99, 99)
    overhead = len((head + tail).encode("utf-8")) + (200 if a.standalone else 0)
    pages = pack(groups, overhead)

    os.makedirs(a.out, exist_ok=True)
    for old in glob.glob(os.path.join(a.out, "listen-page-*.html")):
        os.remove(old)
    for n, cards in enumerate(pages, 1):
        head, tail = page_shell(n, len(pages))
        body = head + "\n".join(c["html"] for c in cards) + tail
        if a.standalone:
            body = standalone(body)
        path = os.path.join(a.out, "listen-page-%d.html" % n)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        hc = sum(1 for c in cards if c["type"] == "his-correction")
        sp = sum(1 for c in cards if c["type"] == "spot")
        lessons = []
        for c in cards:
            if c["date"] not in lessons:
                lessons.append(c["date"])
        print("%s  %.2f MB  %d cards (%d his-correction, %d held, %d old-or-new)  lessons: %s" % (
            path, os.path.getsize(path) / 1e6, len(cards), hc, len(cards) - hc - sp, sp, ", ".join(lessons)))
    print("%d page(s), %d cards, %d lesson(s)" % (len(pages), len(todo), len(per)))
    for w in warns:
        print("WARNING " + w)
    return 0


def council_main(a):
    """The council check: one card per Amal-confirmed slip whose line changed (see council_cards). Own pages."""
    todo = council_cards()
    if not todo:
        print("No council cards: kept-rows.json lists no Amal-confirmed slip whose line changed. Nothing written.")
        return 0
    todo.sort(key=lambda c: (c["date"], c["t"]))
    srcs = {d: both_sources(d) for d in {c["date"] for c in todo}}
    with ThreadPoolExecutor(max_workers=6) as ex:
        warns = [w for ws in ex.map(lambda c: encode(c, srcs[c["date"]]), todo) for w in ws]
    head, tail = council_shell(99, 99)
    overhead = len((head + tail).encode("utf-8")) + (200 if a.standalone else 0)
    pages = pack([todo], overhead)
    os.makedirs(a.out, exist_ok=True)
    for old in glob.glob(os.path.join(a.out, "council-check-*.html")):
        os.remove(old)
    for n, cards in enumerate(pages, 1):
        head, tail = council_shell(n, len(pages))
        body = head + "\n".join(c["html"] for c in cards) + tail
        if a.standalone:
            body = standalone(body)
        path = os.path.join(a.out, "council-check-%d.html" % n)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        print("%s  %.2f MB  %d cards (council check)  lessons: %s" % (path, os.path.getsize(path) / 1e6, len(cards), ", ".join(sorted({c["date"] for c in cards}))))
    print("%d page(s), %d council cards, %d lesson(s)" % (len(pages), len(todo), len(srcs)))
    for w in warns:
        print("WARNING " + w)
    return 0


def council_shell(n, total):
    head, tail = page_shell(n, total)
    head = head.replace("<title>Listen and tap</title>", "<title>Council check</title>").replace(
        "<h1>Listen and tap</h1><p class=\"lead\">Play the sound. Tap what you said.</p>",
        "<h1>Council check</h1><p class=\"lead\">Amal confirmed these slips. The second listen wrote the line another way. Play the sound, then tap: did you say it wrong?</p>")
    return head, tail.replace(json.dumps(STORE_KEY), json.dumps(STORE_KEY + "-council"))


if __name__ == "__main__":
    sys.exit(main())
