from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
DO_ROOT = HERE.parents[1]
OUT = DO_ROOT / "outputs"
REPORT = OUT / "anees-independent-test-report.md"
STAGE = HERE / "bundle-stage"
ZIP = OUT / "anees-independent-test-bundle.zip"

ROOT_FILES = [
    "protocol.md",
    "manifest.json",
    "comparison.json",
    "meet-captions-selected.json",
    "results-elevenlabs.json",
    "results-elevenlabs-segmented.json",
    "results-elevenlabs-keyterms.json",
    "results-elevenlabs-keyterms-local.json",
    "results-openai-strict.json",
    "results-openai-vocab.json",
    "run_test.py",
    "run_eleven_segmented.py",
    "run_eleven_keyterms.py",
    "run_eleven_keyterms_local.py",
    "analyze_results.py",
    "build_report.py",
    "build_bundle.py",
    "claim-to-source-ledger.md",
]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate() -> dict:
    report = REPORT.read_text(encoding="utf-8")
    assert report == (HERE / "report-source.md").read_text(encoding="utf-8")
    assert report.count("```") % 2 == 0
    assert report.count("<details>") == report.count("</details>") == 20
    assert "\ufffd" not in report
    assert "needs_amал" not in report
    assert "Base evidence transcript\n" not in report

    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    selected = manifest["selection"]["selected_indexes"]
    assert selected == list(range(1, 20)) + [21]
    for window in manifest["windows"]:
        clip = Path(window["clip"])
        assert clip.exists()
        assert sha(clip) == window["clip_sha256"]

    result_names = [
        "results-elevenlabs.json",
        "results-elevenlabs-segmented.json",
        "results-elevenlabs-keyterms.json",
        "results-elevenlabs-keyterms-local.json",
        "results-openai-strict.json",
        "results-openai-vocab.json",
    ]
    for name in result_names:
        rows = json.loads((HERE / name).read_text(encoding="utf-8"))
        assert len(rows) == 20, (name, len(rows))
        assert [row["index"] for row in rows] == selected, name
        for row in rows:
            assert row.get("text", "").strip(), (name, row["index"])
            if "status_code" in row:
                assert row["status_code"] == 200, (name, row["index"], row["status_code"])

    comparison = json.loads((HERE / "comparison.json").read_text(encoding="utf-8"))
    assert len(comparison["rows"]) == 20
    assert set(comparison["aggregate"]) == {"E", "ES", "O1", "O2", "EKG", "EKL"}
    return {
        "report_bytes": REPORT.stat().st_size,
        "report_lines": len(report.splitlines()),
        "report_words": len(report.split()),
        "report_sha256": sha(REPORT),
        "clips_validated": len(manifest["windows"]),
        "result_files_validated": len(result_names),
    }


def main() -> None:
    qa = validate()
    resolved_stage = STAGE.resolve()
    assert resolved_stage.parent == HERE.resolve()
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir()

    shutil.copy2(REPORT, STAGE / REPORT.name)
    for name in ROOT_FILES:
        shutil.copy2(HERE / name, STAGE / name)
    shutil.copytree(HERE / "clips", STAGE / "clips")
    shutil.copytree(HERE / "source-vocabulary", STAGE / "source-vocabulary")

    files = sorted(path for path in STAGE.rglob("*") if path.is_file())
    sums = [f"{sha(path)}  {path.relative_to(STAGE).as_posix()}" for path in files]
    (STAGE / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in STAGE.rglob("*") if p.is_file()):
            archive.write(path, path.relative_to(STAGE).as_posix())

    with zipfile.ZipFile(ZIP) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len([name for name in names if name.startswith("clips/") and name.endswith(".mp3")]) == 20
        assert "anees-independent-test-report.md" in names
        assert "SHA256SUMS.txt" in names

    print(json.dumps({
        **qa,
        "bundle_bytes": ZIP.stat().st_size,
        "bundle_sha256": sha(ZIP),
        "bundle_files": len(names),
    }, indent=2))


if __name__ == "__main__":
    main()
