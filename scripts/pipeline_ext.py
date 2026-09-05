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


def transcribe_with_retry(post, mp3_path, key, minutes, tries=3, backoff=(5, 20, 60), sleep=time.sleep):
    """post(url, headers, data, files, timeout) -> response-like (status_code, text, json()). Retries 429 / 5xx / network errors
    up to `tries` times; refuses to start when the ElevenLabs budget would pass 90 %."""
    est = minutes * ELEVEN_USD_PER_MIN
    if not budget_ok('elevenlabs', est):
        raise BudgetStop(f'ElevenLabs budget: {ledger().get("elevenlabs", 0):.2f} + {est:.2f} USD would pass 90 % of the {CAPS["elevenlabs"]:.0f} USD cap')
    last = None
    attempts = 0
    for i in range(tries):
        attempts += 1
        try:
            with open(mp3_path, 'rb') as f:
                r = post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key': key},
                         data={'model_id': 'scribe_v2', 'diarize': 'true', 'num_speakers': '2', 'timestamps_granularity': 'word', 'tag_audio_events': 'true'},
                         files={'file': (Path(mp3_path).name, f, 'audio/mpeg')}, timeout=1800)
        except Exception as e:                      # network error
            last = f'network: {e}'
            sleep(backoff[min(i, len(backoff) - 1)]); continue
        if r.status_code == 200:
            spend('elevenlabs', est, f'scribe {Path(mp3_path).name} ({minutes:.0f} min)')
            return r.json()
        last = f'ElevenLabs {r.status_code}: {str(r.text)[:200]}'
        if r.status_code == 429 or r.status_code >= 500:
            sleep(backoff[min(i, len(backoff) - 1)]); continue
        break                                       # 4xx other than 429: do not retry
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
