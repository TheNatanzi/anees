"""M2 cleanup script safety (offline): only the frozen 108 IDs, all matching, or nothing happens."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delete_test_card_rows_2026_09_29 as D

SPEC = json.loads((ROOT / "data/cleanup/card-results-test-rows-2026-09-29.json").read_text(encoding="utf-8"))


def _rows():
    return [{"id": i, "subject": SPEC["subject"], "created_at": "2026-09-29T09:30:00+00:00", "round_id": SPEC["round_ids"][0]} for i in SPEC["ids"]]


def test_frozen_list_is_exactly_108():
    assert len(SPEC["ids"]) == 108 == len(set(SPEC["ids"]))


def test_all_matching_rows_pass():
    assert D.check_rows(SPEC, _rows()) == []


def test_a_real_answer_or_missing_row_stops_it():
    r = _rows(); r[5] = dict(r[5], subject="sel:all:topic:Food")
    assert D.check_rows(SPEC, r)
    assert D.check_rows(SPEC, _rows()[:-1])
    r = _rows(); r[0] = dict(r[0], created_at="2026-09-28T09:30:00+00:00")
    assert D.check_rows(SPEC, r)
