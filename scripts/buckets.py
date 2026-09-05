"""Grip buckets (plan section 0), computed from word_events (lessons) + card_results (flashcards). One function, one truth;
the flashcards page carries the same rules in JS (docs/js/buckets.js) and this module is the reference the JS test compares to.

  ice_cold  right 5 in a row on flashcards on >= 3 different days (first-try rights); one miss -> cold
  cold      said unprompted in a lesson with no correction, or flashcard right first try
  shaky     right on second try, or said only after Amal said it (prompted)
  missed    Amal corrected it, Medi asked for it, or wrong twice in a row on cards
  new       first heard in one of the last 3 lessons and not yet drilled (fewer than 3 first-try card rights on 2 different days);
            new words never mix with missed words: they go through the strict review-and-repeat loop first
  never     no Medi signal yet (Amal may have said it: times_seen counts it)
The latest signal (lesson event or card result) decides, except that the ice-cold streak rule is checked on cards first.
Missed words and words learned in the last 3 lessons get weight 3 (cards, sentence suggestions, homework)."""
import datetime, collections

RECENT_LESSONS = 3
NEW_DRILL_RIGHTS, NEW_DRILL_DAYS = 3, 2      # a new word leaves 'new' after 3 first-try rights on 2 different days


GRAMMAR_KINDS = ('article', 'gender', 'tense', 'plural')


def _signal_from_event(e):
    if e.get('speaker') != 'Medi' or e.get('prompted') is None:
        return None
    if e.get('correction') and e.get('miss_kind') in GRAMMAR_KINDS and not e.get('asked'):
        return 'shaky' if e.get('prompted') else 'cold'      # the word was known; the slip is grammar, counted separately
    if e.get('miss_kind') == 'choice':
        return 'shaky'                                        # known word, wrong place: shaky, not missed
    if e.get('correction') or e.get('asked'):
        return 'missed'
    if e.get('prompted'):
        return 'shaky'
    return 'cold'


def _signal_from_cards(cards):
    """cards: chronological [{'ts','result','attempt'}] -> (bucket, streak, streak_days)."""
    if not cards:
        return None, 0, []
    streak, days = 0, []
    for c in reversed(cards):
        if c['result'] == 'got' and int(c.get('attempt') or 1) == 1:
            streak += 1
            d = str(c['ts'])[:10]
            if d not in days:
                days.append(d)
        else:
            break
    last = cards[-1]
    if streak >= 5 and len(days) >= 3:
        return 'ice_cold', streak, days
    if last['result'] == 'missed':
        if sum(1 for c in cards[-3:] if c['result'] == 'missed') >= 2:   # wrong twice (within the last three answers)
            return 'missed', 0, []
        return 'cold' if _was_ice(cards[:-1]) else 'shaky', 0, []      # one miss after an ice-cold streak -> cold
    if int(last.get('attempt') or 1) > 1:
        return 'shaky', streak, days
    return 'cold', streak, days


def _was_ice(cards):
    b, s, d = _signal_from_cards(cards) if cards else (None, 0, [])
    return b == 'ice_cold'


def compute(word_events, card_results, lesson_dates, today=None):
    """Returns {word_key: stats}. word_events rows need lesson_date, word_key, speaker, prompted, correction, t_start.
    card_results rows need word_key, ts, result, attempt. lesson_dates = all lesson dates (ISO strings)."""
    lesson_dates = sorted(set(str(d) for d in lesson_dates))
    recent_dates = set(lesson_dates[-RECENT_LESSONS:])
    ev_by = collections.defaultdict(list)
    for e in word_events:
        ev_by[e['word_key']].append(e)
    cd_by = collections.defaultdict(list)
    for c in card_results:
        cd_by[c['word_key']].append(c)
    out = {}
    for key in set(ev_by) | set(cd_by):
        evs = sorted(ev_by[key], key=lambda e: (str(e['lesson_date']), e.get('t_start') or 0))
        cards = sorted(cd_by[key], key=lambda c: str(c['ts']))
        lesson_signals = [(str(e['lesson_date']), _signal_from_event(e)) for e in evs]
        lesson_signals = [(d, s) for d, s in lesson_signals if s]
        card_bucket, streak, days = _signal_from_cards(cards)
        last_lesson_sig = lesson_signals[-1] if lesson_signals else None
        last_card_ts = str(cards[-1]['ts'])[:10] if cards else None
        bucket = 'never'
        if last_lesson_sig and (not last_card_ts or last_lesson_sig[0] >= last_card_ts):
            bucket = last_lesson_sig[1]
        elif card_bucket:
            bucket = card_bucket
        if card_bucket == 'ice_cold' and bucket in ('cold',):
            bucket = 'ice_cold'
        first_lesson = str(evs[0]['lesson_date']) if evs else None
        lesson_signal = bucket
        drilled = streak >= NEW_DRILL_RIGHTS and len(days) >= NEW_DRILL_DAYS
        if first_lesson and first_lesson in recent_dates and not drilled:
            bucket = 'new'                                          # strict review first; the lesson signal is kept in lesson_signal
        seen_dates = sorted({str(e['lesson_date']) for e in evs})
        last_reviewed = max([x for x in [seen_dates[-1] if seen_dates else None, str(cards[-1]['ts']) if cards else None] if x], default=None)
        recent = first_lesson in recent_dates if first_lesson else False
        out[key] = {'word_key': key, 'bucket': bucket, 'last_reviewed': last_reviewed, 'last_lesson': seen_dates[-1] if seen_dates else None,
                    'seen_lessons': len(seen_dates), 'times_seen': len(evs), 'times_missed': sum(1 for e in evs if e.get('correction')) + sum(1 for c in cards if c['result'] == 'missed'),
                    'card_right': sum(1 for c in cards if c['result'] == 'got'), 'card_wrong': sum(1 for c in cards if c['result'] == 'missed'),
                    'streak': streak, 'streak_days': days, 'recent': recent, 'weight': 3.0 if (bucket in ('missed', 'new') or recent) else 1.0, 'lesson_signal': lesson_signal,
                    'grammar_misses': sum(1 for e in evs if e.get('correction') and e.get('miss_kind') in GRAMMAR_KINDS),
                    'grammar_kinds': sorted({e['miss_kind'] for e in evs if e.get('correction') and e.get('miss_kind') in GRAMMAR_KINDS})}
    return out


def recompute_and_store():
    """Reads word_events + card_results + lessons from Supabase, writes word_stats. Returns the stats dict."""
    import db
    evs = db.select('word_events', {'select': 'lesson_date,word_key,speaker,prompted,correction,asked,miss_kind,t_start'})
    cards = db.select('card_results', {'select': 'word_key,ts,result,attempt'})
    dates = [r['date'] for r in db.select('lessons', {'select': 'date'})]
    stats = compute(evs, cards, dates)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = []
    for s in stats.values():
        r = dict(s); r['updated_at'] = now
        if r['last_reviewed'] and len(r['last_reviewed']) == 10:
            r['last_reviewed'] = r['last_reviewed'] + 'T00:00:00Z'
        rows.append(r)
    db.upsert('word_stats', rows, on='word_key')
    # rows for words that no longer have any event or card are stale (earlier builds, purged test rows): remove them
    live = set(stats)
    for r in db.select('word_stats', {'select': 'word_key'}):
        if r['word_key'] not in live:
            db.rest('DELETE', 'word_stats', params={'word_key': f"eq.{r['word_key']}"}, prefer='return=minimal')
    return stats
