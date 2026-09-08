"""No providers, filesystem writes, lesson rebuilds, or real human labels."""
import copy
from html.parser import HTMLParser
import unittest

from transcript_display import annotate_runs, render_display_item, render_spelling_word, nonstandard_latin_warning, StaleDisplayRule


def fixture():
    return [
        {'s': 117, 'e': 120, 'spk': 'Medi', 'items': [{'pause': .3}, {'w': 'Ɣama,'}, {'w': 'ōinti.'}, {'w': 'I'}, {'w': 'I'}, {'w': 'أنا'}]},
        {'s': 121, 'e': 124, 'spk': 'Amal', 'items': [{'w': 'English'}, {'w': 'وكمان'}, {'w': 'فارسی'}]},
        {'s': 150, 'e': 152, 'spk': 'Medi', 'items': [{'w': 'Ɣama'}, {'w': 'yebkedu.', 'ok': True}]},
    ]


def restored(runs):
    result = copy.deepcopy(runs)
    for run in result:
        run['items'] = [original for item in run['items'] for original in
                        (item['display']['source_items'] if 'display' in item else [item])]
    return result


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class DisplayTests(unittest.TestCase):
    def test_approved_spelling_preserves_case_source_and_punctuation(self):
        for text in ['aganee', 'Aganee.', 'AGANEE?', '“aganee”،', '(aganee)', 'aganee…']:
            result = render_spelling_word(text)
            self.assertIsNotNone(result, text)
            parser = Tags()
            parser.feed(result)
            self.assertEqual(parser.tags[0][1]['data-source'], text)
            self.assertIn('a8aani', parser.tags[0][1]['title'])
            self.assertIn('pronunciation not assessed', parser.tags[0][1]['title'])
            self.assertIn('<bdi lang="ar" dir="rtl">أغاني</bdi>', result)

    def test_spelling_does_not_expand_to_other_words_or_false_starts(self):
        for text in ['aganee-', '-aganee', 'aganee-aganee', 'preaganee', 'aganees',
                     'aganee2', "aganee's", 'agane', 'agaani', 'guitar', 'great',
                     'أغاني', 'أغنية', 'اغاني', 'a8aani', 'aganee aganee', '<aganee>',
                     '<script>aganee</script>', 'aganee\n', ' aganee']:
            self.assertIsNone(render_spelling_word(text), text)

    def test_approved_spelling_is_reused_in_future_lesson_display_only(self):
        from lesson_pipeline import render
        from lesson_text import run_text
        runs = [{'spk': 'Medi', 's': 10, 'e': 13, 'items': [
            {'w': 'I'}, {'w': 'said'}, {'w': 'aganee'}, {'w': 'aganee.'}, {'pause': .3}]}]
        before = copy.deepcopy(runs)
        summary = dict(date='2026-09-09', minutes=1, words=4, medi_arabic_words=0,
                       confirmations=0, medi_pauses=1, lesson_start=0, lesson_end=60)
        page = render(runs, summary)
        self.assertEqual(runs, before)
        self.assertEqual(run_text(runs[0]), 'I said aganee aganee. (pause 0.3s)')
        self.assertEqual(page.count('class="transcript-spelling"'), 2)
        self.assertIn('I said', page)
        self.assertIn('(pause 0.3s)', page)
        self.assertIn('Approved spelling rules applied to 2 words', page)

    def test_spelling_rule_survives_stale_unrelated_unclear_phrase_notes(self):
        from lesson_pipeline import render
        runs = [{'spk': 'Medi', 's': 10, 'e': 11, 'items': [{'w': 'aganee'}]}]
        summary = dict(date='2026-09-05', minutes=1, words=1, medi_arabic_words=0,
                       confirmations=0, medi_pauses=0, lesson_start=0, lesson_end=60)
        page = render(runs, summary)
        self.assertIn('No old unclear-phrase replacements were applied', page)
        self.assertIn('<bdi lang="ar" dir="rtl">أغاني</bdi>', page)
        self.assertEqual(runs[0]['items'][0]['w'], 'aganee')

    def test_seed_spans_are_grouped_without_modifying_source(self):
        original = fixture()
        before = copy.deepcopy(original)
        result = annotate_runs(original, '2026-09-05')
        self.assertEqual(original, before)
        self.assertEqual(restored(result), original)
        self.assertEqual(result[0]['items'][1]['display']['source_text'], 'Ɣama, ōinti.')
        self.assertEqual(result[2]['items'][0]['display']['source_text'], 'Ɣama yebkedu.')
        self.assertEqual(result[0]['items'][1]['display']['source_span'], {'run_index': 0, 'start_item': 1, 'end_item_exclusive': 3})

    def test_timestamps_speakers_pauses_repeats_and_code_switches_unchanged(self):
        original = fixture()
        result = annotate_runs(original, '2026-09-05')
        for left, right in zip(original, result):
            self.assertEqual({k: v for k, v in left.items() if k != 'items'}, {k: v for k, v in right.items() if k != 'items'})
        self.assertEqual(result[0]['items'][0], {'pause': .3})
        self.assertEqual(result[0]['items'][2:], [{'w': 'I'}, {'w': 'I'}, {'w': 'أنا'}])
        self.assertEqual(result[1], original[1])

    def test_deep_copy_does_not_share_mutable_source_items(self):
        original = fixture()
        result = annotate_runs(original, '2026-09-05')
        result[0]['items'][1]['display']['source_items'][0]['w'] = 'changed copy'
        result[1]['items'][0]['w'] = 'changed ordinary copy'
        self.assertEqual(original, fixture())

    def test_other_lessons_are_untouched_deep_copies(self):
        original = fixture()
        result = annotate_runs(original, '2026-09-06')
        self.assertEqual(result, original)
        self.assertIsNot(result, original)

    def test_missing_or_changed_source_fails_before_any_mutation(self):
        for changed in ['Gamma,', 'Ɣama', 'Ɣama, ']:
            original = fixture()
            original[0]['items'][1]['w'] = changed
            before = copy.deepcopy(original)
            with self.assertRaisesRegex(StaleDisplayRule, 'found 0'):
                annotate_runs(original, '2026-09-05')
            self.assertEqual(original, before)

    def test_nonunique_source_fails_instead_of_selecting_first(self):
        original = fixture()
        original.append(copy.deepcopy(original[0]))
        with self.assertRaisesRegex(StaleDisplayRule, 'found 2'):
            annotate_runs(original, '2026-09-05')

    def test_phrase_cannot_cross_pause_or_speaker_boundary(self):
        original = fixture()
        original[0]['items'].insert(2, {'pause': .5})
        with self.assertRaises(StaleDisplayRule):
            annotate_runs(original, '2026-09-05')
        with self.assertRaises(StaleDisplayRule):
            annotate_runs([{'spk': 'Medi', 'items': [{'w': 'Ɣama,'}]}, {'spk': 'Amal', 'items': [{'w': 'ōinti.'}]}],
                          '2026-09-05', rules=[{'id': 'one', 'source_text': 'Ɣama, ōinti.', 'expected_occurrences': 1}])

    def test_overlapping_rules_rejected(self):
        with self.assertRaisesRegex(StaleDisplayRule, 'overlap'):
            annotate_runs(fixture(), '2026-09-05', rules=[
                {'id': 'a', 'source_text': 'Ɣama, ōinti.', 'expected_occurrences': 1},
                {'id': 'b', 'source_text': 'ōinti.', 'expected_occurrences': 1}])

    def test_expected_count_is_explicit_and_type_checked(self):
        for count in [0, -1, True, '1']:
            with self.assertRaises(ValueError):
                annotate_runs(fixture(), '2026-09-05', rules=[{'id': 'a', 'source_text': 'I', 'expected_occurrences': count}])

    def test_html_is_escaped_and_no_guessed_arabic_or_correctness_is_added(self):
        text = '<script>alert(1)</script>'
        runs = [{'spk': 'Medi', 'items': [{'w': text, 'ok': True}]}]
        item = annotate_runs(runs, 'synthetic', rules=[{'id': 'x', 'source_text': text, 'expected_occurrences': 1}])[0]['items'][0]
        fragments = render_display_item(item)
        self.assertNotIn('<details', fragments['inline_html'])
        self.assertTrue(fragments['details_html'].startswith('<details'))
        rendered = fragments['inline_html'] + fragments['details_html']
        parser = Tags()
        parser.feed(rendered)
        self.assertEqual([tag for tag, attrs in parser.tags], ['span', 'details', 'summary', 'span'])
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', rendered)
        self.assertIn('Unclear — needs audio review', rendered)
        self.assertNotIn('class="ok"', rendered)
        self.assertNotIn(' open', rendered)
        self.assertNotIn('✓', rendered)

    def test_renderer_rejects_mismatched_preserved_source(self):
        item = annotate_runs(fixture(), '2026-09-05')[0]['items'][1]
        item['display']['source_text'] = 'different'
        with self.assertRaises(StaleDisplayRule):
            render_display_item(item)

    def test_ordinary_items_are_left_to_existing_renderer(self):
        self.assertIsNone(render_display_item({'w': 'I'}))
        self.assertIsNone(render_display_item({'pause': .4}))

    def test_warning_is_unicode_based_not_ascii_ignorecase(self):
        for text in ['I', 'i', 'I am fine.', 'English أنا فارسی', '123', 'I’m here — okay.']:
            self.assertIsNone(nonstandard_latin_warning(text), text)
        for text in ['Ɣama, ōinti.', 'ʕ', 'ʔ', 'café', 'İ']:
            self.assertIsNotNone(nonstandard_latin_warning(text), text)
        # A warning does not classify language or perform transliteration.
        self.assertIn('language and wording are not confirmed', nonstandard_latin_warning('Ɣama'))


if __name__ == '__main__':
    unittest.main()
