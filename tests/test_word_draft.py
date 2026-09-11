"""Draft usage must be source-bound, conservative and grading-neutral."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_word_draft import build


def fixture(texts, speaker='Medi'):
    items = [{'id': f'i{i}', 'type': 'word', 'text': text, 'local_start': i,
              'local_end': i+.4, 'timeline_start': i+.6} for i, text in enumerate(texts)]
    return {'status': 'unreviewed_asr', 'lesson': '2026-09-10',
            'sources': {'track': {'speaker_label': speaker, 'duration_s': 100, 'source_sha256': 'abc'}},
            'rows': [{'id': 'r0', 'source_id': 'track', 'speaker_label': speaker, 'items': items}]}


class DraftTests(unittest.TestCase):
    def test_only_medi_and_repetitions_not_mastery(self):
        vocab = [{'key': 'k', 'arabic': 'كلمة'}]
        self.assertEqual(build(fixture(['كلمة', 'كلمة']), vocab)['occurrence_count'], 2)
        self.assertEqual(build(fixture(['كلمة'], 'Amal'), vocab)['occurrence_count'], 0)

    def test_english_mixed_script_and_false_starts_are_not_matches(self):
        v = [{'key': 'k', 'arabic': 'كلمة'}]
        self.assertEqual(build(fixture(['word', 'the كلمة', 'كلمة-', 'صلاhto']), v)['occurrence_count'], 0)

    def test_collision_does_not_choose_meaning(self):
        v = [{'key': 'laugh', 'arabic': 'بضحك'}, {'key': 'make_laugh', 'arabic': 'بضحِّك'}]
        d = build(fixture(['بضحك']), v)
        self.assertEqual(d['word_count'], 0)
        self.assertEqual(d['ambiguous_spans_omitted'], 1)

    def test_longest_phrase_and_english_gap(self):
        v = [{'key': 'one', 'arabic': 'كل'}, {'key': 'phrase', 'arabic': 'كل اشي'}]
        self.assertEqual(set(build(fixture(['كل', 'اشي']), v)['words']), {'phrase'})
        self.assertNotIn('phrase', build(fixture(['كل', 'English', 'اشي']), v)['words'])
        d = fixture(['كل', 'اشي']);d['rows'][0]['items'][1]['local_start'] = 5
        d['rows'][0]['items'][1]['local_end'] = 5.4
        self.assertNotIn('phrase', build(d, v)['words'])

    def test_no_article_or_conjugation_inference(self):
        v = [{'key': 'today', 'arabic': 'اليوم'}, {'key': 'break', 'arabic': 'أنا بكسر'}]
        self.assertEqual(build(fixture(['يوم', 'بكسر']), v)['occurrence_count'], 0)

    def test_duplicate_source_span_not_counted_twice(self):
        d = fixture(['كلمة']);d['rows'].append(copy.deepcopy(d['rows'][0]))
        self.assertEqual(build(d, [{'key': 'k', 'arabic': 'كلمة'}])['occurrence_count'], 1)

    def test_inputs_immutable(self):
        d = fixture(['كلمة']);before = copy.deepcopy(d)
        build(d, [{'key': 'k', 'arabic': 'كلمة'}])
        self.assertEqual(d, before)

    def test_js_validation_is_display_only(self):
        js = (ROOT / 'docs/js/word-drafts.js').read_text(encoding='utf-8')
        test = r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const d=JSON.parse(fs.readFileSync('docs/data/lesson-word-drafts.json','utf8'));
const before=JSON.stringify(d);const good=AneesWordDrafts.valid(d);const l=AneesWordDrafts.latest(good);
assert.equal(l.date,'2026-09-10');assert.equal(l.word_count,70);assert.equal(l.occurrence_count,169);
assert.equal(JSON.stringify(d),before);assert.equal(AneesWordDrafts.word(l,'__proto__'),null);
assert(AneesWordDrafts.link(l,{row_id:'a:b'}).endsWith('#a%3Ab'));
const bad=JSON.parse(before);bad.lessons[0].occurrence_count++;assert.throws(()=>AneesWordDrafts.valid(bad));
const url=JSON.parse(before);url.lessons[0].transcript_url='javascript:alert(1)';assert.throws(()=>AneesWordDrafts.valid(url));
'''
        r = subprocess.run(['node'], input=js + '\n' + test, text=True, encoding='utf-8', capture_output=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('word_events', js)
        self.assertNotIn('word_stats', js)
        self.assertNotIn('PATCH', js)


if __name__ == '__main__':
    unittest.main()
