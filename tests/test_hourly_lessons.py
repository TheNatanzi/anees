import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import hourly_lessons as H
import load_lesson as L

DONE = [{'code': 'joining_call'}, {'code': 'done'}]


def bot(i, date=None, join='2026-09-21T20:35:16Z', status=DONE):
    return {'id': i, 'join_at': join, 'meeting_url': {'meeting_id': 'kht-vfaq-bxh', 'platform': 'google_meet'},
            'metadata': {'anees_lesson': date} if date else {}, 'status_changes': status}


def test_api_discovers_bots_missing_from_the_ledger():
    ledger = [{'bot_id': 'a', 'date': '2026-09-19', 't': '2026-09-19T14:15:55'}]
    new = H.merge_bots(ledger, [bot('a', '2026-09-19'), bot('b', '2026-09-21')])
    assert [(r['bot_id'], r['date'], r['meeting_url']) for r in new] == [('b', '2026-09-21', 'https://meet.google.com/kht-vfaq-bxh')]


def test_bot_date_falls_back_to_pacific_join_day():
    assert H.bot_date(bot('x', join='2026-09-22T03:10:00Z')) == '2026-09-21'


def touch(p, size=H.MIN_BYTES):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'wb') as f:
        f.truncate(size)
    return p


def test_both_drive_folder_styles_are_scanned(tmp_path):
    touch(tmp_path / 'Meet Recordings' / 'vzq-tryv-mdw (2026-08-25 14 27 GMT-7)')
    touch(tmp_path / 'Google Meet' / 'pki-dqkp-kyn - 2026 09 18 14 08 PDT' / 'pki-dqkp-kyn (2026-09-18 14 08 GMT-7)')
    touch(tmp_path / 'Google Meet' / 'pki-dqkp-kyn - 2026 09 18 14 08 PDT' / 'pki-dqkp-kyn (2026-09-18 14 08 GMT-7) - Chat Transcript', 10)
    touch(tmp_path / 'Google Meet' / 'x - 2026 09 19' / 'cuv-feor-sou (2026-09-19 14 08 GMT-7)', 10)      # too small
    found = [(c, d, h) for _, c, d, h in H.meet_recordings(tmp_path)]
    assert found == [('vzq-tryv-mdw', '2026-08-25', '1427'), ('pki-dqkp-kyn', '2026-09-18', '1408')]


def test_plan_tracks_beat_meet_loaded_dates_untouched_and_unfinished_bots_wait(tmp_path):
    ledger = [{'bot_id': 'old', 'date': '2026-09-19', 't': 'x'}]
    bots = [bot('old', '2026-09-19'), bot('new', '2026-09-21'), bot('live', '2026-09-23', status=[{'code': 'in_call_recording'}])]
    rec = lambda code, d: (tmp_path / f'{code} ({d} 14 08 GMT-7)', code, d, '1408')
    recordings = [rec('kht-vfaq-bxh', '2026-09-21'), rec('pki-dqkp-kyn', '2026-09-18'), rec('mqp-zwfh-wby', '2026-09-22'), rec('ctn-wxzy-oms', '2026-06-17')]
    new_rows, todo = H.plan(ledger, bots, recordings, loaded_dates={'2026-09-19'}, raw=tmp_path,
                            decided={'mqp-zwfh-wby (2026-09-22 14 08 GMT-7)': 'not a lesson'})
    assert {r['bot_id'] for r in new_rows} == {'new', 'live'}
    assert [(t['kind'], t['date']) for t in todo] == [('tracks', '2026-09-21'), ('meet', '2026-09-18')]


def test_host_account_is_never_a_speaker():
    assert L._person('Ray Adib') is None and L._person('Amal Abusrour') == 'Amal' and L._person('Medi Natanzi') == 'Medi'
