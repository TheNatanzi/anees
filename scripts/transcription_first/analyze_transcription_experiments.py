"""Offline diagnostics for frozen Sep 5 experiments. Never uploads or writes a budget.

All metrics compare machine transcripts; none measures accuracy or human gold.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import datetime as dt
import difflib
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import unicodedata

from transcription_experiments import atomic_json, canonical, file_hash

ENGLISH_LEXICON = frozenset("""
a about actually again all almost already also always am an and another any are around as ask asked at away
back be because been before being better big bit both but by call called can can't cannot come correct could
couldn't day did didn't different do does doesn't doing don't down each else even ever every exactly example
far feel few first for forgot forget from full get getting give go goes going good got great guess had half
has have haven't having he help her here here's him his hot hour how however i i'd i'll i'm i've if in into
is isn't it it's its just keep kind know last later learn learning left lesson let let's like little long look
lot made make makes making many maybe me mean meaning means might minute more most much my need never new
next no not nothing now of off often oh okay old on once one only or other our out over own part past people
perfect person place please point present probably put question quick read really remember repeat right same
said say saying says second see seems sentence she she's should show since so some something sometimes sound
sounds speak speaking start still stop stuff sure take talk tell than thank thanks that that's the their them
then there there's these they thing things think this those though thought three through time times to today
together too took try trying turn two understand up us use used using very wait want wanted was wasn't way
we we're well went were what what's when where which while who why will with without word words work would
wouldn't yeah year yes yet you you'd you'll you're you've your yours um uh hmm ah eh mm er
""".split())
FILLERS = frozenset("um uh uhm umm uhh hmm hm ah eh mm mmm er erm".split())
LEXICON_DESCRIPTION = "Frozen hand-written common-English lexicon; words such as 'ana' and other Arabizi spellings are deliberately not classified as English. Homographs and borrowed words remain possible."
EVENT_SPANS = {
    "e4_medi_event_clip": (36.57, 62.42),
    "e4_amal_event_clip": (1650.924, 1683.774),
}


def normal(text):
    text = unicodedata.normalize("NFKC", str(text)).lower().replace("’", "'")
    return text.strip(" \t\r\n.,!?;:\"()[]{}<>—–-")


def is_arabic_letter(char):
    return unicodedata.category(char).startswith("L") and "ARABIC" in unicodedata.name(char, "")


def words(transcript):
    return [x for x in transcript.get("words", []) if x.get("type") == "word"]


def time_value(item, field):
    try:
        value = float(item[field])
        return value if math.isfinite(value) else None
    except (KeyError, TypeError, ValueError):
        return None


def select_items(transcript, start, end, offset=0.0):
    """Half-open interval by item start, using explicit source-to-comparison offset."""
    selected = []
    for item in transcript.get("words", []):
        stamp = time_value(item, "start")
        if stamp is not None and start <= stamp + offset < end:
            selected.append({**item, "start": stamp + offset, "end": (time_value(item, "end") or stamp) + offset})
    return {**transcript, "words": selected, "text": "".join(str(x.get("text", "")) for x in selected)}


def text_words(transcript):
    return " ".join(str(x.get("text", "")) for x in words(transcript))


def item_brief(item):
    return {k: item.get(k) for k in ("start", "end", "type", "text", "speaker_id")}


def surface_stats(transcript):
    stream = transcript.get("words", [])
    ws = words(transcript)
    events = [x for x in stream if x.get("type") == "audio_event"]
    stats = {
        "language_code": transcript.get("language_code"), "language_probability": transcript.get("language_probability"),
        "word_items": len(ws), "all_items": len(stream), "item_types": dict(Counter(x.get("type", "missing") for x in stream)),
        "arabic_script_word_items": sum(any(is_arabic_letter(c) for c in str(x.get("text", ""))) for x in ws),
        "legacy_arabic_block_word_items": sum(bool(re.search(r"[\u0600-\u06ff]", str(x.get("text", "")))) for x in ws),
        "arabic_block_without_arabic_letters": [item_brief(x) for x in ws if re.search(r"[\u0600-\u06ff]", str(x.get("text", ""))) and not any(is_arabic_letter(c) for c in str(x.get("text", "")))],
        "arabic_letters": sum(sum(is_arabic_letter(c) for c in str(x.get("text", ""))) for x in ws),
        "latin_script_word_items": sum(bool(re.search("[A-Za-z]", str(x.get("text", "")))) for x in ws),
        "english_lexicon_word_items": sum(normal(x.get("text", "")) in ENGLISH_LEXICON for x in ws),
        "filler_word_items": sum(normal(x.get("text", "")) in FILLERS for x in ws),
        "visible_cutoff_word_items": sum(bool(re.search(r"[-–—]+[.!?,;:'\"]*$", str(x.get("text", "")))) for x in ws),
        "audio_event_items": len(events), "event_labels": dict(Counter(str(x.get("text", "")) for x in events)),
        "speaker_ids": dict(Counter(str(x.get("speaker_id")) for x in ws)),
        "longest_audio_events": [], "longest_word_durations": [], "longest_word_start_gaps": [],
    }
    def duration(item):
        a, b = time_value(item, "start"), time_value(item, "end")
        return b - a if a is not None and b is not None else -1
    stats["longest_audio_events"] = [{**item_brief(x), "duration_s": round(duration(x), 3)} for x in sorted(events, key=duration, reverse=True)[:10]]
    stats["longest_word_durations"] = [{**item_brief(x), "duration_s": round(duration(x), 3)} for x in sorted(ws, key=duration, reverse=True)[:5]]
    timed = sorted((x for x in ws if time_value(x, "start") is not None), key=lambda x: float(x["start"]))
    gaps = []
    for before, after in zip(timed, timed[1:]):
        end = time_value(before, "end")
        start = time_value(after, "start")
        if end is not None and start > end:
            gaps.append({"start": end, "end": start, "duration_s": round(start - end, 3), "before": before["text"], "after": after["text"]})
    stats["longest_word_start_gaps"] = sorted(gaps, key=lambda x: x["duration_s"], reverse=True)[:10]
    stats["gap_warning"] = "These are gaps in recognized word coverage, not measured acoustic silence; speaker pauses or omissions are indistinguishable here."
    return stats


def english_retention(baseline, hypothesis, time_tolerance_s=2.0):
    reference = [x for x in words(baseline) if normal(x.get("text", "")) in ENGLISH_LEXICON]
    candidate = [x for x in words(hypothesis) if normal(x.get("text", "")) in ENGLISH_LEXICON]
    rc = Counter(normal(x["text"]) for x in reference)
    hc = Counter(normal(x["text"]) for x in candidate)
    lexical_overlap = sum((rc & hc).values())
    candidates = defaultdict(list)
    for index, item in enumerate(candidate):
        stamp = time_value(item, "start")
        if stamp is not None:
            candidates[normal(item["text"])].append((index, stamp))
    used = set()
    matched = 0
    missing = []
    for item in reference:
        stamp = time_value(item, "start")
        label = normal(item["text"])
        options = [] if stamp is None else [(abs(stamp - t), index) for index, t in candidates[label] if index not in used and abs(stamp - t) <= time_tolerance_s]
        if options:
            _, index = min(options)
            used.add(index)
            matched += 1
        else:
            missing.append(item_brief(item))
    denominator = len(reference)
    return {
        "description": LEXICON_DESCRIPTION,
        "denominator": "English-lexicon word items in the cached machine baseline; not human speech truth",
        "reference_count": denominator, "candidate_count": len(candidate),
        "global_multiset_overlap": lexical_overlap,
        "global_multiset_retention_fraction": lexical_overlap / denominator if denominator else None,
        "timestamp_tolerance_s": time_tolerance_s, "time_local_one_to_one_matches": matched,
        "time_local_retention_fraction": matched / denominator if denominator else None,
        "time_local_nonmatches": missing,
        "global_missing_token_counts": dict(rc - hc), "global_extra_token_counts": dict(hc - rc),
        "limitation": "Global overlap can match the wrong occurrence. Time-local greedy matching can fail from timestamp drift. Neither measures correctness, translation quality, or actual English recall.",
    }


def compare_sequences(baseline, hypothesis):
    bw, hw = words(baseline), words(hypothesis)
    raw_b, raw_h = [str(x.get("text", "")) for x in bw], [str(x.get("text", "")) for x in hw]
    nb, nh = [normal(x) for x in raw_b], [normal(x) for x in raw_h]
    matcher = difflib.SequenceMatcher(a=nb, b=nh, autojunk=False)
    counts = Counter()
    changes = []
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == "equal":
            counts["equal_normalized_baseline_items"] += b - a
            continue
        counts[tag + "_hunks"] += 1
        counts["baseline_changed_items"] += b - a
        counts["candidate_changed_items"] += d - c
        changes.append({
            "operation_relative_to_baseline": tag, "baseline_indices": [a, b], "candidate_indices": [c, d],
            "baseline_start_s": bw[a].get("start") if a < len(bw) else None,
            "candidate_start_s": hw[c].get("start") if c < len(hw) else None,
            "baseline_text": " ".join(raw_b[a:b]), "candidate_text": " ".join(raw_h[c:d]),
        })
    return {"raw_word_text_sequence_identical": raw_b == raw_h, "normalized_word_text_sequence_identical": nb == nh,
            "sequence_similarity_ratio": matcher.ratio(), "counts": dict(counts), "changes": changes,
            "warning": "Insert/delete/replace refer to differences from another machine transcript, not acoustic hallucination/error labels."}


def load_success(output, arm):
    run_dir = output / "runs" / arm["id"]
    result_file = run_dir / "result.json"
    if not result_file.is_file():
        return None, {"status": "pending_no_final_result"}
    result = json.loads(result_file.read_text(encoding="utf-8"))
    if result.get("status") != "success_estimated_cost":
        return None, result
    request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
    if hashlib.sha256(canonical(request)).hexdigest() != result["request_sha256"]:
        raise ValueError("Request hash mismatch: " + arm["id"])
    if request.get("params") != arm["params"] or request.get("source_sha256") != arm["source_sha256"]:
        raise ValueError("Request differs from manifest: " + arm["id"])
    response_path = run_dir / "response.raw.json"
    if file_hash(response_path) != result["response_sha256"]:
        raise ValueError("Response hash mismatch: " + arm["id"])
    return json.loads(response_path.read_text(encoding="utf-8")), result


def aligned_windows(review, baseline, outputs):
    result = []
    for window in review.get("windows", []):
        start, end = float(window["start"]), float(window["end"])
        row = {k: window.get(k) for k in ("id", "category", "selection_reason", "start", "end")}
        row["clock"] = "common meeting clock; per-track offsets taken from frozen review manifest"
        row["transcripts"] = {}
        for label, transcript in baseline.items():
            offset = float(review["sources"][label]["offset"]) if label in ("Medi", "Amal") else 0.0
            row["transcripts"]["baseline_" + label] = text_words(select_items(transcript, start, end, offset))
        for label, (arm, transcript) in outputs.items():
            if arm["experiment"] == "E4":
                continue
            offset = float(review["sources"]["Medi"]["offset"])
            row["transcripts"][label] = text_words(select_items(transcript, start, end, offset))
        result.append(row)
    return result


def event_html(output, events):
    def esc(value):
        return html.escape(str(value))
    blocks = []
    for event in events:
        arm = event["arm"]
        encoded_audio = base64.b64encode(Path(arm["input_path"]).read_bytes()).decode("ascii")
        embedded_audio = "data:audio/mpeg;base64," + encoded_audio
        before = event["baseline_clip"]
        after = event.get("candidate_clip")
        columns = '<section><h3>Cached full-track output in clip window</h3><pre dir="auto">' + esc(text_words(before)) + '</pre><p>Events: ' + esc(json.dumps(surface_stats(before)["event_labels"], ensure_ascii=False)) + '</p></section>'
        columns += '<section><h3>New clip-only output</h3><pre dir="auto">' + esc(text_words(after) if after else "Pending successful response") + '</pre><p>Events: ' + esc(json.dumps(surface_stats(after)["event_labels"], ensure_ascii=False) if after else "pending") + '</p></section>'
        blocks.append(f'<article><h2>{esc(arm["id"])}</h2><p>Source-track {arm["source_start_s"]:g}–{arm["source_end_s"]:g}s; tagged span {event["event_start_s"]:g}–{event["event_end_s"]:g}s.</p><audio controls preload="metadata" src="{embedded_audio}"></audio><div class="columns">{columns}</div><p class="pending">Human listening pending. Does this span contain speech, laughter, a dropout, or overlap? Neither machine output is accepted as the answer.</p></article>')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sep 5 event-span diagnostics</title><style>body{font:17px system-ui;max-width:1100px;margin:32px auto;padding:0 20px;color:#172330;background:#f7f9fb}article{background:white;padding:22px;border:1px solid #ccd6df;margin:20px 0;border-radius:14px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}pre{font:17px/1.7 system-ui;white-space:pre-wrap;overflow-wrap:anywhere}audio{width:100%}.pending{background:#fff2cb;padding:14px;border-radius:8px}@media(max-width:700px){.columns{grid-template-columns:1fr}}</style></head><body><h1>Are event tags hiding speech?</h1><p>These two embedded original-track clips and machine transcripts are for Medi and Amal to inspect. This file works without separate audio files or network access. The automated analysis cannot determine what is audible. No human gold label has been inferred or exported.</p>' + "".join(blocks) + '</body></html>'


def render_markdown(report):
    lines = ["# Sep 5 experiment diagnostics", "", "These are mechanical differences between machine transcripts, not transcription accuracy. Human gold and acoustic judgments remain pending.", "",
             f"Successful responses analyzed: **{report['successful_count']}/{report['registered_count']}**. Generated {report['generated_at']}.", "", "All six paid requests have final successful outputs when the count is 6/6. **E4 acoustic review and E5 human comparison scores remain pending.** The review page creates the workflow for collecting gold; these outputs are not a completed gold set.", "",
             "## Surface measurements", "", "| Output | Word items | Arabic-script items | Latin-script items | Common-English items | Fillers | Cutoffs | Event items |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    stats = {"cached_Medi": report["baseline_stats"]["Medi"], "cached_Amal": report["baseline_stats"]["Amal"], "cached_mixed": report["baseline_stats"]["cached_mixed"]}
    stats.update({k: v["surface"] for k, v in report["comparisons"].items()})
    for label, s in stats.items():
        lines.append("| " + " | ".join(str(x) for x in [label, s["word_items"], s["arabic_script_word_items"], s["latin_script_word_items"], s["english_lexicon_word_items"], s["filler_word_items"], s["visible_cutoff_word_items"], s["audio_event_items"]]) + " |")
    punctuation = report["baseline_stats"]["Medi"]["arabic_block_without_arabic_letters"]
    punctuation_examples = "; ".join(f"`{x['text']}` at {x['start']}s" for x in punctuation)
    lines += ["", "Arabic-script counts above require at least one Unicode letter whose Unicode name contains ARABIC. A broad U+0600–U+06FF test also counts Arabic punctuation attached to English. For cached Medi, that gives 257 broad-block items versus 254 Arabic-letter items: " + punctuation_examples + ". This classifier difference explains the separate audit's 257; the underlying bytes agree.", "", "## Full-track comparison against cached Medi", "", "Common-English membership is a fixed lexicon heuristic; other Latin text may be Arabizi. Retention refers to cached tokens, not correct speech. These figures cannot establish complete English survival or transcription accuracy. Time-local matches are one-to-one within ±2 seconds of cached timestamps.", "", "| Arm | Exact raw word sequence? | Normalized sequence ratio | Global English token overlap | Time-local English token matches |", "|---|---|---:|---:|---:|"]
    for label, value in report["comparisons"].items():
        if value["experiment"] == "E4":
            continue
        er, seq = value["english_retention"], value["sequence"]
        lines.append(f"| {label} | {seq['raw_word_text_sequence_identical']} | {seq['sequence_similarity_ratio']:.4f} | {er['global_multiset_overlap']}/{er['reference_count']} | {er['time_local_one_to_one_matches']}/{er['reference_count']} |")
    contemporary = report.get("contemporary_no_events_vs_explicit_verbatim")
    if contemporary:
        lines += ["", "### Contemporary E3 comparison", "", f"Compare `e3_medi_no_events` with `e3_medi_explicit_verbatim`, since both explicitly set `no_verbatim=false`. Their raw word sequences are identical: **{contemporary['raw_word_text_sequence_identical']}**; normalized sequence similarity is **{contemporary['sequence_similarity_ratio']:.4f}**. This is the closest configured comparison for event tagging, but each arm ran once and inference stochasticity remains a confound. A tag disappearing is expected when tags are disabled; it is not proof that hidden speech was recovered."]
    lines += ["", "## Event spans", "", "The current analysis cannot listen to audio. Open `e4-event-diagnostics.html` and have Medi/Amal confirm the acoustic content before calling any tag an error.", ""]
    for event in report["events"]:
        lines.extend([f"### {event['arm']['id']}", "", f"Clip source time {event['arm']['source_start_s']}–{event['arm']['source_end_s']}s; tagged span {event['event_start_s']}–{event['event_end_s']}s.", "", "Cached full-track word items in clip:", "", "```text", text_words(event["baseline_clip"]), "```", "", "New clip-only word items:", "", "```text", text_words(event["candidate_clip"]) if event.get("candidate_clip") else "Pending", "```", ""])
    lines += ["## Limits on interpretation", ""] + ["- " + x for x in report["limitations"]]
    lines += ["", "## Evidence integrity", "", "Baseline hashes and successful request/response hashes were checked against frozen records. Failed or unfinished outputs are excluded from metrics. This script did not call any provider, touch the budget ledger, or create human judgments.", "", "The JSON contains all changed sequence hunks, longest event spans and word-coverage gaps. `window-comparisons.md` contains frozen-window text when a review manifest was supplied.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Experiment directory with manifest.json and runs/")
    parser.add_argument("--review-manifest", type=Path)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    baseline = {}
    for label, name in (("Medi", "scribe_Medi.json"), ("Amal", "scribe_Amal.json"), ("cached_mixed", "scribe_meet_mixed_1615.json")):
        record = manifest["baselines"][name]
        if file_hash(record["path"]) != record["sha256"]:
            raise ValueError("Frozen baseline hash mismatch: " + name)
        baseline[label] = json.loads(Path(record["path"]).read_text(encoding="utf-8"))
    report = {
        "schema_version": 1, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "manifest_sha256": file_hash(manifest_path), "registered_count": len(manifest["arms"]),
        "baseline_stats": {label: surface_stats(t) for label, t in baseline.items()},
        "statuses": {}, "comparisons": {}, "events": [],
        "english_lexicon": sorted(ENGLISH_LEXICON),
        "limitations": [
            "No human verbatim gold exists in these machine outputs. Counts, script choice, token overlap and model agreement are not accuracy.",
            "The baseline is a historical full-track call. Exact server version, hidden defaults and inference determinism are not established; time/model drift can confound causal claims.",
            "no_verbatim=false is already the documented default. Differences after making it explicit do not establish an improved verbatim setting.",
            "The no-diarization arm also removes num_speakers because it is inapplicable when speaker annotation is disabled. This paired configuration change is recorded, not an independent speaker-count experiment.",
            "The no-event arm combines explicit no_verbatim=false with tag_audio_events=false. Its clean comparison is the explicit-verbatim arm, with stochasticity still possible.",
            "E4 changes context length and introduces clip encoding/boundaries. Any new word must be confirmed by listening before declaring the full-track tag hid speech.",
            "The current session lacks supported audio-input listening; both E4 acoustic questions remain pending human review.",
            "Twenty review windows were chosen from previously inspected cached outputs. They are diagnostic calibration windows, not an unseen held-out evaluation.",
            "Common-English lexicon retention is a heuristic relative to cached text, with possible homographs, repeated-word matching and timestamp drift.",
            "Cached mixed-recording identity and time alignment must follow the review manifest's provenance; its filename alone does not prove an independent Meet recording.",
        ],
    }
    outputs = {}
    for arm in manifest["arms"]:
        transcript, result = load_success(output, arm)
        report["statuses"][arm["id"]] = result.get("status")
        base = baseline["Amal" if "amal" in arm["id"] else "Medi"]
        if arm["experiment"] == "E4":
            event_start, event_end = EVENT_SPANS[arm["id"]]
            before = select_items(base, arm["source_start_s"], arm["source_end_s"])
            after = select_items(transcript, arm["source_start_s"], arm["source_end_s"], arm["source_start_s"]) if transcript else None
            report["events"].append({"arm": arm, "event_start_s": event_start, "event_end_s": event_end, "baseline_clip": before, "candidate_clip": after, "baseline_inside_tagged_span": select_items(base, event_start, event_end), "candidate_inside_tagged_span": select_items(transcript, event_start, event_end, arm["source_start_s"]) if transcript else None, "acoustic_judgment": "pending_human_listening"})
            base = before
        else:
            after = transcript
        if not transcript:
            continue
        outputs[arm["id"]] = (arm, transcript)
        report["comparisons"][arm["id"]] = {"experiment": arm["experiment"], "surface": surface_stats(transcript), "sequence": compare_sequences(base, after), "english_retention": english_retention(base, after)}
    report["successful_count"] = len(outputs)
    if "e3_medi_explicit_verbatim" in outputs and "e3_medi_no_events" in outputs:
        report["contemporary_no_events_vs_explicit_verbatim"] = compare_sequences(outputs["e3_medi_explicit_verbatim"][1], outputs["e3_medi_no_events"][1])
    report["windows"] = []
    if args.review_manifest:
        review = json.loads(args.review_manifest.read_text(encoding="utf-8"))
        report["review_manifest_sha256"] = file_hash(args.review_manifest)
        report["windows"] = aligned_windows(review, baseline, outputs)
        lines = ["# Frozen diagnostic-window machine transcripts", "", "Offsets use the frozen review manifest. None of these texts is human gold. Medi/Amal raw tracks are kept separate; the cached mixed output is a third comparison.", ""]
        for window in report["windows"]:
            lines += [f"## {window['id']} · {window['start']}–{window['end']}s · {window['category']}", ""]
            for label, text in window["transcripts"].items():
                lines += ["### " + label, "", "```text", text, "```", ""]
        (output / "window-comparisons.md").write_text("\n".join(lines), encoding="utf-8")
    atomic_json(output / "experiment-findings.json", report)
    (output / "experiment-findings.md").write_text(render_markdown(report), encoding="utf-8")
    (output / "e4-event-diagnostics.html").write_text(event_html(output, report["events"]), encoding="utf-8")
    print(json.dumps({"successful_count": report["successful_count"], "registered_count": report["registered_count"], "windows": len(report["windows"]), "findings": str(output / "experiment-findings.md")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
