"""Conservative presentation overlays. Never rewrite source words or infer Arabic.

Use annotate_runs only when rendering; never feed its grouped display items back
into lesson metrics, corrections, exports, or speech processing. Append returned
details_html after the existing paragraph; inline_html is safe inside that row.
"""
from __future__ import annotations

import copy
import html
import re
import unicodedata

PLACEHOLDER = 'Unclear — needs audio review'
# Medi approved this as a spelling alias on 2026-09-08, not an audio judgment.
# Matches are whole words only: never infer other aliases or repair false starts.
APPROVED_SPELLINGS = {'aganee': {'arabic': 'أغاني', 'arabizi': 'a8aani'}}
_SPELLING_TOKEN = re.compile(r'''(["'“”‘’(\[«]*)([A-Za-z]+)([.,!?;:،؛؟…"'“”‘’)\]»]*)''', re.ASCII)


def render_spelling_word(text):
    """Apply only an approved writing alias, preserving source text in markup.

    None means no rule matched. This is display-only and not evidence that the
    speaker pronounced the target correctly. Hyphenated attempts do not match.
    """
    match = _SPELLING_TOKEN.fullmatch(text)
    if not match:
        return None
    rule = APPROVED_SPELLINGS.get(match[2].lower())
    if not rule:
        return None
    title = f"Spelling only; pronunciation not assessed. Original: {text} | Arabizi: {rule['arabizi']}"
    word = '<bdi lang="ar" dir="rtl">' + html.escape(rule['arabic']) + '</bdi>'
    return ('<span class="transcript-spelling" data-source="' + html.escape(text, quote=True)
            + '" title="' + html.escape(title, quote=True) + '">'
            + html.escape(match[1]) + word + html.escape(match[3]) + '</span>')


DEFAULT_RULES = {
    '2026-09-05': (
        {'id': 'sep05-opening-unclear', 'source_text': 'Ɣama, ōinti.', 'expected_occurrences': 1},
        {'id': 'sep05-second-unclear', 'source_text': 'Ɣama yebkedu.', 'expected_occurrences': 1},
    ),
}


class StaleDisplayRule(ValueError):
    """An exact display rule no longer matches its expected immutable source."""


def annotate_runs(runs, lesson, *, rules=None):
    """Return deep-copied runs with exact, nonoverlapping phrases grouped for UI.

    Rules are local to the requested lesson; each matches consecutive word items
    within one speaker run. Pauses, existing displays and run boundaries prevent
    a match. Validate every occurrence count before modifying the returned copy.
    """
    if not isinstance(runs, list) or any(not isinstance(r, dict) or not isinstance(r.get('items'), list) for r in runs):
        raise ValueError('Expected a list of runs with item lists')
    selected = DEFAULT_RULES.get(lesson, ()) if rules is None else rules
    if not isinstance(selected, (list, tuple)):
        raise ValueError('Expected a list of display rules')
    patches, occupied, rule_ids = [], set(), set()
    for rule in selected:
        if not isinstance(rule, dict) or not isinstance(rule.get('id'), str) or not rule['id'] or rule['id'] in rule_ids:
            raise ValueError('Display rules need unique nonempty IDs')
        rule_ids.add(rule['id'])
        text, count = rule.get('source_text'), rule.get('expected_occurrences')
        if not isinstance(text, str) or not text or any(not token for token in text.split(' ')):
            raise ValueError('Rule source_text must contain exact space-separated words')
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError('Rule expected_occurrences must be a positive integer')
        tokens = text.split(' ')
        matches = []
        for run_index, run in enumerate(runs):
            items = run['items']
            for start in range(len(items) - len(tokens) + 1):
                group = items[start:start + len(tokens)]
                if all(isinstance(item, dict) and 'display' not in item and 'pause' not in item
                       and item.get('w') == token for item, token in zip(group, tokens)):
                    matches.append((run_index, start, start + len(tokens)))
        if len(matches) != count:
            raise StaleDisplayRule(f'{rule["id"]}: expected {count} exact occurrence(s), found {len(matches)}; source is missing, changed or ambiguous')
        for run_index, start, end in matches:
            cells = {(run_index, index) for index in range(start, end)}
            if occupied.intersection(cells):
                raise StaleDisplayRule('Display rules overlap; refusing to hide or duplicate source words')
            occupied.update(cells)
            patches.append((run_index, start, end, rule['id'], text))
    result = copy.deepcopy(runs)
    for run_index, start, end, rule_id, text in sorted(patches, reverse=True):
        source_items = copy.deepcopy(runs[run_index]['items'][start:end])
        display = {'kind': 'unclear', 'text': PLACEHOLDER, 'source_text': text,
                   'source_items': source_items, 'rule_id': rule_id,
                   'source_span': {'run_index': run_index, 'start_item': start, 'end_item_exclusive': end}}
        result[run_index]['items'][start:end] = [{'display': display}]
    return result


def render_display_item(item):
    """Return {'inline_html', 'details_html'}, or None for an ordinary item."""
    if not isinstance(item, dict) or 'display' not in item:
        return None
    display = item['display']
    if not isinstance(display, dict) or display.get('kind') != 'unclear':
        raise ValueError('Unknown display overlay')
    raw = display.get('source_text')
    source_items = display.get('source_items')
    if not isinstance(raw, str) or not isinstance(source_items, list) or not source_items:
        raise ValueError('Missing preserved source evidence')
    if not all(isinstance(value, dict) and isinstance(value.get('w'), str) for value in source_items):
        raise ValueError('Invalid source word evidence')
    if raw != ' '.join(value['w'] for value in source_items):
        raise StaleDisplayRule('Display source text differs from preserved source items')
    # Do not inherit source ok/confirmation styling: this is explicitly unclear.
    return {'inline_html': '<span class="transcript-unclear" dir="auto">' + html.escape(PLACEHOLDER) + '</span>',
            'details_html': '<details class="transcript-source"><summary>Raw source output</summary>'
                            + '<span dir="auto">' + html.escape(raw, quote=True) + '</span></details>'}


def nonstandard_latin_warning(text):
    """Advisory only: extended Latin/phonetic characters are not proof of Arabic.

    ASCII English (including I/i), Arabic, Farsi, digits and normal punctuation
    pass unchanged. Accented names/English can also trigger this warning; callers
    must not automatically transliterate, hide or replace such text.
    """
    if not isinstance(text, str):
        raise TypeError('Expected text')
    for char in text:
        code = ord(char)
        if code < 128 or not unicodedata.category(char).startswith('L'):
            continue
        if 'LATIN' in unicodedata.name(char, '') or 0x0250 <= code <= 0x02FF or 0x1D00 <= code <= 0x1DBF:
            return 'Nonstandard Latin or phonetic characters in source — needs review; language and wording are not confirmed.'
    return None
