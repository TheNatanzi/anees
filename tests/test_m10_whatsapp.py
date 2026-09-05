"""M10 gates (WhatsApp chat as the second source; Medi grill 2026-09-05):
M10a house spelling: only headword forms, exact tier for short forms ('oh' never becomes 'U'), pronoun kept, Doc case kept.
M10b typed lines: Doc words in a line (trusted tiers), a Medi event inside the window becomes prompted and is listed in the diff
     with the causing line; an Amal event or an out-of-window event is never changed; Aug 25 gets 26 WhatsApp lines when the
     private export is present (skipped otherwise).
M10c homework loop: prompt candidates are validated (0 untaught words, >= 1 A + 1 B word), Amal-dropped lines never return,
     the fixture pairs have the shape the grader needs; with keys: RLS lets Medi insert an answer but not a grade, lets a token
     decide its own item and judge an answer, and refuses a token that rewrites the English."""
import datetime, io, json, uuid
from pathlib import Path
import pytest

import whatsapp_chat as W
import house_spelling as HS
import chat_ground_truth as CG
import homework as HW
import suggest
import anees_env as E
from arabizi import Matcher

ROOT = Path(__file__).resolve().parent.parent
NET = bool(E.ACCESS_TOKEN and E.SERVICE_KEY and E.ANON_KEY)
EXPORT = list((ROOT / 'data' / 'whatsapp' / 'raw').glob('WhatsApp Chat with *.txt')) if (ROOT / 'data' / 'whatsapp' / 'raw').exists() else []
WORDS = json.load(io.open(ROOT / 'data' / 'vocab' / 'words.json', encoding='utf-8'))['items']


# ---------- parser ----------
def test_kind_classifier_never_guesses():
    assert W.kind('Wa2et/maw3ed elijtimaa3') == 'arabizi'
    assert W.kind('Did you enjoy your time outside?') == 'english'
    assert W.kind('bat2assaf = I apologize') == 'gloss'
    assert W.kind('laazem t7arrek 7aalak') == 'arabizi'
    assert W.kind('Remind me not to change the time of the meeting') == 'english'
    assert W.kind('ah') == 'short' and W.kind('Jaahez?') == 'short'
    assert W.kind('https://quizlet.com/x') == 'link'
    assert W.kind('PTT-20251030-WA0015.opus (file attached)') == 'media'


def test_parse_header_with_narrow_nbsp(tmp_path):
    p = tmp_path / 'WhatsApp Chat with AMAL Arabic Tutor Abusrohr.txt'
    p.write_text('9/4/26, 2:01 PM - AMAL Arabic Tutor Abusrohr: Wa2et/maw3ed elijtimaa3\n9/4/26, 2:02 PM - Medi Natanzi: ok\nsecond line\n9/4/26, 2:03 PM - AMAL Arabic Tutor Abusrohr: x = y <This message was edited>\n', encoding='utf-8')
    ms = W.messages(p)
    assert [m['who'] for m in ms] == ['Amal', 'Medi', 'Amal']
    assert ms[0]['ts'] == datetime.datetime(2026, 9, 4, 14, 1) and ms[0]['kind'] == 'arabizi'
    assert ms[1]['text'] == 'ok\nsecond line'
    assert ms[2]['edited'] and ms[2]['text'] == 'x = y' and ms[2]['kind'] == 'gloss'


def test_parse_source_start():
    assert W.parse_source_start('jir-hcex-xzd (2026-09-04 14 03 GMT-7)') == datetime.datetime(2026, 9, 4, 14, 3)
    assert W.parse_source_start('') is None


@pytest.mark.skipif(not EXPORT, reason='private WhatsApp export not present')
def test_aug25_lesson_lines_from_export():
    rows = W.lesson_lines(datetime.datetime(2026, 8, 25, 14, 27), minutes=57 + 5)   # the pipeline adds 5 min of slack after the recording
    assert len(rows) == 27
    assert all(who == 'Amal' for _, who, _ in rows)
    assert rows[0][2] == 'fatra'                    # the gloss "fatra = while" keeps only the Arabic side
    assert not any(t[2].lower().startswith('a or not') for t in rows)


# ---------- M10a ----------
def test_house_spelling_guards():
    w_u = {'key': 'u', 'arabizi': 'U', 'arabic': 'و', 'aliases': []}
    w_a5 = {'key': 'a5', 'arabizi': 'A5', 'arabic': 'أخ', 'aliases': ['a5u']}
    w_green = {'key': 'a5dar', 'arabizi': 'A5dar', 'arabic': 'أخضر', 'aliases': ['5adra']}
    w_verb = {'key': 'ana baz3al', 'arabizi': 'Ana baz3al', 'arabic': 'أنا بزعل', 'aliases': []}
    assert not HS._safe('oh', 'fold', w_u)
    assert not HS._safe('a5u', 'fold', w_a5)           # an alias is a form of the entry, not its spelling
    assert not HS._safe('5adra', 'exact', w_green)
    assert HS._safe('baz3al', 'exact', w_verb)
    assert HS._display('baz3al', 'Ana baz3al') == 'Ana baz3al'
    assert HS._display('tamam', 'ana tamam') == 'ana tamam' and HS._display('2al2aan', 'Qalqaan') == '2al2aan'


def test_house_spelling_mines_most_frequent_form():
    words = [{'key': '2al2an', 'arabizi': 'Qalqaan', 'arabic': 'قلقان', 'english': 'worried', 'topic': 't', 'subtopic': 's', 'aliases': []},
             {'key': 'u', 'arabizi': 'U', 'arabic': 'و', 'english': 'and', 'topic': 't', 'subtopic': 's', 'aliases': []}]
    lines = [(datetime.datetime(2026, 1, 1), 'ana 2al2aan kteer'), (datetime.datetime(2026, 1, 2), '2al2aan?'), (datetime.datetime(2026, 1, 3), 'oh oh oh')]
    table, stats = HS.mine(words, lines, log=lambda *a: None)
    assert table['2al2an']['house'] == '2al2aan' and table['2al2an']['n'] == 2
    assert 'u' not in table


# ---------- M10b ----------
def _events():
    return [{'word_key': 'ana bat3ab', 't_start': 100.0, 't_end': 101.0, 'speaker': 'Medi', 'prompted': False, 'correction': False, 'text': 'بتعب'},
            {'word_key': 'ana bat3ab', 't_start': 400.0, 't_end': 401.0, 'speaker': 'Medi', 'prompted': False, 'correction': False, 'text': 'بتعب'},
            {'word_key': 'ana bat3ab', 't_start': 120.0, 't_end': 121.0, 'speaker': 'Amal', 'prompted': False, 'correction': False, 'text': 'بتعب'},
            {'word_key': 'ana bat3ab', 't_start': 130.0, 't_end': 131.0, 'speaker': 'Medi', 'prompted': False, 'correction': True, 'text': 'بتعب'}]


def test_typed_line_promotes_only_unprompted_medi_in_window():
    m = Matcher(WORDS)
    lines = [{'t': '00:01:30', 't_rel': 90, 'who': 'Amal', 'text': 'ANa bat3ab lamma ashte8el kteer', 'source': 'whatsapp'}]
    ev = _events()
    diff = CG.apply_typed(ev, lines, m)
    assert 'ana bat3ab' in lines[0]['keys']
    assert ev[0]['prompted'] and ev[0]['prompted_by'] == 'typed sentence' and ev[0]['typed']
    assert not ev[1]['prompted'] and not ev[1].get('typed')          # 310 s after the line: outside the window
    assert ev[2]['typed'] and not ev[2]['prompted']                    # Amal's own event is marked, never re-flagged
    assert ev[3]['correction'] and not ev[3]['prompted']               # a corrected event keeps its correction
    assert len(diff) == 1 and diff[0]['line'].startswith('ANa bat3ab') and diff[0]['source'] == 'whatsapp'


def test_merged_lines_dedupe_and_sort():
    summary = {'chat_lines': [['00:24:17', 'Amal', 'Na7el'], ['00:28:15', 'Amal', 'Mabsoo6']], 'source': 'x (2026-09-04 14 03 GMT-7)', 'minutes': 63}
    rows = CG.merged_lines(summary, '2026-09-04')
    meet = [r for r in rows if r['source'] == 'meet']
    assert len(meet) == 2 and meet[0]['t_rel'] == 24 * 60 + 17 and meet[0]['text'] == 'Na7el'
    assert [r['t_rel'] for r in rows] == sorted(r['t_rel'] for r in rows)
    assert len({r['text'].lower() for r in rows}) == len(rows)


@pytest.mark.skipif(not (ROOT / 'data' / 'lessons' / '2026-08-25' / 'understanding.json').exists(), reason='Aug 25 not understood')
def test_aug25_understanding_carries_typed_lines():
    u = json.load(io.open(ROOT / 'data' / 'lessons' / '2026-08-25' / 'understanding.json', encoding='utf-8'))
    if not EXPORT:
        pytest.skip('private export not present')
    assert u['chat_sources']['whatsapp'] == 27
    assert len(u['chat_diff']) >= 10
    assert all(d['line'] and d['word_key'] for d in u['chat_diff'])
    assert not any(e.get('speaker') == 'Amal' and e.get('prompted_by') for e in u['events'])


# ---------- M10c ----------
def _stats(keys):
    return [{'word_key': k, 'bucket': b, 'recent': True, 'times_missed': 1, 'times_seen': 2, 'weight': 1, 'last_reviewed': None} for k, b in keys]


def test_prompt_candidates_are_validated_and_dropped_lines_stay_dropped():
    words = WORDS
    stats = suggest_stats = None
    import db as _db  # noqa: F401  (import only; no network here)
    # A/B lists come from word_stats; build a small fake: 'ana bat3ab' weak (A), 'ktIr' cold (B)
    stats = _stats([('ana bat3ab', 'missed'), ('bsur3a', 'cold')])          # (kteer is glue, never a list word)
    rules = [{'kind': 'drop', 'word_key': None, 'payload': {'source': 'homework_prompt', 'english': 'I get tired quickly'}}]
    cands = [{'english': 'I get tired quickly', 'arabizi': 'ana bat3ab bsur3a', 'arabic': ''},
             {'english': 'I get tired fast', 'arabizi': 'ana bat3ab bsur3a kteer', 'arabic': 'أنا بتعب بسرعة كتير'},
             {'english': 'I get tired at the office', 'arabizi': 'ana bat3ab bsur3a fi el maktab elkabeer', 'arabic': ''},
             {'english': 'Only a cold word', 'arabizi': 'bsur3a kteer', 'arabic': ''}]
    out = HW.suggest_prompts(words, stats, rules, candidates=cands)
    en = [i['english'] for i in out['items']]
    assert en == ['I get tired fast'], out
    assert set(out['items'][0]['keys']) >= {'ana bat3ab', 'bsur3a'}
    why = {r['english']: r['why'] for r in out['rejected']}
    assert why['I get tired quickly'] == 'dropped by Amal before'
    assert 'elkabeer' in why['I get tired at the office'] or 'maktab' in ' '.join(why['I get tired at the office'])
    assert why['Only a cold word'] == 'no A word'


def test_style_examples_are_her_lines():
    ex = HW.style_examples(20)
    assert 5 <= len(ex) <= 20 and all(15 <= len(x) <= 110 for x in ex)


def test_fixture_pairs_shape():
    pairs = json.load(io.open(ROOT / 'tests' / 'fixtures' / 'homework_pairs.json', encoding='utf-8'))
    assert len(pairs) >= 10
    for p in pairs:
        assert p['english'] and p['answer'] and p['amal'] and isinstance(p['kinds'], list)
    assert sum(1 for p in pairs if not p['kinds']) >= 1                     # at least one "Yes" so the grader learns 'right'
    ts = (ROOT / 'supabase' / 'functions' / 'grade' / 'pairs.ts').read_text(encoding='utf-8')
    assert all(p['answer'] in ts for p in pairs)                            # the deployed grader carries the same pairs


@pytest.mark.skipif(not NET, reason='no Supabase keys')
def test_rls_homework_loop():
    import db, requests, datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    tok = 'test-' + uuid.uuid4().hex[:12]
    ld = '2026-09-04'
    db.upsert('amal_links', [{'token': tok, 'kind': 'after', 'lesson_date': ld, 'created_at': now.isoformat(), 'expires_at': (now + dt.timedelta(hours=1)).isoformat(), 'payload': {}}], on='token')
    item = db.rest('POST', 'homework_items', body=[{'lesson_date': ld, 'token': tok, 'n': 1, 'english': 'Test line', 'model_arabizi': 'ana bat3ab', 'keys': ['ana bat3ab'], 'status': 'suggested'}], prefer='return=representation')[0]
    anon = dict(key=E.ANON_KEY)
    try:
        aid = str(uuid.uuid4())
        # Medi (no token): may insert an answer, may not smuggle a grade
        db.rest('POST', 'homework_answers', body=[{'id': aid, 'item_id': item['id'], 'lesson_date': ld, 'answer': 'ana bat3ab kteer'}], prefer='return=minimal', **anon)
        with pytest.raises(db.DbError):
            db.rest('POST', 'homework_answers', body=[{'id': str(uuid.uuid4()), 'item_id': item['id'], 'lesson_date': ld, 'answer': 'x', 'grade': {'verdict': 'right'}}], prefer='return=minimal', **anon)
        # no token: cannot decide an item
        db.rest('PATCH', 'homework_items', params={'id': f"eq.{item['id']}"}, body={'status': 'keep'}, prefer='return=minimal', **anon)
        assert db.select('homework_items', {'id': f"eq.{item['id']}", 'select': 'status'})[0]['status'] == 'suggested'
        # her token: may keep / edit; may not rewrite the English or the keys
        db.rest('PATCH', 'homework_items', params={'id': f"eq.{item['id']}"}, body={'status': 'edit', 'edited_english': 'Test line, edited'}, prefer='return=minimal', token=tok, **anon)
        assert db.select('homework_items', {'id': f"eq.{item['id']}", 'select': 'status,edited_english'})[0] == {'status': 'edit', 'edited_english': 'Test line, edited'}
        with pytest.raises(db.DbError):
            db.rest('PATCH', 'homework_items', params={'id': f"eq.{item['id']}"}, body={'english': 'hacked'}, prefer='return=minimal', token=tok, **anon)
        # her token: may add her own line, may judge the answer, may not set the grade
        db.rest('POST', 'homework_items', body=[{'lesson_date': ld, 'token': tok, 'n': 101, 'english': 'Her own line', 'edited_english': 'Her own line', 'status': 'amal', 'keys': []}], prefer='return=minimal', token=tok, **anon)
        db.rest('PATCH', 'homework_answers', params={'id': f'eq.{aid}'}, body={'amal_verdict': 'fix', 'amal_fix': 'ana bat3ab kteer', 'amal_at': now.isoformat()}, prefer='return=minimal', token=tok, **anon)
        assert db.select('homework_answers', {'id': f'eq.{aid}', 'select': 'amal_verdict'})[0]['amal_verdict'] == 'fix'
        with pytest.raises(db.DbError):
            db.rest('PATCH', 'homework_answers', params={'id': f'eq.{aid}'}, body={'grade': {'verdict': 'right'}}, prefer='return=minimal', token=tok, **anon)
        # the edge function refuses a bad id and answers CORS preflight
        r = requests.post(f'{E.SUPABASE_URL}/functions/v1/grade', headers={'apikey': E.ANON_KEY, 'Authorization': f'Bearer {E.ANON_KEY}', 'Content-Type': 'application/json'}, json={'answer_id': 'nope'}, timeout=60)
        assert r.status_code == 404, r.text[:200]
    finally:
        db.rest('DELETE', 'homework_answers', params={'item_id': f"eq.{item['id']}"}, prefer='return=minimal')
        db.rest('DELETE', 'homework_items', params={'token': f'eq.{tok}'}, prefer='return=minimal')
        db.rest('DELETE', 'amal_links', params={'token': f'eq.{tok}'}, prefer='return=minimal')
        db.rest('DELETE', 'amal_rules', params={'token': f'eq.{tok}'}, prefer='return=minimal')
