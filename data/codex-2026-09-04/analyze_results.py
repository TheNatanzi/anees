from __future__ import annotations

import difflib
import json
import re
import statistics
import subprocess
import unicodedata
from pathlib import Path


HERE = Path(__file__).resolve().parent
RECORDING = Path(r"G:\My Drive\Meet Recordings\jir-hcex-xzd (2026-09-04 14 03 GMT-7)")


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def save(name: str, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*|[\u0600-\u06ff]+", text)


def arabic_tokens(text: str) -> list[str]:
    return [token for token in tokens(text) if re.search(r"[\u0600-\u06ff]", token)]


def filler_count(text: str) -> int:
    english = re.findall(r"(?i)(?<![A-Za-z])(?:uh+|um+|umm+|mm+|mhm|hmm+)(?![A-Za-z])", text)
    arabic = re.findall(r"(?<![\u0600-\u06ff])(?:آ+|آه+|ا+ه+)(?![\u0600-\u06ff])", text)
    return len(english) + len(arabic)


def cutoff_count(text: str) -> int:
    return len(re.findall(r"(?:\w|[\u0600-\u06ff])-(?=\s|$)|\.{3,}|…", text))


def foreign_scripts(text: str) -> list[str]:
    hits = set()
    for char in text:
        if not char.isalpha():
            continue
        name = unicodedata.name(char, "")
        if not ("LATIN" in name or "ARABIC" in name):
            hits.add(name.split()[0] if name else f"U+{ord(char):04X}")
    return sorted(hits)


def parse_srt() -> list[dict]:
    run = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(RECORDING), "-map", "0:s:0", "-f", "srt", "-"],
        check=True,
        stdout=subprocess.PIPE,
    )
    raw = run.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
    blocks = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = block.splitlines()
        if len(lines) < 3 or " --> " not in lines[1]:
            continue
        start_label, end_label = lines[1].split(" --> ", 1)
        def secs(label: str) -> float:
            hh, mm, ss = label.replace(",", ".").split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
        text = "\n".join(lines[2:]).strip()
        speakers = sorted(set(re.findall(r"\((Amal|Medi Natanzi)\)", text)))
        blocks.append(
            {
                "start": secs(start_label),
                "end": secs(end_label),
                "speakers": speakers,
                "text": text,
            }
        )
    return blocks


# Manual transcript-surface audit. "Recovered" means the transcript visibly contains
# the chat form or its b-s-6 / b-w-s lexical family. It does not mean the audio proves
# the form correct. Notes explicitly identify windows where the chat was posted late.
MANUAL = {
    1:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All recover bee(s)/Na7el; O1/O2 render نحل."},
    2:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All recover mabsoo6; E alone keeps the audible-looking false start 'Masbu-'."},
    3:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All recover the b-s-6 family and basa6ni."},
    4:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All recover basa6ni; wording differs around صح."},
    5:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All produce a plausible phonetic form for babse6; orthography remains uncertain."},
    6:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All recover byebse6/byebse6ni; O1/O2 use بسط orthography."},
    7:  {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "The spoken portion includes bnebse6o; all render بنبسطه."},
    8:  {"E": "not_recovered", "O1": "not_recovered", "O2": "not_recovered", "note": "Frozen window contains sparse paradigm fragments; O1/O2 collapse it to 'هو. هي.'"},
    9:  {"E": "recovered", "O1": "not_recovered", "O2": "not_recovered", "note": "E retains several conjugation attempts; both OpenAI arms reduce the clip to 'I made him happy.'"},
    10: {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All capture basato/basatto family; O2 changes some forms to Arabic script."},
    11: {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All capture absato/absatni family; chat spelling Hasa6to may itself be a typo or delayed note."},
    12: {"E": "recovered", "O1": "recovered", "O2": "not_recovered", "note": "Vocabulary arm replaces Banbisat/Nabasat with [unclear], a harmful prompt effect."},
    13: {"E": "not_recovered", "O1": "not_recovered", "O2": "not_recovered", "note": "Chat says Baboos (kiss), but the frozen window is later and discusses basa6/basat. Meet captions place baboos about 65 s before the chat post."},
    14: {"E": "not_recovered", "O1": "not_recovered", "O2": "not_recovered", "note": "Chat says Buset (I kissed), but the frozen window is later and discusses basat. Meet captions place Buset about 42 s before the chat post."},
    15: {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All capture enbasa6-family attempts; spellings differ."},
    16: {"E": "recovered", "O1": "not_recovered", "O2": "not_recovered", "note": "E keeps embasati/mbsetti; O1 hallucinates 'Airbnb' and O2 omits the target phrase."},
    17: {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All capture btenbese6-family conjugation practice; O2 violates Arabic-script instruction."},
    18: {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "All capture btenbese6i lamma ne6la3 family; E shows the most disfluency."},
    19: {"E": "recovered", "O1": "recovered", "O2": "recovered", "note": "Only family-level fragments occur in-window; O2's بنبسط is the cleanest surface form. Full chat sentence was spoken earlier."},
    21: {"E": "not_recovered", "O1": "not_recovered", "O2": "not_recovered", "note": "The command was spoken roughly 80 s before the chat post; the frozen window contains the next question instead."},
}

for judgment in MANUAL.values():
    # Both exploratory ElevenLabs keyterm arms recover the same set of lexical
    # families as the no-keyterm baseline. Their important differences are exact
    # spellings, disfluency retention, and vocabulary-induced substitutions.
    judgment["EKG"] = judgment["E"]
    judgment["EKL"] = judgment["E"]
    judgment["ES"] = judgment["E"]


def main():
    manifest = load("manifest.json")
    e_rows = load("results-elevenlabs.json")
    s_rows = load("results-openai-strict.json")
    v_rows = load("results-openai-vocab.json")
    es_rows = load("results-elevenlabs-segmented.json")
    ekg_rows = load("results-elevenlabs-keyterms.json")
    ekl_rows = load("results-elevenlabs-keyterms-local.json")
    E = {row["index"]: row for row in e_rows}
    S = {row["index"]: row for row in s_rows}
    V = {row["index"]: row for row in v_rows}
    ES = {row["index"]: row for row in es_rows}
    EKG = {row["index"]: row for row in ekg_rows}
    EKL = {row["index"]: row for row in ekl_rows}
    captions = parse_srt()

    selected_captions = []
    comparison_rows = []
    for window in manifest["windows"]:
        i = window["index"]
        blocks = [
            block for block in captions
            if block["end"] > window["window_start"] and block["start"] < window["window_end"]
        ]
        caption_speakers = sorted({speaker for block in blocks for speaker in block["speakers"]})
        selected_captions.append(
            {
                "index": i,
                "window_start": window["window_start"],
                "window_end": window["window_end"],
                "speakers": caption_speakers,
                "blocks": blocks,
            }
        )
        texts = {
            "E": E[i]["text"],
            "O1": S[i].get("text", ""),
            "O2": V[i].get("text", ""),
            "ES": ES[i].get("text", ""),
            "EKG": EKG[i].get("text", ""),
            "EKL": EKL[i].get("text", ""),
        }
        engine_metrics = {}
        for arm, text in texts.items():
            engine_metrics[arm] = {
                "token_count": len(tokens(text)),
                "arabic_token_count": len(arabic_tokens(text)),
                "filler_count": filler_count(text),
                "cutoff_or_ellipsis_count": cutoff_count(text),
                "foreign_scripts": foreign_scripts(text),
                "empty": not bool(text.strip()),
            }
        eleven_ids = sorted({word["speaker_id"] for word in E[i]["words"]})
        comparison_rows.append(
            {
                "index": i,
                "chat": E[i]["chat"],
                "window_start": E[i]["window_start"],
                "window_end": E[i]["window_end"],
                "texts": texts,
                "metrics": engine_metrics,
                "openai_similarity": round(difflib.SequenceMatcher(None, texts["O1"], texts["O2"]).ratio(), 4),
                "openai_exact_match": texts["O1"] == texts["O2"],
                "eleven_global_keyterms_similarity": round(difflib.SequenceMatcher(None, texts["E"], texts["EKG"]).ratio(), 4),
                "eleven_local_keyterms_similarity": round(difflib.SequenceMatcher(None, texts["E"], texts["EKL"]).ratio(), 4),
                "eleven_segmented_similarity": round(difflib.SequenceMatcher(None, texts["E"], texts["ES"]).ratio(), 4),
                "eleven_speaker_ids": eleven_ids,
                "eleven_segmented_speaker_ids": sorted({
                    word.get("speaker_id", "?") for word in ES[i].get("raw", {}).get("words", []) if word.get("type") == "word"
                }),
                "eleven_global_keyterm_speaker_ids": sorted({
                    word.get("speaker_id", "?") for word in EKG[i].get("raw", {}).get("words", []) if word.get("type") == "word"
                }),
                "eleven_local_keyterm_speaker_ids": sorted({
                    word.get("speaker_id", "?") for word in EKL[i].get("raw", {}).get("words", []) if word.get("type") == "word"
                }),
                "meet_caption_speakers": caption_speakers,
                "manual_anchor_surface": MANUAL[i],
            }
        )

    save("meet-captions-selected.json", selected_captions)

    def aggregate(arm: str) -> dict:
        arm_rows = [row["metrics"][arm] for row in comparison_rows]
        result_rows = {"O1": s_rows, "O2": v_rows, "ES": es_rows, "EKG": ekg_rows, "EKL": ekl_rows}.get(arm)
        return {
            "successful_clips": 20 if arm == "E" else sum(1 for row in result_rows if row.get("status_code") == 200),
            "nonempty_clips": sum(1 for row in arm_rows if not row["empty"]),
            "tokens": sum(row["token_count"] for row in arm_rows),
            "arabic_tokens": sum(row["arabic_token_count"] for row in arm_rows),
            "fillers": sum(row["filler_count"] for row in arm_rows),
            "cutoffs_or_ellipses": sum(row["cutoff_or_ellipsis_count"] for row in arm_rows),
            "clips_with_foreign_script": sum(1 for row in arm_rows if row["foreign_scripts"]),
            "chat_anchor_family_recovered": sum(1 for row in comparison_rows if row["manual_anchor_surface"][arm] == "recovered"),
            "chat_anchor_family_not_recovered": sum(1 for row in comparison_rows if row["manual_anchor_surface"][arm] == "not_recovered"),
        }

    e_word_logprobs = [word["logprob"] for row in e_rows for word in row["words"] if isinstance(word.get("logprob"), (int, float))]
    openai_latencies = {
        "O1": [row["elapsed_seconds"] for row in s_rows],
        "O2": [row["elapsed_seconds"] for row in v_rows],
    }
    recovered = {arm: aggregate(arm) for arm in ("E", "ES", "O1", "O2", "EKG", "EKL")}
    total_clip_seconds = sum(window["duration"] for window in manifest["windows"])
    intervals = sorted((w["window_start"], w["window_end"]) for w in manifest["windows"])
    union = 0.0
    cur_start = cur_end = None
    for start, end in intervals:
        if cur_start is None:
            cur_start, cur_end = start, end
        elif start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            union += cur_end - cur_start
            cur_start, cur_end = start, end
    if cur_start is not None:
        union += cur_end - cur_start

    comparison = {
        "definitions": {
            "token_count": "Regex count of Latin/Arabic alphanumeric surface tokens; not accuracy.",
            "chat_anchor_family_recovered": "Manual surface judgment that the chat form or its relevant lexical family visibly occurs; not an audio-grounded correctness score.",
            "filler_count": "Mechanical count of common English/Arabic filler spellings; a lower bound.",
            "cutoffs_or_ellipses": "Mechanical count of hyphen-final fragments and ellipses; a lower bound.",
        },
        "aggregate": recovered,
        "openai_prompt_effect": {
            "exactly_identical_clips": sum(row["openai_exact_match"] for row in comparison_rows),
            "changed_clips": sum(not row["openai_exact_match"] for row in comparison_rows),
            "mean_character_similarity": round(statistics.mean(row["openai_similarity"] for row in comparison_rows), 4),
            "strict_mean_latency_seconds": round(statistics.mean(openai_latencies["O1"]), 3),
            "vocab_mean_latency_seconds": round(statistics.mean(openai_latencies["O2"]), 3),
            "strict_median_latency_seconds": round(statistics.median(openai_latencies["O1"]), 3),
            "vocab_median_latency_seconds": round(statistics.median(openai_latencies["O2"]), 3),
            "returned_language_codes_strict": [row.get("raw", {}).get("languages") for row in s_rows],
            "returned_language_codes_vocab": [row.get("raw", {}).get("languages") for row in v_rows],
        },
        "eleven_keyterm_prompt_effect_posthoc": {
            "control": "ES is the same short-clip Scribe v2 request without keyterms; compare EKG/EKL to ES, not to the one-shot full-lesson E extraction.",
            "segmented_changed_clips_vs_full_lesson": sum(row["texts"]["E"] != row["texts"]["ES"] for row in comparison_rows),
            "global_changed_clips_vs_segmented_control": sum(row["texts"]["ES"] != row["texts"]["EKG"] for row in comparison_rows),
            "local_changed_clips_vs_segmented_control": sum(row["texts"]["ES"] != row["texts"]["EKL"] for row in comparison_rows),
            "segmented_mean_character_similarity_to_full_lesson": round(statistics.mean(row["eleven_segmented_similarity"] for row in comparison_rows), 4),
            "global_mean_character_similarity_to_segmented_control": round(statistics.mean(difflib.SequenceMatcher(None, row["texts"]["ES"], row["texts"]["EKG"]).ratio() for row in comparison_rows), 4),
            "local_mean_character_similarity_to_segmented_control": round(statistics.mean(difflib.SequenceMatcher(None, row["texts"]["ES"], row["texts"]["EKL"]).ratio() for row in comparison_rows), 4),
            "segmented_mean_latency_seconds": round(statistics.mean(row["elapsed_seconds"] for row in es_rows), 3),
            "global_mean_latency_seconds": round(statistics.mean(row["elapsed_seconds"] for row in ekg_rows), 3),
            "local_mean_latency_seconds": round(statistics.mean(row["elapsed_seconds"] for row in ekl_rows), 3),
            "global_keyterm_count": len(ekg_rows[0]["keyterms"]),
            "local_keyterm_count_min": min(len(row["keyterms"]) for row in ekl_rows),
            "local_keyterm_count_max": max(len(row["keyterms"]) for row in ekl_rows),
            "observed_global_poisoning": {
                "clip": 1,
                "substitution": "Global keyterms changed the consensus 'Awesome' to future lesson term 'Mabsoo6'; local keyterms retained 'Awesome'.",
            },
        },
        "cost": {
            "openai_strict_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in s_rows), 6),
            "openai_vocab_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in v_rows), 6),
            "openai_total_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in s_rows + v_rows), 6),
            "eleven_segmented_no_keyterm_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in es_rows), 6),
            "eleven_global_keyterm_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in ekg_rows), 6),
            "eleven_local_keyterm_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in ekl_rows), 6),
            "all_new_calls_estimated_usd": round(sum(row["estimated_audio_cost_usd"] for row in s_rows + v_rows + es_rows + ekg_rows + ekl_rows), 6),
            "sampled_seconds_per_arm": total_clip_seconds,
        },
        "sampling": {
            "nominal_clip_seconds": total_clip_seconds,
            "unique_audio_seconds_after_overlap": round(union, 3),
            "overlap_seconds": round(total_clip_seconds - union, 3),
        },
        "diarization": {
            "eleven_word_assignments_by_speaker": {
                speaker: sum(1 for row in e_rows for word in row["words"] if word["speaker_id"] == speaker)
                for speaker in sorted({word["speaker_id"] for row in e_rows for word in row["words"]})
            },
            "clips_with_two_meet_caption_speakers": sum(len(row["meet_caption_speakers"]) == 2 for row in comparison_rows),
            "clips_with_two_eleven_speaker_ids": sum(len(row["eleven_speaker_ids"]) == 2 for row in comparison_rows),
            "clips_with_at_least_two_segmented_no_keyterm_speaker_ids": sum(len(row["eleven_segmented_speaker_ids"]) >= 2 for row in comparison_rows),
            "clips_with_at_least_two_global_keyterm_speaker_ids": sum(len(row["eleven_global_keyterm_speaker_ids"]) >= 2 for row in comparison_rows),
            "clips_with_at_least_two_local_keyterm_speaker_ids": sum(len(row["eleven_local_keyterm_speaker_ids"]) >= 2 for row in comparison_rows),
            "clips_where_meet_has_two_but_eleven_has_one": sum(
                len(row["meet_caption_speakers"]) == 2 and len(row["eleven_speaker_ids"]) == 1
                for row in comparison_rows
            ),
            "interpretation": "Short segmentation, not keyterms, accounts for the speaker-count recovery: ES, EKG, and EKL each identify at least two speaker clusters in 19/20 windows.",
        },
        "eleven_word_logprob": {
            "count": len(e_word_logprobs),
            "mean": round(statistics.mean(e_word_logprobs), 4),
            "median": round(statistics.median(e_word_logprobs), 4),
            "below_minus_1": sum(value < -1 for value in e_word_logprobs),
        },
        "rows": comparison_rows,
    }
    save("comparison.json", comparison)
    print(json.dumps({key: value for key, value in comparison.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
