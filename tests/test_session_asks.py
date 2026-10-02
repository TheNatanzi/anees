"""Rule PR-08 (report M10): every message Medi types in a session - including the ones typed mid-run - is ticked before
the agent reports done. The asks are read from the transcript, never from the agent's memory of them."""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import session_asks as S


def L(**j):
    return json.dumps(j)


TRANSCRIPT = [
    L(type='user', uuid='u1', timestamp='2026-10-02T07:18:30Z', origin={'kind': 'human'},
      message={'role': 'user', 'content': 'build the lesson alerts'}),
    L(type='assistant', uuid='a1', message={'content': [{'type': 'text', 'text': 'on it'}]}),
    L(type='user', uuid='t1', message={'content': [{'type': 'tool_result', 'content': 'ok'}]}),            # tool output
    L(type='attachment', uuid='q1', timestamp='2026-10-02T07:25:26Z',                                      # typed mid-run
      attachment={'type': 'queued_command', 'prompt': 'lets also upload todays lesson', 'source_uuid': 's1',
                  'origin': {'kind': 'human'}}),
    L(type='attachment', uuid='q2', timestamp='2026-10-02T07:26:00Z',                                      # an agent, not Medi
      attachment={'type': 'queued_command', 'prompt': '<task-notification>done</task-notification>',
                  'origin': {'kind': 'task-notification'}}),
    L(type='user', uuid='m1', isMeta=True, message={'content': 'injected context'}),
    L(type='user', uuid='n1', origin={'kind': 'task-notification'}, message={'content': '<task-notification>x'}),
    L(type='attachment', uuid='q3', timestamp='2026-10-02T07:28:21Z',
      attachment={'type': 'queued_command', 'prompt': [{'type': 'image', 'source': {'data': 'iVBOR'}},
                                                       {'type': 'text', 'text': 'get rid of this block'}],
                  'source_uuid': 's3', 'origin': {'kind': 'human'}}),
]


def test_PR08_asks_come_from_the_transcript_including_mid_run_messages():
    """Rule PR-08: Medi's typed messages AND the ones queued while the agent worked; tool output, meta lines, task
    notifications and other agents are not asks."""
    items = S.asks(TRANSCRIPT)
    assert [(i['text'], i['mid_run']) for i in items] == [
        ('build the lesson alerts', False), ('lets also upload todays lesson', True), ('[image] get rid of this block', True)]


def test_PR08_check_fails_while_a_mid_run_ask_is_unticked(tmp_path):
    """Rule PR-08, planted: the agent ticked the first ask and reported done; the message typed mid-run was dropped."""
    items = S.asks(TRANSCRIPT)
    doc = S.tick({'ticks': {}}, items, [1], 'done: commit 2711ec1')
    ok, lines = S.check(items, doc)
    assert not ok and any('#2' in l and 'typed mid-run' in l and 'upload todays lesson' in l for l in lines)
    doc = S.tick(doc, items, S.numbers(['2-3'], len(items)), 'needs Medi: which lesson', done=False)
    ok, lines = S.check(items, doc)
    assert ok and any(l.startswith('NOT DONE #2') for l in lines)       # ticked, and the report must name it


def test_PR08_a_tick_needs_a_note_and_the_cli_exits_1_until_all_ticked(tmp_path):
    """Rule PR-08: a bare tick is refused (no 'tick all'); the command line check is what the agent runs before 'done'."""
    import pytest
    items = S.asks(TRANSCRIPT)
    with pytest.raises(SystemExit):
        S.tick({}, items, [1], '  ')
    tr = tmp_path / 'abc12345-x.jsonl'
    tr.write_text('\n'.join(TRANSCRIPT), encoding='utf-8')
    lf = tmp_path / 'list.json'
    base = ['--transcript', str(tr), '--list-file', str(lf)]
    assert S.main(['check', *base]) == 1
    assert S.main(['tick', '1-3', '--note', 'done', *base]) == 0
    assert S.main(['check', *base]) == 0
