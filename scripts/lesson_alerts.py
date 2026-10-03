# -*- coding: utf-8 -*-
"""Rule LS-04 (report M9, Medi 2026-10-02: "I thought we load lessons automatically now? Why didn't today's get loaded").

Lesson 2026-10-01 was recorded at 15:15 and the hourly job failed on it every hour for 9 h (ElevenLabs: "quota_exceeded,
133 credits remaining, 530 required"). Only hourly.log on the PC knew; no page said so. This module keeps one small status
file, docs/data/lesson-alerts.json, that the hourly job rewrites every run (only when something changed, so a quiet hour
makes no commit) and commits with the run's built files. Progress and Lessons show each problem as one line through
docs/js/lesson-behind.js (which adds the "since"), e.g. "10-01 lesson not loaded: voice-to-text credits ran out (since 15:15)".

A load failure does not block the run's push (only failed BUILD steps do), so the line reaches the site the same hour.
When publishing itself is blocked, nothing reaches the site; the hourly log and data/publish-guard/state.json say why.
No phone alert is sent: no ntfy topic or other push channel for Medi exists on this PC (checked 2026-10-02).

Pure functions + one GET to ElevenLabs (`elevenlabs_credits`, injectable); the tests never touch the network.
"""
from __future__ import annotations

import datetime, json, os
from pathlib import Path

ALERTS = 'docs/data/lesson-alerts.json'
# measured 2026-10-01: Amal's 42.9-min track needed 530 credits (ElevenLabs' own quota message) -> about 12.4 per minute
CREDITS_PER_MIN = 530 / (2571.5 / 60)
LESSON_MIN = 110        # one lesson = two tracks (10-01: Amal 43 min + Medi 66 min); warn below this much audio
SUBSCRIPTION_URL = 'https://api.elevenlabs.io/v1/user/subscription'


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def plain_cause(err) -> str:
    """The raw error of a failed load, in plain words for Medi (the raw text stays in hourly.log)."""
    s = str(err or '')
    low = s.lower()
    if 'quota_exceeded' in low or 'credits remaining' in low or 'exceeds your quota' in low:
        return 'voice-to-text credits ran out'
    if 'budget' in low and 'cap' in low:
        return 'the spending cap was reached'
    if 'missing elevenlabs_api_key' in low:
        return 'voice-to-text key is missing on the PC'
    if 'elevenlabs' in low:
        return 'voice-to-text failed'
    if 'tracks.json' in low or 'no saved transcript' in low or ('no such file' in low and '.mp3' in low):
        return 'the recording tracks are missing'
    if 'ffprobe' in low or 'ffmpeg' in low:
        return 'the recording could not be read'
    if 'load_lesson' in low or 'supabase' in low or 'database' in low:
        return 'saving it to the database failed'
    return 'loading failed'


def line_for(p):
    """One short line per problem (Medi reads one line, plain words). The page adds "(since 15:15)" from `since`, in the
    viewer's own day, so the file only changes when a problem does."""
    if p.get('kind') == 'not-loaded':
        return f"{str(p.get('date'))[5:]} lesson not loaded: {p.get('cause')}"
    if p.get('kind') == 'missing-audio':           # rule TR-17: a recording the hourly job could not transcribe
        return f"{str(p.get('date'))[5:]} lesson missing {p.get('minutes')} min of audio: {p.get('cause')}"
    if p.get('kind') == 'doc-stale':                # rule AM-20: Amal's Doc export stopped reaching this PC
        if not p.get('since'):
            return f"Amal's word Doc never synced on this PC: {p.get('cause')}"
        return "Amal's word Doc not synced since {since}: " + str(p.get('cause'))   # the page fills {since}
    if p.get('kind') == 'credits-low':
        return f"Voice-to-text credits low: {p.get('left')} left, a lesson needs about {p.get('need')}"
    return str(p.get('cause'))


def credits_problem(left, minutes=LESSON_MIN):
    """None when the credits left cover `minutes` of audio (or are unknown), else a credits-low problem."""
    if left is None:
        return None
    need = int(round(minutes * CREDITS_PER_MIN, -1))
    return None if left >= need else {'key': 'credits', 'kind': 'credits-low', 'left': int(left), 'need': need,
                                      'cause': 'voice-to-text credits low'}


def elevenlabs_credits(get=None, key=None, timeout=20):
    """Credits left on the ElevenLabs plan (character_limit - character_count), or None when unknown (no key, no network)."""
    key = key if key is not None else os.environ.get('ELEVENLABS_API_KEY')
    if not key:
        return None
    try:
        if get is None:
            import requests
            get = requests.get
        r = get(SUBSCRIPTION_URL, headers={'xi-api-key': key}, timeout=timeout)
        if getattr(r, 'status_code', 0) != 200:
            return None
        j = r.json()
        return int(j['character_limit']) - int(j['character_count'])
    except Exception:
        return None


def read(root):
    try:
        return json.loads((Path(root) / ALERTS).read_text(encoding='utf-8'))
    except Exception:
        return {}


def update(root, problems, now=None, keep=()):
    """Write this hour's problems. A problem already open keeps its first `since`; one that is gone is dropped.
    `keep`: key prefixes this run did not look at (e.g. 'credits' when the credit check could not run): kept as they are.
    The file is only rewritten when its content changes (a quiet hour makes no commit). Returns (doc, changed, new_keys)."""
    now = now or now_iso()
    old = read(root)
    before = {p.get('key'): p for p in old.get('problems') or []}
    out = []
    for p in problems:
        prev = before.get(p['key'])
        q = dict(p)
        # a problem that knows its own start (AM-20: the last good Doc export) keeps it
        q['since'] = p['since'] if 'since' in p else (prev.get('since') if prev and prev.get('cause') == p.get('cause') else now)
        out.append(q)
    seen = {p['key'] for p in out}
    out += [p for k, p in before.items() if k not in seen and any(str(k).startswith(x) for x in keep)]
    for q in out:
        q['text'] = line_for(q)
    out.sort(key=lambda p: (p.get('kind') != 'not-loaded', str(p.get('key'))))
    doc = {'about': 'Problems the hourly lesson job hit (rule LS-04). Written by scripts/hourly_lessons.py, shown on '
                    'Progress and Lessons by js/lesson-behind.js; empty = every recorded lesson loaded.',
           'problems': out}
    new_keys = sorted(seen - set(before))
    changed = doc != old
    if changed:
        p = Path(root) / ALERTS
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return doc, changed, new_keys
