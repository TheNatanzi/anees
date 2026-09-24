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
    try:
        from zoneinfo import ZoneInfo                # Pacific civil time: -7 in summer, -8 in winter (Codex 2026-09-23)
        return t.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
    except Exception:
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


def plan(ledger, bots, recordings, loaded_dates, raw, decided=(), half_done=()):
    """What this hour should do. Tracks win over a Meet file; a loaded date is never touched again.
    half_done = dates with a database row but no published page (a run that failed after loading): republish them."""
    todo, new_rows = [{'kind': 'republish', 'date': d} for d in sorted(half_done)], merge_bots(ledger, bots)
    loaded_dates = set(loaded_dates) | set(half_done)
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


def longest_tracks(tracks):
    """{'Amal': track, 'Medi': track}: each person's longest recording (the host's silent track is skipped)."""
    import load_lesson as L
    best = {}
    for trk in tracks:
        who = L._person(trk['participant'])
        if who and (who not in best or (trk.get('duration_s') or 0) > (best[who].get('duration_s') or 0)):
            best[who] = trk
    return best


def load(date, lesson_dir, work, meet, apply):
    cmd = [sys.executable, str(HERE / 'load_lesson.py'), date, '--raw', str(lesson_dir), '--work', str(work)]
    if meet:
        cmd += ['--meet', str(meet)]
    if apply:
        cmd += ['--apply']
    out = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
    if out.returncode:
        raise RuntimeError(out.stderr[-800:])
    return json.loads(out.stdout)


def build_clips(dates, raw, work):
    """Word Bank excerpts for every learner event (build_audit_audio.py). The audio map lives with the raw archive
    (raw/audio-source-map.json, first written 2026-09-23); new lessons' recordings are hashed into it."""
    import hashlib
    review = json.loads((ROOT / 'docs/data/word-bank-review.json').read_text(encoding='utf-8'))
    events = json.loads((ROOT / 'docs/data/word-bank-evidence.json').read_text(encoding='utf-8'))['events']
    audited = [{**e, **review['patches'].get(e['id'], {}).get('changes', {})} for e in events] + [x['event'] for x in review['additions']]
    cw = work / 'clipbuild'
    (cw / 'audit-audio').mkdir(parents=True, exist_ok=True)
    (cw / 'audited-events.json').write_text(json.dumps(audited, ensure_ascii=False), encoding='utf-8')
    mp = raw / 'audio-source-map.json'
    amap = json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else {}
    for d in dates:
        for f in list((raw / d).glob('tracks/*.mp3')) + list((raw / d).glob('meet-*/audio.mp3')) + list((raw / d).glob('tracks/recovered/*.mp3')):
            amap.setdefault(hashlib.sha256(f.read_bytes()).hexdigest(), str(f))
    mp.write_text(json.dumps(amap, indent=2), encoding='utf-8')
    (cw / 'audio-source-map.json').write_text(json.dumps(amap, indent=2), encoding='utf-8')
    subprocess.run([sys.executable, str(HERE / 'build_audit_audio.py'), str(cw)], check=True, cwd=ROOT, capture_output=True)


def refresh_published(dates, raw, work):
    """Published fallback + review + audit for the new dates (clips are rebuilt by hand with build_audit_audio.py)."""
    import db
    live = db.rest('GET', 'rpc/speaking_snapshot', retries=4)      # 2026-09-23: one call failed transiently under load
    (ROOT / 'docs/data/word-bank-evidence.json').write_text(
        json.dumps({'version': datetime.date.today().isoformat(), 'events': live['events']}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    run = lambda *c: subprocess.run([*c], check=True, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    run(sys.executable, str(HERE / 'review_new_lessons.py'), *dates)
    build_clips(dates, raw, work)
    track_dates = [d for d in dates if (raw / d / 'tracks' / 'tracks.json').exists()]
    if track_dates:
        run(sys.executable, str(HERE / 'review_silent_credits.py'), '--raw', str(raw), '--work', str(work), *track_dates)
    run('node', str(HERE / 'audit_word_bank_reliability.cjs'), str(ROOT / 'docs/data/word-bank-evidence.json'))
    run(sys.executable, str(HERE / 'write_build.py'))


def publish(dates):
    run = lambda *c: subprocess.run(['git', *c], check=True, cwd=ROOT, capture_output=True, text=True)
    # data/budget.json: transcribing writes the cost log; left unstaged it made 'pull --rebase' refuse (exit 128) and the
    # 2026-09-23 lesson commit never reached master (2026-09-24 fix; --autostash covers any other stray edit).
    run('add', 'docs/data', 'docs/js/build.js', 'data/lessons/recall_bots.json', 'data/budget.json', *[f'docs/lessons/{d}.html' for d in dates])
    run('add', '-f', *[f'docs/lessons/{d}/audio/lesson.mp3' for d in dates],
        *[f'docs/lessons/{d}/clips' for d in dates if (ROOT / 'docs' / 'lessons' / d / 'clips').exists()])
    run('commit', '-m', f'Lessons {", ".join(dates)} loaded by the hourly job\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')
    # No automatic conflict side: '-X theirs' in a rebase keeps THIS job's copy and could drop another session's review
    # patches in docs/data. On any conflict: abort, keep the local commit, fail loudly; a person merges.
    try:
        run('pull', '--rebase', '--autostash', 'origin', 'master')
    except subprocess.CalledProcessError as e:
        subprocess.run(['git', 'rebase', '--abort'], cwd=ROOT, capture_output=True)
        raise RuntimeError('pull --rebase failed; lesson commit kept locally, not pushed: ' + (e.stderr or '')[-400:])
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
    in_db = {r['date'] for r in db.select('lessons', {'select': 'date'}, retries=4)}
    published = {p.stem for p in (ROOT / 'docs' / 'lessons').glob('20??-??-??.html')}
    recordings = meet_recordings(DRIVE)
    new_rows, todo = plan(ledger, recall_bots(), recordings, in_db & published, raw, decided,
                          half_done={d for d in in_db - published if d >= AUTO_START})
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
            lesson_dir, meet = raw / d, meet_for(d, recordings)
            if t['kind'] == 'republish':
                if not (lesson_dir / 'tracks' / 'tracks.json').exists():
                    found = sorted(p.parent for p in lesson_dir.glob('meet-*/scribe.json'))
                    if not found:
                        raise RuntimeError('database has the lesson but no saved transcript on this PC')
                    lesson_dir = found[0]
            elif t['kind'] == 'tracks':
                if not (lesson_dir / 'tracks' / 'tracks.json').exists():
                    R.fetch(t['bot_id'], date=d, wait_minutes=0)
                for who, trk in longest_tracks(json.loads((lesson_dir / 'tracks' / 'tracks.json').read_text(encoding='utf-8'))['tracks']).items():
                    transcribe_once(lesson_dir / f'scribe_{who}.json', Path(trk['file']), who)
            else:
                import lesson_pipeline as lp
                src = Path(t['path'])
                lesson_dir = raw / d / ('meet-' + t['code'])     # one folder per call: two calls on one day never share audio
                lesson_dir.mkdir(parents=True, exist_ok=True)
                mp3 = lp.extract_audio(src, lesson_dir / 'audio.mp3')
                if not (chat_has_tutor(src) or (lesson_dir / 'scribe.json').exists() or lp.is_arabic_lesson(mp3, lesson_dir)):
                    decided[src.name] = 'not a lesson (no tutor chat, Arabic pre-check failed)'
                    decided_path.write_text(json.dumps(decided, indent=1), encoding='utf-8'); continue
                transcribe_once(lesson_dir / 'scribe.json', mp3, 'mixed Meet recording')
                meet = src
            receipt = load(d, lesson_dir, work, meet, apply=True)
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
        # A lesson commit a failed push left behind is 'published' locally (its page exists), so no later hour re-plans it:
        # push it here instead of stranding it (2026-09-23 sat unpushed overnight).
        ahead = subprocess.run(['git', 'rev-list', '--count', 'origin/master..HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if not a.dry_run and not a.no_push and ahead not in ('', '0'):
            if subprocess.run(['git', 'pull', '--rebase', '--autostash', 'origin', 'master'], cwd=ROOT, capture_output=True).returncode:
                subprocess.run(['git', 'rebase', '--abort'], cwd=ROOT, capture_output=True)
                log('FAILED to rebase', ahead, 'unpushed local commit(s); a person merges'); return 1
            subprocess.run(['git', 'push', 'origin', 'HEAD:master'], check=True, cwd=ROOT, capture_output=True)
            log('pushed', ahead, 'local commit(s) left by an earlier run')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
