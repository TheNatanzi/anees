"""Builds reports/READER-90-OVERNIGHT-2026-10-17.pdf (Medi: "Send me a PDF in the morning with the results")."""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(REPO, 'reports'); os.makedirs(OUTD, exist_ok=True)
PDF = os.path.join(OUTD, 'READER-90-OVERNIGHT-2026-10-17.pdf')
WORK = os.path.join(REPO, 'data', 'lesson-work', 'reader-tiers', 'overnight-2026-10-17')
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB', r'C:\Windows\Fonts\arialbd.ttf'))

TEAL, GOLD, INK, MUTE, RED = '#0f6e76', '#b7791f', '#15212b', '#5b6b78', '#b4442f'
ar = lambda s: get_display(arabic_reshaper.reshape(str(s)))

# (method, plain meaning, held-out F0.5, caught/102, % of flags real, group)
M = [
    ('Judge panel: Opus + Gemini Flash', 'every model\'s flags pooled, two judges rule on each', 80.6, 68, 85.0, 'best'),
    ('Judge panel, all judges combined (learned)', 'judges + reader votes + tutor signal, weights learned', 79.6, 64, 85.3, 'judge'),
    ('Learned weights over 8 readers', 'learns which models and clues to trust', 79.4, 67, 83.8, 'vote'),
    ('Opus + Sonnet agree (with rule fix)', 'the live reader, plus dropping "asked" moments', 78.8, 69, 82.1, 'vote'),
    ('Judges with worked examples', 'judges also see right/wrong examples from other lessons', 78.0, 64, 83.1, 'judge'),
    ('8 models vote', 'keep a flag when enough of 8 models agree', 77.7, 60, 84.5, 'vote'),
    ('GPT-5.5 + Gemini Flash + Opus vote', 'your 3-model team', 77.5, 66, 81.5, 'vote'),
    ('Opus read 3 times, vote', 'same model 3 times, keep repeated finds', 75.3, 66, 78.6, 'repeat'),
    ('Judges on 5-minute slices', 'judge sees only the nearby part of the lesson', 75.1, 67, 77.9, 'judge'),
    ('Council: 5 advisors + chairman', 'grammar teacher, native speaker, tutor rules, noise skeptic, learner expert', 73.9, 73, 74.5, 'debate'),
    ('Defense-lawyer judges', 'judges told to clear him unless clearly corrected', 73.9, 63, 77.8, 'debate'),
    ('Gemini 3.7 Flash alone', 'best single model', 73.6, 58, 79.5, 'single'),
    ('Opus alone (same input as all)', 'fair re-run', 72.7, 73, 73.0, 'single'),
    ('GPT-5.5 alone', '', 72.4, 75, 72.1, 'single'),
    ('Sonnet alone (same input as all)', 'fair re-run', 68.0, 65, 69.1, 'single'),
    ('Gemini 4 Argon alone', "Google's top model: flags too much", 60.7, 74, 58.3, 'single'),
]
COL = {'best': TEAL, 'judge': '#3f8f96', 'vote': '#6c9aa0', 'repeat': '#8aa6ab', 'debate': GOLD, 'single': '#a9b6be'}


def chart():
    fig, ax = plt.subplots(figsize=(7.6, 5.4), dpi=200)
    names = [m[0] for m in M][::-1]; vals = [m[2] for m in M][::-1]; cols = [COL[m[5]] for m in M][::-1]
    ax.barh(names, vals, color=cols, height=0.62)
    for y, v in enumerate(vals):
        ax.text(v + 0.6, y, f'{v:.1f}', va='center', fontsize=8, color=INK)
    ax.axvline(90, color=RED, lw=1.6, ls='--'); ax.text(90.4, len(M) - 0.6, 'goal 90', color=RED, fontsize=8, va='top')
    ax.axvline(85.9, color=MUTE, lw=1, ls=':'); ax.text(85.6, -0.9, 'max if AI wins\nall 9 disputes: 85.9', color=MUTE, fontsize=7, ha='right')
    ax.set_xlim(50, 95); ax.set_xlabel('Score on a lesson the method was NOT tuned on (F0.5, out of 100)', fontsize=8)
    ax.tick_params(axis='y', labelsize=7.5); ax.tick_params(axis='x', labelsize=7.5)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); p = os.path.join(WORK, 'scorecard.png'); fig.savefig(p); plt.close(fig); return p


S = lambda name, **kw: ParagraphStyle(name, fontName=kw.pop('font', 'Arial'), textColor=colors.HexColor(kw.pop('color', INK)), **kw)
H1 = S('h1', font='ArialB', fontSize=20, leading=24, spaceAfter=6)
H2 = S('h2', font='ArialB', fontSize=14, leading=18, spaceBefore=6, spaceAfter=6, color=TEAL)
B = S('b', fontSize=10, leading=14)
SM = S('sm', fontSize=8.5, leading=11, color=MUTE)
BIG = S('big', font='ArialB', fontSize=13, leading=17, color=INK, backColor=colors.HexColor('#d5ecee'), borderPadding=8, spaceAfter=10)
ACT = S('act', font='ArialB', fontSize=11.5, leading=15, color=INK, backColor=colors.HexColor('#f6ead2'), borderPadding=8, spaceBefore=8)


def bullets(items):
    return [Paragraph('• ' + i, B) for i in items]


def table(rows, widths, head=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    st = [('FONT', (0, 0), (-1, -1), 'Arial', 8.5), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#d9e0e6')), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
    if head:
        st += [('FONT', (0, 0), (-1, 0), 'ArialB', 8.5), ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(MUTE))]
    t.setStyle(TableStyle(st)); return t


def build():
    key = json.load(open(os.path.join(WORK, 'key-check.json'), encoding='utf-8'))
    doc = SimpleDocTemplate(PDF, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title='Overnight mistake-reader test', author='Claude for Medi')
    s = []
    s += [Paragraph('Overnight test: can the AI reach 90?', H1),
          Paragraph('No. The best honest score is <b>80.6</b>. Your answer key itself is about 90% reliable, so 90 is roughly the ceiling.', BIG),
          Image(chart(), width=7.1 * inch, height=5.05 * inch),
          Paragraph('Score = F0.5: how many of your 102 marked mistakes it caught, plus how many of its flags were real (fake flags count double). '
                    'Every score here is on a lesson the method did NOT learn from (tune on 2 lessons, test on the 3rd, rotate).', SM),
          Paragraph('Your one action: check the 9 disputed moments on page 3 (about 10 minutes).', ACT), PageBreak()]

    s += [Paragraph('The 3 things that mattered', H2),
          table([['Finding', 'Effect'],
                 ['Stop counting "you asked for a word" and "no reaction" moments as mistakes (your grade book already does)', '+5 to +10 points on every method'],
                 ['A judge panel (Opus + Gemini Flash) ruling on every model\'s flags', 'best overall: 80.6'],
                 ['Reading the same lesson 3 times and voting', '+2.6 for Opus (72.7 to 75.3)']], [4.6 * inch, 2.4 * inch]),
          Spacer(1, 6), Paragraph('What did NOT help', H2),
          *bullets(['<b>Council</b> (5 advisors + chairman): 73.9. On the 33 borderline flags the chairman was right only 16 times.',
                    '<b>Defense-lawyer judges</b>: 73.9. They clear too many real mistakes.',
                    '<b>More judges</b> (adding Sonnet and Gemini Pro): 76.1. Weaker judges dilute the strong ones.',
                    '<b>Short 5-minute slices</b>: 75.1. The judge loses the lesson context.',
                    '<b>Gemini 4 Argon</b> (Google\'s top model): 60.7. It flags too much.',
                    '<b>Making the test fair</b> (everyone gets the same pasted input) barely changed the ranking: Opus 72.5 to 72.7.']),
          Spacer(1, 6), Paragraph('Every method in plain words', H2),
          table([['Method', 'What it does', 'Score', 'Caught /102', 'Flags real']] +
                [[Paragraph(m[0], SM), Paragraph(m[1], SM), f'{m[2]:.1f}', str(m[3]), f'{m[4]:.0f}%'] for m in M],
                [1.9 * inch, 2.9 * inch, 0.6 * inch, 0.8 * inch, 0.8 * inch]), PageBreak()]

    s += [Paragraph('Why not 90', H2),
          table([['Limit', 'Number'],
                 ['Your own key: Amal fully agreed with 78 of your 86 notes on 10-09', 'about 91% reliable'],
                 ['Mistakes in your key that NO model ever flags', '6 of 102'],
                 ['Moments where your key and the AI strongly disagree', '9 (below)'],
                 ['Best score if the AI is right on all 9', '85.9'],
                 ['Smallest difference 102 mistakes can tell apart from luck', 'about 4 points']], [4.9 * inch, 2.1 * inch]),
          Spacer(1, 8), Paragraph('Your check list: 9 moments where your key and the AI disagree', H2),
          Paragraph('"AI says mistake" = 5 to 8 models flagged it and both judges agreed, but your key does not mark it. '
                    '"Key says mistake" = your key marks it but both judges said it was not one. Open the lesson at the time and decide.', SM)]
    rows = [['Who says mistake', 'Lesson', 'Time', 'He said', 'Amal wanted']]
    for kind, d, t, w, r, sig, n in key:
        rows.append([('AI (key says no)' if kind.startswith('AI') else 'Key (AI says no)'), d[5:], t, Paragraph(ar(w)[:60], SM), Paragraph(ar(r)[:60], SM)])
    s += [table(rows, [1.4 * inch, 0.6 * inch, 0.6 * inch, 2.2 * inch, 2.2 * inch]), PageBreak()]

    s += [Paragraph('Recommendation', H2),
          table([['Do', 'Why'],
                 ['1. Ship the rule fix now: never mark "asked for a word" or "no reaction" moments', 'Biggest, cheapest gain (+5 to +10), matches your grade book'],
                 ['2. Keep Opus + Sonnet live for now', 'The judge panel is +1.8 better, inside the 4-point noise'],
                 ['3. Check the 9 moments on page 3', 'If the AI is right on most, the real score is about 84-86'],
                 ['4. Fully grade 2 more lessons', 'A locked test set; 3 lessons cannot separate methods under 4 points'],
                 ['5. Then switch to the judge panel if it wins again', 'Protocol rule: a winner must win again on a new lesson']], [3.6 * inch, 3.4 * inch]),
          Spacer(1, 8), Paragraph('Honest caveats', H2),
          *bullets(['16 methods were tried on the same 3 lessons. The best of many tries is a little lucky, so expect the real 80.6 to be about 78-80.',
                    'The "asked" rule fix was found by looking at all 3 lessons\' errors. It matches your grade book\'s written rule, but it was not blind.',
                    'OpenAI\'s credit ran out at the start of the night, so GPT-6-astra, GPT-5.4 and the OpenAI judge did not run.',
                    'Codex is logged out (my mistake earlier). It needs <b>codex login</b> before it can join a test.',
                    'Claude runs used your monthly plan (no extra money). Gemini cost was small; see Google AI Studio billing for the exact amount.',
                    'Nothing live was changed. All files are on the branch claude/reader-90-overnight.']),
          Spacer(1, 8), Paragraph('Your one action: check the 9 disputed moments on page 3, then say "ship the rule fix".', ACT)]
    doc.build(s)
    print(PDF)


if __name__ == '__main__':
    build()
