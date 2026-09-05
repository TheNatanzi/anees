"""Recall.ai meeting bot: one audio file per participant from a Google Meet (Medi joins from his phone, wc@adibs.com hosts).

  python scripts/recall_bot.py join  "https://meet.google.com/xxx-yyyy-zzz" [--name "Anees notes"] [--date 2026-09-08]
  python scripts/recall_bot.py fetch <bot_id> [--date 2026-09-08]        # after the call: download data/lessons/<date>/tracks/<participant>.<ext>
  python scripts/recall_bot.py status <bot_id>

Needs RECALL_API_KEY (User env, clipboard method) and RECALL_REGION (default us-west-2). Never sends anything to Amal; the host
account admits the bot once (or "Quick access" lets it in). Costs ~$0.50/h + $0.10/h for the 4-core bot the per-participant
audio needs. Files are kept on Recall for 7 days; here forever. Nothing is uploaded to any other provider by this script."""
import argparse, datetime, io, json, sys, time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anees_env as E

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / 'data' / 'lessons'
KEY = E.env('RECALL_API_KEY')
REGION = E.env('RECALL_REGION', 'us-west-2')
BASE = f'https://{REGION}.recall.ai/api/v1'
LEDGER = LESSONS / 'recall_bots.json'


def _h():
    if not KEY:
        sys.exit('RECALL_API_KEY missing (User env). Nothing was sent.')
    return {'Authorization': f'Token {KEY}', 'Content-Type': 'application/json', 'Accept': 'application/json'}


def _ledger(entry=None):
    hist = json.load(io.open(LEDGER, encoding='utf-8')) if LEDGER.exists() else []
    if entry:
        hist.append(entry); LEDGER.parent.mkdir(parents=True, exist_ok=True)
        io.open(LEDGER, 'w', encoding='utf-8').write(json.dumps(hist, ensure_ascii=False, indent=1))
    return hist


def join(meeting_url, name='Anees notes', date=None, session=requests):
    """Create the bot. audio_separate_mp3 = one file per participant, decided by Recall from Meet's own per-person streams.
    variant 4-core is what Recall recommends for separate audio."""
    body = {'meeting_url': meeting_url, 'bot_name': name,
            'recording_config': {'audio_separate_mp3': {}, 'audio_mixed_mp3': {}},
            'variant': {'google_meet': 'web_4_core'},
            'metadata': {'anees_lesson': date or datetime.date.today().isoformat()}}
    r = session.post(f'{BASE}/bot', headers=_h(), data=json.dumps(body), timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f'Recall create bot {r.status_code}: {r.text[:300]}')
    bot = r.json()
    _ledger({'t': datetime.datetime.now().isoformat(timespec='seconds'), 'bot_id': bot['id'], 'date': body['metadata']['anees_lesson'], 'meeting_url': meeting_url})
    return bot


def status(bot_id, session=requests):
    r = session.get(f'{BASE}/bot/{bot_id}', headers=_h(), timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f'Recall get bot {r.status_code}: {r.text[:300]}')
    b = r.json()
    codes = [s.get('code') for s in b.get('status_changes', [])]
    return b, (codes[-1] if codes else None)


def fetch(bot_id, date=None, session=requests, wait_minutes=30, sleep=time.sleep):
    """Wait for the bot to finish, then download one file per participant into data/lessons/<date>/tracks/."""
    deadline = time.time() + wait_minutes * 60
    while True:
        b, code = status(bot_id, session)
        if code in ('done', 'fatal', 'media_expired') or not b.get('recordings') and code in ('call_ended',):
            break
        if time.time() > deadline:
            raise RuntimeError(f'bot {bot_id} still {code} after {wait_minutes} min')
        sleep(30)
    if code != 'done':
        raise RuntimeError(f'bot {bot_id} ended with status {code}')
    date = date or (b.get('metadata') or {}).get('anees_lesson') or datetime.date.today().isoformat()
    out = LESSONS / date / 'tracks'
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for rec in b.get('recordings', []):
        r = session.get(f'{BASE}/audio_separate', headers=_h(), params={'recording_id': rec['id']}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f'Recall audio_separate {r.status_code}: {r.text[:300]}')
        for part in r.json().get('results', []):
            url = (part.get('data') or {}).get('download_url')
            if not url:
                continue
            p = part.get('participant') or {}
            who = (p.get('name') or f"participant-{p.get('id', 'x')}").strip().replace(' ', '_')
            ext = 'mp3' if part.get('format') in (None, 'mp3') else part.get('format')
            path = out / f'{who}.{ext}'
            with session.get(url, stream=True, timeout=600) as d:
                d.raise_for_status()
                with open(path, 'wb') as f:
                    for chunk in d.iter_content(1 << 20):
                        f.write(chunk)
            saved.append({'participant': p.get('name'), 'is_host': p.get('is_host'), 'file': str(path), 'bytes': path.stat().st_size})
    io.open(out / 'tracks.json', 'w', encoding='utf-8').write(json.dumps({'bot_id': bot_id, 'date': date, 'tracks': saved}, ensure_ascii=False, indent=1))
    return saved


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    j = sub.add_parser('join'); j.add_argument('meeting_url'); j.add_argument('--name', default='Anees notes'); j.add_argument('--date')
    f = sub.add_parser('fetch'); f.add_argument('bot_id'); f.add_argument('--date')
    s = sub.add_parser('status'); s.add_argument('bot_id')
    a = ap.parse_args()
    if a.cmd == 'join':
        b = join(a.meeting_url, a.name, a.date); print('bot', b['id'], 'created; the host admits "%s" when it knocks' % a.name)
    elif a.cmd == 'fetch':
        for t in fetch(a.bot_id, a.date):
            print(t)
    elif a.cmd == 'status':
        b, code = status(a.bot_id); print(code, json.dumps(b.get('status_changes', [])[-3:], indent=1))
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
