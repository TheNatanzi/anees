"""Grip buckets (plan section 0), computed from word_events (lessons) + card_results (flashcards). One function, one truth;
the flashcards page carries the same rules in JS (docs/js/buckets.js) and this module is the reference the JS test compares to.

Display names (Medi, 2026-09-10): cold = Good; ice_cold = Mastered. Stored IDs, thresholds and history stay unchanged.

  ice_cold  5 consecutive successes across >= 3 days: first-try cards or independent lesson use (one per lesson date)
  cold      said unprompted in a lesson with no correction, or flashcard right first try
  shaky     right on second try, or said only after Amal said it (prompted)
  missed    Amal corrected it, Medi asked for it, or wrong twice in a row on cards
  new       ONLY a word explicitly marked new: Amal (after-link / chat confirmation) or Medi marked it for a lesson (amal_rules kind
            'new'), or it appeared in the Doc after a lesson but not in the snapshot before it (Doc diff; needs the live import).
            It stays new until practised: 5 first-try card rights on 2 different days. Nothing is inferred into 'new'
            (Medi 2026-09-05: "we don't have any more context for what words are new"). The chat/asked inference only
            proposes 'new?' candidates for Amal's after-link; it never buckets.
            New words never mix with missed words: they go through the strict review-and-repeat loop first
  never     no Medi signal yet. Amal never adds to usage, review dates or mastery.
Lesson evidence is ordered after cards on the same date, matching the existing date-only lesson precedence.
Missed words and words learned in the last 3 lessons get weight 3 (cards, sentence suggestions, homework)."""
import datetime, collections

RECENT_LESSONS = 3
NEW_DRILL_RIGHTS, NEW_DRILL_DAYS = 5, 2      # a new word leaves 'new' after 5 first-try rights on 2 different days (Medi 2026-09-05)


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


SIGNAL_RANK = {'missed': 0, 'shaky': 1, 'cold': 2}


def _per_lesson_signals(evs):
    """One signal per lesson, not per event (Medi 2026-09-05, the lAzem case): a word Medi said on his own in a lesson is cold for
    that lesson even if he also echoed it after Amal later; any correction or 'asked' in the lesson makes it missed."""
    by_day = collections.OrderedDict()
    for e in evs:
        s = _signal_from_event(e)
        if s:
            by_day.setdefault(str(e['lesson_date']), []).append(s)
    out = []
    for d, sigs in by_day.items():
        if 'missed' in sigs:
            out.append((d, 'missed'))
        elif 'cold' in sigs:
            out.append((d, 'cold'))          # said unprompted at least once: a later echo does not downgrade it
        else:
            out.append((d, 'shaky'))
    return out


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


def _independent_use(e):
    """A detected Medi use with explicit no-help/no-correction evidence, not verified pronunciation."""
    return (e.get('speaker') == 'Medi' and e.get('prompted') is False
            and e.get('correction') is False and e.get('asked') is False
            and e.get('miss_kind') not in ('choice', 'unclear'))


def _known_help_or_correction(e):
    return (e.get('prompted') is True or e.get('correction') is True
            or e.get('asked') is True or e.get('miss_kind') == 'choice')


def progress_from_context(context):
    """Shared lesson/card mastery model. Card drill streak remains separate for New words."""
    cards = sorted(context['cards'], key=lambda c: (str(c['ts']), str(c.get('id') or '')))
    timeline = [(str(c['ts'])[:10], 0, str(c['ts']), i, 'card', c) for i, c in enumerate(cards)]
    timeline += [(d, 1, '', i, 'lesson', (signal, qualifies))
                 for i, (d, signal, qualifies) in enumerate(context['lessons'])]
    bucket, streak, days, last_cards = 'never', 0, [], []
    for day, _, _, _, source, value in sorted(timeline, key=lambda r: r[:4]):
        was_mastered = bucket == 'ice_cold'
        if source == 'card':
            last_cards.append(value)
            success = value['result'] == 'got' and int(value.get('attempt') or 1) == 1
            if value['result'] == 'missed':
                signal = 'cold' if was_mastered else ('missed' if sum(c['result'] == 'missed' for c in last_cards[-3:]) >= 2 else 'shaky')
            else:
                signal = 'cold' if success else 'shaky'
        else:
            signal, qualifies = value
            if qualifies is None:
                continue  # Unknown evidence neither earns mastery nor erases an established streak.
            success = signal == 'cold' and qualifies
        if success:
            streak += 1
            if day not in days:
                days.append(day)
        else:
            streak, days = 0, []
        bucket = 'ice_cold' if streak >= 5 and len(days) >= 3 else signal
    _, card_streak, card_days = _signal_from_cards(cards)
    signal = bucket
    if context['new'] and not (card_streak >= NEW_DRILL_RIGHTS and len(card_days) >= NEW_DRILL_DAYS):
        bucket = 'new'
    return {'bucket': bucket, 'lesson_signal': signal, 'streak': card_streak, 'streak_days': card_days,
            'mastery_streak': streak, 'mastery_days': days}


def compute(word_events, card_results, lesson_dates, today=None, confirmed_new=None, doc_before=None, introduced=None):
    """Returns {word_key: stats}. word_events rows need lesson_date, word_key, speaker, prompted, correction, asked, t_start.
    card_results rows need word_key, ts, result, attempt. lesson_dates = all lesson dates (ISO strings).
    confirmed_new = {(lesson_date, word_key)} marked new for that lesson by Amal or Medi (amal_rules kind 'new').
    doc_before = {lesson_date: {word_key}} words present in the Doc snapshot taken BEFORE that lesson; a word heard in a lesson
    and absent from that lesson's snapshot is new by the Doc rule; a date missing from the dict = unknown, rule skipped.
    introduced = {(lesson_date, word_key)} chat/asked inference; kept in the stats as 'new_candidate', never buckets."""
    confirmed_new = set(confirmed_new or ())
    doc_before = doc_before or {}
    introduced = set(introduced or ())
    marked_keys = {k for _, k in confirmed_new}
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
        medi = [e for e in evs if e.get('speaker') == 'Medi']
        independent = [e for e in medi if _independent_use(e)]
        qualifying_dates = {str(e['lesson_date']) for e in independent}
        helped_dates = {str(e['lesson_date']) for e in medi if _known_help_or_correction(e)}
        lesson_signals = _per_lesson_signals(medi)
        first_lesson = str(medi[0]['lesson_date']) if medi else None
        seen_dates = sorted({str(e['lesson_date']) for e in medi})
        # Introduction semantics are independent of who spoke; don't lose existing New marks.
        all_dates = sorted({str(e['lesson_date']) for e in evs})
        marked = key in marked_keys
        by_doc = any(d in doc_before and key not in doc_before[d] for d in all_dates)
        new_candidate = bool(first_lesson) and ((first_lesson, key) in introduced
                                                or any(e.get('asked') for e in evs if str(e['lesson_date']) == first_lesson))
        context = {'version': 2, 'new': marked or by_doc,
                   'lessons': [[d, sig, True if d in qualifying_dates else (False if d in helped_dates else None)] for d, sig in lesson_signals],
                   'cards': [{k: c[k] for k in ('id', 'ts', 'result', 'attempt') if k in c} for c in cards]}
        progress = progress_from_context(context)
        bucket = progress['bucket']
        last_reviewed = max([x for x in [seen_dates[-1] if seen_dates else None, str(cards[-1]['ts']) if cards else None] if x], default=None)
        recent = first_lesson in recent_dates if first_lesson else False
        out[key] = {'word_key': key, 'bucket': bucket, 'last_reviewed': last_reviewed, 'last_lesson': seen_dates[-1] if seen_dates else None,
                    'seen_lessons': len(seen_dates), 'times_seen': len(medi), 'independent_uses': len(independent),
                    'times_missed': sum(1 for e in medi if _signal_from_event(e) == 'missed') + sum(1 for c in cards if c['result'] == 'missed'),
                    'card_right': sum(1 for c in cards if c['result'] == 'got'), 'card_wrong': sum(1 for c in cards if c['result'] == 'missed'),
                    **progress, 'progress_context': context, 'recent': recent, 'weight': 3.0 if bucket in ('missed', 'new') else 1.0,
                    'new_candidate': new_candidate, 'grammar_misses': sum(1 for e in medi if e.get('correction') and e.get('miss_kind') in GRAMMAR_KINDS),
                    'grammar_kinds': sorted({e['miss_kind'] for e in medi if e.get('correction') and e.get('miss_kind') in GRAMMAR_KINDS})}
    return out


def introduced_from_chat(typed_rows, words=None):
    """{(lesson_date, word_key)} for every Doc word Amal typed in a lesson chat, by exact/loose/skeleton match of the typed form
    or by consonant family (Basa6tek -> the babse6 family), so a conjugation she typed counts for its Doc lemma."""
    import re
    from arabizi import Matcher
    import understand_lesson as ul
    words = words or ul.load_words()
    m = Matcher(words)
    fam = {}
    for w in words:
        fk = ul.doc_family(w)
        if fk:
            fam.setdefault(fk, set()).add(w['key'])
    out = set()
    for r in typed_rows:
        d = str(r['lesson_date'])
        for form in re.split(r'\s*/\s*|\n', str(r.get('text') or '')):
            form = form.strip(' ?.,!')
            if not form:
                continue
            k = m.match(form, fuzzy=False)
            if k:
                out.add((d, k))
            sk = ul.arabizi_to_ar_skel(form)                     # full consonant skeleton of the typed form (Basa6tek -> بستتك)
            for fk, keys in fam.items():                          # a Doc family is inside it with at most 4 affix consonants
                if len(fk) >= 3 and fk in sk and len(sk) - len(fk) <= 4:
                    out.update((d, k2) for k2 in keys)
    return out


def recompute_and_store():
    """Reads word_events + card_results + lessons from Supabase, writes word_stats. Returns the stats dict."""
    import db
    evs = db.select('word_events', {'select': 'lesson_date,word_key,speaker,prompted,correction,asked,miss_kind,t_start'})
    cards = db.select('card_results', {'select': 'id,word_key,ts,result,attempt'})
    dates = [r['date'] for r in db.select('lessons', {'select': 'date'})]
    typed = db.select('lesson_events', {'select': 'lesson_date,text', 'kind': 'eq.typed'})
    marks = db.select('amal_rules', {'select': 'lesson_date,word_key,kind', 'kind': 'eq.new'})
    confirmed = {(str(r['lesson_date']), r['word_key']) for r in marks if r.get('word_key')}
    stats = compute(evs, cards, dates, confirmed_new=confirmed, introduced=introduced_from_chat(typed))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = []
    for s in stats.values():
        r = dict(s); r.pop('new_candidate', None); r['updated_at'] = now
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
