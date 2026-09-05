"""Arabizi + Arabic-script normalisation and the loose matcher.

Amal's spelling is the KEY; Medi's spelling is matched loosely (plan section 0): 6<->t/ط, 7<->h/ح, 3<->a/ع, 2<->'/ء/ق,
5<->kh/خ, 9<->s/ص, 8<->gh/غ, vowels ignored, doubled letters collapsed.

Forms of a spelling:
  loose(s)     Amal-precision key: digits kept (they are phonemes), kh->5, gh->8, q/'->2, article attached (el jaw -> aljaw),
               long vowels marked A/I/U, doubled consonants collapsed
  fold(s)      Medi-level: 6->t 7->h 9->s 8->g 5->x z->s, 2 and 3 dropped, e->i o->u, final -eh/-ah dropped, vowels kept
  short(s)     fold with long vowels shortened
  skeleton(s)  fold without vowels (leading vowel kept as 'v' so 'ana' != 'n')
Match tiers, strictest first; ambiguity at any tier -> None (never guess), except when every candidate is the same Arabic
word (a row and its pronoun-less twin): then the base row wins.
  exact loose -> exact fold -> exact short -> unique skeleton with short-ratio > 0.8 -> fuzzy (same skeleton, ratio >= 0.86, clear margin)
Arabic script: diacritics stripped, hamza forms unified, taa marbuta -> haa, alef maqsura -> yaa, optional leading al-."""
import re, unicodedata, difflib

ARABIC = re.compile(r'[؀-ۿ]')
_DIAC = re.compile(r'[ً-ْٰـٓ-ٟ]')
_ACCENT = {'â': 'a', 'á': 'a', 'à': 'a', 'ä': 'a', 'ê': 'e', 'é': 'e', 'è': 'e', 'î': 'i', 'í': 'i', 'ô': 'o', 'ó': 'o', 'û': 'u', 'ú': 'u', 'ü': 'u'}
_VOW = re.compile(r'[aeiouAIU]')
PRONOUNS = ('ana', 'inta', 'inti', 'intu', 'i7na', 'e7na', 'huwwe', 'heyye', 'humme', 'hiyye', 'huwe', 'hiye')
AR_PRONOUNS = ('انا', 'انت', 'انتي', 'انتو', 'احنا', 'هو', 'هي', 'هم', 'همه')


def _ascii(s):
    s = (s or '').lower().strip()
    s = ''.join(_ACCENT.get(c, c) for c in s)
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def loose(s):
    """Amal-precision canonical spelling (the words.key)."""
    s = _ascii(s)
    s = re.sub(r"[’'`ʼ]", '2', s)
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = s.replace('kh', '5').replace('gh', '8').replace('th', 's').replace('dh', 'd').replace('sh', 'S').replace('ch', 'S')
    s = s.replace('q', '2').replace('x', '5').replace('c', 'k').replace('v', 'f').replace('p', 'b')
    s = re.sub(r'\b(el|il|al)[ -]+(?=[a-z0-9])', 'al', s)   # the article el-/il-/al- is written attached: "el jaw" -> "aljaw"
    s = re.sub(r'\b(el|il)(?=[a-z]{3})', 'al', s)
    s = re.sub(r'y(?![aeiou])', 'i', s)                # y as a vowel (ghayr -> gair); y before a vowel stays a consonant
    s = re.sub(r'ee+', 'I', s); s = re.sub(r'oo+', 'U', s); s = re.sub(r'aa+', 'A', s); s = re.sub(r'ii+', 'I', s); s = re.sub(r'uu+', 'U', s)
    s = re.sub(r'(.)\1+', r'\1', s)                    # doubled consonants collapse; long vowels stay marked A/I/U
    s = s.replace('S', 'sh')
    return re.sub(r'\s+', ' ', s).strip()


def fold(s):
    """Medi-level form: emphatic/pharyngeal letters folded to their plain neighbours, vowels kept."""
    l = loose(s)
    l = l.replace('6', 't').replace('7', 'h').replace('9', 's').replace('8', 'g').replace('5', 'x').replace('z', 's')
    l = l.replace('2', '').replace('3', '')
    l = l.replace('e', 'i').replace('o', 'u')            # short-vowel spelling pairs (kesra e/i, damma o/u)
    l = re.sub(r'([aiuAIU])h\b', r'\1', l)             # taa marbuta written -eh/-ah drops
    l = re.sub(r'(.)\1+', r'\1', l)
    return re.sub(r'\s+', ' ', l).strip()


def short(s):
    """fold() with long vowels shortened (a Medi "matar" may be Amal's "Ma6aar")."""
    return re.sub(r'(.)\1+', r'\1', fold(s).replace('A', 'a').replace('I', 'i').replace('U', 'u'))


def skeleton(s):
    words = []
    for w in fold(s).split(' '):
        if not w:
            continue
        lead = w[0] in 'aeiouAIU'
        core = _VOW.sub('', w)
        words.append(('v' if lead else '') + core if core else w)
    return ' '.join(words)


def arabic_norm(s, strip_al=False):
    s = _DIAC.sub('', (s or '').strip())
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ٱ', 'ا')
    s = s.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي').replace('ء', '')
    s = re.sub(r'[^؀-ۿ ]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if strip_al and s.startswith('ال') and len(s) > 4:
        s = s[2:]
    return s


def arabic_core(s):
    """Arabic word without a leading pronoun: 'أنا بخاف' -> 'بخاف'."""
    toks = [t for t in arabic_norm(s).split() if t]
    while len(toks) > 1 and toks[0] in AR_PRONOUNS:
        toks = toks[1:]
    return toks[0] if toks else ''


def strip_pronoun(s):
    parts = (s or '').split()
    if len(parts) > 1 and parts[0].lower().rstrip('.,') in PRONOUNS:
        return ' '.join(parts[1:])
    return s or ''


def _forms(w):
    forms = [w['arabizi']] + list(w.get('aliases') or [])
    for f in list(forms):
        st = strip_pronoun(f)
        if st != f:
            forms.append(st)                              # pronoun optional in speech
    return forms


class Matcher:
    """Index of Doc words; match(spelling) -> key or None. Never returns a key when two different words tie."""

    def __init__(self, words):
        self.words = {w['key']: w for w in words}
        self.by_loose, self.by_fold, self.by_short, self.by_skel, self.by_ar, self.by_ar_al = {}, {}, {}, {}, {}, {}
        for w in words:
            for f in _forms(w):
                self.by_loose.setdefault(loose(f), set()).add(w['key'])
                self.by_fold.setdefault(fold(f), set()).add(w['key'])
                self.by_short.setdefault(short(f), set()).add(w['key'])
                self.by_skel.setdefault(skeleton(f), set()).add(w['key'])
            for part in re.split(r'\s*/\s*', w.get('arabic') or ''):
                if part.strip():
                    self.by_ar.setdefault(arabic_norm(part), set()).add(w['key'])
                    self.by_ar_al.setdefault(arabic_norm(part, strip_al=True), set()).add(w['key'])
        self._short_keys = list(self.by_short)

    def match(self, s, fuzzy=True):
        return (self.match_tier(s, fuzzy) or (None, None))[0]

    def tier(self, s):
        return (self.match_tier(s) or (None, None))[1]

    def match_tier(self, s, fuzzy=True):
        s = (s or '').strip()
        if not s:
            return None
        if ARABIC.search(s):
            k = self._one(self.by_ar.get(arabic_norm(s))) or self._one(self.by_ar_al.get(arabic_norm(s, strip_al=True)))
            return (k, 'arabic') if k else None
        l = loose(s)
        if not l:
            return None
        k = self._one(self.by_loose.get(l))
        if k:
            return k, 'exact'
        f = fold(s)
        k = self._one(self.by_fold.get(f))
        if k:
            return k, 'fold'
        sh = short(s)
        k = self._one(self.by_short.get(sh))
        if k:
            return k, 'short'
        sk = skeleton(s)
        cands = self.by_skel.get(sk) or set()
        if cands:
            best = sorted(((self._ratio(sh, k), k) for k in cands), reverse=True)
            top = [k for r, k in best if r == best[0][0]]
            k = self._one(set(top))
            if k and best[0][0] > 0.8 and (len(best) == 1 or best[0][0] - best[1][0] >= 0.1 or self._same_word(set(k2 for _, k2 in best[:2]))) \
                    and not self._final_vowel_clash(sh, k):
                return k, 'skeleton'
        if not fuzzy or len(sh) < 4:
            return None
        close = difflib.get_close_matches(sh, self._short_keys, n=5, cutoff=0.86)
        scored = sorted(((difflib.SequenceMatcher(None, sh, c).ratio(), c) for c in close), reverse=True)
        scored = [(r, c) for r, c in scored if skeleton(c) == sk]
        if not scored:
            return None
        if any(self._one(self.by_short[c]) is None for _, c in scored[:2]):
            return None                                   # a near spelling is itself ambiguous: do not guess
        if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.04 and self.by_short[scored[0][1]] != self.by_short[scored[1][1]]:
            return None
        k = self._one(self.by_short[scored[0][1]])
        if self._final_vowel_clash(sh, k):
            return None
        return k, 'fuzzy'

    def _final_vowel_clash(self, sh, key):
        """'tabi' (natural) vs 'tabia' (nature): a different final vowel is a different word, not a misspelling."""
        for x in _forms(self.words[key]):
            t = short(x)
            if t[-1:] == sh[-1:] or (t[-1:] not in 'aiu' and sh[-1:] not in 'aiu'):
                return False
        return True

    def _ratio(self, sh, key):
        return max(difflib.SequenceMatcher(None, sh, short(x)).ratio() for x in _forms(self.words[key]))

    def _same_word(self, keys):
        return len({arabic_core(self.words[k]['arabic']) for k in keys}) == 1

    def _one(self, keys):
        """One key, or None. Several keys that are the same Arabic word (a row and its pronoun-less twin) resolve to the base row."""
        if not keys:
            return None
        if len(keys) == 1:
            return next(iter(keys))
        if self._same_word(keys):
            base = [k for k in keys if strip_pronoun(self.words[k]['arabizi']) == self.words[k]['arabizi']]
            if len(base) == 1:
                return base[0]
            return sorted(keys, key=lambda k: (len(self.words[k]['arabizi']), k))[0]
        return None
