"""Independent Speaking and Flashcards scores, mirrored in docs/js/buckets.js.

Stored cold/ice_cold display as Good/Mastered. Each lane owns its dates, errors,
recovery and mastery: five consecutive successes across >=3 dates. Speaking
earns at most one success per word/lesson date; Flashcards earns first-try rights.
Missed recovery within that lane: one independent success -> Shaky, another -> Good.
Unknown speech is neutral; helped or corrected evidence interrupts clean streaks.

Explicit New marking is shared vocabulary metadata, never inferred from an error.
Speaking leaves introduction after five timed Medi uses since the earliest New
mark, including helped uses; its underlying score then applies. Flashcards retains
the five-consecutive-first-try / two-date New drill. Neither lane graduates the other.
Amal, typed homework and untimed events never count toward Speaking.
Legacy generic fields alias Speaking. Card weighting uses only Flashcards.
"""
import datetime, collections, math

RECENT_LESSONS = 3
NEW_DRILL_RIGHTS, NEW_DRILL_DAYS = 5, 2      # Flashcards-only New drill.


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


def _is_spoken(e):
    return (e.get('speaker') == 'Medi' and type(e.get('t_start')) in (int, float)
            and math.isfinite(e['t_start']) and e['t_start'] >= 0
            and not str(e.get('text') or '').lower().startswith('homework:'))


def _track_progress(context, lane):
    """One isolated evidence lane, with its own recovery and mastery state."""
    cards = sorted(context['cards'] if lane == 'flashcards' else [], key=lambda c: (str(c['ts']), str(c.get('id') or '')))
    timeline = [(str(c['ts'])[:10], 0, str(c['ts']), i, 'card', c) for i, c in enumerate(cards)]
    timeline += [(d, 1, '', i, 'lesson', (signal, qualifies))
                 for i, (d, signal, qualifies) in enumerate(context['lessons'] if lane == 'speaking' else [])]
    bucket, streak, days, last_cards = 'never', 0, [], []
    recovery_left = 0  # Replay carries Missed recovery even while the displayed bucket is Shaky.
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
            if recovery_left:
                recovery_left -= 1
                signal = 'shaky' if recovery_left else 'cold'
        else:
            streak, days = 0, []
            if signal == 'missed' or recovery_left:
                recovery_left = 2
                if signal == 'cold':
                    signal = 'shaky'  # A grammar-only correction cannot shortcut independent recovery.
        bucket = 'ice_cold' if streak >= 5 and len(days) >= 3 else signal
    return {'bucket': bucket, 'streak': streak, 'streak_days': days,
            'mastery_streak': streak, 'mastery_days': days, 'recovery_left': recovery_left}


def progress_from_context(context):
    """Generic legacy fields now mean Speaking only; Flashcards is explicitly separate."""
    if context.get('version') != 3:
        raise ValueError('Speaking provenance must be rebuilt before scoring old mixed contexts')
    speaking = {**_track_progress(context, 'speaking'), **context['speaking']}
    raw_speaking = speaking['bucket']
    if context['new'] and speaking['intro_uses'] < 5:
        speaking['bucket'] = 'new'
    speaking['intro_target'] = 5 if context['new'] else 0
    speaking['weight'] = 3 if speaking['bucket'] in ('new', 'missed') else 1
    cards = sorted(context['cards'], key=lambda c: (str(c['ts']), str(c.get('id') or '')))
    flashcards = _track_progress(context, 'flashcards')
    if context['new'] and not (flashcards['streak'] >= NEW_DRILL_RIGHTS and len(flashcards['streak_days']) >= NEW_DRILL_DAYS):
        flashcards['bucket'] = 'new'
    flashcards.update(last_reviewed=str(cards[-1]['ts']) if cards else None,
                      attempts=len(cards), card_right=sum(c['result'] == 'got' for c in cards),
                      times_missed=sum(c['result'] == 'missed' for c in cards),
                      first_try_right=sum(c['result'] == 'got' and int(c.get('attempt') or 1) == 1 for c in cards))
    flashcards['weight'] = 3 if flashcards['bucket'] in ('new', 'missed') else 1
    return {k: speaking[k] for k in ('bucket', 'streak', 'streak_days', 'mastery_streak', 'mastery_days', 'last_reviewed', 'times_missed', 'weight')} | {
        'lesson_signal': raw_speaking, 'card_right': flashcards['card_right'], 'card_wrong': flashcards['times_missed'],
        'progress_scores': {'version': 1, 'speaking': speaking, 'flashcards': flashcards}}


def compute(word_events, card_results, lesson_dates, today=None, confirmed_new=None, doc_before=None, introduced=None):
    """Returns {word_key: stats}. word_events need lesson_date, word_key, speaker, prompted, correction, asked, t_start, text.
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
    for key in set(ev_by) | set(cd_by) | marked_keys:
        evs = sorted(ev_by[key], key=lambda e: (str(e['lesson_date']), e.get('t_start') or 0))
        cards = sorted(cd_by[key], key=lambda c: str(c['ts']))
        medi = [e for e in evs if _is_spoken(e)]
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
        new_since = min([str(d) for d, k in confirmed_new if k == key] + [d for d in all_dates if d in doc_before and key not in doc_before[d]], default=None)
        speaking_summary = {'times_seen': len(medi), 'independent_uses': len(independent),
                            'times_missed': sum(_signal_from_event(e) == 'missed' for e in medi),
                            'last_reviewed': seen_dates[-1] if seen_dates else None, 'seen_lessons': len(seen_dates),
                            'intro_uses': sum(not new_since or str(e['lesson_date']) >= new_since for e in medi),
                            'new_since': new_since}
        context = {'version': 3, 'new': marked or by_doc, 'speaking': speaking_summary,
                   'lessons': [[d, sig, True if d in qualifying_dates else (False if d in helped_dates else None)] for d, sig in lesson_signals],
                   'cards': [{k: c[k] for k in ('id', 'ts', 'result', 'attempt') if k in c} for c in cards]}
        progress = progress_from_context(context)
        bucket = progress['bucket']
        last_reviewed = seen_dates[-1] if seen_dates else None
        recent = first_lesson in recent_dates if first_lesson else False
        out[key] = {'word_key': key, 'bucket': bucket, 'last_reviewed': last_reviewed, 'last_lesson': seen_dates[-1] if seen_dates else None,
                    'seen_lessons': len(seen_dates), 'times_seen': len(medi), 'independent_uses': len(independent),
                    'times_missed': sum(1 for e in medi if _signal_from_event(e) == 'missed'),
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
    evs = db.select('word_events', {'select': 'lesson_date,word_key,speaker,prompted,correction,asked,miss_kind,t_start,text'})
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
