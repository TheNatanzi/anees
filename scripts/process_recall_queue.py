"""Finish completed Recall.ai lessons during the hourly Anees pipeline.

The meeting bot is created separately because its Meet URL is only known when
the lesson starts.  This worker owns the missing post-call handoff: once Recall
reports ``done``, download the participant tracks and run the established
two-track lesson pipeline.  Existing lesson outputs are never reprocessed.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import recall_bot  # noqa: E402

LESSONS = ROOT / "data" / "lessons"
DOCS = ROOT / "docs" / "lessons"
LEDGER = LESSONS / "recall_bots.json"

# Older bot rows predate this worker and already have deliberate/manual outputs.
# Starting after today's recovered lesson prevents a historical paid rerun.
AUTO_START_DATE = "2026-09-12"


def log(*parts: object) -> None:
    print(datetime.datetime.now().strftime("%H:%M:%S"), *parts, flush=True)


def hhmm(entry: dict) -> str:
    stamp = str(entry.get("t") or "")
    try:
        return datetime.datetime.fromisoformat(stamp).strftime("%H%M")
    except ValueError:
        return "0000"


def lesson_complete(date: str, lessons: Path | None = None, docs: Path | None = None) -> bool:
    lessons = lessons or LESSONS
    docs = docs or DOCS
    return (lessons / date / "summary.json").exists() and (docs / f"{date}-report.html").exists()


def pending_entries(entries: list[dict], lessons: Path | None = None,
                    docs: Path | None = None) -> list[dict]:
    lessons = lessons or LESSONS
    docs = docs or DOCS
    out = []
    for entry in sorted(entries, key=lambda row: str(row.get("t") or "")):
        date = str(entry.get("date") or "")
        if date < AUTO_START_DATE or lesson_complete(date, lessons, docs):
            continue
        if not entry.get("bot_id"):
            log("Recall row has no bot_id; skipped", date or "unknown date")
            continue
        out.append(entry)
    return out


def process_entry(entry: dict, *, dry_run: bool = False, status_fn=None,
                  fetch_fn=None, run_fn=None) -> str:
    date = str(entry["date"])
    bot_id = str(entry["bot_id"])
    if dry_run:
        return f"would check Recall bot {bot_id} for {date}"

    status_fn = status_fn or recall_bot.status
    fetch_fn = fetch_fn or recall_bot.fetch
    run_fn = run_fn or subprocess.run
    manifest = LESSONS / date / "tracks" / "tracks.json"
    if not manifest.exists():
        _bot, code = status_fn(bot_id)
        if code != "done":
            return f"Recall bot {bot_id} for {date} is {code or 'not ready'}"
        log("fetching completed Recall lesson", date, bot_id)
        fetch_fn(bot_id, date=date, wait_minutes=0)
    if not manifest.exists():
        raise RuntimeError(f"Recall fetch produced no track manifest for {date}")

    command = [sys.executable, "-B", str(ROOT / "scripts" / "ingest_tracks.py"),
               date, "--hhmm", hhmm(entry)]
    log("processing Recall participant tracks", date)
    run_fn(command, cwd=ROOT, check=True, timeout=3 * 60 * 60)
    if not lesson_complete(date):
        raise RuntimeError(f"Recall pipeline finished without complete lesson outputs for {date}")
    return f"completed Recall lesson {date}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not LEDGER.exists():
        log("Recall ledger not found; nothing to do")
        return 0
    entries = json.loads(LEDGER.read_text(encoding="utf-8-sig"))
    pending = pending_entries(entries)
    if not pending:
        log("no pending Recall lessons")
        return 0

    failures = 0
    for entry in pending:
        try:
            log(process_entry(entry, dry_run=args.dry_run))
        except Exception as exc:
            failures += 1
            log("Recall lesson FAILED", entry.get("date"), str(exc)[:500])
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
