"""Check 03: ElevenLabs Scribe v2 vs ChatGPT's transcriber (gpt-4o-transcribe, Arabic-hinted) on the same 20 clips.
Plain words only for both (no speaker labels, no pause tags) so nothing gives the engine away."""
import json, io, base64, os, html, random, re
random = random.SystemRandom()
R = 'data/aug25/'
wins = json.load(io.open(R + 'check02_windows.json', encoding='utf-8'))
ele = json.load(io.open(R + 'eleven_scribe_auto.json', encoding='utf-8'))['words']
ele = [w for w in ele if w['type'] == 'word']
gpt = json.load(io.open(R + 'openai_clips_gpttranscribe.json', encoding='utf-8'))
chat = json.load(io.open(R + 'openai_chat_clips.json', encoding='utf-8'))
def clean(t):
    t = re.sub(r'"?(Learner|Tutor)"?\s*:\s*', ' ', t)
    return re.sub(r'[{}\[\]"]', ' ', t).strip()
FILL = re.compile(r"^[\W_]*(u+m+|u+h+|h+m+|m+m+|أ*م+|ا+م+|آ+|ا{2,}|ه+م+|إ+م+)[\W_]*$", re.I)
def ele_text(st, en):
    out = []
    for w in ele:
        dur = max(0.05, w['end'] - w['start']); ins = min(w['end'], en) - max(w['start'], st)
        if ins / dur >= 0.6 and not FILL.match(w['text']):
            out.append(w['text'].replace('\ufffd', ''))
    return ' '.join(out)
def gpt_text(i):
    return ' '.join(s['text'] for s in gpt.get(str(i), []))
def chat_text(i):
    return ' '.join(clean(s['text']) for s in chat.get(str(i), []))
rows = []; key = {}
for w in wins:
    i = w['i']; st, en = w['start'], w['end']
    b64 = base64.b64encode(open(w['clip'], 'rb').read()).decode()
    pair = [('eleven', ele_text(st, en)), ('gpt-transcribe', gpt_text(i)), ('gpt-audio', chat_text(i))]
    random.shuffle(pair); key[i] = [p[0] for p in pair]
    cols = ''.join(f'<div class="col"><div class="lbl">{L}</div><p class="ar" dir="auto">{html.escape(t) or "(nothing)"}</p></div>' for L, (_, t) in zip('ABC', pair))
    m, s = int(st // 60), int(st % 60)
    rows.append(f'<div class="row" data-i="{i}"><div class="meta"><span class="t">{m:02d}:{s:02d}</span><span class="t">#{i+1}</span></div>'
                f'<audio controls preload="none" src="data:audio/mpeg;base64,{b64}"></audio><div class="cols">{cols}</div>'
                f'<div class="btns"><button data-v="A">A</button><button data-v="B">B</button><button data-v="C">C</button><button data-v="tie">Same</button><button data-v="none">Both wrong</button></div></div>')
n = len(rows)
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Anees Check 03</title>
<style>
:root{{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E;--coral:#B54324}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--coral:#F08A6C}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:16px}} h1{{font-size:26px;margin:8px 0 4px}} .lead{{color:var(--mute);margin:0 0 14px}}
.bar{{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:8px;align-items:center;font-weight:700;z-index:2}}
.bar button{{margin-left:8px;background:var(--teal);color:#fff;border:0;border-radius:999px;padding:8px 14px;font-weight:700;cursor:pointer}} .bar span{{margin-right:auto}}
.row{{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:12px 0}} .row.done{{opacity:.55}}
.meta{{display:flex;gap:10px;font-size:12px;color:var(--mute);margin-bottom:6px}} audio{{width:100%;margin:4px 0}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:8px 0}}
.col{{border:1px solid var(--line);border-radius:10px;padding:8px 10px;min-width:0;overflow-wrap:anywhere}} .lbl{{font-weight:700;color:var(--teal);font-size:14px}}
.ar{{font-size:19px;line-height:1.6;margin:6px 0}}
.btns{{display:flex;gap:8px;flex-wrap:wrap}} .btns button{{flex:1;min-width:70px;padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:15px;cursor:pointer}}
.btns button.on{{background:var(--teal);color:#fff;border-color:var(--teal)}} .btns button.on[data-v=none]{{background:var(--coral);border-color:var(--coral)}} .btns button.on[data-v=tie]{{background:var(--amber);border-color:var(--amber)}}
.note{{font-size:13px;color:var(--mute);margin:20px 0}}
</style></head><body><main>
<h1>Anees check 03</h1>
<p class="lead">Same 20 clips. Three engines wrote down the words (ElevenLabs and two ChatGPT models), shown as A, B, C in a random order on every row. No names, no pauses, just the words. Play the clip, then tap the one that matches what was said best. "Same" if they tie, "Both wrong" if neither is close.</p>
<div class="bar"><span id="cnt">0 / {n}</span><button id="copy">Copy results</button><button id="mail">Email results to Medi</button></div>
{''.join(rows)}
<p class="note">Answers save on this device. When you hit {n}, tap Copy results (paste to Claude) or Email results to Medi.</p>
</main><script>
const K='anees-check-03-v4';let st={{}};try{{st=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{}}
function paint(){{let c=0;document.querySelectorAll('.row').forEach(r=>{{const v=st[r.dataset.i];r.classList.toggle('done',!!v);if(v)c++;r.querySelectorAll('.btns button').forEach(b=>b.classList.toggle('on',b.dataset.v===v))}});document.getElementById('cnt').textContent=c+' / {n}'}}
document.querySelectorAll('.btns button').forEach(b=>b.addEventListener('click',()=>{{const r=b.closest('.row');st[r.dataset.i]=b.dataset.v;try{{localStorage.setItem(K,JSON.stringify(st))}}catch(e){{}}paint()}}));
const out=()=>'anees-check-03 '+Object.entries(st).map(([i,v])=>i+':'+v).join(',');
document.getElementById('copy').addEventListener('click',()=>{{navigator.clipboard.writeText(out()).then(()=>{{document.getElementById('copy').textContent='Copied'}})}});
document.getElementById('mail').addEventListener('click',()=>{{location.href='mailto:thenatanzi@gmail.com?subject='+encodeURIComponent('Anees check 03 results')+'&body='+encodeURIComponent(out())}});
paint();
</script></body></html>'''
io.open(r'C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\abd0ba78-530c-4869-b100-285fee95f910\scratchpad\anees-check-03.html', 'w', encoding='utf-8').write(page)
os.makedirs('docs', exist_ok=True); io.open('docs/check03.html', 'w', encoding='utf-8').write(page)
json.dump(key, io.open(R + 'check03_key.json', 'w', encoding='utf-8'), indent=1)
print('check03 rows', n, 'KB', len(page) // 1024, 'positions', {n: [sum(1 for v in key.values() if v[p] == n) for p in range(3)] for n in ['eleven','gpt-transcribe','gpt-audio']})
