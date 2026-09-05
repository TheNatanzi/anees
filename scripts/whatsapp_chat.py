"""M10 - the WhatsApp chat with Amal as a second source (never pushed: data/whatsapp is git-ignored).

Facts (export of 2026-09-05): Amal live-types every drill sentence into WhatsApp during a Meet lesson (one line per ~minute),
then after class posts English prompt lines; Medi answers in Arabizi; she corrects. This module only READS the export:

  messages()                      -> [{'ts': datetime (local), 'who': 'Amal'|'Medi', 'text', 'media', 'kind', 'line'}]
  lesson_lines(start, end)        -> Amal's typed lines inside a lesson window as (rel 'HH:MM:SS', 'Amal', text) - the
                                     same shape as the Meet-chat sidecar, so understand_lesson.locate_chat() takes them as-is
  homework_episodes()             -> [{'date', 'prompts': [...English lines...], 'answers': [...Medi Arabizi...], 'corrections': [...]}]
  kind(text)                      -> 'arabizi' | 'english' | 'gloss' | 'link' | 'media' | 'short' (never guessed: short/unknown stays 'short')

The export is `data/whatsapp/raw/WhatsApp Chat with *.txt` (Android format "M/D/YY, H:MM AM - Name: text", narrow no-break
space before AM/PM, multi-line messages continue on lines without a timestamp)."""
import datetime, io, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'whatsapp' / 'raw'
AMAL = 'AMAL Arabic Tutor Abusrohr'
NAMES = {AMAL: 'Amal', 'Medi Natanzi': 'Medi'}
_HEAD = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{2}), (\d{1,2}):(\d{2})[  ]([AP]M) - (.*)$')
_ARABIZI_DIGIT = re.compile(r'[a-z][235678][a-z]|^[235678][a-z]|[a-z][235678]$', re.I)
_URL = re.compile(r'https?://\S+')
_EN = set("""the a an to of and is are was were be do does did don't doesn't didn't you your he she it they we i my me him her
his them their this that these those what when where why how who which not no yes if or but so because with without for from
in on at by about into over after before again very really just only also still yet can could should would will won't
have has had make made get got give gave take took go went come came say said tell told ask asked know knew think thought
want wanted need like love feel felt see saw look time day today tomorrow yesterday week meeting people someone anything
everything something nothing upset happy sad angry tired ready sure maybe never always sometimes remind change enjoy fun
pictures songs camping everyone excited apologize apologise hurt deal told unintentionally many""".split())
_AR_GLUE = set('ana inta inti intu i7na e7na huwwe heyye humme shu bas la ma mish mesh fi bi min ma3 3ala kteer kaman ya3ni lamma lama iza aw u w wa ya el al hon honak bukra mbaare7 embare7 laazem lazem mumken yemken ra7 bedi beddi bedak bedek bedna bedo bedha bedhom'.split())


def kind(text):
    """Classify one message. 'gloss' = "arabizi = english" teaching line; 'short' = too little to tell (never guessed)."""
    t = (text or '').strip()
    if not t:
        return 'short'
    if t.endswith('(file attached)'):
        return 'media'
    if _URL.search(t):
        return 'link'
    if re.search(r'[؀-ۿ]', t):
        return 'arabizi'                                   # Arabic script counts as Arabic
    if ' = ' in t or re.search(r'\w\s*=\s*\w', t):
        return 'gloss'
    toks = [w.strip('.,!?…"\'()') for w in re.split(r'\s+', t)]
    toks = [w for w in toks if w]
    if not toks:
        return 'short'
    ar = sum(1 for w in toks if _ARABIZI_DIGIT.search(w) or w.lower().rstrip('?') in _AR_GLUE)
    en = sum(1 for w in toks if w.lower().strip("’'") in _EN or w.lower().replace('’', "'") in _EN)
    if len(toks) == 1 and ar == 0 and en == 0:
        return 'short'
    if ar and ar >= en:
        return 'arabizi'
    if en and en > ar:
        return 'english'
    return 'short' if len(toks) <= 2 else 'arabizi'   # 3+ Latin words with no English function word: Arabizi typed without digits (e.g. "Jaahez ya Medi")


def _file():
    fs = sorted(RAW.glob('WhatsApp Chat with *.txt'))
    if not fs:
        raise FileNotFoundError(f'no WhatsApp export in {RAW}')
    return fs[0]


_CACHE = {}


def messages(path=None):
    path = Path(path) if path else _file()
    k = str(path)
    if k in _CACHE:
        return _CACHE[k]
    out, cur = [], None
    for n, raw in enumerate(io.open(path, encoding='utf-8').read().split('\n'), 1):
        line = raw.rstrip('\r')
        m = _HEAD.match(line)
        if m:
            mo, d, y, h, mi, ap, rest = m.groups()
            h = int(h) % 12 + (12 if ap == 'PM' else 0)
            ts = datetime.datetime(2000 + int(y), int(mo), int(d), h, int(mi))
            who, _, text = rest.partition(': ')
            if who not in NAMES:                          # system lines ("Messages and calls are end-to-end encrypted")
                cur = None
                continue
            cur = {'ts': ts, 'who': NAMES[who], 'text': text, 'line': n}
            out.append(cur)
        elif cur is not None:
            cur['text'] += '\n' + line
    for m in out:
        t = m['text'].strip()
        m['edited'] = t.endswith('<This message was edited>')
        t = t.replace('<This message was edited>', '').strip()
        m['deleted'] = t == 'This message was deleted'
        mm = re.match(r'^(\S+\.(?:opus|jpg|jpeg|mp4|pdf|png)) \(file attached\)$', t)
        m['media'] = mm.group(1) if mm else None
        m['text'] = t
        m['kind'] = 'media' if m['media'] else ('short' if m['deleted'] else kind(t))
    _CACHE[k] = out
    return out


def parse_source_start(source):
    """summary.json 'source' = 'jir-hcex-xzd (2026-09-04 14 03 GMT-7)' -> local datetime of the recording start."""
    m = re.search(r'\((\d{4})-(\d{2})-(\d{2}) (\d{2}) (\d{2})', source or '')
    if not m:
        return None
    y, mo, d, h, mi = map(int, m.groups())
    return datetime.datetime(y, mo, d, h, mi)


def lesson_lines(start, end=None, minutes=None, who='Amal', slack=3):
    """Lines `who` typed between start and end (datetimes, local). Returns the Meet-sidecar shape:
    [('HH:MM:SS' relative to start, 'Amal', text)] - only Arabizi / gloss / Arabic lines (never links, media or English chat)."""
    if end is None:
        end = start + datetime.timedelta(minutes=minutes or 75)
    lo = start - datetime.timedelta(minutes=slack)
    out = []
    for m in messages():
        if m['who'] != who or m['deleted'] or not (lo <= m['ts'] <= end):
            continue
        rel = max(0, int((m['ts'] - start).total_seconds()))
        for piece, from_gloss in _split_gloss(m['text'], tagged=True):   # each line of a multi-line message is judged on its own
            if from_gloss or kind(piece) in ('arabizi', 'gloss'):            # the Arabic side of "fatra = while" is a typed word even when short
                out.append((f'{rel // 3600:02d}:{rel % 3600 // 60:02d}:{rel % 60:02d}', who, piece))
    return out


def _split_gloss(text, tagged=False):
    """'bat2assaf = I apologize' -> ['bat2assaf'] (the English side is not a typed Arabic word). Multi-line messages split.
    tagged=True returns (piece, came_from_a_gloss) pairs."""
    out = []
    for ln in text.split('\n'):
        ln = ln.strip()
        if not ln:
            continue
        if re.search(r'\s=\s', ln) or re.search(r'\w=\w', ln):
            left = re.split(r'\s*=\s*', ln)[0].strip()
            if left and kind(left) != 'english':
                out.append((left, True))
            continue
        out.append((ln, False))
    return out if tagged else [p for p, _ in out]


def meet_links():
    """Every Meet link posted, oldest first: (ts, who, code)."""
    out = []
    for m in messages():
        mm = re.search(r'meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})', m['text'])
        if mm:
            out.append((m['ts'], m['who'], mm.group(1)))
    return out


def homework_episodes(burst_min=3, gap_minutes=25, answer_hours=36):
    """Real homework rounds, found by their shape (no lesson anchor needed - most lessons before Aug 2026 had no Meet link in
    the chat): a BURST of >= `burst_min` English lines by Amal (each a sentence, within `gap_minutes` of each other, no Medi
    line in between) = prompts; Medi's Arabizi lines after the burst (within `answer_hours`, until Amal's next burst) = answers;
    Amal's Arabizi / gloss lines after the first answer = corrections. Pairing is by order only (never guessed)."""
    msgs = [m for m in messages() if not m['deleted'] and m['kind'] not in ('media', 'link')]
    eps, i = [], 0
    while i < len(msgs):
        m = msgs[i]
        if m['who'] == 'Amal' and m['kind'] == 'english' and _looks_prompt(m['text']):
            j, burst = i, [m]
            while j + 1 < len(msgs) and msgs[j + 1]['who'] == 'Amal' and (msgs[j + 1]['ts'] - msgs[j]['ts']).total_seconds() <= gap_minutes * 60:
                j += 1
                if msgs[j]['kind'] == 'english' and _looks_prompt(msgs[j]['text']):
                    burst.append(msgs[j])
            if len(burst) >= burst_min:
                stop = burst[-1]['ts'] + datetime.timedelta(hours=answer_hours)
                answers, corrections, k = [], [], j + 1
                while k < len(msgs) and msgs[k]['ts'] <= stop:
                    x = msgs[k]
                    if x['who'] == 'Amal' and x['kind'] == 'english' and _looks_prompt(x['text']) and answers:
                        break                                     # her next round starts
                    if x['who'] == 'Medi' and x['kind'] == 'arabizi':
                        answers.append({'text': x['text'], 'ts': x['ts'].isoformat(timespec='minutes')})
                    elif x['who'] == 'Amal' and x['kind'] in ('arabizi', 'gloss') and answers:
                        corrections.append({'text': x['text'], 'ts': x['ts'].isoformat(timespec='minutes'), 'after_answer': len(answers)})
                    k += 1
                eps.append({'date': burst[0]['ts'].date().isoformat(), 'ts': burst[0]['ts'].isoformat(timespec='minutes'),
                            'prompts': [b['text'] for b in burst], 'answers': answers, 'corrections': corrections})
                i = j + 1
                continue
        i += 1
    return eps


def _looks_prompt(text):
    """An English line that reads as a homework prompt (a sentence for Medi to translate), not chat."""
    t = text.strip()
    if len(t) < 12 or 'lol' in t.lower() or t.lower().startswith(('yeah', 'ok', 'i think', 'i don', 'never mind', 'let', 'sorry', 'thank', 'hi ', 'hey')):
        return False
    return not _URL.search(t)


def stats():
    ms = messages()
    by_who = {}
    for m in ms:
        by_who[m['who']] = by_who.get(m['who'], 0) + 1
    kinds = {}
    for m in ms:
        if m['who'] == 'Amal':
            kinds[m['kind']] = kinds.get(m['kind'], 0) + 1
    return {'messages': len(ms), 'by_who': by_who, 'amal_kinds': kinds, 'first': ms[0]['ts'].isoformat() if ms else None,
            'last': ms[-1]['ts'].isoformat() if ms else None, 'meet_links': len(meet_links()), 'voice_notes': sum(1 for m in ms if (m['media'] or '').endswith('.opus'))}


if __name__ == '__main__':
    import json, sys
    print(json.dumps(stats(), ensure_ascii=False, indent=1))
    if len(sys.argv) > 1:
        st = datetime.datetime.fromisoformat(sys.argv[1])
        for row in lesson_lines(st, minutes=int(sys.argv[2]) if len(sys.argv) > 2 else 75):
            print(*row)
