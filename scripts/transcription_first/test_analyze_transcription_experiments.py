import unittest
import analyze_transcription_experiments as a


def transcript(items):
    return {"text": "", "words": [{"type": "word", "start": t, "end": t + .2, "text": text} for t, text in items]}


class AnalysisTest(unittest.TestCase):
    def test_arabic_not_punctuation_and_arabizi_not_english(self):
        result = a.surface_stats(transcript([(0, "ana"), (1, "yes"), (2, "مرحبا"), (3, "،"), (4, "um"), (5, "biz'a-")]))
        self.assertEqual(1, result["arabic_script_word_items"])
        self.assertEqual(2, result["legacy_arabic_block_word_items"])
        self.assertEqual(1, len(result["arabic_block_without_arabic_letters"]))
        self.assertEqual(2, result["english_lexicon_word_items"])
        self.assertEqual(1, result["filler_word_items"])
        self.assertEqual(1, result["visible_cutoff_word_items"])

    def test_offset_and_half_open_window(self):
        source = transcript([(0, "first"), (1, "second"), (2, "third")])
        self.assertEqual("second", a.text_words(a.select_items(source, 36, 37, offset=35)))

    def test_english_overlap_does_not_reuse_same_occurrence(self):
        baseline = transcript([(0, "yes"), (1, "yes"), (5, "word"), (6, "ana")])
        hypothesis = transcript([(0, "Yes."), (50, "word")])
        result = a.english_retention(baseline, hypothesis)
        self.assertEqual(3, result["reference_count"])
        self.assertEqual(2, result["global_multiset_overlap"])
        self.assertEqual(1, result["time_local_one_to_one_matches"])

    def test_sequence_exact_and_normalized_distinct(self):
        result = a.compare_sequences(transcript([(0, "Yes.")]), transcript([(0, "yes")]))
        self.assertFalse(result["raw_word_text_sequence_identical"])
        self.assertTrue(result["normalized_word_text_sequence_identical"])

    def test_events_not_counted_as_words_or_silence(self):
        t = transcript([(0, "one"), (20, "two")])
        t["words"].append({"type": "audio_event", "text": "[laughs]", "start": 1, "end": 10})
        result = a.surface_stats(t)
        self.assertEqual(2, result["word_items"])
        self.assertEqual(9, result["longest_audio_events"][0]["duration_s"])
        self.assertIn("not measured acoustic silence", result["gap_warning"])


if __name__ == "__main__":
    unittest.main()
