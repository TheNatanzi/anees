# gold/ - frozen eval sets

Each AI step is scored against a named, frozen answer key: `name@version`.
A frozen set is **never edited**. A changed set is a **new version**.

| File | What it is |
|---|---|
| `manifest.json` | every set: id, status, n, sha256, source file + git commit, how and by whom it was labelled, metric, gate |
| `<name>@<version>/` | the frozen copy (byte-checked against the sha256) |
| `history.jsonl` | one line per scored run: dataset, version, sha, n, recall, precision, f1, code_sha, ts, `accepted` |
| `freeze.py` | makes new versions; `--verify` checks nothing frozen changed |

## Status today (2026-09-27)

| Set | n | Status |
|---|---|---|
| grammar@v1-tuned | 105 (79 scored) | frozen; the detector was tuned on it |
| grammar@v1-heldout | 29 (20 scored) | frozen; **the eval floor** |
| grammar@v2-audit | 1,018 (592 scored) | frozen; AI-labelled (silver), trend only |
| arabizi@v1 | 100 | frozen; 96/100 |
| sheet@v1 | 98 | frozen; 56 on list / 42 new |
| sheet@v2 | 273 | frozen; supersedes v1 |
| ladder@v1 | 30 | not saved (only totals kept) |
| asr, speaker, reader, gloss @v1 | - | to label (recipes in the manifest) |
| fsrs@v1 | - | to collect (needs `card_results` grades) |

## Commands

```bash
python gold/freeze.py --verify                                   # nothing frozen changed
python scripts/score_grammar_detector.py --no-run                # score all grammar versions, append to history
python scripts/score_grammar_detector.py --no-run --gold=grammar@v1-heldout --accept   # new floor baseline
python -m pytest tests/test_invariants.py tests/test_eval_floors.py -q
```

## Rules

- **New version:** add a spec in `freeze.py` with a new version string, then run it. It never overwrites a frozen set.
- **Floor:** recall on `grammar@v1-heldout` must stay within 2 points of the last `accepted` line in `history.jsonl`.
- **Accept** only on purpose, e.g. after Medi says yes to a trade-off.
- **Line endings:** sha256 is taken after folding CRLF to LF, and `.gitattributes` here turns EOL conversion off.
- **Two recall numbers:** v2-audit recall here is about 20%: live matching of `grammar` rows, ±20 s. The AI Reports card says 11% (104 of 961): every row kind, from the sweep's `machine_had` flag. They measure different things.
