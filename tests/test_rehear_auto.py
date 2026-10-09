# -*- coding: utf-8 -*-
"""TR-29 (Medi 2026-10-09 "why the fuck wasnt it applied?" ... "go and fix it permanently"): the second listen runs by
itself on every new lesson, inside Medi's own allowance, and a lesson that waits says why. Fakes only: no network, no
paid call (tests/conftest.py also turns the hourly step off)."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import rehear_auto as RH  # noqa: E402
import rehear_job as RJ  # noqa: E402
import rehear_backfill as RB  # noqa: E402
import rehear_status as RS  # noqa: E402


def test_tr_29_every_published_lesson_after_the_backfill_that_is_not_applied_is_on_the_list():
    st = {"lessons": {"2026-10-02": {"status": "applied"}, "2026-10-05": {"status": "pending"}, "2026-10-06": {"status": "applied"},
                      "2026-10-08": {"status": "submitted"}}}
    assert RH.todo(published=["2026-09-30", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-08", "2026-10-12"], status=st) == \
        ["2026-10-05", "2026-10-08", "2026-10-12"]


def test_tr_29_no_room_in_the_allowance_sends_nothing_and_says_why(monkeypatch):
    sent, notes = [], {}
    monkeypatch.setattr(RB, "stage_of", lambda d: "base")
    monkeypatch.setattr(RB, "run_done", lambda d, s, n: False)
    monkeypatch.setattr(RJ, "state", lambda d, n: "none")
    monkeypatch.setattr(RJ, "new_lessons_limit", lambda: 0.0)
    monkeypatch.setattr(RJ, "per_lesson_limit", lambda: None)
    monkeypatch.setattr(RJ, "new_lessons_spent", lambda m, but=None: 0.70)
    monkeypatch.setattr(RB, "submit", lambda ds: sent.append(ds))
    monkeypatch.setattr(RB, "pump_one", lambda d: "base")
    monkeypatch.setattr(RH, "note_wait", lambda d, msg: notes.__setitem__(d, msg))
    st, prob = RH.step_one("2026-10-08")
    assert sent == [] and st == "base"
    assert notes["2026-10-08"].startswith(RH.WAIT) and "$0.70 used of $0.00" in notes["2026-10-08"]
    assert prob.startswith("10-08: second listen waiting")
    # with room, the three base runs go out (the backfill's own submit: allowance checked again per job)
    monkeypatch.setattr(RJ, "new_lessons_limit", lambda: 30.0)
    st, prob = RH.step_one("2026-10-08")
    assert sent == [["2026-10-08"]] and prob is None and notes["2026-10-08"] == ""


def test_tr_29_proposed_is_applied_and_the_lesson_is_read_again(monkeypatch, tmp_path):
    done = []
    monkeypatch.setattr(RH, "REREAD_P", str(tmp_path / "q.json"))
    monkeypatch.setattr(RB, "stage_of", lambda d: "proposed")
    import rehear_apply as RA
    monkeypatch.setattr(RA, "plan", lambda d: done.append(("plan", d)))
    monkeypatch.setattr(RA, "apply", lambda ds: done.append(("apply", tuple(ds))))
    st, prob = RH.step_one("2026-10-05", log=lambda *a: None)
    assert st == "applied" and done == [("plan", "2026-10-05"), ("apply", ("2026-10-05",))]
    assert RH.reread_next() == "2026-10-05"
    RH.reread_done("2026-10-05")
    assert RH.reread_next() is None


def test_tr_29_a_new_lesson_never_draws_on_the_backfill_allowance_and_the_backfill_money_is_seen_everywhere(monkeypatch):
    """The backfill's $43.99 sat in another checkout's git-ignored job files: from the hourly checkout the $45 looked
    untouched. spent() is never less than the committed record; a lesson after 10-02 is checked against Medi's
    new-lessons allowance only."""
    monkeypatch.setattr(RJ, "spend_doc", lambda: {"backfill": {"spent_usd": 43.99}, "new_lessons": {"monthly_usd": 0.0, "per_lesson_usd": None, "jobs": {}}})
    monkeypatch.setattr(RJ, "all_jobs", lambda: [])
    assert RJ.spent() == 43.99
    caps = {}

    def fake_submit(folder, name, est, cap_check=None):
        caps[name] = cap_check(est)
        return {"job": None}
    import batch_jobs as BJ
    monkeypatch.setattr(BJ, "submit", fake_submit)
    monkeypatch.setattr(RJ, "LOCK", os.path.join(RJ.REHEAR, ".test.lock"))
    RJ.submit("2026-10-08", "base-run2", 0.82)
    assert caps["base-run2"].startswith("monthly limit") and "nothing sent" in caps["base-run2"]
    RJ.submit("2026-10-02", "base-run9", 0.82)
    assert caps["base-run9"] is None                      # 43.99 + 0.82 <= 45: inside the backfill's own limit
    RJ.submit("2026-10-02", "base-run9b", 1.50)
    assert caps["base-run9b"].startswith("backfill allowance")


def test_tr_29_the_chip_says_waiting_for_allowance_and_the_hourly_job_steps_it():
    doc = {"lessons": {"2026-10-08": {"status": "pending", "since": "2026-10-08", "note": RH.WAIT + ": $0.70 used of $0.00"}}}
    assert RS.chip("2026-10-08", doc)["label"] == "Second listen: waiting for allowance"
    src = open(os.path.join(ROOT, "scripts", "hourly_lessons.py"), encoding="utf-8").read()
    assert "rh = RH.step(log=log)" in src and "'data/lesson-work/rehear'" in src
    spend = json.load(open(os.path.join(ROOT, "data", "lesson-work", "rehear", "spend.json"), encoding="utf-8"))
    assert spend["backfill"]["spent_usd"] == 43.99 and spend["new_lessons"]["per_lesson_usd"] == 4.0 and spend["new_lessons"]["monthly_usd"] is None


def test_tr_29_tests_never_step_the_paid_listen():
    assert os.environ.get("ANEES_REHEAR_AUTO") == "off"
    assert RH.step(dates=["2026-10-08"]) == {"stages": {}, "problems": [], "changed": False}


def test_tr_29_medi_s_limit_is_per_lesson_with_no_monthly_cap(monkeypatch):
    """Medi 2026-10-09: 'no budget 2.50 per lesson is fine'. Each job of a lesson after 10-02 is checked against what
    that lesson has spent or owes; no month total."""
    jobs = {"2026-10-08/base-run1.job.json": {"date": "2026-10-08", "usd": 0.70}, "2026-10-05/base-run1.job.json": {"date": "2026-10-05", "usd": 2.0}}
    monkeypatch.setattr(RJ, "spend_doc", lambda: {"backfill": {"spent_usd": 43.99}, "new_lessons": {"monthly_usd": None, "per_lesson_usd": 2.5, "jobs": jobs}})
    monkeypatch.setattr(RJ, "all_jobs", lambda: [])
    assert RJ.lesson_spent("2026-10-08") == 0.70 and RJ.new_lessons_limit() is None and RJ.per_lesson_limit() == 2.5
    caps = {}

    def fake_submit(folder, name, est, cap_check=None):
        caps[name] = cap_check(est)
        return {"job": None}
    import batch_jobs as BJ
    monkeypatch.setattr(BJ, "submit", fake_submit)
    monkeypatch.setattr(RJ, "LOCK", os.path.join(RJ.REHEAR, ".test.lock"))
    RJ.submit("2026-10-08", "base-run2", 0.82)
    assert caps["base-run2"] is None                         # 0.70 + 0.82 <= 2.50
    RJ.submit("2026-10-05", "base-run2", 0.82)
    assert caps["base-run2"].startswith("per-lesson limit")    # 2.00 + 0.82 > 2.50: that lesson stops, nothing sent
    monkeypatch.setattr(RJ, "spend_doc", lambda: {"new_lessons": {"monthly_usd": None, "per_lesson_usd": None, "jobs": {}}})
    RJ.submit("2026-10-08", "base-run3", 0.82)
    assert caps["base-run3"].startswith("no Google limit set")


def test_tr_29_a_lesson_frozen_in_another_checkout_gets_its_clips_cut_again_before_anything_is_sent(monkeypatch):
    """2026-10-09 09:00: the hourly checkout had 10-05/06/08's committed lines + manifest but not the git-ignored clips
    (frozen in a worktree) and stopped with 'clips missing'. The step cuts them again (hash-checked) first."""
    calls = []
    import rehear_lesson as RL
    monkeypatch.setattr(RB, "stage_of", lambda d: "base")
    monkeypatch.setattr(RL, "restore_clips", lambda d: calls.append(("restore", d)) or 3)
    monkeypatch.setattr(RB, "run_done", lambda d, s, n: True)
    monkeypatch.setattr(RB, "pump_one", lambda d: calls.append(("pump", d)) or "base")
    RH.step_one("2026-10-08", log=lambda *a: None)
    assert calls == [("restore", "2026-10-08"), ("pump", "2026-10-08")]
    src = open(os.path.join(ROOT, "scripts", "rehear_lesson.py"), encoding="utf-8").read()
    assert "def restore_clips(date):" in src and "check_clips(d, man, [ln[\"clip\"] for ln in listen])" in src
