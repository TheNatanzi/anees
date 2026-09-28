"""M8 hardening for the lesson pipeline: ElevenLabs retries (3× on 429/5xx with backoff) + a failure email to Medi, a paid-call
ledger with hard caps, and the post-transcript steps (understand → report + email → Amal after-link payload) behind one guarded
function. lesson_pipeline.py calls these; every branch is unit-tested with mocks in tests/test_m8_pipeline.py.
Nothing here changes the Task Scheduler entry."""
import datetime, io, json, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / 'data' / 'budget.json'
CAPS = {'elevenlabs': 10.0, 'openai': 10.0}      # USD, the plan's hard limits; paid calls stop at 90 %
STOP_AT = 0.9
ELEVEN_USD_PER_MIN = 0.22 / 60                  # Scribe v2 list price ($0.22 / hour)
KEYTERM_USD_PER_MIN = 0.05 / 60                 # keyterm prompting surcharge (+$0.05 / hour, plan/AI-ENGINEERING-REVIEW-2026-09-27.md)
# Names as Scribe keyterms (Medi 2026-09-28: "the AI understanding that a word is a name"): docs/data/names.json via
# scripts/names.py keyterms(). NAMES ONLY, never vocabulary (vocab biasing could hide Medi's mistakes). Per track:
#   'all'    every place, country and nationality name (Amal's track, default)
#   'places' place names only (Medi's track and a mixed / unknown file, default: a country or nationality word on his
#            side is too close to vocabulary). People are stored only as fingerprints, so no person keyterm is ever sent.
#   'off'    no keyterms (today's behaviour).
# Override per run: ANEES_KEYTERMS_AMAL / ANEES_KEYTERMS_MEDI = all | places | off.
KEYTERMS = {'amal': 'all', 'medi': 'places', 'mixed': 'places'}


def ledger():
    if LEDGER.exists():
        return json.load(io.open(LEDGER, encoding='utf-8'))
    return {'elevenlabs': 0.0, 'openai': 0.0, 'calls': []}


def spend(service, usd, what):
    L = ledger()
    L[service] = round(L.get(service, 0.0) + usd, 4)
    L['calls'].append({'t': datetime.datetime.now().isoformat(timespec='seconds'), 'service': service, 'usd': round(usd, 4), 'what': what})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    io.open(LEDGER, 'w', encoding='utf-8').write(json.dumps(L, ensure_ascii=False, indent=1))
    return L


def budget_ok(service, usd_next):
    """True when the next call keeps the service under 90 % of its cap."""
    L = ledger()
    return L.get(service, 0.0) + usd_next <= CAPS[service] * STOP_AT


class BudgetStop(RuntimeError):
    pass


def track_of(path, who=None):
    """'amal' | 'medi' | 'mixed' from the participant name (ingest_tracks passes it) or the file name."""
    n = (who or Path(str(path)).name).lower()
    if 'amal' in n:
        return 'amal'
    if 'medi' in n or 'mahdi' in n or 'natanzi' in n:
        return 'medi'
    return 'mixed'


def keyterms_for(track):
    """(keyterms, mode, names.json sha) for this track. Never raises: no names file -> no keyterms."""
    import os
    mode = (os.environ.get('ANEES_KEYTERMS_' + track.upper()) if track in ('amal', 'medi') else None) or KEYTERMS.get(track, 'off')
    if mode not in ('all', 'places'):
        return [], 'off', None
    try:
        import names
        return names.load().keyterms('amal' if mode == 'all' else 'medi'), mode, (names.names_sha() or '')[:16]
    except Exception:
        return [], 'off', None


def transcribe_with_retry(post, mp3_path, key, minutes, tries=3, backoff=(5, 20, 60), sleep=time.sleep, who=None):
    """post(url, headers, data, files, timeout) -> response-like (status_code, text, json()). Retries 429 / 5xx / network errors
    up to `tries` times; refuses to start when the ElevenLabs budget would pass 90 %.
    Every call writes one line to data/runs (scripts/track.py): audio minutes, list-price cost, retries, status, the keyterm
    count and the names.json sha they came from - never text (keyterms themselves are not logged)."""
    trk = track_of(mp3_path, who)
    terms, mode, nsha = keyterms_for(trk)
    try:
        import track
        ctx = track.run('scribe.transcribe', _lesson_date_of(mp3_path), kind='ingest', provider='elevenlabs',
                        request_model='scribe_v2', inputs=[mp3_path],
                        params={'diarize': True, 'num_speakers': 2, 'timestamps_granularity': 'word', 'tag_audio_events': True,
                                'track': trk, 'keyterms': len(terms), 'keyterms_mode': mode, 'names_sha': nsha})
        rec = ctx.__enter__()
    except Exception:
        ctx, rec = None, None
    try:
        res = _transcribe_with_retry(post, mp3_path, key, minutes, tries, backoff, sleep, rec, terms)
    except BaseException as e:
        if ctx is not None:
            try:
                if isinstance(e, BudgetStop):
                    rec.set(status='skipped_budget')
                ctx.__exit__(type(e), e, e.__traceback__)
            except BaseException:
                pass
        raise
    if ctx is not None:
        try:
            rec.set(**{'gen_ai.response.model': (res or {}).get('model_id') if isinstance(res, dict) else None})
            if isinstance(res, dict) and not any(w.get('type') == 'word' for w in res.get('words') or []):
                rec.set(status='empty_output')
            ctx.__exit__(None, None, None)
        except Exception:
            pass
    return res


def _lesson_date_of(path):
    """The lesson date in a raw-archive path (.../data/lessons/<date>/...), else None."""
    import re
    m = re.search(r'(20\d\d-\d\d-\d\d)', str(path).replace('\\', '/'))
    return m.group(1) if m else None


def _transcribe_with_retry(post, mp3_path, key, minutes, tries, backoff, sleep, rec=None, keyterms=()):
    est = minutes * (ELEVEN_USD_PER_MIN + (KEYTERM_USD_PER_MIN if keyterms else 0))
    note = (lambda **k: rec.set(**k)) if rec is not None else (lambda **k: None)
    note(usage={'audio_min': round(minutes, 3)})
    if not budget_ok('elevenlabs', est):
        raise BudgetStop(f'ElevenLabs budget: {ledger().get("elevenlabs", 0):.2f} + {est:.2f} USD would pass 90 % of the {CAPS["elevenlabs"]:.0f} USD cap')
    last = None
    attempts = 0
    for i in range(tries):
        attempts += 1
        try:
            with open(mp3_path, 'rb') as f:
                data = {'model_id': 'scribe_v2', 'diarize': 'true', 'num_speakers': '2', 'timestamps_granularity': 'word', 'tag_audio_events': 'true'}
                if keyterms:
                    data['keyterms'] = list(keyterms)       # multipart: one 'keyterms' field per name (max 1000, 50 chars each)
                r = post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key': key},
                         data=data,
                         files={'file': (Path(mp3_path).name, f, 'audio/mpeg')}, timeout=1800)
        except Exception as e:                      # network error
            last = f'network: {e}'
            note(error_type='network_' + type(e).__name__)
            sleep(backoff[min(i, len(backoff) - 1)]); continue
        if r.status_code == 200:
            spend('elevenlabs', est, f'scribe {Path(mp3_path).name} ({minutes:.0f} min)')
            note(retries=attempts - 1, cost_usd=round(est, 6), cost_basis='list_price')
            return r.json()
        last = f'ElevenLabs {r.status_code}: {str(r.text)[:200]}'
        note(error_type=f'http_{r.status_code}')
        if r.status_code == 429 or r.status_code >= 500:
            sleep(backoff[min(i, len(backoff) - 1)]); continue
        break                                       # 4xx other than 429: do not retry
    note(retries=attempts - 1)
    raise RuntimeError(f'ElevenLabs failed after {attempts} tr{"y" if attempts == 1 else "ies"}: {last}')


def failure_email(subject, reason, date=None, run=subprocess.run):
    """Rich failure email to Medi only (house style, via send_lesson_email.mjs). Never raises."""
    payload = {'headline': subject, 'sub': reason[:300], 'rows': [{'tag': 'Lesson', 'name': date or '–', 'detail': 'the recording stays in the Meet folder; nothing was deleted'},
                                                                  {'tag': 'Next', 'name': 'Re-run when fixed', 'detail': 'python scripts/lesson_pipeline.py --file "<recording>" (a cached scribe.json is reused, no new charge)'}],
               'chart': {'title': 'Retries', 'bars': [{'label': 'tries', 'value': 3}], 'legend': 'amber = attempts made'},
               'log': [{'t': datetime.datetime.now().strftime('%H:%M'), 'text': reason[:200]}],
               'footer': 'Anees pipeline. Only Medi receives this email.', 'text': f'{subject}: {reason}'}
    p = ROOT / 'data' / 'lessons' / 'last_failure_email.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    io.open(p, 'w', encoding='utf-8').write(json.dumps(payload, ensure_ascii=False))
    try:
        run(['node', str(ROOT / 'scripts' / 'send_lesson_email.mjs'), subject, str(p)], check=True, timeout=120)
        return True
    except Exception:
        return False


def post_process(date, scribe=None, audio=None, src=None, send_email=True, use_openai=True, log=print):
    """After a transcript page exists: understanding → report (+ email) → after-lesson payload + link (never sent).
    Each step is guarded; a failure is logged, emailed to Medi, and never blocks the transcript that already shipped."""
    out = {'date': date}
    try:
        import understand_lesson, build_report, lesson_pipeline
        understand_lesson.understand(date, scribe, audio, src)
        out['report'] = build_report.build(date, use_db=True, send=False)        # writes the page + report_email.json, sends nothing
        import sync_speaking_lesson
        out['speaking'] = sync_speaking_lesson.sync_if_active(date)
        out['report']['url'] = lesson_pipeline.publish_report(date)               # push + wait for HTTP 200; raises otherwise
        if send_email:
            subprocess.run(['node', str(ROOT / 'scripts' / 'send_lesson_email.mjs'), f'Anees: lesson report {date}',
                            str(ROOT / 'data' / 'lessons' / date / 'report_email.json')], check=True, timeout=120)
            out['report']['emailed'] = True
    except Exception as e:
        out['report_error'] = str(e)[:300]; log('post_process report failed', e); failure_email(f'Anees: report for {date} failed', str(e), date)
        return out
    try:
        import after_questions, amal_links
        ok = use_openai and budget_ok('openai', 0.15)
        p = after_questions.payload(date, audio, use_openai=ok)
        token, url = amal_links.create('after', date, p)
        out['after_link'] = url            # printed to the log only; never sent to Amal
    except Exception as e:
        out['after_error'] = str(e)[:300]; log('post_process after-link failed', e); failure_email(f'Anees: after-lesson link for {date} failed', str(e), date)
    return out
