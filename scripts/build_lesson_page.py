"""Public lesson transcript page: one playable lesson recording, every line seeks the audio, Amal's typed chat lines merged.

  python scripts/build_lesson_page.py 2026-09-21 --lesson-dir <dir with speaking-evidence.json> [--chat <Meet chat file>] [--chat-offset 12.3]

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


STYLE = ('body{font:18px/1.65 system-ui;background:#f4f6f2;color:#18312e;margin:0}main{max-width:850px;margin:auto;padding:0 16px 48px}'
         'p{padding:10px 12px;margin:0;border-bottom:1px solid #dbe4df;overflow-wrap:anywhere}small{color:#60746e}a{color:#146c54}'
         '.note{background:#fff5df;padding:14px 16px;margin:12px 0}.bar{position:sticky;top:0;background:#f4f6f2;padding:10px 0;z-index:2;border-bottom:1px solid #dbe4df}'
         '.bar audio{width:100%}button.t{font:inherit;font-size:14px;color:#146c54;background:none;border:1px solid #bcd3ca;border-radius:6px;padding:0 6px;margin-right:6px;cursor:pointer}'
         'p.chat{background:#eef6f2}p.chat b::after{content:" · typed in chat";font-weight:400;color:#60746e;font-size:14px}p.on{background:#dff0e8}'
         '@media (prefers-color-scheme:dark){body,.bar{background:#101a18;color:#e3ece8}p{border-color:#24332f}.note{background:#3a3120}p.chat{background:#16261f}p.on{background:#1d3a2f}a,button.t{color:#7fd3b3}small{color:#9fb3ac}}')

SCRIPT = ('<script>(function(){var a=document.getElementById("lesson-audio");if(!a)return;var on=null;'
          'document.addEventListener("click",function(e){var b=e.target.closest("button.t");if(!b)return;'
          'if(on)on.classList.remove("on");on=b.parentNode;on.classList.add("on");'
          'a.currentTime=Math.max(0,parseFloat(b.dataset.t)-1);var p=a.play();if(p&&p.catch)p.catch(function(){});});})();</script>')


# Word Bank review overlay (wrong-part marks, corrected lines, excerpt buttons) -- same tags as every lesson page before.
REVIEW = ('<script src="../js/word-bank-review.js?v=context-1"></script>'
          '<script src="../js/transcript-context-review.js?v=context-1"></script>')


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
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Anees lesson {date}</title><style>{STYLE}</style><main><p style="border:0;padding:16px 0 0"><a href="../index.html#lessons">← Lessons</a></p>'
            f'<h1>Lesson · {date}</h1>{player}<div class="note">{html.escape(note)}</div>'
            f'<p>{minutes} minutes · {words:,} transcribed words · {typed} lines Amal typed in chat</p>'
            + ''.join(lines) + '</main>' + (SCRIPT if audio else '') + REVIEW + '</html>')


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
    p = argparse.ArgumentParser()
    p.add_argument('date'); p.add_argument('--lesson-dir', required=True); p.add_argument('--chat'); p.add_argument('--chat-offset', type=float, default=0.0)
    p.add_argument('--note', default='Unreviewed speech recognition. Timestamps use the lesson timeline.'); p.add_argument('--audio')
    a = p.parse_args()
    data = json.loads((Path(a.lesson_dir) / 'speaking-evidence.json').read_text(encoding='utf-8'))
    chat = parse_chat(Path(a.chat).read_text(encoding='utf-8', errors='replace')) if a.chat else []
    print(json.dumps(write_page(a.date, data, chat=chat, chat_offset=a.chat_offset, note=a.note, audio_rel=a.audio)))
