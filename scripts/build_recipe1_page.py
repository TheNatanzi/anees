"""Side-by-side page: ElevenLabs Scribe v2 vs Codex Recipe 1 (ElevenLabs slices -> gpt-transcribe) on the 20 Check 02 clips.
Labels shown (Recipe 1 borrows ElevenLabs labels, so nothing to blind). Writes scratchpad html (artifact) + docs/recipe1.html."""
import json, io, base64, html, re, sys
R = 'data/aug25/'
wins = json.load(io.open(R + 'check02_windows.json', encoding='utf-8'))
rec = json.load(io.open(R + 'openai_recipe1.json', encoding='utf-8'))
FILL = re.compile(r"^[\W_]*(u+m+|u+h+|h+m+|m+m+|أ*م+|ا+م+|آ+|ا{2,}|ه+م+|إ+م+)[\W_]*$", re.I)
def turns(segs, k):
    out = []
    for s in segs:
        t = s[k].strip()
        if not t: t = '(nothing)'
        out.append(f'<div class="turn {s["spk"].lower()}"><span class="who">{s["spk"]}</span><span class="txt" dir="auto">{html.escape(t)}</span></div>')
    return ''.join(out)
tot_e = tot_r = blanks = 0; rows = []
for w in wins:
    i = w['i']; segs = rec[str(i)]
    e = sum(len(s['ele'].split()) for s in segs); r = sum(len(s['text'].split()) for s in segs); b = sum(1 for s in segs if not s['text'])
    tot_e += e; tot_r += r; blanks += b
    b64 = base64.b64encode(open(w['clip'], 'rb').read()).decode()
    m, s_ = int(w['start'] // 60), int(w['start'] % 60)
    rows.append(f'<section class="row"><div class="meta"><span class="t">#{i+1}</span><span class="t">{m:02d}:{s_:02d}</span><span class="t">{len(segs)} slices</span><span class="t">{e} vs {r} words</span></div>'
                f'<audio controls preload="none" src="data:audio/mpeg;base64,{b64}"></audio>'
                f'<div class="cols"><div class="col"><div class="lbl">ElevenLabs</div>{turns(segs, "ele")}</div><div class="col"><div class="lbl">Recipe 1</div>{turns(segs, "text")}</div></div></section>')
body = f'''<title>Anees Recipe 1</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap">
<style>
:root{{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E;--medi:#E9F1EC;--amal:#F7EFE3}}
@media(prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--medi:#1B2A24;--amal:#2A2419}}}}
:root[data-theme="dark"]{{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--medi:#1B2A24;--amal:#2A2419}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:16px}} h1{{font-size:26px;margin:8px 0 4px;text-wrap:balance}} .lead{{color:var(--mute);margin:0 0 14px}}
.score{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 18px}}
.score div{{background:var(--bg2);border:1px solid var(--line);border-radius:10px;padding:10px 12px}} .score b{{display:block;font-size:24px;font-variant-numeric:tabular-nums}} .score span{{color:var(--mute);font-size:14px}}
.row{{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:0 0 14px}}
.meta{{display:flex;gap:14px;color:var(--mute);font-size:14px;font-variant-numeric:tabular-nums;margin-bottom:6px}} .meta .t:first-child{{color:var(--teal);font-weight:700}}
audio{{width:100%;margin:0 0 10px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:12px}} @media(max-width:640px){{.cols{{grid-template-columns:1fr}}}}
.lbl{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin-bottom:6px}}
.turn{{display:grid;grid-template-columns:48px 1fr;gap:8px;padding:4px 8px;border-radius:6px;margin-bottom:3px}} .turn.medi{{background:var(--medi)}} .turn.amal{{background:var(--amal)}}
.who{{font-size:12px;font-weight:700;color:var(--mute);padding-top:4px}} .txt{{font-size:19px;line-height:1.5}}
</style>
<main><h1>Anees Recipe 1</h1>
<p class="lead">Aug 25 lesson, the same 20 clips. Left = ElevenLabs Scribe v2 as-is. Right = Codex Recipe 1: each ElevenLabs speaker turn cut out and sent to ChatGPT's transcriber (gpt-transcribe, Arabic + English, verbatim prompt). Green rows = Medi, sand rows = Amal.</p>
<div class="score"><div><b>{tot_e}</b><span>ElevenLabs words</span></div><div><b>{tot_r}</b><span>Recipe 1 words</span></div><div><b>{sum(len(rec[str(w["i"])]) for w in wins)}</b><span>slices sent</span></div><div><b>{blanks}</b><span>slices came back empty</span></div></div>
{''.join(rows)}</main>'''
open(sys.argv[1], 'w', encoding='utf-8').write(body)
open('docs/recipe1.html', 'w', encoding='utf-8').write('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + body.replace('<main>', '</head><body><main>') + '</body></html>')
print('ok', tot_e, tot_r, blanks, 'KB', len(body) // 1024)
