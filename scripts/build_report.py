"""M2 - after-lesson report: data/lessons/<date>/understanding.json -> Supabase (lessons, word_events, lesson_events, word_stats)
-> docs/lessons/<date>-report.html -> rich email to Medi (chart + log, house rule). Publish (git push) only after tests.

  python scripts/build_report.py 2026-09-04 [--no-db] [--no-email]
Numbers on the page are counts of lesson_events rows; unknown = '–' with a one-line reason (speaker-label floor)."""
import argparse, datetime, html, io, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / 'data' / 'lessons'
DOCS = ROOT / 'docs'
PAGES = 'https://thenatanzi.github.io/anees/'
DASH = '–'
MOMENTS = 20


def load_words():
    return {w['key']: w for w in json.load(io.open(ROOT / 'data' / 'vocab' / 'words.json', encoding='utf-8'))['items']}


def mmss(t):
    return f'{int(t // 60):02d}:{int(t % 60):02d}'


def classify(u, earlier_keys):
    """understanding -> lesson_events rows (kinds: missed, nailed, new, reused, typed, moment)."""
    ok = u['label_confidence']['per_speaker_ok']
    date = u['date']
    rows = []
    evs = u['events']
    if ok:
        for e in evs:
            if e['speaker'] != 'Medi':
                continue
            kind = 'missed' if (e['correction'] or e.get('asked')) else ('nailed' if not e['prompted'] else None)
            if kind:
                rows.append({'lesson_date': date, 'kind': kind, 'word_key': e['word_key'], 't_start': e['t_start'], 't_end': e['t_end'], 'speaker': 'Medi',
                             'text': e['text'], 'clip': e['clip'], 'confidence': 1.0, 'detail': {'offset': e['offset'], 'cue': e.get('cue', ''), 'prompted': e['prompted']}})
    seen_now = {}
    for e in evs:
        seen_now.setdefault(e['word_key'], e)
    for k, e in seen_now.items():
        kind = 'reused' if k in earlier_keys else 'new'
        rows.append({'lesson_date': date, 'kind': kind, 'word_key': k, 't_start': e['t_start'], 't_end': e['t_end'], 'speaker': e['speaker'],
                     'text': e['text'], 'clip': e['clip'], 'confidence': 1.0, 'detail': {'offset': e['offset'], 'times': sum(1 for x in evs if x['word_key'] == k)}})
    for r in u.get('chat', []):
        clip = None; off = None
        if r['found']:
            near = min(evs, key=lambda e: abs(e['t_start'] - r['at'])) if evs else None
            if near and abs(near['t_start'] - r['at']) < 15:
                clip, off = near['clip'], max(0.0, round(r['at'] - near['clip_start'], 2))
        rows.append({'lesson_date': date, 'kind': 'typed', 'word_key': None, 't_start': r['at'], 't_end': None, 'speaker': 'Amal',
                     'text': r['typed'], 'clip': clip, 'confidence': (1.0 if r.get('found_form') else (0.6 if r['found'] else 0.0)),
                     'detail': {'chat_time': r['chat_time'], 'found': r['found'], 'found_form': r.get('found_form'), 'token': r['token'], 'delta': r['delta'], 'offset': off}})
    # moments: corrections first, then prompted, then typed forms that were found, then nailed words (distinct), all with audio
    ranked = []
    if ok:
        ranked += [(0 if e.get('cue') == 'recast' else 1, e) for e in evs if e['speaker'] == 'Medi' and (e['correction'] or e.get('asked'))]
        ranked += [(2, e) for e in evs if e['speaker'] == 'Medi' and e['prompted'] and not (e['correction'] or e.get('asked'))]
    seen_k = set()
    for _, e in sorted(ranked, key=lambda x: (x[0], x[1]['t_start'])):
        if e['word_key'] in seen_k:
            continue
        seen_k.add(e['word_key'])
    moments = []
    used = set()
    for pri, e in sorted(ranked, key=lambda x: (x[0], x[1]['t_start'])):
        if e['word_key'] in used:
            continue
        used.add(e['word_key']); moments.append((pri, e['t_start'], e['t_end'], 'Medi', e['text'], e['word_key'], e['clip'], e['offset'],
                                                ('you asked for it' if e.get('asked') else ('Amal repeated it right after (recast)' if e.get('cue') == 'recast' else 'Amal said no / say… right after')) if (e['correction'] or e.get('asked')) else 'said after Amal'))
    if ok:
        for e in evs:
            if e['speaker'] == 'Medi' and not e['prompted'] and not e['correction'] and not e.get('asked') and e['word_key'] not in used and len(moments) < MOMENTS * 2:
                used.add(e['word_key']); moments.append((3, e['t_start'], e['t_end'], 'Medi', e['text'], e['word_key'], e['clip'], e['offset'], 'said cold'))
    else:
        for e in evs:
            if e['word_key'] not in used and len(moments) < MOMENTS * 2:
                used.add(e['word_key']); moments.append((3, e['t_start'], e['t_end'], '?', e['text'], e['word_key'], e['clip'], e['offset'], 'Doc word heard (speaker unknown)'))
    for i, m in enumerate(sorted(moments, key=lambda m: (m[0], m[1]))[:MOMENTS]):
        pri, ts, te, spk, text, key, clip, off, why = m
        rows.append({'lesson_date': date, 'kind': 'moment', 'word_key': key, 't_start': ts, 't_end': te, 'speaker': spk, 'text': text, 'clip': clip,
                     'confidence': 1.0, 'detail': {'offset': off, 'why': why, 'rank': i + 1}})
    return rows


def sync_db(u, rows):
    import db, buckets
    date = u['date']
    conf = u['label_confidence']
    db.upsert('lessons', [{'date': date, 'source': u['source'], 'minutes': u['minutes'], 'words': u['words'], 'arabic_share': None,
                           'speaker_split': conf['split'], 'split_ok': conf['per_speaker_ok'], 'unlabeled_share': conf['unlabeled_share'],
                           'topics': u['topics'][:6], 'summary': u['counts'], 'report_url': f'{PAGES}lessons/{date}-report.html',
                           'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}], on='date')
    db.rest('DELETE', 'word_events', params={'lesson_date': f'eq.{date}'}, prefer='return=minimal')
    wrows = [{'lesson_date': date, 'word_key': e['word_key'], 't_start': e['t_start'], 't_end': e['t_end'], 'speaker': e['speaker'], 'prompted': e['prompted'],
              'correction': e['correction'], 'uptake': e['uptake'], 'asked': e.get('asked'), 'confidence': (1.0 if conf['per_speaker_ok'] else 0.0), 'clip': e['clip'], 'text': e['text']} for e in u['events']]
    db.upsert('word_events', wrows)
    db.rest('DELETE', 'lesson_events', params={'lesson_date': f'eq.{date}'}, prefer='return=minimal')
    db.upsert('lesson_events', rows)
    buckets.recompute_and_store()
    return {'word_events': len(wrows), 'lesson_events': len(rows)}


def earlier_keys_from_db(date):
    import db
    rows = db.select('word_events', {'select': 'word_key', 'lesson_date': f'lt.{date}'})
    return {r['word_key'] for r in rows}


def earlier_keys_local(date):
    keys = set()
    for p in sorted(LESSONS.glob('*/understanding.json')):
        d = p.parent.name
        if d < date:
            keys |= {e['word_key'] for e in json.load(io.open(p, encoding='utf-8'))['events']}
    return keys


def chart_bins(u, words_labeled):
    """Arabic words per 10-minute bin, Medi vs Amal (or everyone when the speaker floor failed)."""
    from arabizi import ARABIC
    lo, hi = u['lesson_start'], u['lesson_end']
    ok = u['label_confidence']['per_speaker_ok']
    n = int((hi - lo) // 600) + 1
    bins = [{'label': f'{int((lo + i * 600) // 60)}m', 'medi': 0, 'amal': 0, 'all': 0} for i in range(n)]
    for w in words_labeled:
        if not (lo <= w['s'] <= hi) or not ARABIC.search(w['w']):
            continue
        b = bins[min(n - 1, int((w['s'] - lo) // 600))]
        b['all'] += 1
        if ok and w['spk'] in ('Medi', 'Amal'):
            b[w['spk'].lower()] += 1
    return bins, ok


def svg_chart(bins, ok):
    W, H, pad = 640, 220, 36
    mx = max([max(b['medi'], b['amal']) if ok else b['all'] for b in bins] + [1])
    bw = (W - 2 * pad) / max(1, len(bins))
    parts = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Arabic words per 10 minutes">']
    for i, b in enumerate(bins):
        x = pad + i * bw
        if ok:
            h1 = (H - 2 * pad) * b['medi'] / mx; h2 = (H - 2 * pad) * b['amal'] / mx
            parts.append(f'<rect class="medi" x="{x + 4:.1f}" y="{H - pad - h1:.1f}" width="{bw / 2 - 5:.1f}" height="{h1:.1f}" rx="3"><title>Medi {b["medi"]} Arabic words</title></rect>')
            parts.append(f'<rect class="amal" x="{x + bw / 2:.1f}" y="{H - pad - h2:.1f}" width="{bw / 2 - 5:.1f}" height="{h2:.1f}" rx="3"><title>Amal {b["amal"]} Arabic words</title></rect>')
        else:
            h = (H - 2 * pad) * b['all'] / mx
            parts.append(f'<rect class="all" x="{x + 4:.1f}" y="{H - pad - h:.1f}" width="{bw - 8:.1f}" height="{h:.1f}" rx="3"><title>{b["all"]} Arabic words (both voices)</title></rect>')
        parts.append(f'<text x="{x + bw / 2:.1f}" y="{H - pad + 16}" text-anchor="middle" class="tick">{b["label"]}</text>')
    parts.append(f'<text x="{pad}" y="{pad - 12}" class="tick">{mx} max</text>')
    if ok:
        parts.append(f'<rect class="medi" x="{W - 200}" y="{pad - 24}" width="12" height="12" rx="2"/><text x="{W - 184}" y="{pad - 13}" class="tick">Medi</text>'
                     f'<rect class="amal" x="{W - 120}" y="{pad - 24}" width="12" height="12" rx="2"/><text x="{W - 104}" y="{pad - 13}" class="tick">Amal</text>')
    parts.append('</svg>')
    return ''.join(parts)


def render(u, rows, words, bins, ok):
    date = u['date']; conf = u['label_confidence']
    by_kind = {}
    for r in rows:
        by_kind.setdefault(r['kind'], []).append(r)
    W = words

    def wcell(k):
        w = W.get(k)
        if not w:
            return html.escape(k)
        return f'<b>{html.escape(w["arabizi"])}</b> <span class="ar" dir="rtl">{html.escape(w["arabic"])}</span> <span class="en">{html.escape(w["english"][:60])}</span>'

    def play(clip, off, t):
        if not clip:
            return f'<span class="t">{mmss(t) if t is not None else DASH}</span>'
        return f'<button class="play" data-clip="{date}/clips/{html.escape(clip)}" data-off="{off}" aria-label="play at {mmss(t)}">▶ {mmss(t)}</button>'

    def li(r):
        d = r.get('detail') or {}
        return f'<li>{play(r["clip"], d.get("offset", 0), r["t_start"])} {wcell(r["word_key"]) if r["word_key"] else html.escape(r["text"])}' + \
               (f' <span class="why">{html.escape(d["why"])}</span>' if d.get('why') else '') + \
               (f' <span class="why">Amal typed at {d["chat_time"]}{"" if d.get("found") else " · not heard in the transcript"}</span>' if r['kind'] == 'typed' else '') + '</li>'

    def section(title, kind, lead):
        items = by_kind.get(kind, [])
        if kind in ('missed', 'nailed') and not ok:
            return f'<section id="{kind}"><h2>{title} <span class="n">{DASH}</span></h2><p class="lead">{html.escape(conf["reason"])}. Per-speaker facts are not published for this lesson.</p></section>'
        distinct = {}
        for r in items:
            distinct.setdefault(r['word_key'] or r['text'], r)
        body = ''.join(li(r) for r in distinct.values()) or '<li class="none">none</li>'
        n = f'{len(items)}' + (f' <small>({len(distinct)} words)</small>' if kind in ('missed', 'nailed') and len(distinct) != len(items) else '')
        return f'<section id="{kind}"><h2>{title} <span class="n">{n}</span></h2><p class="lead">{lead}</p><ul class="list">{body}</ul></section>'

    stats = [('what you missed', len(by_kind.get('missed', [])) if ok else DASH), ('what you nailed', len(by_kind.get('nailed', [])) if ok else DASH),
             ('new words', len(by_kind.get('new', []))), ('reused old words', len(by_kind.get('reused', []))), ('Amal typed', len(by_kind.get('typed', [])))]
    stat_html = ''.join(f'<div class="stat"><div class="num">{v}</div><div class="lab">{k}</div></div>' for k, v in stats)
    warn = '' if conf['split'] == 'ok' else f'<p class="warn">{html.escape(conf["reason"])}.</p>'
    topics = ''.join(f'<li><b>{html.escape(t["topic"])}</b> <small>{", ".join(html.escape(x) for x in t["top_words"][:4])}</small></li>' for t in u['topics'][:3] if not t.get('glue'))
    moments = by_kind.get('moment', [])
    mom_html = ''.join(li(r) for r in sorted(moments, key=lambda r: (r['detail'] or {}).get('rank', 99)))
    data = {'date': date, 'counts': {k: len(v) for k, v in by_kind.items()}, 'per_speaker_ok': ok, 'reason': conf['reason'], 'stats': dict(stats)}
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anees report {date}</title>
<style>
:root{{--bg:#F4F6F2;--bg2:#fff;--ink:#1B2620;--mute:#5B6A62;--line:#D6DDD8;--teal:#0F6E56;--amber:#B26F0E;--red:#B23A2E}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0F1613;--bg2:#17211C;--ink:#E7EDE9;--mute:#9BAAA2;--line:#2A3630;--teal:#4FC4A2;--amber:#E7A93B;--red:#E77A6E}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 "Atkinson Hyperlegible",system-ui,sans-serif;overflow-wrap:anywhere}}
main{{max-width:760px;margin:0 auto;padding:14px}} h1{{font-size:24px;margin:8px 0 2px}} h2{{font-size:20px;margin:26px 0 4px}} .n{{color:var(--teal)}}
.lead{{color:var(--mute);margin:0 0 10px;font-size:14px}} .warn{{background:var(--bg2);border-left:4px solid var(--amber);padding:8px 12px;margin:10px 0}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin:12px 0}}
.stat{{background:var(--bg2);border:1px solid var(--line);border-radius:12px;padding:10px}} .num{{font-size:26px;font-weight:700}} .lab{{font-size:12px;color:var(--mute)}}
.chart{{width:100%;height:auto;background:var(--bg2);border:1px solid var(--line);border-radius:12px}} .chart .medi{{fill:var(--teal)}} .chart .amal{{fill:var(--mute)}} .chart .all{{fill:var(--amber)}} .chart .tick{{fill:var(--mute);font-size:12px}}
.list{{list-style:none;padding:0;margin:0}} .list li{{padding:8px 0;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}}
.play{{background:var(--teal);color:#fff;border:0;border-radius:999px;padding:8px 12px;font:600 14px system-ui;min-height:40px;cursor:pointer}} .play.on{{background:var(--amber)}}
.ar{{font-size:19px}} .en{{color:var(--mute);font-size:14px}} .why{{color:var(--amber);font-size:13px}} .t{{color:var(--mute);font-size:13px}} .none{{color:var(--mute)}}
.topics{{padding-left:18px}} .topics small{{color:var(--mute)}} nav a{{color:var(--teal)}} footer{{color:var(--mute);font-size:13px;margin:30px 0 10px}}
</style></head><body><main>
<nav><a href="../index.html">Anees</a> · <a href="{date}.html">full transcript</a></nav>
<h1>Lesson report, {date}</h1>
<p class="lead">{u['minutes']} minutes · {u['words']} words · ElevenLabs Scribe v2. Every number below is a count of stored lesson events; unknown = {DASH}.</p>
{warn}
<div class="stats">{stat_html}</div>
<h2>Arabic words per 10 minutes</h2>
{svg_chart(bins, ok)}
<h2>Topics</h2><ol class="topics">{topics}</ol>
{section('What you missed', 'missed', 'Possible misses: Amal repeated the word or said la / no / "say…" within 5 seconds after you. Tap ▶ to check; Amal confirms or rejects these on her after-lesson link.')}
{section('What you nailed', 'nailed', 'You said it before Amal did, and she did not correct it.')}
{section('New words', 'new', 'First time this word appears in any recorded lesson.')}
{section('Reused old words', 'reused', 'Heard in an earlier lesson and again today.')}
{section("Amal's typed words", 'typed', 'What she wrote in the Meet chat, in her spelling, with the moment it was said.')}
<section id="moments"><h2>20 moments <span class="n">{len(moments)}</span></h2><p class="lead">Corrections first, then words you needed a prompt for, then words you said cold. Each plays from the lesson audio.</p><ul class="list">{mom_html}</ul></section>
<audio id="player" preload="none"></audio>
<footer>Built {u['built'][:16]} from the recording. Speaker labels: {html.escape(conf['split'])}.</footer>
</main>
<script id="data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
<script>
const a=document.getElementById('player');let cur=null;
document.querySelectorAll('.play').forEach(b=>b.addEventListener('click',()=>{{
  const src=b.dataset.clip,off=parseFloat(b.dataset.off||'0');
  if(cur&&cur!==b)cur.classList.remove('on');
  if(cur===b&&!a.paused){{a.pause();b.classList.remove('on');cur=null;return}}
  if(!a.src.endsWith(src)){{a.src=src;}}
  a.currentTime=off;a.play();b.classList.add('on');cur=b;
}}));
a.addEventListener('ended',()=>{{if(cur)cur.classList.remove('on');cur=null}});
</script></body></html>'''


def email_payload(u, rows, bins, ok, link):
    by_kind = {}
    for r in rows:
        by_kind.setdefault(r['kind'], []).append(r)
    W = load_words()
    conf = u['label_confidence']
    def name(k):
        w = W.get(k); return f"{w['arabizi']} ({w['english'][:30]})" if w else k
    rows_out = [{'tag': 'Missed', 'name': (f"{len(by_kind.get('missed', []))} possible misses (Amal reacted right after)" if ok else f'{DASH} not measurable'),
                 'detail': (', '.join(dict.fromkeys(name(r['word_key']) for r in by_kind.get('missed', [])[:6])) if ok else conf['reason'])},
                {'tag': 'Nailed', 'name': (f"{len(by_kind.get('nailed', []))} said cold" if ok else f'{DASH} not measurable'),
                 'detail': (', '.join(dict.fromkeys(name(r['word_key']) for r in by_kind.get('nailed', [])[:6])) if ok else 'per-speaker facts are blank for this lesson')},
                {'tag': 'New', 'name': f"{len(by_kind.get('new', []))} new words", 'detail': ', '.join(name(r['word_key']) for r in by_kind.get('new', [])[:6])},
                {'tag': 'Reused', 'name': f"{len(by_kind.get('reused', []))} reused words", 'detail': ', '.join(name(r['word_key']) for r in by_kind.get('reused', [])[:6])},
                {'tag': 'Typed', 'name': f"{len(by_kind.get('typed', []))} words Amal typed", 'detail': ', '.join(r['text'] for r in by_kind.get('typed', [])[:8])}]
    chart = {'title': 'Arabic words per 10 minutes' + ('' if ok else ' (both voices; speaker labels not trustworthy)'),
             'bars': [{'label': b['label'], 'value': (b['medi'] if ok else b['all']), 'value2': (b['amal'] if ok else None)} for b in bins],
             'legend': 'teal = Medi, grey = Amal' if ok else 'amber = everyone'}
    log = [{'t': mmss(r['t_start']) if r['t_start'] is not None else DASH, 'text': f"{(r['detail'] or {}).get('why', '')}: {name(r['word_key']) if r['word_key'] else r['text']}"}
           for r in sorted(by_kind.get('moment', []), key=lambda r: (r['detail'] or {}).get('rank', 99))]
    return {'headline': f'Lesson report {u["date"]}', 'sub': f"{u['minutes']} min · {u['words']} words · top topic: {u['topics'][0]['topic'] if u['topics'] else DASH}",
            'link': link, 'button': 'Open the report', 'rows': rows_out, 'chart': chart, 'log': log,
            'footer': 'Anees. Only Medi receives this email. Numbers are counts of stored lesson events; unknown = ' + DASH + '.',
            'text': f'Lesson report {u["date"]}: {link}'}


def build(date, use_db=True, send=False, u=None):
    d = LESSONS / date
    u = u or json.load(io.open(d / 'understanding.json', encoding='utf-8'))
    words_labeled = json.load(io.open(d / 'words_labeled.json', encoding='utf-8')) if (d / 'words_labeled.json').exists() else []
    earlier = earlier_keys_from_db(date) if use_db else earlier_keys_local(date)
    rows = classify(u, earlier)
    bins, ok = chart_bins(u, words_labeled)
    W = load_words()
    page = render(u, rows, W, bins, ok)
    out = DOCS / 'lessons' / f'{date}-report.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding='utf-8')
    io.open(d / 'report_rows.json', 'w', encoding='utf-8').write(json.dumps(rows, ensure_ascii=False))
    res = {'page': str(out), 'rows': len(rows), 'kinds': {k: sum(1 for r in rows if r['kind'] == k) for k in ('missed', 'nailed', 'new', 'reused', 'typed', 'moment')}, 'per_speaker_ok': ok}
    if use_db:
        res['db'] = sync_db(u, rows)
    link = f'{PAGES}lessons/{date}-report.html'
    payload = email_payload(u, rows, bins, ok, link)
    io.open(d / 'report_email.json', 'w', encoding='utf-8').write(json.dumps(payload, ensure_ascii=False))
    if send:
        subprocess.run(['node', str(ROOT / 'scripts' / 'send_lesson_email.mjs'), f'Anees: lesson report {date}', str(d / 'report_email.json')], check=True)
        res['emailed'] = True
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--no-db', action='store_true'); ap.add_argument('--email', action='store_true')
    a = ap.parse_args()
    print(json.dumps(build(a.date, use_db=not a.no_db, send=a.email), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
