from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests


HERE = Path(__file__).resolve().parent
CLIPS = HERE / "clips"
RAW_SOURCES = HERE / "source-vocabulary"
RECORDING = Path(r"G:\My Drive\Meet Recordings\jir-hcex-xzd (2026-09-04 14 03 GMT-7)")
CHAT = Path(str(RECORDING) + " - Chat Transcript")
SCRIBE = Path(r"C:\dev\anees\data\lessons\2026-09-04\scribe.json")
PROTOCOL = HERE / "protocol.md"
LATEST_TOPIC = Path(r"C:\Users\Mahdi\AppData\Local\Temp\browser-use\exports\Arabic Full Vocabulary list-09c6811e-e94f-4047-8b60-d9717ab8ed54.md")
ANIMALS = Path(r"C:\Users\Mahdi\AppData\Local\Temp\browser-use\exports\Arabic Full Vocabulary list-4b2938fc-b32e-453f-a43c-f13fb5715aa1.md")

MODEL = "gpt-transcribe"
PRICE_PER_MINUTE = 0.0045
SELECTED = list(range(1, 20)) + [21]
WINDOW_BEFORE = 15.0
WINDOW_AFTER = 10.0

STRICT_PROMPT = (
    "This is a one-to-one Palestinian Arabic lesson between a male learner, Medi, and his female tutor, Amal. "
    "The only languages spoken are Palestinian Arabic and English. Transcribe exactly what is audible. "
    "Write Arabic speech in Arabic script and English speech in Latin script. Never translate. "
    "Never output German, Japanese, Chinese, Azerbaijani, Spanish, or any other language. "
    "Preserve fillers, repetitions, false starts, cut-off words, wrong grammar, learner mistakes, and uncertain pronunciations. "
    "Do not silently repair Medi's speech into a fluent or correct sentence. "
    "If a sound cannot be identified, write [غير واضح] or a brief phonetic approximation instead of inventing a plausible word. "
    "Do not add explanations or speaker labels."
)

VOCAB_PROMPT_TEMPLATE = (
    "This is a one-to-one Palestinian Arabic lesson between a male learner, Medi, and his female tutor, Amal. "
    "The only languages spoken are Palestinian Arabic and English. Transcribe exactly what is audible. "
    "Write Arabic speech in Arabic script and English speech in Latin script. Never translate. "
    "Never output German, Japanese, Chinese, Azerbaijani, Spanish, or any other language. "
    "Preserve fillers, repetitions, false starts, cut-off words, wrong grammar, learner mistakes, and uncertain pronunciations. "
    "Do not silently repair Medi's speech into a fluent or correct sentence. "
    "The approved vocabulary below is context, not a correction key: prefer one of its words or an ordinary Palestinian inflection only when the audio supports it. "
    "If Medi mispronounces a listed word or produces a nonword, preserve the closest phonetic form rather than replacing it with the approved word. "
    "If a sound does not fit the list, write [غير واضح] or a brief phonetic approximation; do not invent a different Arabic word. "
    "Do not add explanations or speaker labels. APPROVED TOPIC VOCABULARY: {lexicon}"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def timestamp_seconds(value: str) -> float:
    hh, mm, ss = value.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


def parse_chat() -> list[dict]:
    text = CHAT.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    messages = []
    rx = re.compile(r"^(\d\d:\d\d:\d\d\.\d{3}),(\d\d:\d\d:\d\d\.\d{3})\r?\n([^:]+):\s*(.*)$", re.S)
    for block in blocks:
        match = rx.match(block.strip())
        if not match:
            continue
        messages.append(
            {
                "index": len(messages) + 1,
                "start_label": match.group(1),
                "end_label": match.group(2),
                "time": timestamp_seconds(match.group(1)),
                "speaker": match.group(3).strip(),
                "message": "\n".join(line.rstrip() for line in match.group(4).splitlines()).strip(),
            }
        )
    if len(messages) != 21:
        raise RuntimeError(f"Expected 21 chat messages, found {len(messages)}")
    return messages


def clean_md(value: str) -> str:
    return re.sub(r"[*_`]", "", value).strip().strip("—-").strip()


def doc_pairs(path: Path) -> list[tuple[str, str]]:
    pairs = []
    trans_idx = arabic_idx = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not (raw.startswith("|") and raw.endswith("|")):
            continue
        cells = [clean_md(x) for x in raw.strip("|").split("|")]
        lower = [x.casefold() for x in cells]
        if "transliteration" in lower and "arabic" in lower:
            trans_idx, arabic_idx = lower.index("transliteration"), lower.index("arabic")
            continue
        if trans_idx is None or arabic_idx is None or max(trans_idx, arabic_idx) >= len(cells):
            continue
        if all(re.fullmatch(r":?-{2,}:?", x.replace(" ", "")) for x in cells):
            continue
        trans, arabic = cells[trans_idx], cells[arabic_idx]
        if trans or arabic:
            pairs.append((trans, arabic))
    return pairs


def build_lexicon(selected_messages: list[dict]) -> tuple[str, dict]:
    chat_forms = []
    for message in selected_messages:
        for line in message["message"].splitlines():
            value = " ".join(line.split()).strip()
            if value:
                chat_forms.append(value)
    pairs = doc_pairs(LATEST_TOPIC) + doc_pairs(ANIMALS)
    seen_pairs = set()
    unique_pairs = []
    for trans, arabic in pairs:
        key = (trans.casefold(), arabic)
        if key not in seen_pairs:
            seen_pairs.add(key)
            unique_pairs.append((trans, arabic))
    seen_chat = set()
    unique_chat = []
    for value in chat_forms:
        key = value.casefold()
        if key not in seen_chat:
            seen_chat.add(key)
            unique_chat.append(value)
    pair_text = "; ".join(f"{a} = {b}" if b else a for a, b in unique_pairs)
    chat_text = "; ".join(unique_chat)
    block = f"CHAT FORMS: {chat_text}. LEARNED FORMS: {pair_text}."
    return block, {"chat_forms": unique_chat, "document_pairs": unique_pairs}


def generate_clips(selected_messages: list[dict]) -> list[dict]:
    CLIPS.mkdir(parents=True, exist_ok=True)
    records = []
    for message in selected_messages:
        start = max(0.0, message["time"] - WINDOW_BEFORE)
        end = message["time"] + WINDOW_AFTER
        clip = CLIPS / f"clip-{message['index']:02d}.mp3"
        if not clip.exists():
            subprocess.run(
                [
                    "ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                    "-i", str(RECORDING), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(clip),
                ],
                check=True,
            )
        records.append(
            {
                **message,
                "window_start": round(start, 3),
                "window_end": round(end, 3),
                "duration": round(end - start, 3),
                "clip": str(clip),
                "clip_sha256": sha256(clip),
                "clip_bytes": clip.stat().st_size,
            }
        )
    return records


def extract_eleven(windows: list[dict]) -> list[dict]:
    data = json.loads(SCRIBE.read_text(encoding="utf-8"))
    all_words = [w for w in data.get("words", []) if w.get("type") == "word"]
    output = []
    for window in windows:
        words = []
        for word in all_words:
            start = float(word.get("start", 0.0))
            end = float(word.get("end", start))
            midpoint = (start + end) / 2
            if window["window_start"] <= midpoint <= window["window_end"]:
                words.append(
                    {
                        "text": word.get("text", ""),
                        "start": start,
                        "end": end,
                        "speaker_id": word.get("speaker_id", "?"),
                        "logprob": word.get("logprob"),
                    }
                )
        turns = []
        for word in words:
            if turns and turns[-1]["speaker_id"] == word["speaker_id"] and word["start"] - turns[-1]["end"] < 1.25:
                turns[-1]["text"] += " " + word["text"].strip()
                turns[-1]["end"] = word["end"]
            else:
                turns.append(
                    {
                        "speaker_id": word["speaker_id"],
                        "start": word["start"],
                        "end": word["end"],
                        "text": word["text"].strip(),
                    }
                )
        output.append(
            {
                "index": window["index"],
                "window_start": window["window_start"],
                "window_end": window["window_end"],
                "chat": window["message"],
                "text": " ".join(w["text"].strip() for w in words).strip(),
                "token_count": len(words),
                "turns": turns,
                "words": words,
            }
        )
    return output


def load_result(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_result(path: Path, records: list[dict]):
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def call_openai(clip: Path, prompt: str) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    last = None
    for attempt, delay in enumerate((0, 2, 5), start=1):
        if delay:
            time.sleep(delay)
        started = time.perf_counter()
        with clip.open("rb") as audio:
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                data=[
                    ("model", MODEL),
                    ("response_format", "json"),
                    ("prompt", prompt),
                    ("languages[]", "ar"),
                    ("languages[]", "en"),
                ],
                files={"file": (clip.name, audio, "audio/mpeg")},
                timeout=300,
            )
        elapsed = time.perf_counter() - started
        last = {
            "status_code": response.status_code,
            "elapsed_seconds": round(elapsed, 3),
            "attempt": attempt,
            "response_headers": {
                "x-request-id": response.headers.get("x-request-id"),
                "openai-processing-ms": response.headers.get("openai-processing-ms"),
            },
        }
        if response.status_code == 200:
            payload = response.json()
            return {**last, "text": payload.get("text", "").strip(), "raw": payload}
        last["error"] = response.text[:1000]
        if response.status_code != 429 and response.status_code < 500:
            return last
    return last or {"status_code": None, "error": "no attempt"}


def run_arm(arm: str, prompt: str, windows: list[dict], path: Path):
    records = load_result(path)
    done = {record["index"] for record in records}
    for window in windows:
        if window["index"] in done:
            continue
        print(f"CALL {arm} clip {window['index']:02d}", flush=True)
        result = call_openai(Path(window["clip"]), prompt)
        record = {
            "index": window["index"],
            "arm": arm,
            "model": MODEL,
            "chat": window["message"],
            "window_start": window["window_start"],
            "window_end": window["window_end"],
            "duration": window["duration"],
            "clip_sha256": window["clip_sha256"],
            "estimated_audio_cost_usd": round(window["duration"] / 60 * PRICE_PER_MINUTE, 6),
            **result,
        }
        records.append(record)
        records.sort(key=lambda item: item["index"])
        save_result(path, records)
        print(
            f"DONE {arm} clip {window['index']:02d} status={record.get('status_code')} "
            f"chars={len(record.get('text', ''))} elapsed={record.get('elapsed_seconds')}s",
            flush=True,
        )


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    RAW_SOURCES.mkdir(parents=True, exist_ok=True)
    messages = parse_chat()
    selected_messages = [message for message in messages if message["index"] in SELECTED]
    lexicon, lexicon_components = build_lexicon(selected_messages)
    vocab_prompt = VOCAB_PROMPT_TEMPLATE.format(lexicon=lexicon)
    windows = generate_clips(selected_messages)

    shutil.copy2(LATEST_TOPIC, RAW_SOURCES / "latest-topic.md")
    shutil.copy2(ANIMALS, RAW_SOURCES / "animals.md")
    shutil.copy2(CHAT, RAW_SOURCES / "meet-chat.txt")

    manifest = {
        "registered_before_results": True,
        "recording": {
            "path": str(RECORDING),
            "sha256": sha256(RECORDING),
            "duration_seconds": 3876.083333,
        },
        "chat": {"path": str(CHAT), "sha256": sha256(CHAT), "message_count": len(messages)},
        "elevenlabs": {"path": str(SCRIBE), "sha256": sha256(SCRIBE), "model": "scribe_v2"},
        "protocol_sha256": sha256(PROTOCOL),
        "selection": {
            "seed": 20260904,
            "selected_indexes": SELECTED,
            "excluded_indexes": sorted(set(range(1, len(messages) + 1)) - set(SELECTED)),
            "window_before_seconds": WINDOW_BEFORE,
            "window_after_seconds": WINDOW_AFTER,
        },
        "openai": {
            "model": MODEL,
            "official_price_per_minute_usd": PRICE_PER_MINUTE,
            "strict_prompt": STRICT_PROMPT,
            "vocab_prompt": vocab_prompt,
            "lexicon_block": lexicon,
            "lexicon_components": lexicon_components,
            "planned_audio_seconds": sum(w["duration"] for w in windows) * 2,
            "planned_estimated_cost_usd": round(sum(w["duration"] for w in windows) * 2 / 60 * PRICE_PER_MINUTE, 6),
        },
        "windows": windows,
    }
    save_result(HERE / "manifest.json", manifest)
    save_result(HERE / "results-elevenlabs.json", extract_eleven(windows))

    strict_path = HERE / "results-openai-strict.json"
    vocab_path = HERE / "results-openai-vocab.json"
    strict_done = {r["index"] for r in load_result(strict_path)}
    vocab_done = {r["index"] for r in load_result(vocab_path)}
    for window in windows:
        order = [("strict", STRICT_PROMPT, strict_path), ("vocab", vocab_prompt, vocab_path)]
        if window["index"] % 2 == 0:
            order.reverse()
        for arm, prompt, path in order:
            done = strict_done if arm == "strict" else vocab_done
            if window["index"] in done:
                continue
            print(f"CALL {arm} clip {window['index']:02d}", flush=True)
            result = call_openai(Path(window["clip"]), prompt)
            records = load_result(path)
            record = {
                "index": window["index"], "arm": arm, "model": MODEL, "chat": window["message"],
                "window_start": window["window_start"], "window_end": window["window_end"],
                "duration": window["duration"], "clip_sha256": window["clip_sha256"],
                "estimated_audio_cost_usd": round(window["duration"] / 60 * PRICE_PER_MINUTE, 6), **result,
            }
            records.append(record)
            records.sort(key=lambda item: item["index"])
            save_result(path, records)
            done.add(window["index"])
            print(
                f"DONE {arm} clip {window['index']:02d} status={record.get('status_code')} "
                f"chars={len(record.get('text', ''))} elapsed={record.get('elapsed_seconds')}s",
                flush=True,
            )

    print("COMPLETE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FATAL {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
