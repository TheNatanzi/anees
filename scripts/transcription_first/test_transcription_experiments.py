import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import transcription_experiments as e


class ExperimentsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.out = self.root / "out"
        self.lesson = self.repo / "data/lessons/2026-09-05"
        tracks = self.lesson / "tracks"
        tracks.mkdir(parents=True)
        (tracks / "Medi.mp3").write_bytes(b"medi audio")
        (tracks / "Amal.mp3").write_bytes(b"amal audio")
        (tracks / "tracks.json").write_text(json.dumps({"tracks": [
            {"participant": "Medi Natanzi", "file": "C:\\any\\Medi.mp3", "duration_s": 3762.79},
            {"participant": "Amal", "file": "C:\\any\\Amal.mp3", "duration_s": 3736.98}]}))
        for name in ("scribe_Medi.json", "scribe_Amal.json", "scribe_meet_mixed_1615.json"):
            (self.lesson / name).write_text('{"text":"cached", "words":[]}')
        self.ledger = self.repo / "data/budget.json"
        self.old = {"elevenlabs": 0.6885, "openai": 2.2098, "calls": [{"service": "openai", "usd": 2.2098}], "custom": {"keep": True}}
        e.atomic_json(self.ledger, self.old)
        self.key = "test-secret-value-never-print"
        self.privacy = {"provider": "elevenlabs", "purpose": "asr_experiments", "training_opt_out": True, "effective": True, "account_match": True, "key_sha256": hashlib.sha256(self.key.encode()).hexdigest(), "source": "Account UI saved Data use setting", "verified_by": "tester", "verified_at": e.now()}

    def tearDown(self):
        self.temp.cleanup()

    def plan(self):
        return e.make_plan(self.repo, self.out, duration_probe=lambda p: 3763.68 if p.name == "Medi.mp3" else 3738.53)

    def run_arm(self, post, arm=None):
        arm = arm or self.plan()["arms"][0]
        return e.run_arm(arm, self.out, self.ledger, self.key, self.privacy, post=post, duration_probe=lambda p: arm["expected_duration_s"])

    def test_causal_arms_and_cap(self):
        plan = self.plan()
        self.assertLessEqual(plan["estimated_reserved_total_usd"], 1.25)
        self.assertEqual(6, len(plan["arms"]))
        arms = plan["arms"]
        self.assertEqual({**e.BASE_PARAMS, "language_code": "ara"}, arms[0]["params"])
        self.assertEqual("false", arms[1]["params"]["diarize"])
        self.assertNotIn("num_speakers", arms[1]["params"])
        self.assertEqual({**e.BASE_PARAMS, "no_verbatim": "false"}, arms[2]["params"])
        self.assertEqual(e.BASE_PARAMS, arms[4]["params"])
        self.assertEqual((35.0, 64.0, 29.0), tuple(arms[4][k] for k in ("source_start_s", "source_end_s", "expected_duration_s")))
        self.assertEqual("e4_medi_35_64.mp3", Path(arms[4]["input_path"]).name)
        self.assertEqual((1649.0, 1685.0, 36.0), tuple(arms[5][k] for k in ("source_start_s", "source_end_s", "expected_duration_s")))
        self.assertEqual("e4_amal_1649_1685.mp3", Path(arms[5]["input_path"]).name)
        self.assertEqual(3763.68, arms[0]["expected_duration_s"])
        self.assertEqual(3762.79, arms[0]["source_manifest_duration_s"])
        self.assertAlmostEqual(0.89, arms[0]["source_duration_discrepancy_s"])
        with self.assertRaises(e.ExperimentError):
            e.make_plan(self.repo, self.out, rate=0.4, duration_probe=lambda p: 3763.68)

    def test_gate_requires_effective_key_bound_setting(self):
        e.verify_privacy(self.privacy, self.key)
        for update in ({"training_opt_out": False}, {"effective": False}, {"account_match": False}, {"key_sha256": "bad"}, {"source": ""}, {"api_key": self.key}, {"training_opt_out": 1}):
            with self.subTest(update=list(update)):
                with self.assertRaises(e.ExperimentError):
                    e.verify_privacy({**self.privacy, **update}, self.key)
        with self.assertRaises(e.ExperimentError):
            e.verify_privacy({**self.privacy, "verified_at": "2020-01-01T00:00:00Z"}, self.key)

    def test_gate_stops_before_upload_and_reservation(self):
        self.privacy["effective"] = False
        post = Mock()
        with self.assertRaises(e.ExperimentError):
            self.run_arm(post)
        post.assert_not_called()
        self.assertEqual(self.old, e.load_ledger(self.ledger))

    def test_success_reserves_before_post_preserves_other_fields_and_caches(self):
        arm = self.plan()["arms"][0]
        def post(path, params, key):
            ledger = e.load_ledger(self.ledger)
            self.assertEqual("reserved_before_upload", ledger["calls"][-1]["status"])
            self.assertGreater(ledger["elevenlabs"], self.old["elevenlabs"])
            return e.HttpResult(200, b'{"text":"example","words":[]}', "request-test")
        mock = Mock(side_effect=post)
        first = self.run_arm(mock, arm)
        second = self.run_arm(mock, arm)
        self.assertTrue(first["attempted"])
        self.assertFalse(second["attempted"])
        self.assertEqual(1, mock.call_count)
        ledger = e.load_ledger(self.ledger)
        self.assertEqual(self.old["openai"], ledger["openai"])
        self.assertEqual(self.old["custom"], ledger["custom"])
        self.assertEqual(self.old["calls"][0], ledger["calls"][0])
        self.assertEqual("success_estimated_cost", ledger["calls"][-1]["status"])
        self.assertEqual('{"text":"cached", "words":[]}', (self.lesson / "scribe_Medi.json").read_text())

    def test_no_blind_network_or_http_retry_and_reservation_retained(self):
        for response in (ConnectionError("network failure"), e.HttpResult(429, b'{"detail":"rate limited"}')):
            with self.subTest(response=type(response).__name__):
                arm = copy.deepcopy(self.plan()["arms"][0])
                arm["id"] += type(response).__name__
                post = Mock(side_effect=response) if isinstance(response, Exception) else Mock(return_value=response)
                old_total = e.load_ledger(self.ledger)["elevenlabs"]
                result = self.run_arm(post, arm)
                self.assertNotIn("success", result["status"])
                self.run_arm(post, arm)
                self.assertEqual(1, post.call_count)
                self.assertAlmostEqual(old_total + arm["reserved_usd"], e.load_ledger(self.ledger)["elevenlabs"], places=4)

    def test_prior_reservation_without_result_never_reuploads(self):
        arm = self.plan()["arms"][0]
        post = Mock(return_value=e.HttpResult(200, b'{"text":"ok","words":[]}'))
        self.run_arm(post, arm)
        (self.out / "runs" / arm["id"] / "result.json").unlink()
        with self.assertRaises(e.ExperimentError):
            self.run_arm(post, arm)
        self.assertEqual(1, post.call_count)

    def test_input_drift_and_budget_stop_prevent_upload(self):
        arm = self.plan()["arms"][0]
        post = Mock()
        Path(arm["source_path"]).write_bytes(b"changed")
        with self.assertRaises(e.ExperimentError):
            self.run_arm(post, arm)
        arm = self.plan()["arms"][0]
        e.atomic_json(self.ledger, {**self.old, "elevenlabs": 8.99})
        with self.assertRaises(e.ExperimentError):
            self.run_arm(post, arm)
        post.assert_not_called()

    def test_manifest_total_and_ledger_batch_cap_cannot_be_bypassed(self):
        old = {**self.old, "calls": [{"batch_id": e.BATCH_ID, "usd": 1.2}]}
        e.atomic_json(self.ledger, old)
        with self.assertRaises(e.ExperimentError):
            e.reserve(self.ledger, "new", "hash", 0.1, {})
        self.assertEqual(old, e.load_ledger(self.ledger))

    def test_response_credential_is_not_saved(self):
        body = json.dumps({"text": self.key, "words": []}).encode()
        arm = self.plan()["arms"][0]
        self.run_arm(Mock(return_value=e.HttpResult(200, body)), arm)
        for path in self.out.rglob("*"):
            if path.is_file():
                self.assertNotIn(self.key.encode(), path.read_bytes())

    def test_existing_lock_and_immutable_artifact(self):
        lock = Path(str(self.ledger) + ".lock")
        lock.write_text("another process")
        with self.assertRaises(e.ExperimentError):
            with e.ledger_lock(self.ledger, timeout=0):
                self.fail("must not acquire")
        self.assertTrue(lock.exists())
        path = self.out / "immutable.json"
        e.immutable_json(path, {"x": 1})
        e.immutable_json(path, {"x": 1})
        with self.assertRaises(e.ExperimentError):
            e.immutable_json(path, {"x": 2})

    def test_upload_transport_does_not_follow_redirects(self):
        self.assertIsNone(e.NoRedirect().redirect_request(None, None, 307, "temporary", {}, "https://other.example/upload"))


if __name__ == "__main__":
    unittest.main()
