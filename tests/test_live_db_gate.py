"""The live-database gate (tests/conftest.py, audit 2026-09-29): tests that write to Medi's live Supabase data are
skipped unless ANEES_E2E_LIVE=1. Before the gate, test_m5_cards / test_m4_after ran in every full pytest run."""
import importlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


def _fn(mod, name):
    return getattr(importlib.import_module(mod), name)


def test_known_live_writers_are_gated():
    import conftest
    for mod, name in [("test_m5_cards", "test_flip_toggle_shuffle_replay_end_to_end"),
                      ("test_m5_cards", "test_offline_20_answers_then_sync_no_duplicates"),
                      ("test_m4_after", "test_stand_in_answers_5_questions_and_homework_under_5_min"),
                      ("test_m4_after", "test_link_expires_after_7_days"),
                      ("test_m3_planner", "test_stand_in_completes_planner_on_phone_under_2_min")]:
        assert conftest.live_writer(_fn(mod, name)), (mod, name)


def test_offline_tests_are_not_gated():
    import conftest
    for mod, name in [("test_m5_cards", "test_scheduler_missed_3x_cold_over_300_draws"),
                      ("test_m5_cards", "test_js_buckets_parity_with_python"),
                      ("test_m4_after", "test_questions_bounded_and_audio_short")]:
        assert not conftest.live_writer(_fn(mod, name)), (mod, name)
