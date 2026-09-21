"""Frozen Sep 5 Scribe experiments. Dry-run by default; stdlib, no automatic retries.

Prepare E4 clips under OUTPUT/inputs/e4_medi_35_64.mp3 and
OUTPUT/inputs/e4_amal_1649_1685.mp3. Their times are local to each source track.
They surround observed Medi event 36.57–62.42 and Amal event 1650.924–1683.774.
No baseline files, downstream features or review judgments are modified.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

BATCH_ID = "anees-sep05-takeover-2026-09-07-v1"
ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"
CAP_USD = 1.25
LEGACY_SERVICE_STOP_USD = 9.0  # Existing $10 cap × 90%; never relax it.
BASE_PARAMS = {
    "model_id": "scribe_v2", "diarize": "true", "num_speakers": "2",
    "timestamps_granularity": "word", "tag_audio_events": "true",
}


class ExperimentError(RuntimeError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def immutable_bytes(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if path.read_bytes() != value:
            raise ExperimentError(f"Immutable artifact differs: {path.name}")


def immutable_json(path, value):
    immutable_bytes(path, canonical(value))


@contextmanager
def ledger_lock(path, timeout=5.0):
    """Cooperative writer lock. Never remove another process's or a stale lock."""
    lock = Path(str(path) + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ExperimentError("Budget ledger is locked; no request started")
            time.sleep(0.05)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "created_at": now()}))
        yield
    finally:
        lock.unlink()


def load_ledger(path):
    if not Path(path).is_file():
        raise ExperimentError("Existing budget ledger missing; refusing a new unaccounted ledger")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value.get("calls"), list):
        raise ExperimentError("Invalid budget ledger calls field")
    if not isinstance(value.get("elevenlabs"), (int, float)) or value["elevenlabs"] < 0:
        raise ExperimentError("Invalid ElevenLabs ledger total")
    return value


def reserve(path, experiment_id, request_hash, usd, metadata):
    """Reserve before transmission. The legacy total includes uncertain reservations."""
    with ledger_lock(path):
        ledger = load_ledger(path)
        for entry in ledger["calls"]:
            if entry.get("experiment_id") == experiment_id:
                if entry.get("request_sha256") != request_hash:
                    raise ExperimentError("An existing experiment ID has different inputs/configuration")
                return False, copy.deepcopy(entry)
        batch_total = sum(float(x.get("usd", 0)) for x in ledger["calls"] if x.get("batch_id") == BATCH_ID)
        if batch_total + usd > CAP_USD + 1e-8:
            raise ExperimentError("Experiment batch would exceed $1.25")
        if ledger["elevenlabs"] + usd > LEGACY_SERVICE_STOP_USD + 1e-8:
            raise ExperimentError("Existing ElevenLabs 90% budget stop would be exceeded")
        entry = {
            "t": now(), "service": "elevenlabs", "usd": usd,
            "what": "Sep 5 transcript experiment " + experiment_id,
            "batch_id": BATCH_ID, "experiment_id": experiment_id,
            "request_sha256": request_hash, "status": "reserved_before_upload",
            "cost_kind": "estimated_reserved_including_5pct_margin",
            **metadata,
        }
        ledger["elevenlabs"] = round(ledger["elevenlabs"] + usd, 4)
        ledger["calls"].append(entry)
        atomic_json(path, ledger)
        return True, copy.deepcopy(entry)


def finalize_reservation(path, experiment_id, request_hash, status, **metadata):
    """Keep the full estimate charged/reserved even on errors; no blind refunds."""
    with ledger_lock(path):
        ledger = load_ledger(path)
        entries = [x for x in ledger["calls"] if x.get("experiment_id") == experiment_id]
        if len(entries) != 1 or entries[0].get("request_sha256") != request_hash:
            raise ExperimentError("Cannot finalize a missing or mismatched reservation")
        entries[0].update(status=status, completed_at=now(), **metadata)
        atomic_json(path, ledger)


def credentials():
    value = os.environ.get("ELEVENLABS_API_KEY")
    if not value and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
                value, _ = winreg.QueryValueEx(handle, "ELEVENLABS_API_KEY")
        except OSError:
            pass
    if not value:
        raise ExperimentError("ELEVENLABS_API_KEY unavailable")
    return value


def verify_privacy(record, key, clock=None):
    """Attestation must bind the effective setting to this key/account, not another login."""
    required = {
        "provider": "elevenlabs", "purpose": "asr_experiments",
        "training_opt_out": True, "effective": True, "account_match": True,
    }
    if any(record.get(k) != v or (v is True and record.get(k) is not True) for k, v in required.items()):
        raise ExperimentError("No effective account-matched no-training attestation")
    expected = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if record.get("key_sha256") != expected:
        raise ExperimentError("Privacy attestation does not match the configured API credential")
    if not all(isinstance(record.get(k), str) and record[k].strip() for k in ("source", "verified_by", "verified_at")):
        raise ExperimentError("Privacy evidence source, verifier and time required")
    try:
        stamp = dt.datetime.fromisoformat(record["verified_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("timezone missing")
    except (ValueError, TypeError):
        raise ExperimentError("Privacy verification time must be timezone-aware ISO 8601")
    age = ((clock or dt.datetime.now(dt.timezone.utc)) - stamp).total_seconds()
    if age < -300 or age > 7 * 24 * 3600:
        raise ExperimentError("Privacy attestation must be verified within the past seven days")
    forbidden = {"api_key", "key", "token", "password", "secret"}
    if forbidden.intersection(record):
        raise ExperimentError("Privacy record must not contain credentials")
    return hashlib.sha256(canonical(record)).hexdigest()


def make_plan(repo, output, rate=0.22, duration_probe=None):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if not math.isfinite(rate) or rate <= 0:
        raise ExperimentError("Rate must be a positive estimate")
    lesson = repo / "data/lessons/2026-09-05"
    tracks = json.loads((lesson / "tracks/tracks.json").read_text(encoding="utf-8"))["tracks"]
    medi = next(x for x in tracks if x["participant"].startswith("Medi"))
    amal = next(x for x in tracks if x["participant"] == "Amal")
    source_medi = lesson / "tracks" / Path(medi["file"].replace("\\", "/")).name
    source_amal = lesson / "tracks" / Path(amal["file"].replace("\\", "/")).name
    source_hashes = {str(p): file_hash(p) for p in (source_medi, source_amal)}
    probe = duration_probe or probe_duration
    source_durations = {str(p): probe(p) for p in (source_medi, source_amal)}
    recorded_durations = {str(source_medi): float(medi["duration_s"]), str(source_amal): float(amal["duration_s"])}
    arms = []

    def add(name, experiment, path, source, duration, changes=None, remove=(), start=0, end=None):
        params = dict(BASE_PARAMS)
        params.update(changes or {})
        for field in remove:
            params.pop(field, None)
        estimate = duration / 3600 * rate
        reservation = math.ceil(estimate * 1.05 * 10000) / 10000
        arms.append({
            "id": name, "experiment": experiment, "input_path": str(path),
            "source_path": str(source), "source_sha256": source_hashes[str(source)],
            "source_probed_duration_s": source_durations[str(source)],
            "source_manifest_duration_s": recorded_durations[str(source)],
            "source_duration_discrepancy_s": round(source_durations[str(source)] - recorded_durations[str(source)], 6),
            "source_start_s": start, "source_end_s": end if end is not None else duration,
            "expected_duration_s": duration, "params": params,
            "cost_estimate_usd": round(estimate, 6), "reserved_usd": reservation,
        })

    medi_duration = source_durations[str(source_medi)]
    add("e1_medi_ara", "E1", source_medi, source_medi, medi_duration, {"language_code": "ara"})
    add("e2_medi_no_diarization", "E2", source_medi, source_medi, medi_duration, {"diarize": "false"}, ("num_speakers",))
    add("e3_medi_explicit_verbatim", "E3", source_medi, source_medi, medi_duration, {"no_verbatim": "false"})
    add("e3_medi_no_events", "E3", source_medi, source_medi, medi_duration, {"no_verbatim": "false", "tag_audio_events": "false"})
    add("e4_medi_event_clip", "E4", output / "inputs/e4_medi_35_64.mp3", source_medi, 29.0, start=35.0, end=64.0)
    add("e4_amal_event_clip", "E4", output / "inputs/e4_amal_1649_1685.mp3", source_amal, 36.0, start=1649.0, end=1685.0)
    total = round(sum(x["reserved_usd"] for x in arms), 4)
    if total > CAP_USD:
        raise ExperimentError(f"Manifest reservation ${total:.4f} exceeds $1.25 batch limit")
    baselines = {}
    for name in ("scribe_Medi.json", "scribe_Amal.json", "scribe_meet_mixed_1615.json"):
        p = lesson / name
        baselines[name] = {"path": str(p), "sha256": file_hash(p)}
    return {
        "schema_version": 1, "batch_id": BATCH_ID, "lesson": "2026-09-05",
        "endpoint": ENDPOINT, "rate_usd_per_hour_estimate": rate,
        "batch_cap_usd": CAP_USD, "estimated_reserved_total_usd": total,
        "baseline_effective_no_verbatim": False, "baseline_params": BASE_PARAMS,
        "baseline_provenance": "handoff and pipeline_ext.py; historical server defaults are not independently recoverable",
        "cost_note": "Estimate at documented API rate with 5% reserve margin; actual account billing not verified.",
        "no_retry_policy": "Any attempted/uncertain request is reserved; manual reconciliation required, never blind retry.",
        "e5": "Cached per-track vs mixed comparison; zero provider calls and human scores remain pending.",
        "baselines": baselines, "arms": arms,
    }


def probe_duration(path, ffprobe="ffprobe"):
    executable = shutil.which(str(ffprobe)) or (str(ffprobe) if Path(ffprobe).is_file() else None)
    if not executable:
        raise ExperimentError("ffprobe unavailable; duration verification required before uploading")
    result = subprocess.run([executable, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    if not math.isfinite(duration) or duration <= 0:
        raise ExperimentError("Input has invalid duration")
    return duration


@dataclass
class HttpResult:
    status: int
    body: bytes
    request_id: str | None = None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # Never forward lesson audio or the credential to a redirected destination.
        return None


def http_post(path, params, key):
    boundary = "anees-" + uuid.uuid4().hex
    chunks = []
    for name, value in sorted(params.items()):
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    # Fixed generic filename does not disclose the source participant name.
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="lesson-audio.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode("utf-8"))
    chunks.extend([Path(path).read_bytes(), f"\r\n--{boundary}--\r\n".encode("utf-8")])
    request = urllib.request.Request(ENDPOINT, data=b"".join(chunks), headers={"xi-api-key": key, "Content-Type": "multipart/form-data; boundary=" + boundary}, method="POST")
    try:
        response = urllib.request.build_opener(NoRedirect()).open(request, timeout=1800)
    except urllib.error.HTTPError as error:
        return HttpResult(error.code, error.read(), error.headers.get("request-id") or error.headers.get("x-request-id"))
    with response:
        return HttpResult(response.status, response.read(), response.headers.get("request-id") or response.headers.get("x-request-id"))


def run_arm(arm, output, ledger_path, key, privacy, post=http_post, duration_probe=probe_duration):
    gate_hash = verify_privacy(privacy, key)
    path = Path(arm["input_path"])
    if not path.is_file():
        raise ExperimentError("Missing prepared audio for " + arm["id"])
    actual_duration = duration_probe(path)
    if abs(actual_duration - arm["expected_duration_s"]) > 0.3:
        raise ExperimentError("Input duration differs from registered arm: " + arm["id"])
    audio_hash = file_hash(path)
    if file_hash(arm["source_path"]) != arm["source_sha256"]:
        raise ExperimentError("Source audio changed after manifest creation")
    run_dir = Path(output) / "runs" / arm["id"]
    request_record = {**arm, "endpoint": ENDPOINT, "input_sha256": audio_hash, "actual_duration_s": round(actual_duration, 6)}
    request_hash = hashlib.sha256(canonical(request_record)).hexdigest()
    immutable_json(run_dir / "request.json", request_record)
    result_path = run_dir / "result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("request_sha256") != request_hash:
            raise ExperimentError("Existing result has different request hash")
        return {"arm": arm["id"], "status": "cached_" + result["status"], "attempted": False}
    created, entry = reserve(ledger_path, arm["id"], request_hash, arm["reserved_usd"], {"privacy_record_sha256": gate_hash})
    if not created:
        raise ExperimentError("Prior attempt/reservation exists without a final local result; reconcile manually: " + arm["id"])
    immutable_json(run_dir / "privacy-attestation.json", privacy)
    immutable_json(run_dir / "attempt.json", {"started_at": now(), "request_sha256": request_hash, "reservation": entry})
    try:
        response = post(path, arm["params"], key)
    except Exception as error:
        result = {"status": "unknown_transport_outcome", "error_type": type(error).__name__, "request_sha256": request_hash, "finished_at": now(), "reservation_retained_usd": arm["reserved_usd"]}
        immutable_json(result_path, result)
        finalize_reservation(ledger_path, arm["id"], request_hash, result["status"])
        return {"arm": arm["id"], "status": result["status"], "attempted": True}
    body = response.body
    # Do not preserve a credential even if an unexpected provider response echoes it.
    redacted = key.encode("utf-8") in body
    if redacted:
        body = body.replace(key.encode("utf-8"), b"[REDACTED_API_KEY]")
    immutable_bytes(run_dir / "response.raw.json", body)
    status = "http_error_reservation_retained"
    if response.status == 200:
        try:
            decoded = json.loads(body)
            if not isinstance(decoded, dict) or not isinstance(decoded.get("words"), list) or not isinstance(decoded.get("text"), str):
                raise ValueError("Unexpected transcript schema")
            status = "success_estimated_cost"
        except (ValueError, TypeError):
            status = "invalid_response_reservation_retained"
    result = {"status": status, "http_status": response.status, "provider_request_id": response.request_id, "request_sha256": request_hash, "response_sha256": hashlib.sha256(body).hexdigest(), "response_credential_redacted": redacted, "finished_at": now(), "reserved_usd": arm["reserved_usd"]}
    immutable_json(result_path, result)
    finalize_reservation(ledger_path, arm["id"], request_hash, status, http_status=response.status, provider_request_id=response.request_id)
    return {"arm": arm["id"], "status": status, "attempted": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--privacy-record", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--arms", help="Comma-separated IDs; omission selects all registered arms")
    parser.add_argument("--rate-usd-hour", type=float, default=0.22)
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args(argv)
    probe = lambda p: probe_duration(p, args.ffprobe)
    plan = make_plan(args.repo, args.output, args.rate_usd_hour, duration_probe=probe)
    selected = set(args.arms.split(",")) if args.arms else {x["id"] for x in plan["arms"]}
    arms = [x for x in plan["arms"] if x["id"] in selected]
    if selected != {x["id"] for x in arms}:
        raise ExperimentError("Unknown arm ID")
    if not args.execute:
        preview = {"mode": "dry_run_no_upload", "plan": plan, "selected_arms": sorted(selected), "missing_inputs": [x["input_path"] for x in arms if not Path(x["input_path"]).is_file()]}
        atomic_json(args.output / "plan-preview.json", preview)
        print(json.dumps({"mode": preview["mode"], "plan_path": str(args.output / "plan-preview.json"), "selected_arms": sorted(selected), "reserved_total_usd": plan["estimated_reserved_total_usd"], "missing_input_count": len(preview["missing_inputs"])}))
        return 0
    if not args.privacy_record:
        raise ExperimentError("--execute requires --privacy-record")
    key = credentials()
    privacy = json.loads(args.privacy_record.read_text(encoding="utf-8"))
    verify_privacy(privacy, key)
    # Validate all selected inputs before the first paid call.
    for arm in arms:
        if not Path(arm["input_path"]).is_file():
            raise ExperimentError("Prepare E4 inputs or select full-track arms first: " + arm["id"])
        if abs(probe(arm["input_path"]) - arm["expected_duration_s"]) > 0.3:
            raise ExperimentError("Audio duration differs from registered input: " + arm["id"])
    immutable_json(args.output / "manifest.json", plan)
    results = []
    for arm in arms:
        result = run_arm(arm, args.output, args.repo / "data/budget.json", key, privacy, duration_probe=probe)
        results.append(result)
        print(json.dumps(result), flush=True)
        # Fail closed on any attempted failure; operator reconciles before continuing.
        if "success" not in result["status"]:
            return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExperimentError as error:
        print("Experiment stopped: " + str(error), file=sys.stderr)
        raise SystemExit(2)
