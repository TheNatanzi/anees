# -*- coding: utf-8 -*-
"""Rule PR-08 (report M10; Medi 2026-09-27 "you didnt do all the tasks I just asked you", 2026-10-01 "please dont cut any
stepts"): every ask in a session - including messages typed while the agent was working - is ticked before "done".

The asks come from the session transcript itself, never from the agent's memory of them: Claude Code stores what Medi
types as `user` lines (origin human) and what he types mid-run as separate `queued_command` attachments - the second kind
is the one that gets dropped (an audit of 27 sessions on 2026-10-02 found ~120 of them). The agent ticks each message
with what it did (or why it is not done); `check` exits 1 while any of Medi's messages is unticked.

    python scripts/session_asks.py list  --session 65d34512            # every message Medi typed, #n, ticked or open
    python scripts/session_asks.py tick  --session 65d34512 3 5-7 --note "done: commit 8d730a0"
    python scripts/session_asks.py tick  --session 65d34512 4 --not-done "needs Medi: which leech threshold"
    python scripts/session_asks.py check --session 65d34512            # exit 0 only when every message is ticked

The checklist is local (data/session-asks/, gitignored): Medi's sessions mix other projects, and this repo is public.
Claude Code transcripts only (~/.claude/projects/*/<session>.jsonl); a Codex session is ticked by hand in AGENTS.md terms.
"""
from __future__ import annotations

import argparse, datetime, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTS = 'data/session-asks'
PROJECTS = Path(os.environ.get('CLAUDE_PROJECTS_DIR') or Path.home() / '.claude' / 'projects')


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get('type') == 'text':
                parts.append(b.get('text') or '')
            elif isinstance(b, dict) and b.get('type') == 'image' or (isinstance(b, dict) and 'source' in b):
                parts.append('[image]')
        return ' '.join(p for p in parts if p)
    return str(content or '')


def _human(origin):
    return isinstance(origin, dict) and origin.get('kind') == 'human'


def asks(lines):
    """Every message Medi typed, in order: [{'id', 't', 'text', 'mid_run'}]. `lines` = the transcript's JSONL lines.
    Kept: `user` lines from a human (not tool results, not meta/injected lines, not task notifications) and
    `queued_command` attachments from a human (typed while the agent worked)."""
    out, seen = [], set()
    for line in lines:
        try:
            j = json.loads(line)
        except Exception:
            continue
        if j.get('isSidechain'):
            continue
        if j.get('type') == 'user' and not j.get('isMeta'):
            msg = j.get('message') or {}
            c = msg.get('content')
            if isinstance(c, list) and any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in c):
                continue
            if 'origin' in j and not _human(j.get('origin')):
                continue
            text = _text(c).strip()
            if not text or text.startswith(('<task-notification>', '<command-', '<local-command', 'Another Claude session sent')):
                continue
            mid = False
        elif j.get('type') == 'attachment' and (j.get('attachment') or {}).get('type') == 'queued_command':
            a = j['attachment']
            if not _human(a.get('origin')):
                continue
            text, mid = _text(a.get('prompt')).strip(), True
            if not text:
                continue
        else:
            continue
        key = j.get('uuid') if not mid else (j['attachment'].get('source_uuid') or j.get('uuid'))
        if key in seen:
            continue
        seen.add(key)
        out.append({'id': key, 't': str(j.get('timestamp') or '')[:19], 'text': text, 'mid_run': mid})
    return out


def find_transcript(session, projects=None):
    projects = Path(projects or PROJECTS)
    hits = sorted(projects.glob(f'*/{session}*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not hits:
        raise SystemExit(f'no Claude Code transcript for session {session!r} under {projects}')
    return hits[0]


def load_list(path):
    try:
        d = json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        d = None
    return d if isinstance(d, dict) else {'ticks': {}}


def save_list(path, doc):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')


def numbers(specs, n):
    out = []
    for s in specs:
        m = re.fullmatch(r'(\d+)(?:-(\d+))?', s)
        if not m:
            raise SystemExit(f'not a message number or range: {s!r}')
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if not (1 <= a <= b <= n):
            raise SystemExit(f'{s}: messages run 1..{n}')
        out += range(a, b + 1)
    return out


def tick(doc, items, nums, note, done=True):
    if not (note or '').strip():
        raise SystemExit('a tick says what was done (--note) or why not (--not-done)')
    for i in nums:
        it = items[i - 1]
        doc.setdefault('ticks', {})[it['id']] = {'n': i, 'done': done, 'note': note.strip(),
                                                 'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    return doc


def open_asks(items, doc):
    ticks = (doc or {}).get('ticks') or {}
    return [(i, it) for i, it in enumerate(items, 1) if it['id'] not in ticks]


def short(text, n=90):
    t = ' '.join(str(text).split())
    return t if len(t) <= n else t[:n - 3] + '...'


def check(items, doc):
    """(ok, lines): ok only when every message Medi typed is ticked; not-done ticks are listed so the report names them."""
    ticks = (doc or {}).get('ticks') or {}
    lines = [f"OPEN #{i} {it['t'][11:16]}{' (typed mid-run)' if it['mid_run'] else ''}: {short(it['text'])}"
             for i, it in open_asks(items, doc)]
    lines += [f"NOT DONE #{i}: {short(it['text'], 60)} -> {ticks[it['id']]['note']}"
              for i, it in enumerate(items, 1) if it['id'] in ticks and not ticks[it['id']].get('done')]
    ok = not open_asks(items, doc)
    return ok, lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['list', 'tick', 'check'])
    ap.add_argument('nums', nargs='*')
    ap.add_argument('--session'); ap.add_argument('--transcript')
    ap.add_argument('--note'); ap.add_argument('--not-done')
    ap.add_argument('--list-file')
    a = ap.parse_args(argv)
    if not (a.session or a.transcript):
        ap.error('--session <id prefix> or --transcript <path>')
    tr = Path(a.transcript) if a.transcript else find_transcript(a.session)
    items = asks(tr.read_text(encoding='utf-8', errors='replace').splitlines())
    lf = Path(a.list_file) if a.list_file else ROOT / LISTS / f'{(a.session or tr.stem)[:8]}.json'
    doc = load_list(lf)
    if a.cmd == 'tick':
        done = a.not_done is None
        tick(doc, items, numbers(a.nums, len(items)), a.note if done else a.not_done, done=done)
        save_list(lf, doc)
    if a.cmd in ('list', 'tick'):
        ticks = doc.get('ticks') or {}
        for i, it in enumerate(items, 1):
            tk = ticks.get(it['id'])
            mark = '[x]' if tk and tk.get('done') else '[-]' if tk else '[ ]'
            print(f"{mark} #{i} {it['t'][5:16]}{' mid-run' if it['mid_run'] else ''}: {short(it['text'])}"
                  + (f"  -> {tk['note']}" if tk else ''))
        return 0
    ok, lines = check(items, doc)
    for l in lines:
        print(l)
    print(f'session asks: {"OK - all " + str(len(items)) + " ticked" if ok else str(len(open_asks(items, doc))) + " of " + str(len(items)) + " not ticked"}')
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    sys.exit(main())
