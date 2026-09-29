# -*- coding: utf-8 -*-
"""Rule A2 'Amal's tap beats any machine label' and the 09-25 decisions (her 'correction is correct' scores the rows now,
her 'reason not to correct' drops them and becomes a rule, never asked again) - scripts/apply_amal_audit_rulings.py had
no test (eng audit 2026-09-29, area 5). Offline: Supabase and the page rebuilds are stubbed."""
import json, sys, types

import pytest

import apply_amal_audit_rulings as aar


@pytest.fixture
def env(tmp_path, monkeypatch):
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"rows": [
        {"uid": "FA-b1", "kind": "grammar-B", "signal": "none", "confidence": "low"},
        {"uid": "FA-b2", "kind": "vocab-B", "signal": "none", "confidence": "medium"},
        {"uid": "FA-b3", "kind": "grammar-B", "signal": "none", "confidence": "low"},
        {"uid": "FA-a1", "kind": "grammar", "signal": "recast", "confidence": "high"},
        {"uid": "FA-a2", "kind": "vocab-A", "signal": "recast", "confidence": "low"}]}), encoding="utf-8")
    rules = tmp_path / "ai_rules.json"
    rules.write_text(json.dumps({"groups": []}), encoding="utf-8")
    monkeypatch.setattr(aar, "AUDIT", str(audit))
    monkeypatch.setattr(aar, "RULES", str(rules))
    patched = []
    fake_db = types.SimpleNamespace(rest=lambda *a, **k: patched.append(k.get("params")), select=lambda *a, **k: [])
    monkeypatch.setitem(sys.modules, "db", fake_db)
    monkeypatch.setattr(aar.subprocess, "run", lambda *a, **k: None)
    rulings = [
        {"id": 1, "kind": "audit_confirm", "word_key": "P-b-after-lamma", "payload": {"rows": ["FA-b1", "FA-b2"]}},
        {"id": 2, "kind": "audit_skip", "word_key": "P-sun-letters", "payload": {"rows": ["FA-b3"], "reason": "not a priority"}},
        {"id": 3, "kind": "right", "word_key": None, "payload": {"audit_uid": "FA-a1"}, "created_at": "2026-09-27T10:00:00Z"},
        {"id": 4, "kind": "wrong", "word_key": None, "payload": {"audit_uid": "FA-a2"}, "created_at": "2026-09-27T10:00:00Z"},
        {"id": 5, "kind": "audit_confirm", "word_key": "P-old", "payload": {"rows": ["FA-a1"], "applied": "2026-09-20"}}]
    monkeypatch.setattr(aar, "load_rulings", lambda: rulings)
    return audit, rules, patched


def rows(p):
    return {r["uid"]: r for r in json.loads(p.read_text(encoding="utf-8"))["rows"]}


def test_her_confirm_scores_the_pattern_rows(env):
    audit, _, _ = env
    aar.apply()
    r = rows(audit)
    assert (r["FA-b1"]["kind"], r["FA-b1"]["signal"]) == ("grammar", "amal-ruling")
    assert (r["FA-b2"]["kind"], r["FA-b2"]["signal"]) == ("vocab-A", "amal-ruling")
    assert r["FA-b1"]["amal_ruling"]["kind"] == "confirm" and r["FA-b1"]["confidence"] == "high"


def test_her_reason_drops_the_rows_and_becomes_a_rule_asked_once(env):
    audit, rules, _ = env
    aar.apply()
    assert rows(audit)["FA-b3"]["kind"] == "dropped-by-amal"
    grp = next(g for g in json.loads(rules.read_text(encoding="utf-8"))["groups"] if g["title"] == "Amal's rulings")
    assert [x["pattern"] for x in grp["rules"]] == ["P-sun-letters"] and grp["rules"][0]["why"] == "not a priority"


def test_her_tap_beats_the_machine_label(env):
    audit, _, _ = env
    aar.apply()
    r = rows(audit)
    assert r["FA-a1"]["kind"] == "rejected"                              # machine said slip, she said Right
    assert r["FA-a2"]["kind"] == "vocab-A" and r["FA-a2"]["confidence"] == "high"   # she confirmed a low-confidence row


def test_applied_rulings_are_not_reapplied(env):
    audit, _, patched = env
    aar.apply()
    # 2026-09-29 (AI review 09-27): no write-back to Supabase any more; idempotency lives in the audit JSON
    assert patched == []
    assert json.loads(audit.read_text(encoding="utf-8"))["rulings_applied"][-1]["rules"] == [1, 2, 3, 4]
    assert rows(audit)["FA-a1"].get("amal_ruling", {}).get("pattern") != "P-old"


def test_dry_run_writes_nothing(env):
    audit, rules, patched = env
    before = audit.read_text(encoding="utf-8"), rules.read_text(encoding="utf-8")
    aar.apply(dry=True)
    assert (audit.read_text(encoding="utf-8"), rules.read_text(encoding="utf-8")) == before and not patched
