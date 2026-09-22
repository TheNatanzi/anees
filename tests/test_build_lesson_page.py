import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_lesson_page as B

CHAT = """00:34:48.539,00:34:51.539
Amal Abusrour: Babse6
Btebse6
Btebse6i

00:36:43.396,00:36:46.396
Medi Natanzi: shu ya3ni: basa6?

00:37:01.489,00:37:04.489
Amal: Hasa6to
"""


def test_parse_chat_names_continuations_and_colons():
    lines = B.parse_chat(CHAT)
    assert [(c['t'], c['who'], c['text']) for c in lines] == [
        (2088, 'Amal', 'Babse6'), (2088, 'Amal', 'Btebse6'), (2088, 'Amal', 'Btebse6i'),
        (2203, 'Medi', 'shu ya3ni: basa6?'), (2221, 'Amal', 'Hasa6to')]


def row(t, who, *words):
    return {'timeline_start': t, 'timeline_end': t + 1, 'speaker_label': who,
            'items': [{'type': 'word', 'text': w} for w in words]}


def test_merge_orders_by_time_with_offset_and_speech_first_on_ties():
    rows = [row(10, 'Amal', 'marhaba'), row(20, 'Medi', 'ahlan')]
    chat = [{'t': 5, 'who': 'Amal', 'text': 'Babse6'}]
    merged = B.merge(rows, chat, offset=5)
    assert [(x['kind'], x['t']) for x in merged] == [('speech', 10), ('chat', 10), ('speech', 20)]
    assert B.merge(rows, chat, offset=-60)[0]['t'] == 0.0     # never before the lesson start


def test_render_escapes_text_and_seeks_audio():
    merged = B.merge([row(3725.5, 'Medi', '<b>', 'x')], [{'t': 1, 'who': 'Amal', 'text': 'a&b'}])
    page = B.render('2026-09-21', merged, minutes=62.1, words=2, note='n', audio='2026-09-21/audio/lesson.mp3')
    assert '<b>Medi</b>: &lt;b&gt; x</p>' in page and 'a&amp;b' in page
    assert 'data-t="3725.50"' in page and '<small>62:05</small>' in page
    assert 'transcript-context-review.js' in page
    assert 'id="lesson-audio"' in page and 'src="2026-09-21/audio/lesson.mp3"' in page
    assert '1 lines Amal typed in chat' in page
    assert 'lesson-audio' not in B.render('d', merged, minutes=1, words=1, note='n')


def test_name_clusters_uses_pitch_majority_not_arabic_share():
    import load_lesson as L
    clusters = ['s1'] * 10 + ['s0'] * 10
    pitch = ['Medi'] * 9 + ['?'] + ['Amal'] * 8 + ['Medi', '?']
    assert L.name_clusters(clusters, pitch) == ({'s1': 'Medi', 's0': 'Amal'}, 'diarization_named_by_pitch')
    # a mixed-up cluster is not named: its words keep their own pitch label
    names, basis = L.name_clusters(clusters, ['Medi'] * 10 + ['Amal', 'Medi'] * 5)
    assert names == {'s1': 'Medi'} and basis == 'pitch_estimate'
