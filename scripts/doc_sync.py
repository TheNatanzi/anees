# -*- coding: utf-8 -*-
"""Rule AM-20 (Medi 2026-10-02: "DUDE FUCKING FIX THE ISSUE WITH HER DOCUMENT. YOU HAVE A DIRECT GOOGLE CONNECTION TO THE
DOC WHY IS THIS SO FUCKING HARD").

Amal's Doc ("Arabic Full Vocabulary list") is private (anonymous export = 401) and the Drive connector only exists inside
a Claude chat, so the hourly "Anees vocab import" task had no live source and imported nothing. The source now:

  Google Apps Script "Anees doc sync" (scripts/apps_script/doc_sync/Code.gs) under wc@adibs.com - an editor of the Doc and
  the Google account Drive for desktop syncs to G:/My Drive on this PC - runs every hour on Google's side, exports the Doc
  as markdown (Drive API, read-only scope: the Doc is never written, ai_rules N2) and writes two files into
  "My Drive/Anees doc sync/": amal-vocab-doc.md and amal-vocab-doc.status.json ({ok_at, tried_at, error, chars}).
  Drive for desktop brings them to G:/My Drive/Anees doc sync/, scripts/import_vocab.py reads them.

No action from Amal or Medi. A source older than STALE_H hours is never imported (it could undo a newer sync) and is
shown loudly: one LS-04 line on Progress + Lessons ("Amal's word Doc not synced since <time>: <reason>") and a
data_freshness warning in the publish guard. Pure file reads: the tests never touch the network.
"""
from __future__ import annotations

import datetime, json, os
from pathlib import Path

SYNC_DIR_DEFAULT = 'G:/My Drive/Anees doc sync'
MD_NAME = 'amal-vocab-doc.md'
STATUS_NAME = 'amal-vocab-doc.status.json'
STALE_H = 2.0


def sync_dir():
    return Path(os.environ.get('ANEES_DOC_SYNC_DIR') or SYNC_DIR_DEFAULT)


def _parse(ts):
    try:
        t = datetime.datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        return t if t.tzinfo else t.astimezone()
    except Exception:
        return None


def state(folder=None, now=None):
    """{'path', 'exported_at' (aware datetime or None), 'age_h', 'fresh', 'reason'} for the synced export.
    exported_at = the export script's last good run (status file), else the markdown file's modified time."""
    folder = Path(folder) if folder else sync_dir()
    now = now or datetime.datetime.now().astimezone()
    md, stp = folder / MD_NAME, folder / STATUS_NAME
    st = {}
    try:
        st = json.loads(stp.read_text(encoding='utf-8-sig'))
    except Exception:
        st = {}
    out = {'path': str(md), 'exported_at': None, 'age_h': None, 'fresh': False, 'reason': ''}
    if not md.exists():
        out['reason'] = (f'no export file at {md} (the Google export script "Anees doc sync" has not written it, '
                         'or Drive for desktop is not running)')
        return out
    t = _parse(st.get('ok_at')) or datetime.datetime.fromtimestamp(md.stat().st_mtime).astimezone()
    out['exported_at'] = t
    out['age_h'] = max(0.0, (now - t).total_seconds() / 3600)
    if out['age_h'] <= STALE_H:
        out['fresh'] = True
        return out
    if st.get('error'):
        out['reason'] = 'the Google export failed: ' + str(st['error'])[:160]
    else:
        tried = _parse(st.get('tried_at'))
        if tried and (now - tried).total_seconds() / 3600 <= STALE_H:
            out['reason'] = 'the Google export ran but Drive for desktop has not brought the new file to this PC'
        else:
            out['reason'] = (f'the hourly Google export has not run for {out["age_h"]:.0f} h '
                             '(Apps Script "Anees doc sync" under wc@adibs.com, or Drive for desktop stopped)')
    return out


def stale_problem(folder=None, now=None):
    """An LS-04 alert problem when the synced Doc is missing or older than STALE_H hours, else None. `since` = the last
    good export, so the line reads "Amal's word Doc not synced since 14:05: <reason>" and only changes when it does."""
    s = state(folder, now)
    if s['fresh']:
        return None
    return {'key': 'doc-sync', 'kind': 'doc-stale', 'cause': s['reason'],
            'since': s['exported_at'].isoformat(timespec='seconds') if s['exported_at'] else None}
