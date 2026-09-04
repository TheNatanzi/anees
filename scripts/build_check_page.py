import json,io,base64,subprocess,os,html
src=r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\aug25.mp3"
sel=json.load(io.open('data/aug25/gold_selection_v2.json',encoding='utf-8'))
os.makedirs('data/aug25/clips',exist_ok=True)
rows=[]
for i,r in enumerate(sel):
    st=max(0,(r['start'] or 0)-0.5); en=(r['end'] or st+3)+0.7
    if en<st+2: en=st+2
    if en-st>14: en=st+14
    out=f"data/aug25/clips/{i:02d}.mp3"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",str(st),"-to",str(en),"-i",src,"-ac","1","-b:a","48k",out],check=True)
    b64=base64.b64encode(open(out,'rb').read()).decode()
    m=int((r['start'] or 0)//60); s=int((r['start'] or 0)%60)
    rows.append(f'''<div class="row" data-i="{i}"><div class="meta"><span class="k k-{r['kind']}">{r['kind']}</span><span class="t">{m:02d}:{s:02d}</span></div>
<audio controls preload="none" src="data:audio/mpeg;base64,{b64}"></audio>
<p class="ar" dir="auto">{html.escape(r['text'])}</p>
<div class="btns"><button data-v="right">Right</button><button data-v="wrong">Wrong</button><button data-v="unsure">Unsure</button></div></div>''')
page=f'''<title>Anees Check 01</title>
<style>
:root{{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E;--coral:#B54324}}
@media(prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--coral:#F08A6C}}}}
:root[data-theme="dark"]{{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--coral:#F08A6C}}
body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif}}
main{{max-width:720px;margin:0 auto;padding:16px}}
h1{{font-size:26px;margin:8px 0 4px}} .lead{{color:var(--mute);margin:0 0 14px}}
.bar{{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;font-weight:700}}
.bar button{{margin-left:auto;background:var(--teal);color:#fff;border:0;border-radius:999px;padding:8px 14px;font-weight:700;cursor:pointer}}
.row{{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:12px 0}}
.row.done{{opacity:.55}}
.meta{{display:flex;gap:10px;align-items:center;font-size:12px;color:var(--mute);margin-bottom:6px}}
.k{{padding:2px 8px;border-radius:999px;border:1px solid var(--line);text-transform:uppercase;letter-spacing:.06em;font-size:11px}}
.k-correction{{color:var(--teal);border-color:var(--teal)}} .k-gap{{color:var(--amber);border-color:var(--amber)}} .k-hesitation{{color:var(--coral);border-color:var(--coral)}}
audio{{width:100%;margin:4px 0}}
.ar{{font-size:22px;line-height:1.7;margin:8px 0}}
.btns{{display:flex;gap:8px}} .btns button{{flex:1;padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:15px;cursor:pointer}}
.btns button.on{{background:var(--teal);color:#fff;border-color:var(--teal)}} .btns button.on[data-v=wrong]{{background:var(--coral);border-color:var(--coral)}} .btns button.on[data-v=unsure]{{background:var(--amber);border-color:var(--amber)}}
.note{{font-size:13px;color:var(--mute);margin:20px 0}}
</style>
<main>
<h1>Anees check 01</h1>
<p class="lead">Aug 25 lesson, 50 lines from the dialect engine (v2, tight clips). Play the clip, read the line: does the text match what was said? Right = mostly right. Wrong = wrong words. Unsure = can't tell.</p>
<div class="bar"><span id="cnt">0 / 50</span><button id="copy">Copy results</button></div>
{''.join(rows)}
<p class="note">Answers save on this device. When you hit 50, tap Copy results and paste them to Claude.</p>
</main>
<script>
const K='anees-check-01-v2';let st={{}};try{{st=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{}}
function paint(){{let n=0;document.querySelectorAll('.row').forEach(r=>{{const v=st[r.dataset.i];r.classList.toggle('done',!!v);if(v)n++;r.querySelectorAll('.btns button').forEach(b=>b.classList.toggle('on',b.dataset.v===v))}});document.getElementById('cnt').textContent=n+' / 50'}}
document.querySelectorAll('.btns button').forEach(b=>b.addEventListener('click',()=>{{const r=b.closest('.row');st[r.dataset.i]=b.dataset.v;try{{localStorage.setItem(K,JSON.stringify(st))}}catch(e){{}}paint()}}));
document.getElementById('copy').addEventListener('click',()=>{{const out=Object.entries(st).map(([i,v])=>i+':'+v).join(',');navigator.clipboard.writeText('anees-check-01 '+out).then(()=>{{document.getElementById('copy').textContent='Copied'}})}});
paint();
</script>'''
io.open(r"C:\Users\Mahdi\AppData\Local\Temp\claude\C--Claude\b4922477-31d0-4ffd-b5c6-f94db85d4f0c\scratchpad\anees-check-01.html",'w',encoding='utf-8').write(page)
print('page ok, rows',len(rows),'size KB',len(page)//1024)
