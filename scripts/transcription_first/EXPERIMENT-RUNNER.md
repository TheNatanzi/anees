# Sep 5 controlled transcription runner

This staged implementation touches only the selected output directory and `REPO/data/budget.json` when executing. It never invokes the lesson pipeline or sends messages. Dry-run requires no key and makes no network request.

```powershell
python transcription_experiments.py --repo C:\dev\anees --output C:\Users\Mahdi\Documents\Codex\2026-09-04\do\work\takeover-2026-09-07\experiments
python -m unittest -v test_transcription_experiments.py
```

The real dry-run on Sep 5 files reserved **$0.9707** for six requests (four full Medi arms, two short event clips), including a 5% margin over the documented $0.22/hour estimate. E5 uses cached outputs and human judgments, so has no request. The E4 clips must be prepared before selecting their arms. The full-batch $1.25 cap and pre-existing service stop at $9 remain enforced. This is an estimate; the account key lacked permission to reveal billing metadata.

## Inputs

The runner resolves tracks through `data/lessons/2026-09-05/tracks/tracks.json`, mapping the recorded basenames into that local directory. Original tracks and the three baseline JSON files are hashed into the plan. **Full-track expected durations and cost estimates use actual ffprobe results**, retaining manifest durations and their discrepancies separately. It refuses changed source audio or submitted durations differing by more than 0.3 seconds from the probed full source or intended clip length. Use `--ffprobe PATH` if ffprobe is not on PATH, including for dry-run.

Prepare these clips without overwriting source audio:

- `OUTPUT/inputs/e4_medi_35_64.mp3`: Medi source-track time 35–64 seconds, surrounding event 36.57–62.42.
- `OUTPUT/inputs/e4_amal_1649_1685.mp3`: Amal source-track time 1649–1685 seconds, surrounding event 1650.924–1683.774.

Confirm local track boundaries against the raw event records. Clip-relative outputs must be offset by the request's `source_start_s` when comparing with whole-track outputs; source track/meeting start offsets remain separate. The runner does not cut or normalize audio.

## Privacy record

The parent agent must independently verify the matching account's saved, effective no-training setting. A source note is not sufficient if no account state was observed. The JSON attestation must contain:

```json
{
  "provider": "elevenlabs",
  "purpose": "asr_experiments",
  "training_opt_out": true,
  "effective": true,
  "account_match": true,
  "key_sha256": "SHA256_OF_ACTUAL_API_KEY_NOT_THE_KEY",
  "source": "Exact observation/source confirming saved effective opt-out for this credential's account",
  "verified_by": "Verifier identity",
  "verified_at": "2026-09-07T00:00:00+00:00"
}
```

The example is not an attestation and cannot clear the gate. A timezone-aware observation within seven days is required. No secret value belongs in this file. Keys load from process environment, then Windows User environment.

```powershell
python transcription_experiments.py --repo C:\dev\anees --output C:\Users\Mahdi\Documents\Codex\2026-09-04\do\work\takeover-2026-09-07\experiments --privacy-record PATH_TO_VERIFIED_RECORD --execute --ffprobe PATH_TO_FFPROBE
```

Use `--arms e1_medi_ara,e2_medi_no_diarization,e3_medi_explicit_verbatim,e3_medi_no_events` to execute only full-track arms. Later invoke the same output directory with the two E4 IDs after their clips exist. The frozen full manifest remains unchanged between subsets.

The runner must have write access to the exact `REPO/data/budget.json` and its adjacent lock/temp files. In a restricted workspace, obtain that scoped filesystem capability through the normal approval mechanism before execution; do not route around the budget ledger or substitute an untracked ledger. Key values stay in environment memory, never command arguments. Run the script directly; do not call the legacy lesson pipeline because that would invoke downstream features.

## Reservations, evidence, and recovery

- Each request has an immutable configuration, input hash, measured duration, source boundaries, and source hash.
- The provider receives a generic filename; the secret remains in the authenticated HTTPS header. HTTP redirects are not followed.
- An atomic, locked ledger update reserves the request before transmission. Unrelated fields and prior calls are preserved.
- The local result records HTTP status, provider request ID if returned, response hash, and estimated cost status. Provider response bytes are saved; an unexpected echo of the secret is redacted and that event recorded.
- No 429, 5xx, network timeout, or malformed response is automatically retried. Failed/uncertain attempts retain their whole reservation.
- Reexecution returns a cached completed result. A prior reservation without a completed local result blocks another upload until manually reconciled. A cached unsuccessful result remains unsuccessful.
- The lock is cooperative: legacy `pipeline_ext.spend()` does not honor it. Avoid an overlapping legacy pipeline run while these requests execute.
- Successful charges remain estimates until the account's billing can be inspected. Do not silently release reservations or invent actual billed amounts.

## Interpretation limits

Only the specified field changes relative to the captured baseline settings. The historical model version/defaults are not independently recoverable, and Scribe determinism is not guaranteed. A difference from an earlier call cannot by itself prove the option caused it. `no_verbatim=false` is already the documented default; that arm audits explicit versus implicit configuration. Event-clip results differ in context length, so compare with the whole-track span and listen before claiming words were hidden.

The script prepares experimental evidence. It does not manufacture human gold labels or calculate accuracy without them.
