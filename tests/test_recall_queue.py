import json
from pathlib import Path

import lesson_pipeline as lp
import process_recall_queue as queue


def bot(date="2026-09-12"):
    return {"t": f"{date}T14:27:12", "date": date, "bot_id": "bot-1"}


def test_pending_skips_history_and_complete_lessons(tmp_path):
    lessons = tmp_path / "data" / "lessons"
    docs = tmp_path / "docs" / "lessons"
    assert queue.pending_entries([bot("2026-09-11"), bot()], lessons, docs) == [bot()]
    (lessons / "2026-09-12").mkdir(parents=True)
    (lessons / "2026-09-12" / "summary.json").write_text("{}", encoding="utf-8")
    docs.mkdir(parents=True)
    (docs / "2026-09-12-report.html").write_text("done", encoding="utf-8")
    assert queue.pending_entries([bot()], lessons, docs) == []


def test_completed_bot_fetches_then_runs_ingest(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, "LESSONS", tmp_path / "data" / "lessons")
    monkeypatch.setattr(queue, "DOCS", tmp_path / "docs" / "lessons")
    calls = []

    def fetch(bot_id, date, wait_minutes):
        manifest = queue.LESSONS / date / "tracks" / "tracks.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("{}", encoding="utf-8")
        calls.append(("fetch", bot_id, date, wait_minutes))

    def run(command, **kwargs):
        date = "2026-09-12"
        (queue.LESSONS / date).mkdir(parents=True, exist_ok=True)
        (queue.LESSONS / date / "summary.json").write_text("{}", encoding="utf-8")
        queue.DOCS.mkdir(parents=True)
        (queue.DOCS / f"{date}-report.html").write_text("done", encoding="utf-8")
        calls.append(("run", command, kwargs))

    result = queue.process_entry(bot(), status_fn=lambda _id: ({}, "done"),
                                 fetch_fn=fetch, run_fn=run)
    assert result == "completed Recall lesson 2026-09-12"
    assert calls[0] == ("fetch", "bot-1", "2026-09-12", 0)
    assert "ingest_tracks.py" in calls[1][1][2]


def test_drive_scan_does_not_overwrite_track_lesson(tmp_path, monkeypatch):
    source = tmp_path / "meet"
    lessons = tmp_path / "lessons"
    source.mkdir()
    recording = source / "abc-defg-hij (2026-09-12 14 27 GMT-7)"
    recording.write_bytes(b"")
    recording.touch()
    monkeypatch.setattr(lp, "SRC", source)
    monkeypatch.setattr(lp, "LESSONS", lessons)
    monkeypatch.setattr(lp, "MIN_BYTES", 0)
    summary = lessons / "2026-09-12" / "summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"speaker_split": "ok: one audio track per person (Recall bot)"}), encoding="utf-8")
    assert lp.new_recordings({}) == []
    summary.write_text(json.dumps({"speaker_split": "model labels"}), encoding="utf-8")
    assert lp.new_recordings({})[0][1:] == ("2026-09-12", "1427")
