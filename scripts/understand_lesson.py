"""M1 - understand one lesson: topics, every Doc-word occurrence with time/speaker/prompted/correction/uptake, label confidence,
audio clips (<= 25 s, shared by nearby events), Amal's typed chat words located in the transcript (+-120 s).

  python scripts/understand_lesson.py 2026-09-04
  python scripts/understand_lesson.py 2026-08-25 --scribe data/aug25/eleven_scribe_auto.json --audio data/aug25/audio/aug25.mp3

Writes data/lessons/<date>/understanding.json and docs/lessons/<date>/clips/*.mp3. Never calls a paid API (reuses scribe.json).
Rules reused from scripts/tutor_reaction_exp.py (wiki 15): NEG / META_EN cues, recast within 5 s, learner uptake within 10 s."""
import argparse, io, json, re, subprocess, sys, collections, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import Matcher, ARABIC, arabic_norm, loose, short, skeleton, strip_pronoun
from lesson_text import is_filler, is_confirm
from english_stop import ENGLISH_STOP
import lesson_pipeline as lp

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / 'data' / 'lessons'
DOCS = ROOT / 'docs' / 'lessons'
WORDS_JSON = ROOT / 'data' / 'vocab' / 'words.json'
MAX_UNLABELED = 0.15        # speaker-label floor: above this share of '?' words, per-speaker facts are published as "-"
CLIP_MAX = 25.0
CLIP_PAD_BEFORE, CLIP_PAD_AFTER = 3.0, 4.0
CHAT_WINDOW = 120.0
NEG = {'la', 'laa', 'no', 'nope', 'not', 'mish', 'mush', 'لا', 'لأ', 'لاء', 'مش', 'مو'}
ELICIT_TUTOR = ('how do you say', 'how do we say', 'how would you say', 'what is', "what's", 'what do you say', 'say it', 'in arabic', 'شو يعني', 'كيف بتقول', 'كيف بنقول', 'كيف بتحكي', 'شو بتقول', 'ايش يعني')
ASK_LEARNER = ('how do you say', 'how do i say', 'how to say', 'what is', "what's", 'in arabic', 'what was', 'شو يعني', 'كيف بقول', 'كيف بحكي', 'شو اسم', 'كيف بنقول')
META_EN = {'say', 'says', 'said', 'instead', 'means', 'mean', 'meaning', 'use', 'takes', 'take', "don't", 'dont', 'should', 'because',
           'preposition', 'verb', 'plural', 'feminine', 'masculine', 'past', 'present', 'form', 'conjugate'}
STOP_KEYS = {'ana', 'inta', 'inti', 'intu', 'huwe', 'hiye', 'hume', 'i7na', 'shu', 'bas', 'la', 'ah', 'ok', 'okay', 'yes', 'no', 'tamam'}
# glue keys (Doc rows that are conversation moves, not vocabulary to grade): never counted as missed / nailed
GLUE_KEYS = {'shu', 'bas', 'ai', 'aw', 'em', 'u', 'fi', 'bi', 'min', 'ya3ni', 'iza', 'lama', 'hala', 'ah', 'aha', 'tayeb', 'tamam', '5alas', 'sa7', 'mashi', 'wala', 'ma', 'ma3', 'la'}
FARSI_SPANS = {'2026-08-25': [(218.0, 259.0), (2440.0, 2452.0)]}      # Medi talking to his father (memory rule)

# Arabizi -> Arabic consonant skeleton (for chat-form <-> transcript matching without the Doc)
_A2C = [('kh', 'خ'), ('gh', 'غ'), ('sh', 'ش'), ('th', 'ث'), ('dh', 'ذ'), ('6', 'ط'), ('7', 'ح'), ('3', 'ع'), ('5', 'خ'), ('9', 'ص'), ('8', 'غ'),
        ('2', 'ق'), ('q', 'ق'), ('b', 'ب'), ('t', 'ت'), ('j', 'ج'), ('d', 'د'), ('r', 'ر'), ('z', 'ز'), ('s', 'س'), ('f', 'ف'), ('k', 'ك'),
        ('l', 'ل'), ('m', 'م'), ('n', 'ن'), ('h', 'ه'), ('w', 'و'), ('y', 'ي'), ('g', 'ج'), ('p', 'ب'), ('v', 'ف'), ('c', 'ك'), ('x', 'خ')]
_FOLD_AR = str.maketrans({'ط': 'ت', 'ص': 'س', 'ض': 'د', 'ظ': 'ز', 'ث': 'ت', 'ذ': 'د', 'ق': '', 'ح': 'ه', 'ا': '', 'و': '', 'ي': '', 'ء': '', 'ة': ''})


def arabizi_to_ar_skel(s):
    s = s.lower()
    s = re.sub(r"[’'`ʼ]", '2', s)
    out = ''
    i = 0
    while i < len(s):
        for a, c in _A2C:
            if s.startswith(a, i):
                out += c; i += len(a); break
        else:
            i += 1
    return out.translate(_FOLD_AR)


def ar_skel(word):
    """Consonant skeleton of an Arabic-script token (folded: ط=ت, ص=س ...; long vowels and ع/ء dropped)."""
    n = arabic_norm(word)
    return n.translate(_FOLD_AR)


PREFIXES = ('بت', 'بن', 'بي', 'ب', 'ن', 'ت', 'ي', 'ا', 'م')
SUFFIXES = ('ني', 'نا', 'تو', 'تي', 'هم', 'ها', 'كم', 'ه', 'ت', 'و', 'ي', 'ك')


def family_key(form):
    """Chat/Doc form -> root-ish key: conjugation prefixes and suffixes are peeled off the Arabic consonant skeleton while
    at least 3 consonants remain (Btenbese6i, Banbese6, Enbasa6u -> the same family)."""
    sk = arabizi_to_ar_skel(re.split(r'[ /?]', form.strip())[0])
    changed = True
    while changed and len(sk) > 3:
        changed = False
        for p in PREFIXES:
            if sk.startswith(p) and len(sk) - len(p) >= 3:
                sk = sk[len(p):]; changed = True; break
    changed = True
    while changed and len(sk) > 3:
        changed = False
        for x in SUFFIXES:
            if sk.endswith(x) and len(sk) - len(x) >= 3:
                sk = sk[:-len(x)]; changed = True; break
    return sk


def load_words():
    return json.load(io.open(WORDS_JSON, encoding='utf-8'))['items']


def labeled_words(date, scribe, audio, src_name):
    """Word stream with Medi/Amal/? labels, via the pipeline's own labeling (pitch fallback when ElevenLabs merged voices)."""
    res = json.load(io.open(scribe, encoding='utf-8'))
    words, runs, summary = lp.build(res, date, '0000', src_name, mp3=audio)
    return words, runs, summary


def looks_arabizi(tok):
    """A Latin token that is plausibly Arabizi: has a digit, or an Arabic digraph / long vowel and is not common English.
    Pure vowel runs (Aaaa, ooo) are fillers, never words."""
    tok = tok.lower().strip(".,?!-'\"")
    if re.search(r'[0-9]', tok):
        return True
    if tok in ENGLISH_STOP or len(tok) < 4 or re.fullmatch(r'[aeiouh]+', tok):
        return False
    return bool(re.search(r"aa|ee|oo|kh|gh|sh|7|3|'", tok))


def find_doc_events(words, matcher, lo, hi, exclude):
    """Every Doc-word occurrence (1-3 word n-grams, longest first) inside the lesson window."""
    events = []
    n = len(words)
    i = 0
    toks = [w['w'] for w in words]
    while i < n:
        w = words[i]
        if not (lo <= w['s'] <= hi) or any(a <= w['s'] <= b for a, b in exclude) or is_filler(w['w']):
            i += 1; continue
        hit = None
        for span in (3, 2, 1):
            if i + span > n or any(words[j]['spk'] != w['spk'] for j in range(i, i + span)):
                continue
            text = ' '.join(toks[i:i + span])
            r = matcher.match_tier(text, fuzzy=False)
            if not r:
                continue
            k, tier = r
            if loose(text) in STOP_KEYS or k in STOP_KEYS or k in GLUE_KEYS:
                continue
            if not ARABIC.search(text):
                # Latin token: the lesson is mostly English, so only an Arabizi-looking token may match below the exact tier
                clean = [t.lower().strip(".,?!-'\"") for t in text.split()]
                if any(t in ENGLISH_STOP for t in clean) or any(len(t) < 2 for t in clean) or any(re.fullmatch(r'[aeiouh]+', t) for t in clean):
                    continue
                # Codex P0 (M1): a Latin hit must look like Arabizi (soon / sit / Aaaa were becoming Doc words) — except an EXACT
                # spelling of a Doc word with >= 4 letters that is not common English (Nahl for Na7el, said by Amal and repeated by Medi)
                # 'Nahl' counts when Amal herself said it within 10 s AND she typed that word in the chat (prefer set): ASR writes
                # such words in plain Latin; without the chat anchor an English look-alike (Wait, Bien) would slip through
                said_by_amal = k in matcher.prefer and any(words[j]['spk'] == 'Amal' and words[j]['w'].lower().strip(".,?!-") in clean for j in range(max(0, i - 25), min(n, i + 25)) if abs(words[j]['s'] - w['s']) <= 10)
                if not all(looks_arabizi(t) or (tier == 'exact' and len(t) >= 4) or (said_by_amal and len(t) >= 4) for t in clean):
                    continue
                if tier in ('skeleton', 'fuzzy') and not (said_by_amal and tier == 'skeleton'):
                    continue
            hit = (k, span, text, tier); break
        if hit:
            k, span, text, tier = hit
            events.append({'t_start': round(w['s'], 2), 't_end': round(words[i + span - 1]['e'], 2), 'speaker': w['spk'], 'word_key': k,
                           'text': text, 'tier': tier})
            i += span
        else:
            i += 1
    return events


def _window_text(words, starts, t0, t1, spk):
    import bisect
    a, b = bisect.bisect_left(starts, t0), bisect.bisect_right(starts, t1)
    return ' '.join(words[j]['w'].lower() for j in range(a, b) if words[j]['spk'] == spk)


def annotate(events, words, tutor='Amal', learner='Medi'):
    """prompted: Amal said the same word <= 10 s before. correction: within 5 s after Medi's word Amal says la/no/meta, or repeats
    it (recast) unless she had just elicited it ("how do you say sorry?" -> Medi answers -> Amal repeats = confirmation).
    asked: Medi asked for the word ("how do you say", "شو يعني") <= 8 s before Amal said it; his repeat is then prompted+asked.
    uptake: Medi repeats Amal's word within 10 s (marks Amal's event)."""
    by_key = collections.defaultdict(list)
    for e in events:
        by_key[e['word_key']].append(e)
    starts = [w['s'] for w in words]
    import bisect
    for e in events:
        e['prompted'] = e['correction'] = e['uptake'] = e['asked'] = e['elicited'] = False
        same = by_key[e['word_key']]
        if e['speaker'] == learner:
            prior_tutor = [o for o in same if o['speaker'] == tutor and 0 < e['t_start'] - o['t_end'] <= 10]
            e['prompted'] = bool(prior_tutor)
            tutor_before = _window_text(words, starts, e['t_start'] - 8, e['t_start'], tutor)
            e['elicited'] = any(c in tutor_before for c in ELICIT_TUTOR) and not e['prompted']
            recast = any(o['speaker'] == tutor and 0 < o['t_start'] - e['t_end'] <= 5 for o in same)
            a, b = bisect.bisect_left(starts, e['t_end']), bisect.bisect_right(starts, e['t_end'] + 5)
            cue = any(words[j]['spk'] == tutor and (loose(words[j]['w']) in NEG or words[j]['w'].lower().strip('.,?!') in META_EN or words[j]['w'] in NEG)
                      for j in range(a, b))
            e['correction'] = bool(cue or (recast and not e['elicited']))
            e['cue'] = 'cue' if cue else ('recast' if (recast and not e['elicited']) else '')
        elif e['speaker'] == tutor:
            e['uptake'] = any(o['speaker'] == learner and 0 < o['t_start'] - e['t_end'] <= 10 for o in same)
            learner_before = _window_text(words, starts, e['t_start'] - 8, e['t_start'], learner)
            e['asked'] = any(c in learner_before for c in ASK_LEARNER)
    for e in events:            # Medi's repeat of a word he asked for is prompted + asked (bucket: missed)
        if e['speaker'] == learner and e['prompted']:
            e['asked'] = any(o['speaker'] == tutor and o.get('asked') and 0 < e['t_start'] - o['t_end'] <= 10 for o in by_key[e['word_key']])
    return events


def label_confidence(words, summary):
    n = len(words)
    unl = sum(1 for w in words if w['spk'] not in ('Medi', 'Amal')) / max(1, n)
    split_ok = summary.get('speaker_split', 'ok') == 'ok'
    ok = split_ok or unl <= MAX_UNLABELED
    reason = '' if split_ok else (f'ElevenLabs merged the two voices; words were labeled by voice pitch, {unl:.0%} stayed unlabeled'
                                  + ('' if ok else f' (> {MAX_UNLABELED:.0%} floor, so per-speaker facts are not published)'))
    return {'split': summary.get('speaker_split', 'ok'), 'unlabeled_share': round(unl, 3), 'per_speaker_ok': ok, 'reason': reason}


def locate_chat(chat_lines, words, lo=0):
    """For each typed chat form: nearest transcript token (+-120 s) of the same word family (consonant skeleton, Arabic or Latin,
    one consonant may differ) -> found_family; found_form = the token carries the typed form's exact affixes too."""
    import difflib
    out = []
    for t, who, text in chat_lines:
        h, m, s_ = (int(x) for x in t.split(':'))
        ct = h * 3600 + m * 60 + s_
        forms = [f for f in re.split(r'\s*/\s*|\s+', text) if f and f.lower() not in ('bi', 'fi', 'el', 'lamma', 'ne6la3?', 'i', 'u')]
        base = (forms[0] if forms else text).strip('?.,!')
        sk = arabizi_to_ar_skel(base)                      # Arabic consonant skeleton of the typed form
        fam = family_key(base)
        lat_sk = skeleton(base)
        best, best_form = None, False
        for w in words:
            if abs(w['s'] - ct) > CHAT_WINDOW:
                continue
            tok = w['w'].strip('.,?!-')
            if ARABIC.search(tok):
                ts = ar_skel(tok)
                fam_ok = len(fam) >= 3 and fam in ts
                form_ok = bool(sk) and ts == sk
            else:
                tl = tok.lower()
                if tl in ENGLISH_STOP or len(tl) < 3 or re.fullmatch(r'[aeiouh]+', tl):
                    continue                         # Codex P0 (M1): 'the' / 'both' / 'Inti' are not Arabizi forms
                ts = arabizi_to_ar_skel(tok)         # same consonant alphabet as the Arabic branch (ASR spells Medi's forms freely: Betenbisti, Imbasatu)
                fam_ok = len(fam) >= 3 and fam in ts and len(ts) - len(fam) <= 4
                form_ok = bool(sk) and ts == sk
            if not (fam_ok or form_ok):
                continue
            better = best is None or (form_ok and not best_form) or (form_ok == best_form and abs(w['s'] - ct) < abs(best['s'] - ct))
            if better:
                best, best_form = w, form_ok
        out.append({'chat_time': t, 'chat_t': ct, 'typed': text, 'found': best is not None, 'found_form': bool(best) and best_form,
                    'at': round(best['s'], 1) if best else None, 'delta': round(best['s'] - ct, 1) if best else None,
                    'token': best['w'] if best else None, 'speaker': best['spk'] if best else None})
    return out


GLUE_SUBTOPICS = ('Sentence Toolbox', 'Quantity / Degree Words', 'Introductions', 'Greetings', 'Everyday Expressions', 'Adverbs of Time')


def doc_family(w):
    """Doc word -> Arabic consonant family key (affixes stripped); '' when too short to be a safe family."""
    fk = family_key(strip_pronoun(w['arabizi']))
    return fk if len(fk) >= 3 else ''


def rank_topics(events, chat_rows, words, lo, hi, exclude, wordmap):
    """Topics = Doc subtopics + typed-chat families, scored by DISTINCT content words heard (exact Doc hits + same-family
    tokens such as conjugated forms), each word capped at 5 hits so one drilled word cannot own the lesson. Glue subtopics
    (Sentence Toolbox, quantity words, greetings) are listed separately as 'glue'."""
    toks = [w for w in words if lo <= w['s'] <= hi and not any(a <= w['s'] <= b for a, b in exclude) and not is_filler(w['w'])]
    tok_sk = collections.Counter()
    for w in toks:
        t = w['w'].strip('.,?!-')
        if ARABIC.search(t):
            sk = ar_skel(t)
        else:
            tl = t.lower()
            if tl in ENGLISH_STOP or not looks_arabizi(tl):
                continue
            sk = arabizi_to_ar_skel(t)
        if len(sk) >= 3:
            tok_sk[sk] += 1

    def fam_count(fk):
        # a family is heard when a token skeleton contains it with at most 3 extra consonants (affixes), never inside long unrelated words
        return sum(c for sk, c in tok_sk.items() if fk in sk and len(sk) - len(fk) <= 3)

    exact = collections.defaultdict(collections.Counter)
    for e in events:
        exact[e['word_key']][e['text']] += 1
    # one score per FAMILY per subtopic (a past-tense paradigm of 8 rows is one family, not eight)
    fam_rows = collections.defaultdict(list)
    for k, w in wordmap.items():
        fk = doc_family(w)
        fam_rows[(f"{w['topic']} › {w['subtopic']}", fk or k)].append(k)
    scores, why = collections.Counter(), {}
    fam_cache = {}
    for (label, fk), keys in fam_rows.items():
        ex = sum(sum(exact[k].values()) for k in keys)
        if fk in fam_cache:
            fh = fam_cache[fk]
        else:
            fh = fam_count(fk) if (fk not in wordmap and len(fk) >= 3) else 0
            fam_cache[fk] = fh
        hits = ex + fh
        if hits == 0:
            continue
        scores[label] += min(hits, 5)
        shown = sorted(keys, key=lambda k: -sum(exact[k].values()))[0]
        why.setdefault(label, collections.Counter())[wordmap[shown]['arabizi']] += hits
    chat_fams = collections.defaultdict(list)
    for r in chat_rows:
        chat_fams[family_key(r['typed'])].append(r['typed'])
    for fk, forms in chat_fams.items():
        if len(fk) < 3:
            continue
        n = fam_count(fk)
        if n:
            uniq = list(dict.fromkeys(forms))
            label = 'typed family: ' + ' / '.join(uniq[:5]) + (f' … (+{len(uniq) - 5} more)' if len(uniq) > 5 else '')
            scores[label] += min(n, 5) * max(1, len(set(forms)) // 2)
            why[label] = collections.Counter({f: 1 for f in forms}) + collections.Counter({sk: c for sk, c in tok_sk.items() if fk in sk and len(sk) - len(fk) <= 3})
    ranked = [{'topic': k, 'score': n, 'distinct_words': len(why[k]), 'top_words': [f'{w} ×{c}' for w, c in why[k].most_common(6)],
               'glue': any(g in k for g in GLUE_SUBTOPICS)} for k, n in scores.most_common(40)]
    content = [t for t in ranked if not t['glue']][:10]
    glue = [t for t in ranked if t['glue']][:5]
    return content + glue


def apply_floor(events, conf):
    """Speaker-label floor: when per-speaker facts are not trustworthy, every event loses its speaker and its speaker-based flags."""
    for e in events:
        e['label_ok'] = conf['per_speaker_ok']
        if not conf['per_speaker_ok']:
            e['speaker'] = '?'; e['prompted'] = e['correction'] = e['uptake'] = e['asked'] = None
    return events


def cut_clips(events, audio, out_dir, date):
    """Group events into windows <= 25 s (pad 3 s before, 4 s after), cut once per window, share the clip."""
    out_dir.mkdir(parents=True, exist_ok=True)
    ev = sorted(events, key=lambda e: e['t_start'])
    i, clips = 0, []
    while i < len(ev):
        cs = max(0.0, ev[i]['t_start'] - CLIP_PAD_BEFORE)
        j = i
        while j + 1 < len(ev) and ev[j + 1]['t_end'] + CLIP_PAD_AFTER - cs <= CLIP_MAX:
            j += 1
        ce = min(ev[j]['t_end'] + CLIP_PAD_AFTER, cs + CLIP_MAX)
        name = f'{date}_{int(cs * 10):06d}_{int(ce * 10):06d}.mp3'      # start+end in the name: a re-cut window never reuses a stale file
        path = out_dir / name
        if not path.exists():
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{cs:.2f}', '-t', f'{ce - cs:.2f}', '-i', str(audio), '-ac', '1', '-ar', '16000', '-b:a', '32k', str(path)], check=True)
        for k in range(i, j + 1):
            ev[k]['clip'] = name; ev[k]['clip_start'] = round(cs, 2); ev[k]['clip_end'] = round(ce, 2)
            ev[k]['offset'] = round(ev[k]['t_start'] - cs, 2)
        clips.append({'file': name, 'start': round(cs, 2), 'end': round(ce, 2), 'events': j - i + 1})
        i = j + 1
    return clips


def log_fn(*a):
    print(*a)


def understand(date, scribe=None, audio=None, src=None, clips=True):
    d = LESSONS / date
    scribe = Path(scribe) if scribe else d / 'scribe.json'
    audio = Path(audio) if audio else d / 'audio.mp3'
    summary = json.load(io.open(d / 'summary.json', encoding='utf-8')) if (d / 'summary.json').exists() else {}
    src_name = src or summary.get('source', date)
    words, runs, s2 = labeled_words(date, scribe, audio, src_name)
    summary = {**s2, **{k: v for k, v in summary.items() if k in ('chat_lines', 'link')}}
    lo, hi = summary['lesson_start'], summary['lesson_end']
    exclude = FARSI_SPANS.get(date, [])
    conf = label_confidence(words, summary)
    wlist = load_words(); wordmap = {w['key']: w for w in wlist}
    m = Matcher(wlist)
    chat0 = summary.get('chat_lines') or []
    m.prefer = frozenset(k for k in (m.match(re.split(r'\s*/\s*|\s+', t)[0].strip('?.,!'), fuzzy=False) for _, _, t in chat0) if k)   # Amal's typed words break ties (Na7el vs Na7le)
    events = annotate(find_doc_events(words, m, lo, hi, exclude), words)
    import miss_kind
    miss_kind.classify_all(events, words, wordmap, use_llm=False, log=log_fn, matcher=m)
    chat = summary.get('chat_lines') or []
    if not chat and src:
        chat = [list(x) for x in lp.chat_sidecar(Path(src)) if x[1].lower() != 'medi' and not x[1].lower().startswith('mahdi')]
    chat_rows = locate_chat(chat, words)
    topics = rank_topics(events, chat_rows, words, lo, hi, exclude, wordmap)
    events = apply_floor(events, conf)
    clip_meta = cut_clips(events, audio, DOCS / date / 'clips', date) if clips else []
    medi_ev = [e for e in events if e['speaker'] == 'Medi'] if conf['per_speaker_ok'] else None
    out = {'date': date, 'source': src_name, 'engine': 'elevenlabs scribe_v2 (reused scribe.json, no new charge)', 'built': datetime.datetime.now().isoformat(timespec='seconds'),
           'lesson_start': lo, 'lesson_end': hi, 'minutes': summary.get('minutes'), 'words': len([w for w in words if lo <= w['s'] <= hi]),
           'label_confidence': conf, 'topics': topics,
           'counts': {'doc_events': len(events), 'distinct_words': len({e['word_key'] for e in events}),
                      'medi_events': (len(medi_ev) if medi_ev is not None else None),
                      'medi_unprompted': (sum(1 for e in medi_ev if not e['prompted'] and not e['correction']) if medi_ev is not None else None),
                      'medi_prompted': (sum(1 for e in medi_ev if e['prompted']) if medi_ev is not None else None),
                      'medi_corrected': (sum(1 for e in medi_ev if e['correction']) if medi_ev is not None else None),
                      'chat_typed': len(chat_rows), 'chat_found': sum(1 for r in chat_rows if r['found']), 'chat_found_form': sum(1 for r in chat_rows if r['found_form'])},
           'chat': chat_rows, 'events': events, 'clips': clip_meta}
    io.open(d / 'understanding.json', 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    io.open(d / 'words_labeled.json', 'w', encoding='utf-8').write(json.dumps(words, ensure_ascii=False))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--scribe'); ap.add_argument('--audio'); ap.add_argument('--src'); ap.add_argument('--no-clips', action='store_true')
    a = ap.parse_args()
    out = understand(a.date, a.scribe, a.audio, a.src, clips=not a.no_clips)
    print(json.dumps({k: out[k] for k in ('date', 'minutes', 'words', 'label_confidence', 'counts')}, ensure_ascii=False, indent=1))
    for t in out['topics'][:6]:
        print(f"  topic {t['score']:4} {'glue ' if t['glue'] else '     '} {t['topic']}  {t['top_words'][:5]}")
    print('  chat found (family)', out['counts']['chat_found'], '/', out['counts']['chat_typed'], ' exact form', out['counts']['chat_found_form'], ' clips', len(out['clips']))


if __name__ == '__main__':
    main()
