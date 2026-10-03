# -*- coding: utf-8 -*-
"""Open speech models on this PC's GPU for the engine benchmark (PR-18). No network, no cost.

    python scripts/bench_local.py 2026-10-02 cohere-open [runs]     # CohereLabs/cohere-transcribe-arabic-07-2026, language ar
    python scripts/bench_local.py 2026-10-02 audar-open [runs]      # audarai/Audar-ASR-V1-Turbo, language detected by the model
    python scripts/bench_local.py 2026-10-02 audar-open-ar [runs]   # the same, language forced to Arabic

Per-line clips only: neither model returns word times, so a whole-file run cannot be laid on the lesson's lines.
Both load their own model code from the model folder (read 2026-10-03: no network, file or process calls beyond
torch / transformers / librosa; Cohere's optional decode worker process is left off).
"""
import os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench_common as BC  # noqa: E402

MODELS = r"C:\dev\models"


def clips(date):
    d = BC.bench_dir(date)
    truth = BC.J(os.path.join(d, "truth.json"))
    items = [(str(ln["i"]), os.path.join(d, ln["clip"])) for ln in truth["lines"]]
    items += [("A%d" % ln["i"], os.path.join(d, ln["clip"])) for ln in truth["amal_lines"]]
    return items


def run_cohere(items):
    import torch
    import importlib.util
    p = os.path.join(MODELS, "cohere-transcribe-arabic-07-2026")
    # The folder's own classes, loaded as a package: its config has no auto_map (it targets transformers >= 5.4, this PC
    # is pinned to 4.57.6 for Audar), so AutoProcessor / AutoModel cannot find them.
    spec = importlib.util.spec_from_file_location("cohere_asr_local", os.path.join(p, "modeling_cohere_asr.py"), submodule_search_locations=[p])
    pkg = importlib.util.module_from_spec(importlib.util.spec_from_loader("cohere_asr_local", loader=None, is_package=True))
    pkg.__path__ = [p]
    sys.modules["cohere_asr_local"] = pkg
    mods = {}
    for name in ("configuration_cohere_asr", "tokenization_cohere_asr", "processing_cohere_asr", "modeling_cohere_asr"):
        sp = importlib.util.spec_from_file_location("cohere_asr_local." + name, os.path.join(p, name + ".py"))
        mods[name] = importlib.util.module_from_spec(sp)
        sys.modules["cohere_asr_local." + name] = mods[name]
        sp.loader.exec_module(mods[name])
    # The front end's settings live in config.json "preprocessor" (the folder's preprocessor_config.json is empty of them).
    pre = BC.J(os.path.join(p, "config.json"))["preprocessor"]
    P = mods["processing_cohere_asr"]
    fe = P.CohereAsrFeatureExtractor(feature_size=pre["features"], sampling_rate=pre["sample_rate"], n_window_size=int(pre["window_size"] * pre["sample_rate"]),
                                     n_window_stride=int(pre["window_stride"] * pre["sample_rate"]), window=pre["window"], normalize=pre["normalize"],
                                     n_fft=pre["n_fft"], log=pre["log"], dither=pre["dither"], pad_to=pre["pad_to"], padding_value=pre["pad_value"],
                                     frame_splicing=pre["frame_splicing"])
    from pathlib import Path
    P._maybe_load_preprocessor_buffers_from_checkpoint(feature_extractor=fe, model_dir=Path(p))
    tok = mods["tokenization_cohere_asr"].CohereAsrTokenizer.from_pretrained(p)
    proc = mods["processing_cohere_asr"].CohereAsrProcessor(feature_extractor=fe, tokenizer=tok)
    cfg = mods["configuration_cohere_asr"].CohereAsrConfig.from_pretrained(p)
    from transformers import GenerationMixin

    class Model(mods["modeling_cohere_asr"].CohereAsrForConditionalGeneration, GenerationMixin):   # 4.57: generate() is a mixin
        pass

    model = Model.from_pretrained(p, config=cfg, torch_dtype=torch.bfloat16).to("cuda").eval()
    out = {}
    with torch.inference_mode():
        for k in range(0, len(items), 16):
            batch = items[k:k + 16]
            texts = model.transcribe(proc, language="ar", audio_files=[f for _, f in batch], batch_size=16)
            for (i, _), t in zip(batch, texts):
                out[i] = {"text": t}
            print("cohere", k + len(batch), "/", len(items), flush=True)
    return out, "CohereLabs/cohere-transcribe-arabic-07-2026 (local, bf16, language=ar)"


def run_audar(items, force=None):
    import soundfile as sf
    import torch
    from transformers import AutoModel, AutoProcessor
    p = os.path.join(MODELS, "Audar-ASR-V1-Turbo")
    proc = AutoProcessor.from_pretrained(p, trust_remote_code=True)
    model = AutoModel.from_pretrained(p, trust_remote_code=True, torch_dtype=torch.bfloat16).to("cuda").eval()
    msgs = [{"role": "system", "content": ""}, {"role": "user", "content": [{"type": "audio", "audio": ""}]}]
    prompt = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    if force:
        prompt += "language %s<asr_text>" % force
    out = {}
    with torch.inference_mode():
        for n, (i, f) in enumerate(items):
            wav, sr = sf.read(f, dtype="float32")
            assert sr == 16000
            if len(wav) > 30 * sr:
                wav = wav[:30 * sr]                      # the model's 30 s window (no clip of 10-02 is longer than 14 s)
            inp = proc(text=[prompt], audio=[wav], return_tensors="pt", padding=True).to("cuda")
            inp = {k: (v.to(torch.bfloat16) if v.is_floating_point() else v) for k, v in inp.items()}
            res = model.generate(**inp, max_new_tokens=256, do_sample=False)
            seq = res.sequences[0][inp["input_ids"].shape[1]:]
            txt = proc.tokenizer.decode(seq, skip_special_tokens=True)
            lang = None
            m = re.match(r"\s*language\s+(\w+)\s*(?:<asr_text>)?", txt)
            if m and not force:
                lang, txt = m.group(1), txt[m.end():]
            out[i] = {"text": txt.replace("<asr_text>", " ").strip(), "language": lang or force}
            if n % 50 == 49:
                print("audar", n + 1, "/", len(items), flush=True)
    return out, "audarai/Audar-ASR-V1-Turbo (local, bf16, language=%s)" % (force or "auto")


def main(argv):
    date, engine = argv[0], argv[1]
    runs = int(argv[2]) if len(argv) > 2 else 3
    items = clips(date)
    for n in range(1, runs + 1):
        p = os.path.join(BC.bench_dir(date), engine, "line-run%d.json" % n)
        if os.path.exists(p):
            continue
        t0 = time.time()
        if engine == "cohere-open":
            lines, model = run_cohere(items)
        elif engine in ("audar-open", "audar-open-ar"):
            lines, model = run_audar(items, "Arabic" if engine.endswith("-ar") else None)
        else:
            raise SystemExit("unknown local engine " + engine)
        BC.W(p, {"engine": engine, "mode": "line", "run": n, "model": model, "seconds": time.time() - t0, "cost_usd": 0.0, "lines": lines})
        print(engine, "run", n, "%.0f s" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
