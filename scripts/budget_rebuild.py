# -*- coding: utf-8 -*-
"""data/budget.json is a GENERATED file (RULES.md S7 G1, rule PR-13): rebuilt from the run logs, never merged.

Medi 2026-10-10 ("MAKE A SYSTEM"): the hourly job was blocked from 2026-10-09 11:34 for ~29 h because a `pull --rebase`
conflicted on data/budget.json and the guard treated it as a hand-made file ("a person merges"). Now the guard keeps
master's copy on a conflict and runs rebuild() right after the rebase (scripts/publish_guard.py after_generated_rebase).

Shape (unchanged): {"elevenlabs": usd, "openai": usd, "gemini": usd, "anthropic": usd, "calls": [{t, service, usd, what}]}.
There are no hand-set fields: the caps live in code (scripts/pipeline_ext.py CAPS). Every per-service total is the sum of
its calls. The calls list is the ledger itself (it starts 2026-09-05, before the run log, data/runs, began on 09-28), so it
is never thrown away: rebuild() keeps master's calls, adds every PAID run line (data/runs/*.jsonl) that has no matching
call (same cost within 0.00015 USD and within 14 h: the ledger's clock is local, the run log is UTC; the same match the
AI-paid-logged check uses, one call per run line), and recomputes every total. Run lines that are paid-ledger calls:
LEDGER_STEPS below (measured 2026-10-11: those steps match a ledger call 1:1; the Claude CLI readers, translate_lines and
misheard_check are not ledger calls and stay out).

    python scripts/budget_rebuild.py          # rebuild data/budget.json in place, print what changed
"""
from __future__ import annotations

import datetime as dt, glob, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL = 'data/budget.json'
SERVICES = ('elevenlabs', 'openai', 'gemini', 'anthropic')
PROVIDER = {'elevenlabs': 'elevenlabs', 'openai': 'openai', 'google': 'gemini', 'gemini': 'gemini', 'anthropic': 'anthropic'}
LEDGER_STEPS = re.compile(r'^(scribe\.|context\.listen$|bench\.total\.|correction_parse\.|meet_gap_fill)')
TOL_USD, TOL_H = 0.00015, 14


def _ts(s):
    return dt.datetime.fromisoformat(str(s).replace('Z', '')[:19])


def run_lines(root):
    out = []
    for p in sorted(glob.glob(os.path.join(str(root), 'data', 'runs', '*.jsonl'))):
        with open(p, encoding='utf-8') as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def paid_calls(runs):
    """The run lines that are paid-ledger calls -> [{'t' (local), 'service', 'usd', 'what', 'utc'}]."""
    out = []
    for r in runs:
        svc = PROVIDER.get(str(r.get('gen_ai.provider.name') or ''))
        try:
            usd = float(r.get('cost_usd') or 0)
        except Exception:
            continue
        if not svc or usd <= 0 or not r.get('started_at') or not LEDGER_STEPS.match(str(r.get('step') or '')):
            continue
        utc = dt.datetime.fromisoformat(str(r['started_at']).replace('Z', '+00:00'))
        if utc.tzinfo is None:
            utc = utc.replace(tzinfo=dt.timezone.utc)
        out.append({'t': utc.astimezone().replace(tzinfo=None).isoformat(timespec='seconds'), 'service': svc,
                    'usd': round(usd, 4), 'what': '%s (rebuilt from run %s)' % (r.get('step'), str(r.get('run_id') or '')[:8]),
                    'utc': utc.replace(tzinfo=None)})
    return out


def rebuild(base, runs):
    """base: the budget.json kept (master's copy). Returns the rebuilt ledger (same shape; totals = sums of the calls)."""
    base = dict(base or {})
    calls = [dict(c) for c in base.get('calls') or []]
    free = list(range(len(calls)))
    for pc in paid_calls(runs):
        hit = None
        for i in free:
            c = calls[i]
            try:
                if abs(float(c.get('usd') or 0) - pc['usd']) < TOL_USD and abs((_ts(c['t']) - pc['utc']).total_seconds()) < TOL_H * 3600:
                    hit = i
                    break
            except Exception:
                continue
        if hit is not None:
            free.remove(hit)
        else:
            calls.append({k: pc[k] for k in ('t', 'service', 'usd', 'what')})
    calls.sort(key=lambda c: str(c.get('t')))
    out = {k: v for k, v in base.items() if k != 'calls'}
    for s in sorted(set(SERVICES) | {c.get('service') for c in calls if c.get('service')}):
        out[s] = round(sum(float(c.get('usd') or 0) for c in calls if c.get('service') == s), 4)
    out['calls'] = calls
    return out


def rebuild_file(root=ROOT):
    """Rebuild <root>/data/budget.json in place. Returns (changed, added_calls)."""
    p = Path(root) / REL
    try:
        base = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        base = {}
    new = rebuild(base, run_lines(root))
    added = len(new['calls']) - len(base.get('calls') or [])
    changed = new != base
    if changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding='utf-8')
    return changed, added


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ch, n = rebuild_file(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT)
    print('budget_rebuild: ' + ('rebuilt, %d call(s) added from the run log' % n if ch else 'unchanged'))
