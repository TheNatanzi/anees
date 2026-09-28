# -*- coding: utf-8 -*-
"""Decisions log: one JSON line per human verdict -> data/decisions/YYYY-MM.jsonl (plan/AI-ENGINEERING-REVIEW-2026-09-27.md,
"Tracking design" 2). Append-only: a line is never edited; a changed verdict is a new line whose `supersedes` names the old one.

    import decisions
    decisions.record(who="Amal", channel="tutor_page", about_type="pattern", about_id="P12", answer="audit_confirm",
                     ts="2026-09-27T16:17:50Z", source_row={"table": "amal_rules", "id": 1705})

Public repo: every string value passes track.safe() (Arabic letters or more than 200 characters -> "sha256:<16 hex>").
The month file is picked from `ts` (the moment of the verdict). Readers de-duplicate by decision_id (two machines can
append the same pulled row before they sync; the .gitattributes union merge keeps both copies).

Env: ANEES_DECISIONS_DIR writes elsewhere (tests). Under pytest nothing is written unless it is set.
"""
import datetime, json, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import track  # noqa: E402

FIELDS = ("decision_id", "ts", "who", "channel", "about_type", "about_id", "ai_run_id", "ai_value", "answer",
          "corrected_value", "confidence", "reason", "latency_ms", "sampling", "supersedes", "applied_commit", "source_row")
WHO = ("Medi", "Amal")
# the review's lists, plus review_page/app (Medi's own review pages) and homework/plan/change (Amal's after-lesson homework
# taps, her lesson-plan choices, a yes/no on a whole commit)
CHANNELS = ("swipe", "tutor_page", "chat", "commit", "review_page", "app")
ABOUT = ("rule", "audit_row", "pattern", "word", "arabizi", "label", "homework", "plan", "change")
SAMPLING = (None, "random", "uncertain", "repeat")


def decisions_dir():
    if os.environ.get("ANEES_DECISIONS_DIR"):
        return os.environ["ANEES_DECISIONS_DIR"]
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return None
    return os.path.join(REPO, "data", "decisions")


def _iso(ts):
    if ts is None:
        return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    s = str(ts).replace(" ", "T")
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            return d.isoformat(timespec="seconds")
        return d.astimezone(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except Exception:
        return s


def make(who, channel, about_type, about_id, answer, ts=None, decision_id=None, ai_run_id=None, ai_value=None,
         corrected_value=None, confidence=None, reason=None, latency_ms=None, sampling=None, supersedes=None,
         applied_commit=None, source_row=None):
    """A validated, sanitised decision line (dict with exactly FIELDS). Raises ValueError on a bad enum."""
    if who not in WHO:
        raise ValueError(f"who must be one of {WHO}: {who!r}")
    if channel not in CHANNELS:
        raise ValueError(f"channel must be one of {CHANNELS}: {channel!r}")
    if about_type not in ABOUT:
        raise ValueError(f"about_type must be one of {ABOUT}: {about_type!r}")
    if sampling not in SAMPLING:
        raise ValueError(f"sampling must be one of {SAMPLING[1:]} or None: {sampling!r}")
    if answer is None or answer == "":
        raise ValueError("answer is required")
    line = {"decision_id": decision_id or ("d-" + uuid.uuid4().hex), "ts": _iso(ts), "who": who, "channel": channel,
            "about_type": about_type, "about_id": None if about_id is None else str(about_id), "ai_run_id": ai_run_id,
            "ai_value": ai_value, "answer": answer, "corrected_value": corrected_value, "confidence": confidence,
            "reason": reason, "latency_ms": latency_ms, "sampling": sampling, "supersedes": supersedes,
            "applied_commit": applied_commit, "source_row": source_row}
    return track.safe(line)


def record(directory=None, **fields):
    """Validate + append one decision line. Returns the line written (or built, when writing is off under pytest)."""
    line = make(**fields)
    d = directory or decisions_dir()
    track.append_line(d, line["ts"][:7], line)
    return line


def read(directory=None):
    """Every decision line of every month (unreadable lines skipped), in file order."""
    d = directory or decisions_dir() or os.path.join(REPO, "data", "decisions")
    out = []
    if not os.path.isdir(d):
        return out
    for n in sorted(os.listdir(d)):
        if n.endswith(".jsonl"):
            with open(os.path.join(d, n), encoding="utf-8") as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
    return out


def known_ids(directory=None):
    return {x.get("decision_id") for x in read(directory)}


def latest(directory=None):
    """decision_id -> line, with superseded lines removed and duplicates collapsed (the view a dashboard should read)."""
    lines = {}
    for x in read(directory):
        lines.setdefault(x.get("decision_id"), x)
    gone = {x.get("supersedes") for x in lines.values() if x.get("supersedes")}
    return {k: v for k, v in lines.items() if k not in gone}
