"""Public lesson transcript page: one playable lesson recording, every line seeks the audio, Amal's typed chat lines merged.

  python scripts/build_lesson_page.py 2026-09-21 --lesson-dir <dir with speaking-evidence.json> [--chat <Meet chat file>] [--chat-offset 12.3]
  python scripts/build_lesson_page.py --restyle-all     PG-47: every published lesson page gets the chat colours

Pure helpers (chat parsing, row merge, HTML) are tested in tests/test_build_lesson_page.py. The audio is a low-bitrate mono mix
of the saved participant tracks placed on the lesson timeline (ffmpeg adelay), so timestamps on the page equal the audio clock.
Nothing is sent anywhere; the page is written under docs/lessons/.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs' / 'lessons'
CHAT_TIME = re.compile(r'^(\d\d):(\d\d):(\d\d)(?:\.\d+)?(?:,|$)')
CHAT_LINE = re.compile(r'^([A-Za-z][\w .\'-]{0,40}):\s?(.*)$')
LEARNER = ('medi', 'mahdi', 'natanzi')


def parse_chat(text):
    """Google Meet '<code> - Chat Transcript': 'hh:mm:ss.mmm,hh:mm:ss.mmm' then 'Name: text' (+ continuation lines).
    Returns [{'t': seconds on the Meet recording clock, 'who': 'Amal'|'Medi'|<name>, 'text': str}]."""
    out, t, who = [], None, None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = CHAT_TIME.match(line)
        if m:
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)); who = None
            continue
        if not line.strip() or t is None:
            continue
        m = CHAT_LINE.match(line)
        if m and who is None:
            name = m.group(1).strip()
            low = name.lower()
            who = 'Amal' if 'amal' in low else ('Medi' if any(n in low for n in LEARNER) else name)
            out.append({'t': t, 'who': who, 'text': m.group(2).strip()})
        elif who:
            out.append({'t': t, 'who': who, 'text': line.strip()})
    return [c for c in out if c['text']]


def merge(rows, chat, offset=0.0):
    """Interleave transcript rows and chat lines by time. offset = lesson-timeline seconds at Meet chat 00:00:00."""
    items = [{'kind': 'speech', 't': r['timeline_start'], 'who': r['speaker_label'], 'id': r.get('id'),
              'text': ' '.join(i['text'] for i in r['items'] if i.get('type') != 'spacing') or r.get('text', '')}
             for r in rows if r.get('timeline_start') is not None]
    items += [{'kind': 'chat', 't': max(0.0, c['t'] + offset), 'who': c['who'], 'text': c['text']} for c in chat]
    items.sort(key=lambda x: (x['t'], x['kind'] == 'chat'))
    return [x for x in items if x['text'].strip()]


def clock(seconds):
    """mm:ss with unbounded minutes ('62:05'): docs/js/transcript-context-review.js parses exactly this."""
    s = int(seconds)
    return f'{s // 60:02d}:{s % 60:02d}'


# PG-47 (Medi 2026-10-10 "lets put that back in with a different color"): a Google Meet chat line is typed, not spoken -
# its own colour, the Sabz teal pair (sabz-tokens.css --sabz-state-rinad-drifting-text / -fill; these pages carry their own
# small stylesheet, so the hexes are copied): not a speaker colour, not a chip colour (PG-39).
CHAT_LIGHT = ('p.chat{background:#D3EEF2;border-left:4px dashed #0B5966}p.chat b{color:#0B5966}'
              'p.chat b::after{content:" · chat (typed)";font-weight:400;color:#0B5966;font-size:14px}')
CHAT_DARK = 'p.chat{background:#0F3D46;border-left-color:#7EDCEA}p.chat b,p.chat b::after{color:#7EDCEA}'
# the chat style every lesson page carried before PG-47 -> restyle() swaps it in place (display only, S2)
OLD_CHAT = (('p.chat{background:#eef6f2}p.chat b::after{content:" · typed in chat";font-weight:400;color:#60746e;font-size:14px}', CHAT_LIGHT),
            ('p.chat{background:#16261f}', CHAT_DARK))

STYLE = ('body{font:18px/1.65 system-ui;background:#f4f6f2;color:#18312e;margin:0}main{max-width:850px;margin:auto;padding:0 16px 48px}'
         'p{padding:10px 12px;margin:0;border-bottom:1px solid #dbe4df;overflow-wrap:anywhere}small{color:#60746e}a{color:#146c54}'
         '.note{background:#fff5df;padding:14px 16px;margin:12px 0}.bar{position:sticky;top:0;background:#f4f6f2;padding:10px 0;z-index:2;border-bottom:1px solid #dbe4df}'
         '.bar audio{width:100%}button.t{font:inherit;font-size:14px;color:#146c54;background:none;border:1px solid #bcd3ca;border-radius:6px;padding:0 6px;margin-right:6px;cursor:pointer}'
         + CHAT_LIGHT + 'p.on{background:#dff0e8}'
         '@media (prefers-color-scheme:dark){body,.bar{background:#101a18;color:#e3ece8}p{border-color:#24332f}.note{background:#3a3120}' + CHAT_DARK + 'p.on{background:#1d3a2f}a,button.t{color:#7fd3b3}small{color:#9fb3ac}}')

SCRIPT = ('<script>(function(){var a=document.getElementById("lesson-audio");if(!a)return;var on=null;'
          'document.addEventListener("click",function(e){var b=e.target.closest("button.t");if(!b)return;'
          'if(on)on.classList.remove("on");on=b.parentNode;on.classList.add("on");'
          'a.currentTime=Math.max(0,parseFloat(b.dataset.t)-1);var p=a.play();if(p&&p.catch)p.catch(function(){});});})();</script>')


# Word Bank review overlay (wrong-part marks, corrected lines, excerpt buttons) -- same tags as every lesson page before.
REVIEW = ('<script src="../js/word-bank-review.js?v=context-1"></script>'
          '<script src="../js/transcript-context-review.js?v=context-1"></script>'
          # Arabizi everywhere (Medi 2026-09-25, decision b): her spelling on top, the recorded Arabic small underneath.
          '<script src="../js/word-bank-arabizi.js?v=az2"></script>'
          '<script src="../js/transcript-arabizi.js?v=az2" data-arabizi-selector="p.turn .words, p.chat .words"></script>')


def render(date, merged, *, minutes, words, note, audio=None):
    lines = []
    for x in merged:
        # class "turn" + data-row + span.words = the hooks docs/js/transcript-context-review.js uses to mark wrong parts
        # and add the conversation-excerpt button for a Word Bank event on this row.
        cls = ' class="chat"' if x['kind'] == 'chat' else ' class="turn"'
        row = f' data-row="{html.escape(x["id"])}"' if x.get('id') else ''
        stamp = (f'<button class="t" data-t="{x["t"]:.2f}"{row} aria-label="Play from {clock(x["t"])}"><small>{clock(x["t"])}</small></button>' if audio
                 else f'<small{row}>{clock(x["t"])}</small> ')
        lines.append(f'<p dir="auto"{cls}>{stamp}<b>{html.escape(x["who"])}</b>: <span class="words">{html.escape(x["text"])}</span></p>')
    player = (f'<div class="bar"><audio id="lesson-audio" controls preload="none" src="{html.escape(audio)}"></audio>'
              '<small>Tap a time to hear that line.</small></div>') if audio else ''
    typed = sum(x['kind'] == 'chat' for x in merged)
    return dword('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Anees lesson {date}</title><style>{STYLE}</style><main><p style="border:0;padding:16px 0 0"><a href="../index.html#lessons">← Lessons</a></p>'
            f'<h1>Lesson · {date}</h1>{player}<div class="note">{html.escape(note)}</div>'
            f'<p>{minutes} minutes · {words:,} transcribed words · {typed} lines Amal typed in chat</p>'
            + ''.join(lines) + '</main>' + (SCRIPT if audio else '') + REVIEW + '</html>')


# De-word (plan/OVERNIGHT-DEWORD-2026-10-22.md): only the chrome around the transcript changes; every transcript line stays.
# The 3 counts become big numbers, the note becomes one warning chip with the full text behind a small (i) that opens in
# place, and the page gets the app's theme + look switch (js/theme.js) and css/dw-reports.css. Works on a fresh render and
# on an already published page (python scripts/build_lesson_page.py --dword <date>|--dword-all); running it twice is a no-op.
DW_HEAD = ('<meta name="color-scheme" content="light dark"><script src="../js/theme.js"></script>'
           '<link rel="stylesheet" href="../css/sabz-tokens.css"><link rel="stylesheet" href="../css/dw-reports.css?v=1">')
DW_STATS = re.compile(r'<div class="note">(.*?)</div><p>([\d.]+) minutes · ([\d,]+) transcribed words · (\d+) lines Amal typed in chat</p>', re.S)


MIC = '<svg class="dw-pic dw-scene dw-mic" viewBox="0 0 120 80" aria-hidden="true" focusable="false"><circle cx="100" cy="16" r="10" fill="var(--dw-a4)" opacity=".35"/><rect x="10" y="10" width="44" height="26" rx="13" fill="var(--dw-a1)"/><path d="M22 36l-6 10 14-10z" fill="var(--dw-a1)"/><circle cx="24" cy="23" r="3" fill="var(--dw-card)"/><circle cx="32" cy="23" r="3" fill="var(--dw-card)"/><circle cx="40" cy="23" r="3" fill="var(--dw-card)"/><rect x="66" y="30" width="44" height="24" rx="12" fill="var(--dw-a2)"/><path d="M98 54l6 10-14-10z" fill="var(--dw-a2)"/><path d="M76 42h24" stroke="var(--dw-card)" stroke-width="4" stroke-linecap="round"/><rect x="50" y="44" width="16" height="26" rx="8" fill="var(--dw-a3)"/><path d="M45 60a13 13 0 0 0 26 0" fill="none" stroke="var(--dw-ink)" stroke-width="3" stroke-linecap="round"/><line x1="58" y1="73" x2="58" y2="79" stroke="var(--dw-ink)" stroke-width="3"/></svg>'   # a small drawn scene (two speech bubbles + a mic); quiet in Look A, bright in Look B


def dword(page):
    if 'lsn-page' in page:
        return page
    page = page.replace('<html lang="en">', '<html lang="en" class="lsn-page">', 1)
    page = page.replace('<style>', DW_HEAD + '<style>', 1)
    page = page.replace('<main><p style="border:0;padding:16px 0 0"><a href="../index.html#lessons">← Lessons</a></p>',
                        '<main><div class="lsn-top"><a href="../index.html#lessons">← Lessons</a><div class="lsn-switch" data-theme-slot></div></div>' + MIC, 1)
    page = page.replace('<small>Tap a time to hear that line.</small>', '', 1)

    def stats(m):
        note, mins, words, typed = m.groups()
        return ('<div class="dw-bigs lsn-bigs"><div class="dw-big"><b>%s</b><span>minutes</span></div>'
                '<div class="dw-big"><b>%s</b><span>words heard</span></div><div class="dw-big"><b>%s</b><span>typed in chat</span></div></div>'
                '<div class="lsn-note"><span class="dw-chip warn">Not checked by a person</span> <details class="dw-info">'
                '<summary aria-label="About this transcript">ⓘ</summary><div>%s '
                '(%s minutes · %s transcribed words · %s lines Amal typed in chat)</div></details></div>'
                % (mins, words, typed, note + ('' if 'Tap a time' in note else ' Tap a time to hear that line.'), mins, words, typed))
    page = DW_STATS.sub(stats, page, count=1)
    page = page.replace('<div class="lsn-note">', talk_map(page) + '<div class="lsn-note">', 1)
    return mark_turns(page)


ARABIC = re.compile(r'[؀-ۿ]')
TURN = re.compile(r'<p dir="auto" class="turn">(?:<i class="lk"[^>]*></i>)?(<button class="t" data-t="([\d.]+)"[^>]*>.*?</button>)<b>([^<]+)</b>: <span class="words">(.*?)</span></p>')


def mark_turns(page):
    """Every line stays. A line with Arabic gets a colour band ("ar"); a short line with no Arabic (um, mm-hmm, ok) is drawn
    small and faint ("lite"). A button on top jumps to where the Arabic practice starts: the first line from which most of
    the next 10 lines hold Arabic."""
    rows = TURN.findall(page)
    if not rows:
        return page
    aw = [sum(1 for w in r[3].split() if ARABIC.search(w)) for r in rows]   # Arabic words on the line
    has = [n >= 2 for n in aw]
    rich = [n >= 3 for n in aw]
    start = next((i for i in range(len(rows)) if rich[i] and sum(rich[i:i + 10]) >= 6), None)
    k = {'i': -1}

    def sub(m):
        k['i'] += 1
        i, text = k['i'], m.group(4)
        kind = ' data-k="ar"' if has[i] else (' data-k="lite"' if len(text.split()) <= 4 else '')   # <p class="turn"> stays exact (JS hooks, tests)
        rid = ' id="arabic-start"' if i == start else ''
        mark = '<i class="lk"%s%s></i>' % (kind, rid) if (kind or rid) else ''   # an empty marker: <p class="turn">, <b> and the words stay exact
        return '<p dir="auto" class="turn">%s%s<b>%s</b>: <span class="words">%s</span></p>' % (mark, m.group(1), m.group(3), text)
    page = TURN.sub(sub, page)
    if start is not None and start > 0:
        # the talk before the Arabic practice (set-up, small talk) folds into one row that opens in place: every line is still here
        a = page.find('<p dir="auto"')
        b = page.find('<p dir="auto" class="turn"><i class="lk"', a)
        b = page.find('id="arabic-start"', b)
        b = page.rfind('<p dir="auto"', 0, b)
        if 0 <= a < b:
            n = page.count('<p dir="auto"', a, b)
            fold = ('<details class="lsn-before"><summary>Before the Arabic practice · 00:00–%s · %d lines</summary>%s</details>'
                    '<p class="lsn-start">▶ The Arabic practice starts · %s</p>' % (clock(float(rows[start][1])), n, page[a:b], clock(float(rows[start][1]))))
            page = page[:a] + fold + page[b:]
    return page


def talk_map(page, bins=60):
    """A picture of the lesson: one strip, left = start, right = end; each slice is coloured by who spoke most in it
    (the student, the tutor, or typed chat). Read from the page's own rows, so it matches the transcript below."""
    rows = re.findall(r'<p dir="auto" class="(turn|chat)"><button class="t" data-t="([\d.]+)"[^>]*>.*?</button><b>([^<]+)</b>', page)
    if not rows:
        return ''
    end = max(float(t) for _, t, _ in rows) or 1.0
    tally = [dict() for _ in range(bins)]
    for kind, t, who in rows:
        k = 'chat' if kind == 'chat' else ('you' if who.strip().lower() in LEARNER else 'tutor')
        b = min(bins - 1, int(float(t) / end * bins))
        tally[b][k] = tally[b].get(k, 0) + 1
    w = 100.0 / bins
    rects = ''.join('<rect x="%.2f" y="0" width="%.2f" height="10" class="tm-%s"/>' % (i * w, w + .05, max(c, key=c.get))
                    for i, c in enumerate(tally) if c)
    return ('<figure class="lsn-map"><svg class="dw-pic" viewBox="0 0 100 10" preserveAspectRatio="none" role="img" '
            'aria-label="Who spoke when, start to end">' + rects + '</svg><figcaption><i class="tm-you"></i>you '
            '<i class="tm-tutor"></i>tutor <i class="tm-chat"></i>chat <span>start → end</span></figcaption></figure>')


def dword_dates(dates):
    out = []
    for d in dates:
        f = DOCS / f'{d}.html'
        old = f.read_text(encoding='utf-8')
        new = dword(old)
        if new != old:
            f.write_text(new, encoding='utf-8')
            out.append(d)
    return out


def mix_tracks(tracks, out, bitrate='32k'):
    """tracks = [(path, offset_seconds)]. Writes one mono mp3 on the lesson timeline."""
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
    for path, _ in tracks:
        cmd += ['-i', str(path)]
    parts = ''.join(f'[{i}:a]adelay={int(round(off * 1000))}:all=1[a{i}];' for i, (_, off) in enumerate(tracks))
    inputs = ''.join(f'[a{i}]' for i in range(len(tracks)))
    cmd += ['-filter_complex', f'{parts}{inputs}amix=inputs={len(tracks)}:normalize=0:duration=longest[m]', '-map', '[m]',
            '-ac', '1', '-ar', '22050', '-codec:a', 'libmp3lame', '-b:a', bitrate, str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def restyle(page):
    """A lesson page's HTML with the PG-47 chat colours (an older page's chat style swapped; lines untouched)."""
    for old, new in OLD_CHAT:
        page = page.replace(old, new, 1)
    return page


def restyle_all(docs=None):
    """Every published lesson page gets the PG-47 chat colours. -> dates whose page changed."""
    out = []
    for f in sorted(Path(docs or DOCS).glob('20??-??-??.html')):
        old = f.read_text(encoding='utf-8')
        new = restyle(old)
        if new != old:
            f.write_text(new, encoding='utf-8')
            out.append(f.stem)
    return out


def write_page(date, data, *, chat=(), chat_offset=0.0, note, audio_rel=None, minutes=None):
    merged = merge(data['rows'], chat, chat_offset)
    words = sum(i.get('type') == 'word' for r in data['rows'] for i in r['items'])
    if minutes is None:
        ends = [r['timeline_end'] for r in data['rows'] if r.get('timeline_end') is not None]
        minutes = round(max(ends) / 60, 1) if ends else 0
    page = render(date, merged, minutes=minutes, words=words, note=note, audio=audio_rel)
    target = DOCS / f'{date}.html'
    target.write_text(page, encoding='utf-8')
    return {'page': str(target), 'rows': len(data['rows']), 'chat_lines': sum(x['kind'] == 'chat' for x in merged), 'words': words}


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['--dword']:      # de-word the chrome of published pages: --dword 2026-10-14 [more dates]
        print(json.dumps({'deworded': dword_dates(sys.argv[2:])}))
        raise SystemExit(0)
    if sys.argv[1:] == ['--restyle-all']:
        print(json.dumps({'restyled': restyle_all()}))
        raise SystemExit(0)
    p = argparse.ArgumentParser()
    p.add_argument('date'); p.add_argument('--lesson-dir', required=True); p.add_argument('--chat'); p.add_argument('--chat-offset', type=float, default=0.0)
    p.add_argument('--note', default='Unreviewed speech recognition. Timestamps use the lesson timeline.'); p.add_argument('--audio')
    a = p.parse_args()
    data = json.loads((Path(a.lesson_dir) / 'speaking-evidence.json').read_text(encoding='utf-8'))
    chat = parse_chat(Path(a.chat).read_text(encoding='utf-8', errors='replace')) if a.chat else []
    print(json.dumps(write_page(a.date, data, chat=chat, chat_offset=a.chat_offset, note=a.note, audio_rel=a.audio)))
