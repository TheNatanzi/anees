# -*- coding: utf-8 -*-
"""Area 3 (source audio + transcripts) and decision 5 (Codex second judge -> Amal's list on the Tutor page). Offline."""
import json, os, subprocess

import numpy as np
import pytest

import source_audit as S
import codex_rejudge as C
import apply_amal_audit_rulings as A

# the first lines of the 2026-09-18 Meet caption track (ffmpeg -map 0:s:0 -f srt): the speaker is in parentheses
SRT_0918 = """1
00:00:12,000 --> 00:00:16,000
(Amal)
Okay. Give you

2
00:00:32,000 --> 00:00:36,000
(Medi Natanzi)
20. Um, one second.
"""


def test_caption_speaker_in_parentheses(monkeypatch):
    """The parser only knew 'Name:' labels, so the 09-18 speaker check read 0 caption blocks."""
    class R:
        stdout = SRT_0918.encode("utf-8")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R())
    assert S.captions("x.mp4") == [(12.0, 16.0, "Amal"), (32.0, 36.0, "Medi")]


def test_holes_needs_20s_of_speech_in_2_minutes():
    hop = S.HOP
    untx = np.zeros(int(900 / hop), bool)
    untx[int(42 / hop):int(402 / hop):3] = True           # ~120 s of scattered speech 00:42-06:42 (09-28 shape)
    untx[int(600 / hop):int(610 / hop)] = True            # 10 s alone: a backchannel, not a hole
    h = S.holes(untx)
    assert len(h) == 1 and h[0][0] <= 60 and h[0][1] >= 380 and h[0][2] >= 100


def test_segments_lost_and_recovered(tmp_path, monkeypatch):
    """09-16: tracks.json lists two Medi segments under ONE file name; the file holds the long one. The short one is
    'lost' unless tracks/recovered/ has it."""
    d = tmp_path / "2026-09-16" / "tracks"
    d.mkdir(parents=True)
    (d / "Medi_Natanzi.mp3").write_bytes(b"x")
    tracks = {"tracks": [{"participant": "Medi Natanzi", "start": {"relative": 0.163}, "duration_s": 38.7, "file": str(d / "Medi_Natanzi.mp3")},
                         {"participant": "Medi Natanzi", "start": {"relative": 76.443}, "duration_s": 4108.2, "file": str(d / "Medi_Natanzi.mp3")},
                         {"participant": "Ray Adib", "start": {"relative": 0.4}, "duration_s": 14.9, "file": str(d / "Ray_Adib.mp3")}]}
    (d / "tracks.json").write_text(json.dumps(tracks), encoding="utf-8")
    monkeypatch.setattr(S, "ffprobe_dur", lambda p: 4108.3)
    seg = S.segments("2026-09-16", str(tmp_path))
    assert [s["status"] for s in seg["Medi"]] == ["lost", "ok"] and seg["Amal"] == []
    (d / "recovered").mkdir()
    (d / "recovered" / "recovery.json").write_text(json.dumps({"recovered": [
        {"participant": "Medi Natanzi", "start": {"relative": 0.163}, "file": str(d / "recovered" / "Medi_Natanzi-163.mp3")}]}), encoding="utf-8")
    assert [s["status"] for s in S.segments("2026-09-16", str(tmp_path))["Medi"]] == ["recovered", "ok"]


def test_real_source_audit_covers_every_lesson_and_finds_0928():
    sa = json.load(open(os.path.join(S.REPO, "data", "accuracy", "source-audit.json"), encoding="utf-8"))["lessons"]
    lessons = [L["date"] for L in json.load(open(os.path.join(S.REPO, "docs", "data", "lessons.json"), encoding="utf-8"))["lessons"]]
    assert set(lessons) <= set(sa)
    assert any(f["kind"] == "untranscribed" and f["who"] == "Medi" and f["from"] < 60 for f in sa["2026-09-28"]["flags"])
    # 09-23 Medi 0:00-22:37 was the known hole; the gap filler transcribed his first track - the raw audio agrees
    assert not [f for f in sa["2026-09-23"]["flags"] if f["kind"] == "untranscribed" and f["who"] == "Medi"]


# ---------------------------------------------------------------- Codex second judge
def test_codex_record_shape_passes_the_ledger_rules():
    import accuracy_gates as G
    q = {"uid": "FA-1", "date": "2026-09-28", "kind": "grammar", "listen_from": "04:50", "listen_to": "05:25", "wrong": "a", "right": "b"}
    ev = {"clips": [{"who": "Medi", "file": "data/accuracy/clips/x.mp3", "sha256": "0" * 64, "source": "Medi.mp3",
                     "asr": {"large-v3": [{"t": "04:55", "text": "أنا بروح"}]}}]}
    r = C.record(q, ev, {"verdict": "confirmed", "confidence": "high", "reason": "she recasts", "quote": "بروح"}, "run1")
    assert G.ledger_problems({"records": [r]}) == []
    assert r["reviewer"] == "codex gpt-5.5" and r["role"] == "second-judge" and r["evidence"]["t_start"] == 290.0


def test_amal_list_holds_only_open_disagreements(tmp_path):
    ev = {"t_start": 290, "t_end": 325}
    audit = {"rows": [{"uid": u, "date": "2026-09-28", "kind": "grammar", "t": "05:00", "wrong": "a", "right": "b"} for u in ("FA-1", "FA-2", "FA-3", "FA-4")]}
    L = {"records": [
        {"uid": "FA-1", "role": "second-judge", "reviewer": "codex gpt-5.5", "verdict": "rejected", "evidence": ev, "at": "1", "date": "2026-09-28"},
        {"uid": "FA-2", "role": "second-judge", "reviewer": "codex gpt-5.5", "verdict": "confirmed", "evidence": ev, "at": "1", "date": "2026-09-28"},
        {"uid": "FA-3", "role": "second-judge", "reviewer": "codex gpt-5.5", "verdict": "unsure", "evidence": ev, "at": "1", "date": "2026-09-28"},
        {"uid": "FA-3", "role": "human", "method": "human", "reviewer": "Amal", "verdict": "confirmed", "evidence": ev, "at": "2", "date": "2026-09-28"}]}
    out = C.amal_list(audit=audit, ledger=L, repo=str(tmp_path))
    assert [x["uid"] for x in out["items"]] == ["FA-1"] and out["items"][0]["id"] == "verify:FA-1"
    assert out["items"][0]["audio"] is None                  # no lesson recording in this tmp repo: say so, never a dead link


def test_amal_taps_become_human_ledger_records():
    rows = {"FA-1": {"uid": "FA-1", "date": "2026-09-28", "kind": "grammar", "t": "05:00", "t_amal": "05:05"}}
    rulings = [{"id": 11, "kind": "audit_confirm", "word_key": "verify:FA-1", "created_at": "2026-09-30T10:00:00Z", "payload": {}},
               {"id": 12, "kind": "audit_skip", "word_key": "verify:FA-1", "created_at": "2026-09-30T11:00:00Z", "payload": {"reason": "he said it right"}},
               {"id": 13, "kind": "audit_confirm", "word_key": "B7-pattern", "payload": {"rows": ["FA-9"]}}]
    recs = A.verify_records(rulings, rows, {"records": []})
    assert [(r["rule_id"], r["verdict"], r["reviewer"], r["role"]) for r in recs] == [(11, "confirmed", "Amal", "human"), (12, "rejected", "Amal", "human")]
    assert recs[1]["reason"] == "he said it right" and recs[0]["evidence"]["t_start"] == 290.0
    import accuracy_gates as G
    assert G.ledger_problems({"records": recs}) == []
    assert A.verify_records(rulings, rows, {"records": recs}) == []            # idempotent: a tap is recorded once


def test_tutor_page_has_the_check_list_and_no_hub():
    html = open(os.path.join(S.REPO, "docs", "tutor.html"), encoding="utf-8").read()
    js = open(os.path.join(S.REPO, "docs", "js", "tutor-verify.js"), encoding="utf-8").read()
    assert 'id="tv-list"' in html and "tutor-verify.js" in html
    assert "Correction is correct" in js and "Reason not to correct" in js
    assert "audit_confirm" in js and "audit_skip" in js and "amal_rules" in js
    assert "hub.html" not in html and "Amal's hub" not in html                   # removed 2026-09-28, never back
