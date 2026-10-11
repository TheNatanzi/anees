# -*- coding: utf-8 -*-
"""The silent-stall alarm (Medi 2026-10-10: "A COMEPLETE GUIDE SYSTEM AND FOLLOW IT EVERY FUCKING TIME. MAKE A SYSTEM").

From 2026-10-09 11:34 the hourly job could not publish for ~29 h (a `pull --rebase` conflict on data/budget.json) and no
page said so. docs/data/pipeline-health.json is now the one source of truth for "is the hourly robot publishing":

  last_publish_utc / last_publish_sha  newest hourly PUBLISH on origin/master: the guard's own pass commit "Publish
                                       guard: all required checks passed (hourly: ...)" (HOURLY_SUBJECT). The other hourly
                                       subjects ("Hourly job: remaining built files", "Lessons <d> loaded by the hourly job",
                                       "Amal's answers applied + Tutor page refreshed by the hourly job", "AI run + decision
                                       logs by the hourly job") are not used: on 10-10 01:28 a person carried four of them to
                                       master by hand while the robot was still stuck, and "... the hourly job's leftover
                                       data" is a manual subject. A passing hourly push sets it to now.
  last_block_reason / last_block_utc   the newest blocked push since that publish (the hourly checkout's local guard state
                                       first, C:/dev/anees-hourly/data/publish-guard/state.json, read only; then this one's)
  first_block_reason / blocked_since_utc  the FIRST block since that publish: why it got stuck
  open_failures                        failed steps an earlier hour left open (guard state "open_failures")
  pending                              the work that is waiting (see pending_work)
  hours_since_publish                  now - last_publish_utc
  stalled                              hours_since_publish > STALL_H (2) AND pending is not empty
  generated_at

Pending work (kept simple, all things the repo already tracks): today is a lesson day (today's lesson in lessons.json or a
folder for today in the raw archive); a lesson recorded in the raw archive but not on the site; open failures; a blocked
push since the last publish (local commits wait); a second listen not applied yet (data/lesson-work/rehear-status.json
pending / submitted / proposed); Medi's corrections newer than the last publish (data/lesson-work/medi-corrections.json).

Written by scripts/publish_guard.py on every push attempt (a pass: in the publish commit; a block: left in the tree, the
next hourly commit carries it) and by scripts/hourly_lessons.py at the end of every run. Read by docs/js/stale.js (the
banner on every page, PG-01), `publish_guard.py check` / `push` (one WARNING line, advisory) and the LS-04 line of
docs/data/lesson-alerts.json. Never raises: a health problem must not block a publish.
"""
from __future__ import annotations

import datetime as dt, json, os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEALTH = 'docs/data/pipeline-health.json'
STALL_H = 2
HOURLY_ROOT_DEFAULT = r'C:\dev\anees-hourly'
RAW_DEFAULT = r'C:\dev\anees\data\lessons'
HOURLY_SUBJECT = re.compile(r"^Publish guard: all required checks passed \(hourly")
BLOCKS = ('blocked', 'rebase_failed', 'push_failed')
DATE_RE = re.compile(r'^20\d\d-\d\d-\d\d$')


def _utc(s):
    try:
        t = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return (t if t.tzinfo else t.astimezone()).astimezone(dt.timezone.utc)
    except Exception:
        return None


def _iso(t):
    return t.astimezone(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z') if t else None


def _J(p):
    try:
        with open(p, encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception:
        return None


def last_hourly_publish(root, run=subprocess.run, ref='origin/master', n=600):
    """(sha, utc datetime) of the newest hourly commit on `ref`, or (None, None)."""
    try:
        r = run(['git', 'log', ref, '-n', str(n), '--format=%H%x1f%cI%x1f%s'], cwd=str(root), capture_output=True,
                text=True, encoding='utf-8', errors='replace')
        for line in (getattr(r, 'stdout', '') or '').splitlines():
            parts = line.split('\x1f')
            if len(parts) == 3 and HOURLY_SUBJECT.search(parts[2]):
                return parts[0], _utc(parts[1])
    except Exception:
        pass
    return None, None


def _states(root, hourly_root=None):
    """Guard states to read, the hourly checkout's first (it is the robot). Read only."""
    hr = Path(hourly_root or os.environ.get('ANEES_HOURLY_ROOT') or HOURLY_ROOT_DEFAULT)
    out = []
    for r in ([hr] if hr.resolve() != Path(root).resolve() else []) + [Path(root)]:
        st = _J(r / 'data/publish-guard/state.json')
        if isinstance(st, dict):
            out.append(st)
    return out


def blocks_since(states, since):
    """[(utc, reason)] of every blocked push after `since` (None = all), oldest first, across the states."""
    seen, out = set(), []
    for st in states:
        for h in st.get('history') or []:
            t = _utc(h.get('at'))
            if h.get('outcome') in BLOCKS and t and (since is None or t > since) and (t, h.get('reason')) not in seen:
                seen.add((t, h.get('reason')))
                out.append((t, str(h.get('reason') or '')))
    return sorted(out)


def pending_work(root, now, states, last_utc, raw=None):
    root = Path(root)
    why = []
    today = now.astimezone().date().isoformat()
    listed = {str(x.get('date')) for x in ((_J(root / 'docs/data/lessons.json') or {}).get('lessons') or [])}
    raw = Path(raw or os.environ.get('ANEES_RAW') or RAW_DEFAULT)
    raw_today = raw.is_dir() and (raw / today).is_dir()
    if today in listed or raw_today:
        why.append(f'lesson day ({today})')
    if raw.is_dir():
        for d in sorted(x.name for x in raw.iterdir() if x.is_dir() and DATE_RE.match(x.name) and x.name >= '2026-09-10'):
            if d not in listed and (list((raw / d).glob('scribe*.json')) or list((raw / d).glob('meet-*/scribe.json'))
                                    or (raw / d / 'tracks').is_dir()):
                why.append(f'lesson {d} recorded, not on the site')
    of = {}
    for st in states:
        of.update(st.get('open_failures') or {})
    if of:
        why.append(f'{len(of)} open failure(s): ' + ', '.join(sorted(of))[:120])
    nb = len(blocks_since(states, last_utc))
    if nb:
        why.append(f'{nb} blocked push(es) since the last publish')
    rs = (_J(root / 'data/lesson-work/rehear-status.json') or {}).get('lessons') or {}
    waiting = sorted(d for d, v in (rs.items() if isinstance(rs, dict) else []) if isinstance(v, dict)
                     and v.get('status') in ('pending', 'submitted', 'proposed'))
    if waiting:
        why.append('second listen not applied: ' + ', '.join(waiting))
    rows = (_J(root / 'data/lesson-work/medi-corrections.json') or {}).get('rows') or []
    newer = [r for r in rows if last_utc and (_utc(r.get('ts')) or last_utc) > last_utc]
    if newer:
        why.append(f"{len(newer)} of the student's corrections since the last publish")
    return why, of


def compute(root=ROOT, run=subprocess.run, now=None, hourly_root=None, raw=None, published=None, prev=None):
    """The health document. published = (sha, utc) of a publish happening now (a passing hourly push)."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    sha, last = published or last_hourly_publish(root, run)
    prev = prev if prev is not None else (_J(Path(root) / HEALTH) or {})
    if not last and prev.get('last_publish_utc'):                 # no origin/master here: keep what the file knew
        sha, last = prev.get('last_publish_sha'), _utc(prev.get('last_publish_utc'))
    states = _states(root, hourly_root)
    bl = blocks_since(states, last)
    pend, of = pending_work(root, now, states, last, raw)
    hours = round((now - last).total_seconds() / 3600, 1) if last else None
    stalled = bool(pend) and hours is not None and hours > STALL_H     # unknown last publish (no origin/master here): not claimed
    if not bl and prev.get('last_block_utc'):          # a block another PC recorded (its state is not readable here)
        t = _utc(prev.get('last_block_utc'))
        if t and (last is None or t > last):
            bl = [(t, str(prev.get('last_block_reason') or ''))]
            pend.append('a blocked push since the last publish')
            stalled = hours is not None and hours > STALL_H
    doc = {'about': 'Is the hourly robot publishing? Written by scripts/pipeline_health.py (publish guard + hourly job); '
                     'read by js/stale.js. stalled = no hourly publish for more than %d h while work waits.' % STALL_H,
            'last_publish_utc': _iso(last), 'last_publish_sha': sha,
            'last_block_reason': _flat(bl[-1][1], 400) if bl else None,
            'last_block_utc': _iso(bl[-1][0]) if bl else None,
            'first_block_reason': _flat(bl[0][1], 400) if bl else None, 'blocked_since_utc': _iso(bl[0][0]) if bl else None,
            'open_failures': [f"{k}: {'; '.join(str(x) for x in (v.get('failures') or []))[:160]}" for k, v in sorted(of.items())],
            'pending': pend, 'hours_since_publish': hours, 'stalled': stalled, 'generated_at': _iso(now)}
    doc['plain_reason'] = plain_reason(doc)
    return doc


PLAIN = (   # what blocks it NOW, in plain words for the banner (Medi 2026-10-11: "what is this ... "pass": "presentation"...")
    (r'budget\.json', 'its money file (data/budget.json) clashed with the live copy'),
    (r'conflict', 'its changes clashed with the live site'),
    (r'tests?_(py|node)', 'a test failed'),
    (r'([A-Za-z_]+)(?:\.py)? exit \d', lambda m: 'the step "%s" failed' % m.group(1).replace('_', ' ')),
    (r'clean_tree', 'it had unsaved files'),
    (r'lesson_ledger|ledger', 'the lesson ledger check failed'),
    (r'rule_registry', 'the rule check failed'),
)


def plain_reason(h):
    """One short line for a person: what blocks the robot now (the latest block, else the first, else the open work)."""
    raw = (h or {}).get('last_block_reason') or (h or {}).get('first_block_reason') or ''
    for pat, say in PLAIN:
        m = re.search(pat, raw)
        if m:
            return say(m) if callable(say) else say
    if raw:
        return _flat(re.sub(r'[\[{].*', '', raw), 90) or 'a publish check failed'
    pend = (h or {}).get('pending') or []
    return ('waiting: ' + _flat('; '.join(pend), 90)) if pend else 'unknown'


def _flat(s, n):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s if len(s) <= n else s[:n - 3] + '...'


def reason_of(h):
    """The first blocked reason (why it got stuck), plus what blocks it now when that differs. One line."""
    first, last = h.get('first_block_reason'), h.get('last_block_reason')
    if first or last:
        s = _flat(first or last, 160)
        if first and last and _flat(last, 160) != s:
            s += ' | now: ' + _flat(last, 160)
        return s
    return _flat('; '.join(h.get('open_failures') or []) or 'no blocked push recorded on this PC; waiting: '
                 + '; '.join(h.get('pending') or []), 300)


def warning_line(h):
    """One advisory line for the guard's output, or None when not stalled."""
    if not h or not h.get('stalled'):
        return None
    hrs = h.get('hours_since_publish')
    return ('WARNING: the hourly robot has not published for ' + (f'{hrs:.0f} h' if hrs is not None else 'a long time')
            + ': ' + reason_of(h))


def write(root=ROOT, **kw):
    """Compute and write docs/data/pipeline-health.json. Returns the doc (None on any error: never blocks)."""
    try:
        h = compute(root, **kw)
        p = Path(root) / HEALTH
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(h, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        os.replace(tmp, p)
        return h
    except Exception:
        return None


def alert_problem(h):
    """Rule LS-04 style line for docs/data/lesson-alerts.json (scripts/lesson_alerts.py kind 'stalled'), or None."""
    if not h or not h.get('stalled'):
        return None
    return {'key': 'stalled', 'kind': 'stalled', 'since': h.get('last_publish_utc'), 'cause': reason_of(h)[:200]}


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    h = compute(ROOT)
    print(json.dumps(h, ensure_ascii=False, indent=1))
    print(warning_line(h) or 'pipeline health: not stalled')
