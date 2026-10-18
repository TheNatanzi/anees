"""Builds reports/ANEES-ACCURACY-GUIDE.pdf: start-to-finish infographic of the lesson process and the research grids
(Medi 2026-10-18: 'Create a PDF for me for start to finish easy to read infographic educational on how our new process and
grids of our research. Make as easy to read and follow as possible.')."""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'reports', 'ANEES-ACCURACY-GUIDE.pdf')
IMG = os.path.join(REPO, 'reports', '_guide'); os.makedirs(IMG, exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB', r'C:\Windows\Fonts\arialbd.ttf'))
TEAL, GOLD, INK, MUTE, RED, GREEN, SOFT = '#0f6e76', '#b7791f', '#15212b', '#5b6b78', '#b4442f', '#2f7d4a', '#d5ecee'

S = lambda n, **k: ParagraphStyle(n, fontName=k.pop('font', 'Arial'), textColor=colors.HexColor(k.pop('color', INK)), **k)
H1 = S('h1', font='ArialB', fontSize=26, leading=32, spaceAfter=18)
H2 = S('h2', font='ArialB', fontSize=18, leading=22, spaceAfter=8, color=TEAL)
BIG = S('big', font='ArialB', fontSize=14, leading=19, backColor=colors.HexColor(SOFT), borderPadding=10, spaceAfter=12)
B = S('b', fontSize=12, leading=16)
SM = S('sm', fontSize=10, leading=13, color=MUTE)
CELL = S('cell', fontSize=11, leading=14)
CELLB = S('cellb', font='ArialB', fontSize=11, leading=14)


def table(rows, widths, best_row=None):
    rows = [[Paragraph(str(c), CELLB if i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(rows, colWidths=widths)
    st = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#d9e0e6')),
          ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef2f5')), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]
    if best_row:
        st.append(('BACKGROUND', (0, best_row), (-1, best_row), colors.HexColor(SOFT)))
    t.setStyle(TableStyle(st)); return t


def flow():
    steps = [('1 HEAR', 'ElevenLabs writes it\nGemini re-listens 3x'), ('2 PROTECT', "Changes toward Amal's\nwords wait for her"),
             ('3 READ', 'AI readers find\npossible mistakes'), ('4 JUDGE', 'Judges keep only\nreal mistakes'),
             ('5 RULES', 'Asked / no reaction\nnever a mistake'), ('6 AMAL WINS', 'Her rulings beat\nevery AI'),
             ('7 YOUR PAGE', 'Marks, scores,\nflashcards'), ('8 TEST', 'Graded lessons\ncheck it all')]
    fig, ax = plt.subplots(figsize=(8, 9.2), dpi=200); ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(0, 17)
    for i, (t, d) in enumerate(steps):
        y = 15.4 - i * 2.05
        c = TEAL if i < 7 else GOLD
        ax.add_patch(FancyBboxPatch((0.6, y - 0.75), 8.8, 1.5, boxstyle='round,pad=0.08,rounding_size=0.25', fc=c, ec='none'))
        ax.text(1.1, y, t, color='white', fontsize=15, fontweight='bold', va='center')
        ax.text(4.3, y, d, color='white', fontsize=12.5, va='center')
        if i < 7:
            ax.annotate('', xy=(5, y - 1.25), xytext=(5, y - 0.8), arrowprops=dict(arrowstyle='-|>', color=INK, lw=2))
    ax.annotate('', xy=(9.7, 15.4), xytext=(9.7, 15.4 - 7 * 2.05), arrowprops=dict(arrowstyle='-|>', color=GOLD, lw=2, connectionstyle='arc3,rad=-0.25'))
    ax.text(9.95, 8.2, 'better method\nfound? redo\nALL lessons', fontsize=9, color=GOLD, rotation=0, ha='left', va='center')
    fig.tight_layout(); p = os.path.join(IMG, 'flow.png'); fig.savefig(p); plt.close(fig); return p


def bars(name, items, xlab, goal=None, xmin=0):
    fig, ax = plt.subplots(figsize=(7.4, 0.55 * len(items) + 1.2), dpi=200)
    labels = [i[0] for i in items][::-1]; vals = [i[1] for i in items][::-1]; cols = [i[2] for i in items][::-1]
    ax.barh(labels, vals, color=cols, height=0.62)
    for y, v in enumerate(vals):
        ax.text(v + 0.6, y, f'{v:g}', va='center', fontsize=11, fontweight='bold', color=INK)
    if goal:
        ax.axvline(goal, color=RED, ls='--', lw=1.5); ax.text(goal + 0.3, len(items) - 0.5, 'goal %g' % goal, color=RED, fontsize=9)
    ax.set_xlim(xmin, 100); ax.set_xlabel(xlab, fontsize=10); ax.tick_params(labelsize=10)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout(); p = os.path.join(IMG, name + '.png'); fig.savefig(p); plt.close(fig); return p


def build():
    doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title='Anees accuracy guide', author='Claude for Medi')
    s = []
    # 1 - cover + the whole process
    s += [Paragraph('How Anees grades your Arabic', H1),
          Paragraph('Every lesson goes through 8 steps. Each step was picked by testing it against lessons you graded by hand.', BIG),
          Image(flow(), width=6.3 * inch, height=7.25 * inch), PageBreak()]
    # 2 - words
    s += [Paragraph('Words used in this guide', H2),
          table([['Word', 'Plain meaning'],
                 ['Answer key', 'Your own full review of a lesson. The "right answers" every method is tested against.'],
                 ['Score', 'Out of 100. How many of your real mistakes it caught, and how many of its marks were real (fake marks count double).'],
                 ['Held-out', "Scored on a lesson the method never learned from. The only honest score."],
                 ['Reader', 'An AI that reads the whole lesson and flags possible mistakes.'],
                 ['Judge', 'An AI that looks at every flag and decides: real mistake or not.'],
                 ['Judge panel', 'Many readers flag, two judges decide. Our most accurate method.'],
                 ['Hidden mistake', 'You said it wrong, but the AI wrote it correctly, so your mistake disappears.']], [1.6 * inch, 5.3 * inch]),
          PageBreak()]
    # 3 - hearing
    s += [Paragraph('Step 1: Hearing your words', H2),
          Paragraph('Winner: method A. ElevenLabs writes the lesson, Gemini re-listens to each of your lines 3 times.', BIG),
          Image(bars('hear', [('A: today (winner)', 95, TEAL), ('Gemini listens once', 91, '#7aa7ad'), ('C: 3 AIs vote', 88, '#9fb4ba'),
                              ('F: grade each other', 87, '#9fb4ba'), ('E: Gemini listens twice', 86, '#9fb4ba'), ('B: Gemini whole lesson', 81, '#b8c4ca'),
                              ('ElevenLabs alone', 69, '#ccd5da')], 'Your words heard right (%), lesson 10-09', xmin=50), width=6.6 * inch, height=4.4 * inch),
          Paragraph('Tested on 10-09 and 10-10. Method A won both. It also hid the fewest of your mistakes (1 of 67).', B), PageBreak()]
    # 4 - mistake readers
    s += [Paragraph('Steps 3-4: Finding your mistakes', H2),
          Paragraph('Winner: the judge panel. Many AIs flag, two judges keep only the real mistakes.', BIG),
          Image(bars('read', [('Judge panel (best)', 83.5, TEAL), ('Judge panel, free plans only', 83.1, '#3f8f96'), ('Opus + Sonnet both agree', 80, '#7aa7ad'),
                              ('Gemini 3.7 Flash alone', 74, '#9fb4ba'), ('Opus alone', 73, '#9fb4ba'), ('Council of 5 advisors', 74, GOLD),
                              ('GPT-6-astra alone', 67, '#b8c4ca'), ('Gemini 4 Argon alone', 61, '#ccd5da')], 'Score on lessons it never saw (held-out)', goal=90, xmin=40),
                width=6.6 * inch, height=5 * inch),
          Paragraph('Free plans only = both judges run on your Claude and ChatGPT plans (Opus + GPT-6-astra); 2 of its 6 readers are Gemini (free once the Gemini tool uses your Google plan).', SM), PageBreak()]
    # 5 - every test grid
    s += [Paragraph('Every test we ran', H2),
          table([['Test', 'Winner', 'Result'],
                 ['Listening methods A-F', 'A (today)', 'Kept'],
                 ['25 Gemini + OpenAI models as readers', 'Gemini 3.7 Flash', 'Best single reader'],
                 ['Claude: Fable, Opus, Sonnet, Haiku', 'Opus / Sonnet', 'Fable and Haiku dropped'],
                 ['Two readers must agree', 'Opus + Sonnet', 'Live until the panel'],
                 ['Judge panel (pool + 2 judges)', 'Opus + Gemini Flash / Astra', 'Most accurate'],
                 ['Debate, council, defence lawyer', 'None', "Didn't help"],
                 ['Same model 3-5 times, vote', 'Opus only (+2.6)', 'Small help'],
                 ['Short 5-minute slices', 'None', "Didn't help"],
                 ['Codex searching on its own', '82.1 (best of 13 tries)', 'Inside the noise']], [2.8 * inch, 2.3 * inch, 1.8 * inch], best_row=5),
          PageBreak()]
    # 6 - rules learned
    s += [Paragraph('Rules we learned', H2),
          table([['Rule', 'What it means for you', 'Why'],
                 ['PR-27', '"Asked for a word" = half credit, never a mistake. No reaction from Amal = never a mistake.', 'Matches your grade book'],
                 ['AM-33', "Amal's rulings beat every AI and are kept forever.", 'She found 5 errors in the key'],
                 ['GR-40', "Amal's uploaded collocation cards update the verb + preposition rule.", '49 to 63 verbs'],
                 ['PR-26', 'The hourly job can no longer get stuck on a file clash.', '481 failed publishes'],
                 ['LS-17', 'A recording bot that never recorded is skipped.', 'Oct 14 was stuck 4 days'],
                 ['PR-28', 'One written method for every lesson; old lessons redone when it improves.', 'Your request'],
                 ['Rule 7', 'Your monthly plans first; paid APIs only with your yes.', 'OpenAI credit was drained']],
                [0.9 * inch, 4.1 * inch, 1.9 * inch]), PageBreak()]
    # 7 - limits + change rule
    s += [Paragraph('Why not 100, and how a step can change', H2),
          table([['Limit', 'Number'],
                 ['Two humans grading the same mistakes agree about', '75 / 100'],
                 ['Your own key (Amal agreed with 78 of your 86 notes)', 'about 90% reliable'],
                 ['Our best method', 'about 84'],
                 ['Best single lesson', '91.5'],
                 ['Smallest difference 99 mistakes can prove', 'about 4 points']], [4.9 * inch, 2 * inch]),
          Spacer(1, 14), Paragraph('A step only changes when:', CELLB),
          table([['#', 'Check'],
                 ['1', 'It is tested on lessons you fully graded'],
                 ['2', 'It wins on a lesson it never saw'],
                 ['3', 'It wins by more than the noise (about 4 points)'],
                 ['4', 'It wins again on your next graded lesson'],
                 ['5', 'Then every old lesson is redone with it']], [0.5 * inch, 6.4 * inch]),
          Spacer(1, 14), Paragraph('Your part: fully grade 1 lesson in 3. Amal: answer her Tutor page questions.', BIG)]
    doc.build(s)
    print(OUT)


if __name__ == '__main__':
    build()
