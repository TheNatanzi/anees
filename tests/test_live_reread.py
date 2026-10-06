# -*- coding: utf-8 -*-
"""Rule PG-14 / L1 (freshness audit, Medi 2026-10-02: "ensure the data is getting populated as soon as it's available"):
every page that reads LIVE data (Supabase) re-reads it when the tab comes back into view - docs/js/live-reread.js
(AneesLive.onReturn) or its own visibilitychange listener - or is listed below with the reason it must not.
Precedent: the Progress Flashcards panels read the answers once and never again (fixed in 8d730a0).
A new page that reads Supabase fails this test until it is wired or listed."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
LIVE = re.compile(r"rest/v1|AneesSnapshot\.load|ANEES\.url")
REREADS = re.compile(r"AneesLive\.onReturn|addEventListener\(\s*'visibilitychange'[^;]*(refresh|load|main)\(")

# Reads live data once ON PURPOSE. Each reason says why a re-read on return would hurt or is not needed.
ONCE_OK = {
    'docs/cards.html': 'a flashcard session: re-reading the deck mid-session would reshuffle the cards under Medi',
    'docs/amal/after.html': "Amal's answer page: her unsent answers live on the page; re-reading would reset them",
    'docs/amal/plan.html': "Amal's answer page (see after.html)",
    'docs/amal/review.html': "Amal's answer page (see after.html)",
    'docs/amal/verb-check.html': "Amal's answer page (see after.html)",
    'docs/amal/word-review.html': "Amal's answer page (see after.html)",
    'docs/js/amal-grammar-notes.js': "Amal writes notes under each rule; a re-read would drop a note she is typing",
    'docs/js/hub/after-task.js': 'a task Amal has open inside the Tutor page (tutor.js re-reads the list around it)',
    'docs/js/hub/new-words-task.js': "the 'new words' task Amal has open (tutor.js re-reads the list and her saved choices around it)",
    'docs/js/hub/ledger-task.js': "the 'which word was wrong' task Amal has open (tutor.js re-reads the list and her saved taps around it)",
    'docs/js/hub/plan-task.js': "the before-lesson list Amal has open (tutor.js re-reads the list around it)",
    'docs/js/hub/review-task.js': "the slips list Amal has open; a re-read would close a reason she is typing",
    'docs/js/hub/verb-check-task.js': "the verb list Amal has open; her unsent answers live on the page",
    'docs/js/hub/check-task.js': "a listening / checking list Amal has open; her 'Something else' box and unsent taps live on the page",
    'docs/js/hub/listen-check-task.js': "the listening check Amal has open; her 'Both wrong' box and unsent taps live on the page",
    'docs/js/hub/word-review-task.js': "the word review Amal has open; her unsent answers live on the page",
    'docs/js/tutor-verify.js': "the 'check these moments' task Amal has open (tutor.js re-reads the list around it)",
    'docs/js/hub/upload-task.js': "Amal's upload box: a list she is checking and unsent uploads live on the page (tutor.js re-reads the list around it)",
    'docs/js/hub/homework-task.js': "Amal's assign-homework box and her verdicts in progress live on the page (tutor.js re-reads the list around it)",
    'docs/homework.html': 'Medi types homework answers on it; a re-read would reset them',
    'docs/big-picture.html': "Medi's idea dump: he types on it; a re-read would reset a draft",
    'docs/speaking-review.html': 'review form: re-reads after each submit already',
    'docs/legacy-words.html': 'retired page (legacy), kept for reference',
    'docs/js/speaking-snapshot.js': 'a library: its callers (Word Bank, Progress) re-read',
    'docs/js/progress.js': 'a library used by cards.html / legacy-words.html',
    'docs/js/fluency-ladder.js': "Medi's labels: re-read while queued writes sync; a re-read on return could drop an unsynced label",
    'docs/js/vocab-unknowns.js': 'AI Reports blind-spot tables: a report snapshot, read on open',
    'docs/js/possible-names.js': 'AI Reports names list: Medi labels names on it (see fluency-ladder.js)',
}


def live_files():
    files = sorted(list(DOCS.glob('*.html')) + list(DOCS.glob('amal/*.html')) + list(DOCS.glob('js/*.js')) + list(DOCS.glob('js/*/*.js')))
    return [p for p in files if LIVE.search(p.read_text(encoding='utf-8', errors='replace')) and p.name not in ('config.js', 'live-reread.js')]


def test_every_live_page_rereads_or_says_why_not():
    bad = []
    for p in live_files():
        rel = p.relative_to(ROOT).as_posix()
        if rel in ONCE_OK:
            continue
        if not REREADS.search(p.read_text(encoding='utf-8', errors='replace')):
            bad.append(rel)
    assert not bad, ('these read live data once and never again (rule L1): wire AneesLive.onReturn or add them to ONCE_OK '
                     'with a reason: ' + ', '.join(bad))


def test_the_allowlist_has_no_dead_entries():
    live = {p.relative_to(ROOT).as_posix() for p in live_files()}
    assert not [k for k in ONCE_OK if k not in live and not (ROOT / k).exists()]


def test_pages_that_rely_on_the_helper_load_it():
    """A script calling AneesLive.onReturn must be loaded on a page that loads live-reread.js (or the call is a no-op)."""
    pages = {'docs/js/word-bank.js': 'docs/word-bank.html', 'docs/js/vocabulary-progress.js': 'docs/progress.html',
             'docs/js/tutor.js': 'docs/tutor.html'}
    for js, page in pages.items():
        assert 'AneesLive.onReturn' in (ROOT / js).read_text(encoding='utf-8')
        assert 'live-reread' in (ROOT / page).read_text(encoding='utf-8'), page
