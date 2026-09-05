"""M10b - tutor-typed lines as ground truth for a lesson minute.

Two typed sources, one shape [('HH:MM:SS' into the recording, 'Amal', text)]:
  * the Meet chat sidecar (already in summary.json 'chat_lines')
  * Amal's WhatsApp lines typed while the lesson ran (scripts/whatsapp_chat.lesson_lines, private export)

What a typed line changes (never the speaker of an audio event, never a guessed word):
  1. Doc words in the line (trusted matcher tiers only) join Matcher.prefer, so a tie between two Doc words breaks toward the
     word she typed.
  2. A Medi event of that word 60 s before .. 150 s after the line (WhatsApp stamps are whole minutes and the recording start
     is a whole minute, so the window is wide) is marked `typed`; if it was neither prompted nor corrected it becomes
     prompted (reading her sentence aloud is not unprompted production). Every such change is listed in `diff` with the
     line that caused it, so Medi can accept or reject each one.
  3. The lines are stored in Supabase `chat_lines` (lesson_date, t_rel, source, text, word_keys) for the report and the eval."""
import datetime, io, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arabizi import Matcher, strip_pronoun, PRONOUNS

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / 'data' / 'lessons'
BEFORE, AFTER = 60.0, 150.0
TRUSTED = ('exact', 'fold', 'short', 'arabic')
GLUE = set(PRONOUNS) | {'u', 'w', 'wa', 'ya', 'el', 'al', 'il', 'fi', 'bi', 'min', 'ma3', '3ala', 'mish', 'mesh', 'ma', 'la', 'bas', 'aw', 'iza', 'lamma', 'lama', 'enno', 'inno', 'shu', 'ah', 'yes', 'no', 'or', 'not', 'a', 'the', 'and', 'p', 'f', 'm'}
_TOK = re.compile(r"[A-Za-z0-9'’]+(?:-[A-Za-z0-9'’]+)*|[؀-ۿ]+")


def rel_seconds(hhmmss):
    h, m, s = (int(x) for x in hhmmss.split(':'))
    return h * 3600 + m * 60 + s


def line_keys(text, matcher):
    """Doc words in a typed line, longest span first (1-3 tokens), trusted tiers only. Glue and single letters skipped."""
    toks = [t.strip("'’") for t in _TOK.findall(text)]
    toks = [t for t in toks if t and not re.fullmatch(r'\d+', t)]
    keys, i = [], 0
    while i < len(toks):
        hit = None
        for span in (3, 2, 1):
            if i + span > len(toks):
                continue
            form = ' '.join(toks[i:i + span])
            if span == 1 and (form.lower() in GLUE or len(form) < 2):
                break
            mt = matcher.match_tier(form, fuzzy=False)
            if mt and mt[1] in TRUSTED:
                hit = (mt[0], span); break
        if hit:
            keys.append(hit[0]); i += hit[1]
        else:
            i += 1
    return list(dict.fromkeys(keys))


def whatsapp_lines(summary, date):
    """Amal's WhatsApp lines inside this lesson's recording window, in the sidecar shape. [] when the export is absent."""
    try:
        import whatsapp_chat as W
        start = W.parse_source_start(summary.get('source'))
        if not start:
            return []
        minutes = float(summary.get('minutes') or 75)
        return [list(x) for x in W.lesson_lines(start, minutes=minutes + 5)]
    except FileNotFoundError:
        return []


def merged_lines(summary, date):
    """Meet sidecar lines + WhatsApp lines, tagged by source, sorted by time; a line typed in both places counts once."""
    meet = [list(x) for x in (summary.get('chat_lines') or [])]
    wa = whatsapp_lines(summary, date)
    out = []
    for src, rows in (('meet', meet), ('whatsapp', wa)):
        for t, who, text in rows:
            k, tr = text.strip().lower(), rel_seconds(t)
            if any(o['text'].strip().lower() == k and abs(o['t_rel'] - tr) <= 120 for o in out):
                continue                                    # the same line typed in both places within 2 min counts once; a repeat 20 min later is a new drill  [Codex M10 P1]
            out.append({'t': t, 't_rel': tr, 'who': who, 'text': text, 'source': src})
    out.sort(key=lambda r: r['t_rel'])
    return out


def apply_typed(events, lines, matcher, learner='Medi'):
    """Mark events covered by a typed line; promote unprompted+uncorrected Medi events to prompted. Returns the diff list."""
    diff = []
    for ln in lines:
        ln['keys'] = line_keys(ln['text'], matcher)
        for e in events:
            if e['word_key'] not in ln['keys'] or not (-BEFORE <= e['t_start'] - ln['t_rel'] <= AFTER):
                continue
            e['typed'] = True
            e['typed_line'] = ln['text'][:120]
            e['typed_t'] = ln['t']
            if e['speaker'] == learner and not e['prompted'] and not e['correction']:
                e['prompted'] = True
                e['prompted_by'] = 'typed sentence'
                diff.append({'word_key': e['word_key'], 't_start': e['t_start'], 'text': e.get('text', ''), 'was': 'unprompted (counted as said cold)',
                             'now': 'prompted (read from her typed sentence)', 'line': ln['text'][:160], 'line_t': ln['t'], 'source': ln['source']})
    return diff


def store(date, lines):
    """Upsert the lines into Supabase chat_lines (unique on lesson_date, source, t_rel, text)."""
    import db
    rows = [{'lesson_date': date, 't_rel': ln['t_rel'], 'source': ln['source'], 'who': ln['who'], 'text': ln['text'], 'word_keys': ln.get('keys', [])} for ln in lines]
    if not rows:
        return 0
    db.rest('DELETE', 'chat_lines', params={'lesson_date': f'eq.{date}'}, prefer='return=minimal')
    return db.upsert('chat_lines', rows)


def report(date):
    """One line for the log / handoff."""
    u = json.load(io.open(LESSONS / date / 'understanding.json', encoding='utf-8'))
    src = u.get('chat_sources') or {}
    return f"{date}: typed lines meet {src.get('meet', 0)} + whatsapp {src.get('whatsapp', 0)}; events touched {sum(1 for e in u['events'] if e.get('typed'))}; flag changes {len(u.get('chat_diff') or [])}"


if __name__ == '__main__':
    for d in sys.argv[1:]:
        print(report(d))
