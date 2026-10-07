# Reference lexicon — secondary source only (rule AM-25)

Medi 2026-10-06: "Lets spin up a new agent to do deep research on different levantine arabic curriculum that you can
create an index for yourself to use as a secondary data source, it may be useful to amal to help her" — "ingest".

**What it is.** Open Levantine dictionaries merged into one lookup file, `docs/data/reference-lexicon.json`, read
for **glosses, roots, plurals, example sentences and verb-preposition hints** only.

**What it is not (RULES.md S1).** Not a spelling and not a score. Amal's Doc (`docs/data/words.json`) is the only
word truth and her spelling the only spelling; nothing from here is written into her data, shown as a spelling, or
used to score a word. The lookup helper is `docs/js/reference-lexicon.js` (pure; `load`, `find`, `glossFor`).

The research behind the choice of sources: [docs/reference/LEVANTINE-CURRICULUM-INDEX.md](../../docs/reference/LEVANTINE-CURRICULUM-INDEX.md)
(every Levantine course, lexicon and corpus found on 2026-10-06, scored and licensed).

## Raw dumps (`data/reference/raw/`, git-ignored — never committed)

| File | Source | Fetched | License | Size |
|---|---|---|---|---|
| `kaikki-ajp.jsonl` | Wiktionary **South Levantine Arabic** via kaikki.org — https://kaikki.org/dictionary/South%20Levantine%20Arabic/kaikki.org-dictionary-SouthLevantineArabic.jsonl | 2026-10-06 | CC BY-SA 3.0 (Wiktionary text; https://creativecommons.org/licenses/by-sa/3.0/) | 18.1 MB, 3,455 entries |
| `kaikki-apc.jsonl` | Wiktionary **North Levantine Arabic** via kaikki.org — https://kaikki.org/dictionary/North%20Levantine%20Arabic/kaikki.org-dictionary-NorthLevantineArabic.jsonl | 2026-10-06 | CC BY-SA 3.0 | 2.7 MB, 865 entries |
| `maknuune-v1.0.1.tsv` (from `maknuune-v1.zip`) | **Maknuune** Palestinian Arabic lexicon, CAMeL Lab (NYU Abu Dhabi) — download page https://sites.google.com/nyu.edu/palestine-lexicon/download, TSV https://drive.google.com/uc?id=1prIUi6nw9DHVkvBx0YiVcm6aQYYfqXLy&export=download (a zip holding the TSV + LICENSE.txt); code https://github.com/CAMeL-Lab/maknuune_lexicon (LaTeX/checks only, no data) | 2026-10-06 | CC BY-SA 4.0 (LICENSE.txt in the zip and the download page) | 7.4 MB, 36,302 rows, 17k lemmas |

Attribution (both licenses ask for it): Wiktionary contributors via kaikki.org (Tatu Ylonen, wiktextract);
Dibas, Khairallah, Habash, Sadi, Sairafy, Sarabta, Ardah (2022), *Maknuune: A Large Open Palestinian Arabic Lexicon*,
WANLP 2022. The built file carries each record's sources and licenses; it is redistributed under CC BY-SA.

## Rebuild

```
curl -L -o data/reference/raw/kaikki-ajp.jsonl "https://kaikki.org/dictionary/South%20Levantine%20Arabic/kaikki.org-dictionary-SouthLevantineArabic.jsonl"
curl -L -o data/reference/raw/kaikki-apc.jsonl "https://kaikki.org/dictionary/North%20Levantine%20Arabic/kaikki.org-dictionary-NorthLevantineArabic.jsonl"
curl -L -o data/reference/raw/maknuune-v1.zip "https://drive.google.com/uc?id=1prIUi6nw9DHVkvBx0YiVcm6aQYYfqXLy&export=download"
python -c "import zipfile; z=zipfile.ZipFile('data/reference/raw/maknuune-v1.zip'); open('data/reference/raw/maknuune-v1.0.1.tsv','wb').write(z.read('maknuune-v1.0.1/maknuune-v1.0.1.tsv'))"
set PYTHONIOENCODING=utf-8
python scripts/build_reference_lexicon.py
```

The builder prints the record counts per source and a coverage report (how many of Amal's Doc words it can find,
by part of speech). Output shape, normalisation and the 6 MB cap are documented at the top of the script; tests:
`python -m pytest tests/test_build_reference_lexicon.py -q` and `node --test tests/test_reference_lexicon.cjs`.

Build of 2026-10-06: 15,671 records (kaikki-ajp 3,452 + kaikki-apc 865 entries, Maknuune 36,302 rows), 22,891
form-index rows, 5.99 MB; 1,663 of 2,204 Doc words found (75.5%).
