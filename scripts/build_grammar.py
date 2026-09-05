"""Grammar reference for the Grammar tab: prose (non-table) lines from the Doc's grammar tabs, grouped by heading, plus pointers
to the wiki. Output docs/data/grammar.json. The Doc is read from the saved markdown export; nothing is written to the Doc."""
import io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAMMAR_TABS = ('Past Tense', 'Command Tense', 'Tense', 'Grammar Termonology & Causative Verbs', 'Sentence Toolbox')
HEAD_RE = re.compile(r'^\s*(?:\d+\.\s+)?(#{1,3})\s+(.*?)\s*$')


def build():
    snaps = sorted((ROOT / 'data' / 'vocab').glob('doc_markdown_*.md'))
    text = io.open(snaps[-1], encoding='utf-8').read()
    sections, tab, sub, cur = [], '', '', None
    for line in text.split('\n'):
        m = HEAD_RE.match(line)
        if m:
            lvl, title = len(m.group(1)), re.sub(r'\\\*|\*', '', m.group(2)).strip()
            title = title.replace(chr(92), '')
            if lvl == 1:
                tab, sub = title, ''
            else:
                sub = title
            cur = None
            continue
        if not any(tab.strip().startswith(g) for g in GRAMMAR_TABS):
            continue
        s = line.strip()
        if not s or s.startswith('|') or s.startswith('[') or s.startswith('-----'):
            continue
        s = re.sub(r'^\s*(\d+\.|-)\s+', lambda mm: '• ' if mm.group(1) == '-' else mm.group(1) + ' ', s)
        s = s.replace('\\*', '').replace('**', '')
        if cur is None or cur['tab'] != tab or cur['heading'] != (sub or tab):
            cur = {'tab': tab.strip(), 'heading': (sub or tab).strip(), 'lines': []}
            sections.append(cur)
        cur['lines'].append(s)
    sections = [s for s in sections if any(len(l) > 12 for l in s['lines'])]
    out = {'source': snaps[-1].name, 'sections': sections,
           'wiki': [{'title': 'Palestinian Arabic specifics (dialect, diglossia, Arabizi)', 'url': 'https://github.com/TheNatanzi/anees/blob/master/wiki/05-palestinian-arabic-specifics-dialect-diglossia-ara.md'},
                    {'title': 'How to teach a spoken language (methods, evidence)', 'url': 'https://github.com/TheNatanzi/anees/blob/master/wiki/02-how-to-teach-a-spoken-language-methods-evidence-an.md'},
                    {'title': 'Vocabulary science: how words get learned and kept', 'url': 'https://github.com/TheNatanzi/anees/blob/master/wiki/03-vocabulary-science-how-words-get-learned-and-kept.md'}]}
    (ROOT / 'docs' / 'data').mkdir(parents=True, exist_ok=True)
    io.open(ROOT / 'docs' / 'data' / 'grammar.json', 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == '__main__':
    g = build()
    print(len(g['sections']), 'sections;', sum(len(s['lines']) for s in g['sections']), 'lines')
    for s in g['sections'][:8]:
        print(' ', s['tab'], '›', s['heading'], len(s['lines']))
