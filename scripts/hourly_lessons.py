"""Hourly: find every new lesson (Recall API + both Drive Meet folder styles), load it, publish. Replaces the
process_recall_queue + lesson_pipeline pair, which (a) only knew bots written in recall_bots.json (missed 09-14, 09-21),
(b) only scanned 'Meet Recordings' although Meet saves each call in 'Google Meet/<code> - <date>' since 09-10 (missed 09-18),
(c) stopped on the host's silent track ('Ray Adib' = wc@adibs.com).

  python scripts/hourly_lessons.py [--raw C:/dev/anees/data/lessons] [--dry-run] [--no-push]

Rules kept: a saved transcript is never re-made (scribe*.json reused); per-person tracks beat the mixed Meet recording
(a date with Recall tracks never uses the Meet file); Amal's chat sidecar is always merged; nothing is emailed or sent.
A Meet recording is only paid for when Amal typed in its chat or the 3-minute Arabic pre-check passes (lesson_pipeline).
"""
from __future__ import annotations

import argparse, datetime, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
DRIVE = Path(os.environ.get('ANEES_DRIVE', 'G:/My Drive'))
MEET_NAME = re.compile(r'^([a-z]{3}-[a-z]{4}-[a-z]{3}) \((\d{4}-\d{2}-\d{2}) (\d{2})[ :](\d{2}) GMT[-+]\d+\)( \(\d+\))?$')
MIN_BYTES = 20_000_000
AUTO_START = '2026-09-10'          # earlier recordings were all decided by hand (see plan/LESSON-INVENTORY-2026-09-23.md)


def log(*parts):
    print(datetime.datetime.now().strftime('%H:%M:%S'), *parts, flush=True)


# ---------- discovery (pure, tested) ----------

def bot_date(bot, tz_hours=-7):
    meta = (bot.get('metadata') or {}).get('anees_lesson')
    if meta:
        return meta
    stamp = bot.get('join_at') or ((bot.get('status_changes') or [{}])[0].get('created_at'))
    t = datetime.datetime.fromisoformat(str(stamp).replace('Z', '+00:00'))
    return t.astimezone(datetime.timezone(datetime.timedelta(hours=tz_hours))).date().isoformat()


def merge_bots(ledger, bots):
    """Ledger rows for every API bot that the ledger does not know yet (the 09-14 and 09-21 misses)."""
    known = {e.get('bot_id') for e in ledger}
    new = []
    for b in bots:
        if b['id'] in known:
            continue
        mu = b.get('meeting_url')
        url = 'https://meet.google.com/' + mu['meeting_id'] if isinstance(mu, dict) and mu.get('meeting_id') else mu
        new.append({'t': str(b.get('join_at') or '')[:19], 'bot_id': b['id'], 'date': bot_date(b), 'meeting_url': url,
                    'found': 'Recall API list (hourly discovery)'})
    return new


def meet_recordings(drive):
    """Every host Meet recording in 'Meet Recordings/' AND 'Google Meet/<code> - <date>/' -> [(path, code, date, hhmm)]."""
    out = []
    folders = [drive / 'Meet Recordings'] + sorted(p for p in (drive / 'Google Meet').glob('*') if p.is_dir())
    for folder in folders:
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir()):
            m = MEET_NAME.match(p.name)
            if m and p.is_file() and p.stat().st_size >= MIN_BYTES:
                out.append((p, m.group(1), m.group(2), m.group(3) + m.group(4)))
    return out


def chat_has_tutor(recording):
    import build_lesson_page as P
    side = recording.parent / (recording.name + ' - Chat Transcript')
    return side.exists() and any(c['who'] == 'Amal' for c in P.parse_chat(side.read_text(encoding='utf-8', errors='replace')))


def plan(ledger, bots, recordings, loaded_dates, raw, decided=()):
    """What this hour should do. Tracks win over a Meet file; a loaded date is never touched again."""
    todo, new_rows = [], merge_bots(ledger, bots)
    by_bot = {b['id']: b for b in bots}
    track_dates = set()
    for e in ledger + new_rows:
        d = e['date']
        if d < AUTO_START:
            continue
        track_dates.add(d)
        if d in loaded_dates:
            continue
        b = by_bot.get(e['bot_id'])
        codes = [s.get('code') for s in (b or {}).get('status_changes', [])]
        if b is not None and (codes[-1:] or [None])[0] != 'done':
            continue                              # still in the call / processing on Recall's side
        todo.append({'kind': 'tracks', 'date': d, 'bot_id': e['bot_id']})
    for path, code, d, hhmm in recordings:
        if d < AUTO_START or d in loaded_dates or d in track_dates or path.name in decided:
            continue
        if any(t['date'] == d for t in todo):
            continue
        todo.append({'kind': 'meet', 'date': d, 'path': str(path), 'code': code, 'hhmm': hhmm})
    return new_rows, todo


# ---------- actions ----------

def recall_bots():
    import recall_bot as R, requests
    url, out = f'{R.BASE}/bot/', []
    while url:
        r = requests.get(url, headers=R._h(), timeout=60); r.raise_for_status(); j = r.json()
        out += j.get('results', []); url = j.get('next')
    return out


def transcribe_once(out, mp3, label):
    """Never re-make a saved transcript (2026-09-05: a re-run on the mixed audio overwrote clean tracks)."""
    import hashlib, lesson_pipeline as lp
    if out.exists():
        log('reusing', out.name); return
    log('transcribing', label, mp3.name)
    res = lp.transcribe(mp3)
    out.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    out.with_name(out.stem + '.provenance.json').write_text(json.dumps({
        'source_file': str(mp3), 'source_sha256': sha(mp3), 'provider': 'ElevenLabs Scribe v2', 'response_sha256': sha(out),
        'audio_duration_secs': res.get('audio_duration_secs'), 'language_code': res.get('language_code'),
        'words': sum(1 for w in res.get('words', []) if w.get('type') == 'word')}, indent=2), encoding='utf-8')


def meet_for(date, recordings):
    """The host recording of a lesson date (the one whose chat has Amal, else the longest)."""
    same = [r for r in recordings if r[2] == date]
    same.sort(key=lambda r: (not chat_has_tutor(r[0]), -r[0].stat().st_size))
    return same[0][0] if same else None


def load(date, raw, work, meet, apply):
    cmd = [sys.executable, str(HERE / 'load_lesson.py'), date, '--raw', str(raw / date), '--work', str(work)]
    if meet:
        cmd += ['--meet', str(meet)]
    if apply:
        cmd += ['--apply']
    out = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
    if out.returncode:
        raise RuntimeError(out.stderr[-800:])
    return json.loads(out.stdout)


def refresh_published(dates, raw, work):
    """Published fallback + review + audit for the new dates (clips are rebuilt by hand with build_audit_audio.py)."""
    import db
    live = db.rest('GET', 'rpc/speaking_snapshot', retries=1)
    (ROOT / 'docs/data/word-bank-evidence.json').write_text(
        json.dumps({'version': datetime.date.today().isoformat(), 'events': live['events']}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    run = lambda *c: subprocess.run([*c], check=True, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    run(sys.executable, str(HERE / 'review_new_lessons.py'), *dates)
    track_dates = [d for d in dates if (raw / d / 'tracks' / 'tracks.json').exists()]
    if track_dates:
        run(sys.executable, str(HERE / 'review_silent_credits.py'), '--raw', str(raw), '--work', str(work), *track_dates)
    run('node', str(HERE / 'audit_word_bank_reliability.cjs'), str(ROOT / 'docs/data/word-bank-evidence.json'))
    run(sys.executable, str(HERE / 'write_build.py'))


def publish(dates):
    run = lambda *c: subprocess.run(['git', *c], check=True, cwd=ROOT, capture_output=True, text=True)
    run('add', 'docs/data', 'docs/js/build.js', 'data/lessons/recall_bots.json', *[f'docs/lessons/{d}.html' for d in dates])
    run('add', '-f', *[f'docs/lessons/{d}/audio/lesson.mp3' for d in dates])
    run('commit', '-m', f'Lessons {", ".join(dates)} loaded by the hourly job\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')
    run('pull', '--rebase', '-X', 'theirs', 'origin', 'master')
    run('push', 'origin', 'HEAD:master')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.environ.get('ANEES_RAW', str(ROOT / 'data' / 'lessons')))
    ap.add_argument('--work', default=str(ROOT / 'data' / 'lesson-work'))
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--no-push', action='store_true')
    a = ap.parse_args()
    import db, recall_bot as R
    raw, work = Path(a.raw), Path(a.work)
    R.LESSONS = raw
    ledger_path = ROOT / 'data' / 'lessons' / 'recall_bots.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8-sig')) if ledger_path.exists() else []
    decided_path = raw / 'meet_decisions.json'
    decided = json.loads(decided_path.read_text(encoding='utf-8')) if decided_path.exists() else {}
    loaded = {r['date'] for r in db.select('lessons', {'select': 'date'}, retries=1)}
    recordings = meet_recordings(DRIVE)
    new_rows, todo = plan(ledger, recall_bots(), recordings, loaded, raw, decided)
    for r in new_rows:
        log('new Recall bot found in the API list', r['date'], r['bot_id'])
    if a.dry_run:
        print(json.dumps({'new_bots': new_rows, 'todo': todo}, indent=1)); return 0
    if new_rows:
        ledger_path.write_text(json.dumps(sorted(ledger + new_rows, key=lambda e: e['t']), ensure_ascii=False, indent=1), encoding='utf-8')
    done, failures = [], 0
    for t in todo:
        d = t['date']
        try:
            if t['kind'] == 'tracks':
                if not (raw / d / 'tracks' / 'tracks.json').exists():
                    R.fetch(t['bot_id'], date=d, wait_minutes=0)
                for trk in json.loads((raw / d / 'tracks' / 'tracks.json').read_text(encoding='utf-8'))['tracks']:
                    import load_lesson as L
                    who = L._person(trk['participant'])
                    if not who:
                        continue                  # host account: silent, never a speaker
                    same = [x for x in json.loads((raw / d / 'tracks' / 'tracks.json').read_text(encoding='utf-8'))['tracks'] if L._person(x['participant']) == who]
                    if trk is max(same, key=lambda x: x.get('duration_s') or 0):
                        transcribe_once(raw / d / f'scribe_{who}.json', Path(trk['file']), who)
            else:
                import lesson_pipeline as lp
                src = Path(t['path'])
                (raw / d).mkdir(parents=True, exist_ok=True)
                mp3 = lp.extract_audio(src, raw / d / 'audio.mp3')
                if not (chat_has_tutor(src) or (raw / d / 'scribe.json').exists() or lp.is_arabic_lesson(mp3, raw / d)):
                    decided[src.name] = 'not a lesson (no tutor chat, Arabic pre-check failed)'
                    decided_path.write_text(json.dumps(decided, indent=1), encoding='utf-8'); continue
                transcribe_once(raw / d / 'scribe.json', mp3, 'mixed Meet recording')
            receipt = load(d, raw, work, meet_for(d, recordings), apply=True)
            log('loaded', d, receipt.get('events'), 'events')
            done.append(d)
        except Exception as ex:
            failures += 1; log('FAILED', d, str(ex)[:500])
    if done:
        refresh_published(done, raw, work)
        if not a.no_push:
            publish(done)
        log('published', done)
    else:
        log('nothing new')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
