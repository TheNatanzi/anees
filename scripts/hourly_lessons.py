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
    try:     # run log (scripts/track.py): the saved transcript's path + sha256 and the model that answered (AI review 09-27)
        import track
        date = next((p for p in (out.parent.name, out.parent.parent.name) if re.fullmatch(r'20\d\d-\d\d-\d\d', p)), None)
        track.log_run('scribe.saved', date, kind='ingest', provider='elevenlabs', request_model='scribe_v2',
                      response_model=res.get('model_id') or 'scribe_v2', inputs=[mp3], outputs=[out],
                      params={'label': label, 'language_code': res.get('language_code')})
    except Exception as e:
        log('run log line not written:', e)


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


NODE = os.environ.get('ANEES_NODE') or (r'C:\dev\tools\node-v24.18.0-win-x64\node.exe' if os.path.exists(r'C:\dev\tools\node-v24.18.0-win-x64\node.exe') else 'node')
AUTO_REREVIEW = True     # a lesson whose transcript grew after its readers ran (a Meet gap fill) is re-read, one per hour


def run_step(name, cmd, failures, timeout=None, capture=True):
    """One build step. Fail closed (engineering audit 2026-09-29): a non-zero exit, a crash or a timeout is recorded in
    `failures` (which blocks the push and is retried next hour), never ignored and never raised."""
    try:
        kw = dict(capture_output=True, text=True, encoding='utf-8', errors='replace') if capture else {}
        r = subprocess.run(cmd, cwd=ROOT, timeout=timeout, **kw)
    except Exception as e:
        failures.append(f'{name} failed ({type(e).__name__}: {str(e)[:200]})'); log('FAILED', name, e)
        return None
    if r.returncode:
        tail = ((getattr(r, 'stderr', None) or getattr(r, 'stdout', None) or '').strip().splitlines() or [''])[-1][:200]
        failures.append(f'{name} exit {r.returncode}' + (f': {tail}' if tail else '')); log('FAILED', name, 'exit', r.returncode, tail)
    return r


def refresh_published(dates, raw, work):
    """Everything a lesson feeds, for `dates`: Word Bank evidence + review, clips, silent credits, reliability audit,
    lesson data, sentence ladder, build stamp, then the same-day review (two readers -> third -> pages -> Amal's items).
    Returns the failed steps (empty = all fed). Before 2026-09-29 the ladder and the review were 'never blocks the
    publish' (check=False): a failure published a lesson missing from pages and the review was never retried."""
    failures = []
    try:
        import db
        live = db.rest('GET', 'rpc/speaking_snapshot', retries=4)      # 2026-09-23: one call failed transiently under load
        (ROOT / 'docs/data/word-bank-evidence.json').write_text(
            json.dumps({'version': datetime.date.today().isoformat(), 'events': live['events']}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    except Exception as e:
        failures.append(f'speaking snapshot (Word Bank evidence) failed: {type(e).__name__}: {str(e)[:200]}')
        log('FAILED speaking snapshot', e)
        return failures                                                  # nothing below is right without it
    run_step('review_new_lessons.py', [sys.executable, str(HERE / 'review_new_lessons.py'), *dates], failures)
    try:
        build_clips(dates, raw, work)
    except Exception as e:
        failures.append(f'build_audit_audio.py (Word Bank clips) failed: {type(e).__name__}: {str(e)[:200]}'); log('FAILED clips', e)
    track_dates = [d for d in dates if (raw / d / 'tracks' / 'tracks.json').exists()]
    if track_dates:
        run_step('review_silent_credits.py', [sys.executable, str(HERE / 'review_silent_credits.py'), '--raw', str(raw), '--work', str(work), *track_dates], failures)
    run_step('audit_word_bank_reliability.cjs', [NODE, str(HERE / 'audit_word_bank_reliability.cjs'), str(ROOT / 'docs/data/word-bank-evidence.json')], failures)
    # unresolved / on-hold word events get their audit bins (Medi 2026-09-28); was never in the hourly path, so a new
    # lesson's events stayed un-binned and tests/test_vocab_audit.py went red (eng audit 2026-09-29, area 4)
    run_step('audit_vocab_unresolved.py', [sys.executable, str(HERE / 'audit_vocab_unresolved.py')], failures)
    # grammar uses (the Grammar % denominator): was never run by the hourly job - 09-28 went live with uses/pct = None
    run_step('detect_grammar_usage.py', [sys.executable, str(HERE / 'detect_grammar_usage.py')], failures)
    run_step('build_lessons_page_data.py', [sys.executable, str(HERE / 'build_lessons_page_data.py')], failures)   # the transcript on the lesson clock, for the readers
    run_step('build_sentence_ladder.py', [sys.executable, str(HERE / 'build_sentence_ladder.py')], failures, timeout=900)
    run_step('write_build.py', [sys.executable, str(HERE / 'write_build.py')], failures)
    # Same-day review (full audit step 8, Medi 2026-09-25): two readers -> third reader -> pages -> Amal's line items.
    # Its own log lines go to this log (not captured). A failure blocks the push and is retried every hour until it passes.
    for d in dates:
        run_step(f'review_lesson.py {d}', [sys.executable, str(HERE / 'review_lesson.py'), d, '--no-push'], failures, timeout=3 * 3600, capture=False)
    return failures


def _commit(paths, message):
    """Stage + commit (never push: the one push of a run goes through scripts/publish_guard.py). Returns True if a commit was made."""
    run = lambda *c: subprocess.run(['git', *c], cwd=ROOT, capture_output=True, text=True)
    run('add', *paths)
    return run('commit', '-m', message + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>').returncode == 0


# what the Tutor refresh rebuilds (data/accuracy: accuracy_gates annotate rewrites the verification queue on every
# lesson-data build; left uncommitted it made the guard's clean-tree check block every later hour)
TUTOR_PATHS = ['docs/data', 'docs/amal/grammar-rules.html', 'data/full-audit-2026-09-26.json', 'data/accuracy']
# everything a run may build that the site or the guard reads: committed before the run's one push
BUILT_PATHS = ['docs', 'data/full-audit-2026-09-26.json', 'data/accuracy', 'data/lesson-work/full-audit', 'plan/FULL-AUDIT-2026-09-26.md',
               'data/budget.json', 'data/lessons/recall_bots.json', 'data/runs', 'data/decisions', 'data/backfill',
               'data/amal-trigger', 'data/vocab']


def tutor_refresh(no_push=False, rebuild_all=False):
    """Every hour (2026-09-26): apply Amal's new taps (review page + after links) to the audit and pages, then rebuild the
    Tutor page data, commit, and publish through the guard right away (her taps should not wait for a long lesson run).
    Returns the failed steps (fail closed: they block the push and make the next hour rebuild everything the taps feed)."""
    failures = []
    try:
        run_step('apply_amal_audit_rulings.py', [sys.executable, str(HERE / 'apply_amal_audit_rulings.py')], failures, timeout=1800)
        if rebuild_all:           # an earlier hour failed: rebuild everything that reads the audit, not only on new taps
            for s in ('build_amal_review.py', 'build_lessons_page_data.py', 'build_grammar_console.py', 'build_amal_grammar_rules.py'):
                run_step(s, [sys.executable, str(HERE / s)], failures, timeout=1800)
        run_step('build_tutor_data.py', [sys.executable, str(HERE / 'build_tutor_data.py')], failures, timeout=300)
        paths = [p for p in TUTOR_PATHS if (ROOT / p).exists()]
        changed = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if not changed:
            return failures
        _commit(paths, "Amal's answers applied + Tutor page refreshed by the hourly job")
        if not no_push:
            import publish_guard as G
            G.guarded_push(ROOT, source='hourly: tutor refresh', step_failures=failures, log=log)
        log('tutor_refresh:', changed.count('\n') + 1, 'files', ('FAILED ' + '; '.join(failures)) if failures else '')
    except Exception as e:
        failures.append(f'tutor_refresh crashed: {type(e).__name__}: {str(e)[:200]}'); log('tutor_refresh failed', e)
    return failures


def decisions_refresh(no_push=False):
    """After the lessons (AI tracking, plan/AI-ENGINEERING-REVIEW-2026-09-27.md item 2): pull Amal's answers and Medi's swipes
    into data/decisions (read-only, anon key) and commit the decision + run logs, so the clone is clean for the next hour.
    Append-only JSONL with a union merge driver (data/*/.gitattributes). Logs only (no page reads them): a failure is
    logged, never blocks. Pushed with the run's one guarded push."""
    try:
        r = subprocess.run([sys.executable, str(HERE / 'pull_decisions.py')], cwd=ROOT, timeout=300, capture_output=True, text=True)
        if r.returncode:
            log('decisions_refresh: pull_decisions exit', r.returncode, (r.stderr or '').strip()[-200:])
        paths = [p for p in ('data/decisions', 'data/runs') if (ROOT / p).exists()]
        changed = paths and subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if changed:
            _commit(paths, 'AI run + decision logs by the hourly job')
            log('decisions_refresh: logged', changed.count('\n') + 1, 'files')
    except Exception as e:
        log('decisions_refresh failed', e)


def gap_fill_refresh(raw, no_push=False, rebuild=False):
    """Meet gap filler (scripts/fill_meet_gaps.py, Medi 2026-09-28 "do it"): pending entries of data/backfill/meet_gaps.json
    get the missing speaker's side from the mixed Meet recording (one budget-checked Scribe call per gap, run-logged as
    meet_gap_fill). When an entry finishes (or an earlier rebuild failed: rebuild=True), the lesson data + sentence ladder
    are rebuilt and committed; r['failures'] lists failed rebuilds (they block the push, retried next hour). A crash of
    the filler itself changes no page: logged, returns None. Without a key it pays nothing (entries stay pending)."""
    try:
        import fill_meet_gaps as F
        r = dict(F.process_queue(drive=DRIVE, raw=Path(raw)) or {})
        r['failures'] = []
        if not r.get('changed') and not rebuild:
            return r
        if r.get('done') or rebuild:
            run_step('build_lessons_page_data.py (gap fill)', [sys.executable, str(HERE / 'build_lessons_page_data.py')], r['failures'], timeout=1800)
            run_step('build_sentence_ladder.py (gap fill)', [sys.executable, str(HERE / 'build_sentence_ladder.py')], r['failures'], timeout=900)
        paths = [p for p in ('data/backfill', 'data/budget.json', 'data/runs', 'docs/data/lessons.json', 'docs/data/lessons',
                             'docs/data/sentence-ladder.json', 'docs/data/sentence-ladder') if (ROOT / p).exists()]
        changed = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if changed:
            _commit(paths, f"Meet gap fill: {', '.join(r.get('done') or []) or 'queue updated'} by the hourly job")
        log('gap_fill_refresh: done', r.get('done'), 'failed', r.get('failed'), *(['| rebuild FAILED:', '; '.join(r['failures'])] if r['failures'] else []))
        return r
    except Exception as e:
        log('gap_fill_refresh failed', e)
        return None


def commit_lessons(dates):
    """Commit the loaded lessons (was publish(): it pushed straight to master; the push is now the run's one guarded push)."""
    run = lambda *c: subprocess.run(['git', *c], cwd=ROOT, capture_output=True, text=True)
    # data/budget.json: transcribing writes the cost log; left unstaged it made 'pull --rebase' refuse (exit 128) and the
    # 2026-09-23 lesson commit never reached master (2026-09-24 fix; --autostash covers any other stray edit).
    run('add', 'docs/data', 'docs/js/build.js', 'data/lessons/recall_bots.json', 'data/budget.json',
        *[f'docs/lessons/{d}.html' for d in dates if (ROOT / 'docs' / 'lessons' / f'{d}.html').exists()],
        *[p for p in ('data/runs', 'data/decisions') if (ROOT / p).exists()])   # AI run + decision logs ride along (append-only)
    run('add', '-f', *[f'docs/lessons/{d}/audio/lesson.mp3' for d in dates if (ROOT / 'docs' / 'lessons' / d / 'audio' / 'lesson.mp3').exists()],
        *[f'docs/lessons/{d}/clips' for d in dates if (ROOT / 'docs' / 'lessons' / d / 'clips').exists()])
    return run('commit', '-m', f'Lessons {", ".join(dates)} loaded by the hourly job\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>').returncode == 0


def pending_reviews(root=None):
    """Lessons (from AUTO_START) whose same-day review must run (again): never finished (no settled audit) first, then those
    whose transcript changed after the readers read it. [(date, why)], oldest first within each group."""
    root = Path(root or ROOT)
    work = root / 'data' / 'lesson-work' / 'full-audit'
    dates = sorted(p.stem for p in (root / 'docs' / 'lessons').glob('20??-??-??.html') if p.stem >= AUTO_START)
    never = [(d, 'the same-day review never finished (no settled audit)') for d in dates if not (work / f'{d}.settled.json').exists()]
    import review_lesson as RL
    changed = []
    for d in dates:
        if (work / f'{d}.settled.json').exists():
            try:
                why = RL.readers_read_current(d, str(root))
            except Exception as e:
                why = f'transcript unreadable ({type(e).__name__})'
            if why:
                changed.append((d, why))
    return never + changed


def main():
    """One Anees job at a time: the hourly job waits up to 15 min for the shared lock the 15-minute Amal trigger uses."""
    import amal_trigger as T
    if '--dry-run' not in sys.argv and not T.acquire(wait_s=900):
        log('another Anees job has held the lock for 15 min; skipped this hour'); return 1
    try:
        return _main()
    finally:
        if '--dry-run' not in sys.argv:
            T.release()


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', default=os.environ.get('ANEES_RAW', str(ROOT / 'data' / 'lessons')))
    ap.add_argument('--work', default=str(ROOT / 'data' / 'lesson-work'))
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--no-push', action='store_true')
    a = ap.parse_args()
    os.environ.setdefault('ANEES_STRICT', '1')        # builders fail closed instead of using silent offline fallbacks (eng audit 09-29)
    os.environ.setdefault('ANEES_TRIGGER', 'hourly')     # run log (scripts/track.py): every child call is tagged hourly
    import db, recall_bot as R
    import publish_guard as G
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
        print(json.dumps({'new_bots': new_rows, 'todo': todo, 'open_failures': G.open_failures(ROOT),
                          'pending_reviews': pending_reviews(ROOT)}, indent=1)); return 0
    open_before = G.open_failures(ROOT)          # failed steps of earlier hours: retried below, block every push until fixed
    if open_before:
        log('retrying failed steps of an earlier hour:', ', '.join(sorted(open_before)))
    run_failures = []
    f = tutor_refresh(no_push=a.no_push, rebuild_all='tutor' in open_before)   # Amal's taps -> scores + rules; Tutor page
    G.set_open_failures(ROOT, 'tutor', f); run_failures += f
    # Amal trigger (Medi M3 2026-09-29): any new/changed answer of hers in any source -> re-pull, rebuild, rescore, log.
    # Runs here every hour as the fallback for the 15-minute task (scripts/run_amal_trigger.ps1); this run's one guarded
    # push publishes it. A failed step keeps her old fingerprint, so the next run retries (open failure 'amal').
    try:
        import amal_trigger as T
        tr = T.run(publish=False, log=log)
        af = (tr.get('firing') or {}).get('failures') or []
    except Exception as e:
        af = [f'amal_trigger crashed: {type(e).__name__}: {str(e)[:200]}']
    G.set_open_failures(ROOT, 'amal', af); run_failures += af
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
    # every lesson fed this hour: the new ones + any whose feeding failed in an earlier hour (retried until it passes)
    retry = sorted(k.split(':', 1)[1] for k in open_before if k.startswith('refresh:'))
    batch = sorted(set(done) | set(retry))
    if batch:
        f = refresh_published(batch, raw, work)
        for d in batch:
            G.set_open_failures(ROOT, 'refresh:' + d, f)
        run_failures += f
        commit_lessons(batch)
        log('loaded + committed' if done else 'retried', batch, *(['| FAILED:', '; '.join(f)] if f else []))
    else:
        log('nothing new')
    # a lesson whose review never finished, or whose transcript grew after its readers ran: one re-review per hour
    if not batch and AUTO_REREVIEW:
        pend = pending_reviews(ROOT)
        pend_dates = {d for d, _ in pend}
        for k in [k for k in G.open_failures(ROOT) if k.startswith('review:') and k.split(':', 1)[1] not in pend_dates]:
            G.set_open_failures(ROOT, k, [])     # fixed since (by hand or by a later run)
        if pend:
            d, why = pend[0]
            log('re-review', d, '-', why)
            f = []
            run_step(f'review_lesson.py {d}', [sys.executable, str(HERE / 'review_lesson.py'), d, '--no-push'], f, timeout=3 * 3600, capture=False)
            G.set_open_failures(ROOT, 'review:' + d, f); run_failures += f
    g = gap_fill_refresh(raw, no_push=a.no_push, rebuild='gapfill' in open_before)     # never raises (fill_meet_gaps.py)
    if g is not None:
        G.set_open_failures(ROOT, 'gapfill', g.get('failures') or []); run_failures += g.get('failures') or []
    decisions_refresh()                                 # logs only; never raises
    # The run's ONE push (lessons, gap fill, logs, and any commit an earlier blocked hour left behind) goes through the
    # publish guard: it re-checks the numbers first; on a block nothing is published and the local commits wait.
    # whatever this hour built and no step committed (e.g. data/accuracy/verification-queue.json) goes in one last commit,
    # so the guard checks exactly what would be published
    rest = [p for p in BUILT_PATHS if (ROOT / p).exists()]
    # clips are *.mp3, which .gitignore excludes: without -f the Grammar console's clips never went live (515 of the 1,240
    # it links on master 2026-09-29 are not committed; the page falls back to seeking the lesson audio)
    clips = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'docs' / 'lessons').glob('20??-??-??/clips') if p.is_dir())
    if clips:
        subprocess.run(['git', 'add', '-f', '--', *clips], cwd=ROOT, capture_output=True, text=True)
    if rest and subprocess.run(['git', 'status', '--porcelain', '--', *rest], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        subprocess.run(['git', 'add', '-A', '--', *rest], cwd=ROOT, capture_output=True, text=True)
        _commit(rest, 'Hourly job: remaining built files')
    blocked = False
    if not a.no_push:
        ahead = subprocess.run(['git', 'rev-list', '--count', 'origin/master..HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        if ahead not in ('', '0'):
            what = ('lessons ' + ', '.join(done)) if done else 'retry ' + ', '.join(batch) if batch else f'{ahead} local commit(s)'
            res = G.guarded_push(ROOT, source=f'hourly: {what}', step_failures=run_failures, log=log)
            blocked = not res.get('pushed')
    return 1 if (failures or blocked or run_failures or G.open_failures(ROOT)) else 0


if __name__ == '__main__':
    raise SystemExit(main())
