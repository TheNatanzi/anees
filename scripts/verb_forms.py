"""Verb conjugation engine for the Word Bank (Present, Past, Command).

Pure functions, no I/O. Input is whatever Amal documented for one verb; output
fills every other person with a best guess tagged provenance='inferred'.
A documented form is never replaced. Arabizi and Arabic are built side by side;
Arabic is only built when Amal gave Arabic for that verb.

Forms are bare (no pronoun): {'Past': {'I': ('3refet', 'عرفت'), ...}, ...}.
The present "I" form ('ba3raf', 'بعرف') is the anchor for cross-tense guesses.
"""
import re

TENSES = ['Present', 'Past', 'Command']
PERSONS = ['I', 'You (m)', 'You (f)', 'You (pl)', 'He', 'She', 'We', 'They']
COMMAND_PERSONS = ['You (m)', 'You (f)', 'You (pl)']
PERSONS_BY_TENSE = {'Present': PERSONS, 'Past': PERSONS, 'Command': COMMAND_PERSONS}
PRONOUN = {'I': 'Ana', 'You (m)': 'inta', 'You (f)': 'inti', 'You (pl)': 'intu',
           'He': 'huwwe', 'She': 'heyye', 'We': 'i7na', 'They': 'humme'}
AR_PRONOUN = {'I': 'أنا', 'You (m)': 'إنت', 'You (f)': 'إنتي', 'You (pl)': 'إنتو',
              'He': 'هو', 'She': 'هي', 'We': 'إحنا', 'They': 'هم'}
VOWELS = 'aeiou'
GUTTURAL = set('72358h')          # 7 ح, 2 ء/ق, 3 ع, 5 خ, 8 غ, h ه
DIGRAPHS = ('sh', 'kh', 'gh', 'th', 'dh')
AR_PRONOUN_RE = re.compile(r'^(?:أنا|انا|إنتي|انتي|أنتي|إنتو|انتو|أنتو|إنتوا|انتوا|إنت|انت|أنت|انو|هو|هي|إحنا|احنا|هم)\s+')
HAMZA_STEMS = {'kul', '5ud', 'khud', 'jee'}
AR_DIACRITICS = re.compile('[ً-ْٰ]')


def units(s):
    """Split Arabizi into ('C'|'V', text) units; digraphs are one consonant."""
    out, i = [], 0
    while i < len(s):
        if s[i] in VOWELS:
            j = i
            while j < len(s) and s[j] in VOWELS:
                j += 1
            out.append(('V', s[i:j])); i = j
        elif s[i:i + 2] in DIGRAPHS:
            out.append(('C', s[i:i + 2])); i += 2
        else:
            out.append(('C', s[i])); i += 1
    return out


def shape(s):
    return ''.join(k for k, _ in units(s))


def consonants(s):
    return [t for k, t in units(s) if k == 'C']


def vowels(s):
    return [t for k, t in units(s) if k == 'V']


def strip_pronoun(word):
    bits = word.strip().split(' ', 1)
    return bits[1] if len(bits) == 2 and bits[0].lower() in {p.lower() for p in PRONOUN.values()} | {'huwe', 'heiye', 'hume', 'hiyye', 'huwwa', 'e7na', 'enta', 'enti', 'entu'} else word.strip()


def strip_ar_pronoun(ar):
    return AR_PRONOUN_RE.sub('', AR_DIACRITICS.sub('', (ar or '').strip()))


def drop_last_short_vowel(s):
    """fakker -> fakkr, shte8el -> shte8l, akul -> akl: the unstressed last
    short vowel falls before a vowel ending, only when the stem has two vowels."""
    u = units(s)
    if len(u) < 3 or u[-1][0] != 'C' or u[-2][0] != 'V' or u[-2][1] not in ('e', 'i', 'u'):
        return s
    if sum(k == 'V' for k, _ in u) < 2:
        return s
    return ''.join(t for _, t in u[:-2]) + u[-1][1]


def clean_variant(word):
    """'Ana bassoq / basoo2' -> 'basoo2'; 'ba2/qul' -> 'ba2ul'. Prefer the 2 spelling over q."""
    w = strip_pronoun(word).lower()
    w = re.sub(r'([a-z0-9])/([a-z0-9])', r'', w.replace('q/2', 'q').replace('2/q', '2'))
    options = [x.strip() for x in w.split('/') if x.strip()]
    if not options:
        return ''
    return next((x for x in options if 'q' not in x), options[0])


def double_final(s):
    return s if len(s) > 1 and s[-1] == s[-2] else s + s[-1]


def ends_vowel(s):
    return bool(s) and s[-1] in VOWELS


def replace_final_vowel(s, v):
    return re.sub('[aeiou]+$', '', s) + v


class Verb:
    """Classifies one verb from everything documented about it."""

    def __init__(self, forms):
        self.forms = forms
        present_i = forms.get('Present', {}).get('I', ('', ''))
        self.present_i = clean_variant(present_i[0])
        self.present_i_ar = strip_ar_pronoun(present_i[1]).split('/')[0].strip()
        self.stem = self.present_i[2:] if self.present_i.startswith('ba') else self.present_i[1:]
        self.stem = re.sub('hh$', 'h', self.stem)
        past = {p: f[0].lower() for p, f in forms.get('Past', {}).items() if f[0]}
        command = {p: f[0].lower() for p, f in forms.get('Command', {}).items() if f[0]}
        firsts = [past[p] for p in ('I', 'You (m)', 'We', 'You (f)', 'You (pl)') if p in past]
        self.hamza = self.stem in HAMZA_STEMS or bool(firsts and re.match('^a[^aeiou]', firsts[0])) and shape(self.stem) == 'CVC'
        s = self.stem
        # A geminate verb shows a doubled consonant before -ait in the past, or a
        # doubled final in the present/command (7abbait, bashemm, 7ebb).
        gem_past = any(re.search(r'([^aeiou])\1ai', f) for f in firsts) and not ends_vowel(s)
        gem_written = len(s) > 2 and s[-1] == s[-2] and s[-1] not in VOWELS + 'h'
        gem_command = any(len(c) > 2 and c[-1] == c[-2] for c in command.values()) and shape(s) == 'CVC'
        ar_stem = AR_DIACRITICS.sub('', self.present_i_ar)[1:] if self.present_i_ar.startswith('ب') else ''
        # بحب / بحط: a two-letter present stem is a doubled root (7abb, 7att).
        gem_arabic = len(ar_stem) == 2 and shape(s) == 'CVC' and not ends_vowel(s) and s not in HAMZA_STEMS
        self.geminate = gem_past or gem_written or gem_command or gem_arabic
        self.defective = ends_vowel(s)
        self.hollow = (not self.geminate and not self.hamza and not self.defective and
                       re.fullmatch(r'[^aeiou]{1,2}(?:u|o|oo|ee|aa|e)[^aeiou]{1,2}', s) is not None and
                       shape(s) in ('CVC',) and (re.search('(oo|ee|aa|u|o)', s) is not None) and not self._sound_one_vowel_e())
        self.form2 = re.fullmatch(r'[^aeiou]{1,2}a([^aeiou])\1(?:e|i)[^aeiou]{1,2}', s) is not None or \
            re.fullmatch(r'[^aeiou]{1,2}a([^aeiou]{1,2})\1?e[^aeiou]{1,2}', s) is not None and len(consonants(s)) == 4
        self.form2_def = re.fullmatch(r'[^aeiou]{1,2}a([^aeiou])\1i', s) is not None
        self.form3 = re.fullmatch(r'[^aeiou]{1,2}aa[^aeiou]{1,2}e[^aeiou]{1,2}', s) is not None
        self.form5 = s.startswith('t') and shape(s).startswith('CCV') and re.fullmatch(r't[^aeiou]{1,2}a[^aeiou]{2,4}a[^aeiou]{1,2}|t[^aeiou]{1,2}aa[^aeiou]{1,2}a[^aeiou]{1,2}', s) is not None
        self.form10 = s.startswith('st')
        self.form8 = not self.form10 and re.fullmatch(r'[^aeiou]{1,2}t(?:e|a|aa)[^aeiou]{1,2}(?:e[^aeiou]{1,2})?', s) is not None and len(consonants(s)) >= 3 and s[1:3] != 'ta' or s.startswith(('shte', 'shta'))
        self.form7 = s.startswith('n') and shape(s).startswith('CCV') and not self.form8

    def _sound_one_vowel_e(self):
        # ba7mel, bamsek: CCeC is a sound Form I verb, not hollow.
        return shape(self.stem) == 'CCVC' or bool(re.fullmatch(r'[^aeiou]{2}e[^aeiou]', self.stem))


# ---------------------------------------------------------------- present

PRESENT_PREFIX = {'You (m)': 't', 'You (f)': 't', 'You (pl)': 't', 'She': 't', 'He': 'y', 'They': 'y', 'We': 'n'}


def present_forms(v):
    s = v.stem
    if not s or ' ' in v.present_i:
        return {}
    out = {'I': v.present_i}
    if v.hamza:
        full = 'a' + s
        joiner = ''
    elif shape(s).startswith('CC'):
        full, joiner = s, 'e'
    else:
        full, joiner = s, 'e'
    for p, c in PRESENT_PREFIX.items():
        pre = 'b' + c if v.hamza else ('b' + c + joiner if shape(s).startswith('CC') else 'be' + c)
        if p in ('You (f)', 'You (pl)', 'They'):
            vowel = 'i' if p == 'You (f)' else 'u'
            if v.defective:
                body = replace_final_vowel(full, vowel)
            elif v.geminate:
                body = double_final(full) + vowel
            else:
                body = drop_last_short_vowel(full) + vowel
        else:
            body = full
        out[p] = pre + body
    return out


def present_arabic(v):
    a = AR_DIACRITICS.sub('', v.present_i_ar)
    if not a.startswith('ب') or ' ' in a:
        return {}
    stem = a[1:]
    out = {'I': a}
    for p, c in PRESENT_PREFIX.items():
        pre = 'ب' + {'t': 'ت', 'y': 'ي', 'n': 'ن'}[c]
        body = stem
        if p == 'You (f)':
            body = stem if stem.endswith('ي') else stem + 'ي'
        elif p in ('You (pl)', 'They'):
            body = (stem[:-1] if stem.endswith(('ي', 'ى')) else stem) + 'وا'
        out[p] = pre + body
    return out


# ---------------------------------------------------------------- past

def past_suffix_stem(word):
    """3refet -> 3ref, 7akait -> 7akai, 3refti -> 3ref, 3refna -> 3ref."""
    for suf in ('et', 'it', 'ti', 'tu', 'na', 't'):
        if word.endswith(suf) and len(word) > len(suf) + 1:
            base = word[:-len(suf)]
            if suf in ('ti', 'tu') and base.endswith('t') and not base.endswith('tt'):
                pass
            return base
    return word


def past_from_present(v):
    """(suffix stem A, 3rd-person base H) guessed from the present I form."""
    s = v.stem
    m = re.fullmatch(r'([^aeiou]{1,2}t)aa([^aeiou]{1,2})', s)
    if m:                                   # 7taaj -> 7tajet / 7taaj, rtaa7
        return m[1] + 'a' + m[2], m[1] + 'aa' + m[2]
    m = re.fullmatch(r'([^aeiou]{1,2}t)e([^aeiou]{1,2})i', s)
    if m:                                   # lte2i -> lta2ait / lta2a
        return m[1] + 'a' + m[2] + 'ai', m[1] + 'a' + m[2] + 'a'
    if v.hamza:
        c = consonants(s)
        return 'a' + c[0] + 'a' + c[-1], 'a' + c[0] + 'a' + c[-1]
    if v.form2_def:
        return s[:-1] + 'ai', s[:-1] + 'a'
    if v.defective:
        c = consonants(s)
        if s.startswith(('st', 'sht')) or v.form8:
            body = re.sub('[aeiou]+$', '', s)
            body = re.sub(r'te', 'ta', body, count=1)
            return body + 'ai', body + 'a'
        if len(c) == 2 and s.endswith('i'):
            return c[0] + 'a' + c[1] + 'ai', c[0] + 'a' + c[1] + 'a'
        if len(c) == 2 and s.endswith('a'):
            return c[0] + c[1] + 'ee', c[0] + 'i' + c[1] + 'i'
        body = re.sub('[aeiou]+$', '', s)
        return body + 'ai', body + 'a'
    if v.geminate:
        c = consonants(s)
        return c[0] + 'a' + c[1] + c[1] + 'ai', c[0] + 'a' + c[1] + c[1]
    if v.form10:
        c = consonants(s[2:])
        a = 'sta' + ''.join(c[:-1]) + 'a' + c[-1] if len(c) >= 3 else s
        a = 'sta' + c[0] + c[1] + 'a' + c[-1] if len(c) >= 3 else a
        return a, a
    if v.form5:
        return s, s
    if v.form2 or v.form3:
        a = re.sub(r'(e|i)([^aeiou]{1,2})$', r'a\2', s)
        return a, a
    if s.startswith(('shte', 'shta')) or v.form8:
        a = re.sub(r'^([^aeiou]{1,2}t)(?:e|a)([^aeiou]{1,2})e([^aeiou]{1,2})$', r'\1a\2a\3', s)
        m = re.fullmatch(r'([^aeiou]{1,2}t)aa([^aeiou]{1,2})', s)
        if m:
            return m[1] + 'a' + m[2], m[1] + 'aa' + m[2]
        return a, a
    if v.form7:
        c = consonants(s)
        return c[0] + c[1] + 'a' + c[2] + 'a' + c[-1], c[0] + c[1] + 'a' + c[2] + 'a' + c[-1]
    if v.hollow:
        c = consonants(s)
        mid = 'u' if re.search('(u|o)', s) else 'e'
        return c[0] + mid + c[-1], c[0] + 'aa' + c[-1]
    c = consonants(s)
    if len(c) == 3:
        vw = (vowels(s) or ['a'])[-1]
        if vw in ('u', 'o', 'e') or c[2] in ('7', '2') or c[1] == '2':
            a = c[0] + 'a' + c[1] + 'a' + c[2]
            return a, a
        return c[0] + c[1] + 'e' + c[2], c[0] + 'e' + c[1] + 'e' + c[2]
    return s, s


def _suffix_stem_of(p, w):
    if p in ('I', 'You (m)'):
        return w[:-1] if re.search('(ai|ee|ay)t$', w) else (w[:-2] if w.endswith(('et', 'it')) else None)
    suf = {'You (f)': 'ti', 'You (pl)': 'tu', 'We': 'na'}[p]
    if not w.endswith(suf):
        return None
    base = w[:-len(suf)]
    return base[:-1] if p == 'We' and w.endswith('nna') and not base.endswith('nn') and False else base


def past_forms(v, known):
    """known: {person: arabizi} documented past forms."""
    # The suffix stem is voted by every documented 1st/2nd person form, so one
    # typo (da77aket6) cannot win.
    votes = [a for a in (_suffix_stem_of(p, known[p]) for p in ('I', 'You (m)', 'You (f)', 'You (pl)', 'We') if p in known) if a]
    A = max(votes, key=votes.count) if votes else None
    H = known.get('He')
    cold_A, cold_H = past_from_present(v) if v.stem else (None, None)
    if A is None:
        A = _suffix_stem_from_he(H, v) if H else cold_A
    if H is None:
        H = _he_from_suffix_stem(A, v) if A else cold_H
    if A is None:
        return {}
    first = A + ('t' if re.search('(ai|ee|ay)$', A) else 'et')
    return {'I': first, 'You (m)': first, 'You (f)': A + 'ti', 'You (pl)': A + 'tu', 'We': A + 'na',
            'He': H, 'She': _she(H, v), 'They': _they(H, v)}


def _deletable(H):
    """katab / 3iref / shta8al: a single consonant between two short vowels at the end."""
    u = units(H)
    return (len(u) >= 4 and u[-1][0] == 'C' and u[-2][0] == 'V' and u[-2][1] in ('a', 'e', 'i')
            and u[-3][0] == 'C' and u[-4][0] == 'V' and len(u[-4][1]) == 1)


def _he_from_suffix_stem(A, v):
    if re.search('(ai|ay)$', A):
        base = A[:-2] if not A.endswith('ay') else A[:-2]
        if v.geminate:
            return base
        if shape(base).startswith('CC') and len(consonants(base)) == 2:
            c = consonants(base)
            return c[0] + 'a' + ''.join(c[1:]) + 'a'
        return base + 'a'
    if A.endswith('ee'):
        c = consonants(A)
        return c[0] + 'i' + ''.join(c[1:]) + 'i'
    if v.hollow:
        c = consonants(A)
        return c[0] + ('aa' if len(c) == 2 else '') + c[-1] if len(c) == 2 else re.sub(r'a([^aeiou]+)$', r'aa\1', A)
    if re.fullmatch(r'[^aeiou]{1,2}t?a[^aeiou]', A) and (v.form8 or re.search('taa', v.stem)):
        return re.sub(r'a([^aeiou]+)$', r'aa\1', A)
    if v.form2 and re.search(r'e[^aeiou]{1,2}$', A):
        return re.sub(r'e([^aeiou]{1,2})$', r'a', A)
    u = units(A)
    if shape(A) == 'CCVC' and not A.startswith(('st', 'sht')) and not v.form8 and not v.form5:
        return u[0][1] + 'e' + u[1][1] + 'e' + u[3][1]
    return A


def _suffix_stem_from_he(H, v):
    if v.geminate:
        return H + 'ai'
    if re.search('[aeiou]$', H):
        if H.endswith('i'):
            c = consonants(H)
            return ''.join(c) + 'ee'
        return H[:-1] + 'ai'
    if re.search('aa', H):
        c = consonants(H)
        return c[0] + ('u' if re.search('(u|o)', v.stem) else 'e') + c[-1] if len(c) == 2 else H.replace('aa', 'a')
    m = re.fullmatch(r'([^aeiou]{1,2})[ei]([^aeiou]{1,2})e([^aeiou]{1,2})', H)
    if m:
        return m[1] + m[2] + 'e' + m[3]
    return H


def _she(H, v):
    if H.endswith('i'):
        return H[:-1] + 'et'
    if ends_vowel(H):
        return re.sub('[aeiou]+$', '', H) + 'at'
    if _deletable(H) and not (v.form2 or v.form3 or v.form5):
        u = units(H)
        return ''.join(t for _, t in u[:-2]) + u[-1][1] + 'at'
    return H + 'at'


def _they(H, v):
    if ends_vowel(H):
        return re.sub('[aeiou]+$', '', H) + 'u'
    u = units(H)
    # katab -> katabu keeps its a; 3iref -> 3irfu drops its e.
    if _deletable(H) and u[-2][1] in ('e', 'i') and not (v.form2 or v.form3 or v.form5):
        return ''.join(t for _, t in u[:-2]) + u[-1][1] + 'u'
    return H + 'u'


def past_arabic(v, known_ar, arabizi):
    """Arabic past from Amal's past Arabic; falls back to her present Arabic."""
    A = H = None
    for p in ('I', 'You (m)'):
        if p in known_ar and known_ar[p].endswith('ت'):
            A = known_ar[p][:-1]; break
    if A is None:
        for p, suf in (('You (f)', 'تي'), ('You (pl)', 'تو'), ('We', 'نا')):
            if p in known_ar and known_ar[p].endswith(suf):
                A = known_ar[p][:-len(suf)]; break
    if 'He' in known_ar:
        H = known_ar['He']
    pres = AR_DIACRITICS.sub('', v.present_i_ar)
    pres_stem = pres[1:] if pres.startswith('ب') and ' ' not in pres else ''
    if H is None and pres_stem:
        H = _ar_he_from_present(pres_stem, v, arabizi)
    if A is None and H:
        A = _ar_suffix_stem_from_he(H, v)
    if A is None or H is None:
        return {}
    he = arabizi.get('He', '')
    if he and shape(he).startswith('CC') and len(consonants(he)) >= 3 and not v.form5:
        if not H.startswith(('ا', 'إ', 'أ')):
            H = 'ا' + H
        if 'I' not in known_ar and 'You (m)' not in known_ar and not A.startswith(('ا', 'إ', 'أ')):
            A = 'ا' + A
    first = arabizi.get('I', '')
    if he and 'aa' in he and 'aa' not in first and 'I' not in known_ar and 'You (m)' not in known_ar and 'ا' in A[1:]:
        i = A.rindex('ا')
        A = A[:i] + A[i + 1:]           # راح -> رحت, احتاج -> احتجت
    if he.endswith('i') and H.endswith('ى'):
        H = H[:-1] + 'ي'                # نسي, صحي keep their ي
    out = {'I': A + 'ت', 'You (m)': A + 'ت', 'You (f)': A + 'تي', 'You (pl)': A + 'تو',
           'We': A + ('ا' if A.endswith('ن') else 'نا'), 'He': H}
    she_known = known_ar.get('She')
    base3 = H[:-1] if H.endswith(('ى', 'ا')) and len(H) > 2 else H
    if he.endswith('i'):
        base3 = H
    out['She'] = she_known or base3 + 'ت'
    out['They'] = known_ar.get('They') or base3 + 'وا'
    return out


def _ar_he_from_present(stem, v, arabizi):
    if v.hamza:
        return 'أ' + stem[1:] if stem.startswith('ا') else stem
    if v.defective:
        return stem[:-1] + 'ى' if stem.endswith('ي') else stem
    if v.hollow:
        return stem[0] + 'ا' + stem[2:] if len(stem) == 3 and stem[1] in 'وي' else stem
    if v.form10 or v.form8 or v.form7:
        return 'ا' + stem if not stem.startswith('ا') else stem
    if v.form3:
        return stem
    return stem


def _ar_suffix_stem_from_he(H, v):
    if v.geminate:
        return H + 'ي'
    if H.endswith('ى'):
        return H[:-1] + 'ي'
    if v.hollow and len(H) == 3 and H[1] == 'ا':
        return H[0] + H[2]
    return H


# ---------------------------------------------------------------- command

def command_forms(v, known):
    m = known.get('You (m)')
    if m and ' / ' in m:
        m = None
    if m is None:
        m = _command_m_from_sibling(v, known) or _command_m_from_present(v)
    if not m:
        return {}
    out = {'You (m)': m}
    if v.defective:
        out['You (f)'] = replace_final_vowel(m, 'i')
        out['You (pl)'] = replace_final_vowel(m, 'u')
    elif v.geminate:
        out['You (f)'] = double_final(m) + 'i'
        out['You (pl)'] = double_final(m) + 'u'
    else:
        body = drop_last_short_vowel(m) if not (v.form5 or re.match('^(e|i)', m) and len(vowels(m)) == 2 and not v.form8) else m
        out['You (f)'] = body + 'i'
        out['You (pl)'] = body + 'u'
    for p in ('You (f)', 'You (pl)'):
        if p in known:
            out[p] = known[p]
    # A known f or pl form reveals the body for the other one.
    if 'You (f)' in known and 'You (pl)' not in known and known['You (f)'].endswith('i') and not v.defective:
        out['You (pl)'] = known['You (f)'][:-1] + 'u'
    if 'You (pl)' in known and 'You (f)' not in known and known['You (pl)'].endswith('u') and not v.defective:
        out['You (f)'] = known['You (pl)'][:-1] + 'i'
    return out


def _command_m_from_sibling(v, known):
    """e3refi -> e3ref, e8sli -> e8sel, 7ebbi -> 7ebb, es7i -> es7a."""
    for p, end in (('You (f)', 'i'), ('You (pl)', 'u')):
        w = known.get(p)
        if not w or not w.endswith(end):
            continue
        body = w[:-1]
        if v.defective:
            return body + (v.stem[-1] if v.stem else 'i')
        u = units(body)
        if len(u) >= 3 and u[-1][0] == 'C' and u[-2][0] == 'C' and u[-1][1] != u[-2][1] and len(vowels(body)) >= 1                 and not (len(u) == 3 and u[0][0] == 'V'):
            return ''.join(t for _, t in u[:-1]) + 'e' + u[-1][1]
        return body
    return ''


def _command_m_from_present(v):
    s = v.stem
    if not s or ' ' in v.present_i:
        return ''
    if v.hamza:
        return s
    if v.form5:
        return 'e' + s
    if v.form2 or v.form3 or v.form2_def:
        return s
    if v.geminate:
        return s if s[-1] == s[-2] else s + s[-1]
    if v.hollow:
        c = consonants(s)
        if re.search('(u|o)', s):
            return c[0] + 'oo' + c[-1]
        if 'aa' in s:
            return s
        return c[0] + 'ee' + c[-1]
    if shape(s).startswith('CC'):
        return 'e' + s
    return s


def command_arabic(v, known_ar):
    m = known_ar.get('You (m)')
    if m and '/' in m:
        m = m.split('/')[0]
    if not m:
        pres = AR_DIACRITICS.sub('', v.present_i_ar)
        if not pres.startswith('ب') or ' ' in pres:
            return {}
        stem = pres[1:]
        m = stem
        if not v.hamza and (shape(v.stem).startswith('CC') and not v.form5) and not stem.startswith('ا'):
            m = 'ا' + stem
        if v.hamza:
            m = stem[1:] if stem.startswith('ا') else stem
    body = m[:-1] if m.endswith(('ي', 'ى')) and v.defective else m
    return {'You (m)': m, 'You (f)': (body + 'ي'), 'You (pl)': body + 'وا'}


# ---------------------------------------------------------------- public

def conjugate(forms):
    """forms: {tense: {person: (arabizi, arabic)}} bare, documented only.
    Returns {tense: {person: {'word','arabic','provenance'}}} for every person;
    documented entries are returned unchanged."""
    v = Verb(forms)
    out = {}
    for tense in TENSES:
        known = {p: f[0].lower() for p, f in forms.get(tense, {}).items() if f[0]}
        known_ar = {p: AR_DIACRITICS.sub('', strip_ar_pronoun(f[1])) for p, f in forms.get(tense, {}).items() if f[1]}
        if tense == 'Present':
            guess, guess_ar = present_forms(v), present_arabic(v)
        elif tense == 'Past':
            guess = past_forms(v, known)
            guess_ar = past_arabic(v, known_ar, guess)
        else:
            guess, guess_ar = command_forms(v, known), command_arabic(v, known_ar)
        has_arabic = bool(known_ar) or bool(v.present_i_ar)
        rows = {}
        for p in PERSONS_BY_TENSE[tense]:
            if p in forms.get(tense, {}) and forms[tense][p][0]:
                w, a = forms[tense][p]
                rows[p] = {'word': w, 'arabic': a, 'provenance': 'document'}
            elif p in guess:
                rows[p] = {'word': guess[p], 'arabic': guess_ar.get(p, '') if has_arabic else '', 'provenance': 'inferred'}
        out[tense] = rows
    return out


def with_pronoun(person, word, arabic):
    return (PRONOUN[person] + ' ' + word if person in PRONOUN and not word.lower().startswith(PRONOUN[person].lower() + ' ') else word,
            (AR_PRONOUN[person] + ' ' + arabic) if arabic and person in AR_PRONOUN else arabic)
