# -*- coding: utf-8 -*-
"""PG-55 · writes plan/ANEES-CASE-STUDY-2026-10-19.story.html: the case study told in app-styled infographics (public: roles only,
no lesson words). Colours come from the app's CSS variables via classes (css/ai-reports.css .rs-*), so both themes work."""
import sys
import os
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plan", "ANEES-CASE-STUDY-2026-10-19.story.html")


def dots(n, hot, cols, r=9, gap=26, x0=12, y0=12):
    s = []
    for i in range(n):
        cx, cy = x0 + (i % cols) * gap, y0 + (i // cols) * gap
        s.append('<circle cx="%d" cy="%d" r="%d" class="%s"/>' % (cx, cy, r, 'o' if i < hot else 'm'))
    return ''.join(s)


def hbars(rows, w=640, lab=230, h=34, gap=14):
    """rows: (label, lo, hi, cls, text) -> horizontal bars on a 0-100 scale; a range draws lo..hi."""
    out, y = [], 0
    scale = (w - lab - 70) / 100
    for label, lo, hi, cls, text in rows:
        out.append('<text x="0" y="%d" class="t">%s</text>' % (y + h * 0.68, label))
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="6" class="track"/>' % (lab, y, 100 * scale, h))
        out.append('<rect x="%d" y="%d" width="%.0f" height="%d" rx="6" class="%s"/>' % (lab, y, hi * scale, h, cls))
        out.append('<text x="%.0f" y="%d" class="v">%s</text>' % (lab + hi * scale + 8, y + h * 0.68, text))
        y += h + gap
    return '<svg class="rs-svg" viewBox="0 0 %d %d" role="img" aria-label="%s">%s</svg>' % (
        w, y - gap, '; '.join('%s %s' % (r[0], r[4]) for r in rows), ''.join(out))


def chapter(cid, eyebrow, title, svg, bullets, app=None, paper=None):
    b = ''.join('<li>%s</li>' % x for x in bullets)
    links = []
    if app:
        links.append('<a class="rs-chip rs-app" href="%s">In the app: %s</a>' % app)
    if paper:
        links.append('<a class="rs-chip" href="#%s">In the paper: %s</a>' % paper)
    return ('<section class="rs-ch" id="%s"><div class="rs-text"><span class="vp-eyebrow">%s</span><h2 class="rs-h">%s</h2>'
            '<ul class="rs-pts">%s</ul><div class="rs-links">%s</div></div><figure class="rs-fig">%s</figure></section>') % (
        cid, eyebrow, title, b, ''.join(links), svg)


ICON = {
    'ear': '<path d="M20 34 Q18 12 32 10 Q46 8 46 24 Q46 31 39 35 Q35 38 35 44 Q35 50 29 50" class="ln"/><path d="M28 25 Q28 18 35 19" class="ln"/>',
    'scale': '<line x1="30" y1="10" x2="30" y2="48" class="ln"/><line x1="12" y1="18" x2="48" y2="18" class="ln"/><path d="M6 34 L12 19 L18 34 Z M42 34 L48 19 L54 34 Z" class="fl"/><line x1="20" y1="48" x2="40" y2="48" class="ln"/>',
    'check': '<path d="M10 18 l6 6 l10 -10 M10 38 l6 6 l10 -10" class="ln"/><line x1="32" y1="20" x2="50" y2="20" class="ln"/><line x1="32" y1="40" x2="50" y2="40" class="ln"/>',
}


def puzzles():
    cards = []
    for i, (ic, cls, head, line) in enumerate([('ear', 'a', 'Hearing', 'Write down exactly what he said'),
                                               ('scale', 'o', 'Counting', 'Decide what counts as a mistake'),
                                               ('check', 'k', 'Grading', 'Check if the computer got it right')]):
        x = i * 220
        cards.append('<g transform="translate(%d,0)"><rect width="200" height="210" rx="14" class="card"/>'
                     '<g transform="translate(70,22)"><circle cx="30" cy="30" r="30" class="%s"/><g class="ic">%s</g></g>'
                     '<text x="100" y="120" text-anchor="middle" class="h">%d · %s</text>'
                     '<foreignObject x="14" y="134" width="172" height="70"><div xmlns="http://www.w3.org/1999/xhtml" class="rs-fo">%s</div></foreignObject></g>'
                     % (x, cls, ICON[ic], i + 1, head, line))
    return '<svg class="rs-svg" viewBox="0 0 640 210" role="img" aria-label="Three puzzles: hearing, counting, grading">%s</svg>' % ''.join(cards)


def flow(steps, w=640):
    """steps: (title, sub, cls) boxes left to right with arrows."""
    n = len(steps); bw = (w - (n - 1) * 34) / n; out = []
    for i, (t, s, cls) in enumerate(steps):
        x = i * (bw + 34)
        out.append('<rect x="%.0f" y="10" width="%.0f" height="120" rx="14" class="%s"/>' % (x, bw, cls))
        out.append('<text x="%.0f" y="62" text-anchor="middle" class="h %s">%s</text>' % (x + bw / 2, 'inv' if cls != 'card' else '', t))
        out.append('<text x="%.0f" y="92" text-anchor="middle" class="s %s">%s</text>' % (x + bw / 2, 'inv' if cls != 'card' else '', s))
        if i < n - 1:
            ax = x + bw + 6
            out.append('<path d="M%.0f 70 h18" class="ln"/><path d="M%.0f 62 l9 8 l-9 8 z" class="fl"/>' % (ax, ax + 16))
    return '<svg class="rs-svg" viewBox="0 0 %d 140" role="img" aria-label="%s">%s</svg>' % (
        w, ' then '.join(s[0] + ' (' + s[1] + ')' for s in steps), ''.join(out))


def keybar():
    return ('<svg class="rs-svg" viewBox="0 0 640 170" role="img" aria-label="Answer key: 99 found by the student plus 20 found by an AI and confirmed by him, 119 in all">'
            '<rect x="0" y="20" width="500" height="64" rx="8" class="a"/><text x="16" y="60" class="h inv">99 · found by the student</text>'
            '<rect x="504" y="20" width="101" height="64" rx="8" class="o"/><text x="554" y="60" text-anchor="middle" class="h">+20</text>'
            '<text x="554" y="108" text-anchor="middle" class="s">found by an AI</text>'
            '<text x="0" y="150" class="big">= 119</text><text x="118" y="148" class="s">mistakes in the final key</text></svg>')


def scoreboard():
    def bar(x, v, cls, lbl):
        h = v * 2.2
        return ('<rect x="%d" y="%.0f" width="90" height="%.0f" rx="6" class="%s"/><text x="%d" y="%.0f" text-anchor="middle" class="v">%s</text>'
                % (x, 240 - h, h, cls, x + 45, 232 - h, lbl))
    return ('<svg class="rs-svg" viewBox="0 0 640 300" role="img" aria-label="Found: today\'s reader 74 percent, best judges 60 percent. Right: today\'s reader 74 percent, best judges 92 percent.">'
            '<line x1="0" y1="240" x2="640" y2="240" class="axis"/>'
            + bar(40, 74, 'a', '74%') + bar(140, 60, 'm', '60%') + bar(360, 74, 'm', '74%') + bar(460, 92, 'o', '92%') +
            '<text x="135" y="272" text-anchor="middle" class="h">Found (recall)</text>'
            '<text x="455" y="272" text-anchor="middle" class="h">Right (precision)</text>'
            '<rect x="40" y="284" width="14" height="14" rx="3" class="a"/><text x="60" y="296" class="s">today\'s reader</text>'
            '<rect x="250" y="284" width="14" height="14" rx="3" class="o"/><text x="270" y="296" class="s">best judges (Opus + GPT-6 Astra)</text></svg>')


def coins():
    s = []
    for i in range(112):
        cx, cy = 14 + (i % 16) * 38, 14 + (i // 16) * 30
        s.append('<circle cx="%d" cy="%d" r="11" class="%s"/>' % (cx, cy, 'o' if i == 54 else 'm'))
    return ('<svg class="rs-svg" viewBox="0 0 620 236" role="img" aria-label="112 coins, one highlighted: one method can look best by luck">%s'
            '<text x="0" y="230" class="s">112 methods tested on the same 3 lessons · one looks best partly by luck</text></svg>') % ''.join(s)


def guard():
    return ('<svg class="rs-svg" viewBox="0 0 640 210" role="img" aria-label="Mistakes hidden by the second listener: 12 of 27 early on, 1 of 67 with the guard">'
            '<text x="0" y="16" class="h">Early on, no guard</text><g transform="translate(0,28)">%s</g><text x="0" y="132" class="big o-t">12 of 27 hidden</text>'
            '<text x="330" y="16" class="h">With the guard</text><g transform="translate(330,28)">%s</g><text x="330" y="200" class="big a-t">1 of 67 hidden</text>'
            '</svg>') % (dots(27, 12, 10), dots(67, 1, 12, r=8, gap=24))


def build():
    hear = hbars([('ElevenLabs alone', 0, 65, 'm', '61–69%'), ('Gemini hears whole lesson', 0, 80, 'm', '78–81%'),
                  ('3 engines vote', 0, 89, 'm', '88–90%'), ('Gemini listens once', 0, 92, 'm', '91–92%'),
                  ('Method A (we use this)', 0, 95, 'a', '94–95%')])
    one = hbars([('Opus + Argon', 0, 88.7, 'o', '88.7'), ("Today's reader", 0, 77.7, 'a', '77.7')], lab=170)
    cost = hbars([('One phase of listening tests', 0, 72, 'o', '$120–130'), ('Argon hearing test (capped)', 0, 7.4, 'a', '$12.73')], lab=260)
    ch = [
        chapter('rs-goal', 'The goal', 'An app that lists the mistakes the tutor corrected',
                puzzles(), ['After each recorded lesson, list every mistake the tutor corrected, so the student studies a list instead of replaying the hour.',
                            'Three puzzles stood in the way: <b>hearing</b>, <b>counting</b> and <b>grading</b>.',
                            '46 days (Sept 3 – Oct 18, 2026), 24 recorded lessons; AI coding helpers did the engineering.'],
                ('../lessons.html', 'Lessons &amp; Audio'), ('1-introduction', '1. Introduction')),
        chapter('rs-hear', 'Puzzle 1 · Hearing', 'Speech-to-text "autocorrects" the learner',
                hear, ['<b>Speech-to-text</b> writes what he <i>should</i> have said, so his mistake disappears.',
                       'Method A: ElevenLabs writes first, then Gemini 3.8 Flash re-listens to each of his lines 3 times; 2 of 3 agreeing wins.',
                       'Every other way scored lower. A separate test of Gemini 4 Argon as the listener also scored lower (84% and 79%).'],
                ('../lessons.html', 'every transcript'), ('53-phase-3-hearing', '5.3 Hearing')),
        chapter('rs-methoda', 'Puzzle 1 · Hearing', 'Method A: ask three times, keep the majority',
                flow([('Audio', 'the lesson', 'card'), ('ElevenLabs', 'writes it', 'a'), ('Flash ×3', 're-listens', 'k'), ('2 of 3 agree', 'that wins', 'o')]),
                ['Like asking three friends what they heard and going with the majority.',
                 'Flash also hears the lesson around each line, so it has context.'],
                None, ('appendix-c-configuration-of-the-headline-methods', 'Appendix C')),
        chapter('rs-guard', 'Puzzle 1 · Hearing', 'The danger: copying the teacher',
                guard(), ['The re-listener hears the tutor say the right word a second later and writes it for the student. His mistake vanishes.',
                          '<b>The guard:</b> any change that makes him sound like the tutor waits for the tutor to check.'],
                ('../tutor.html', 'Tutor › lines she checks'), ('53-phase-3-hearing', '5.3 Hearing')),
        chapter('rs-count', 'Puzzle 2 · Counting', 'A mistake = he says it wrong AND the tutor corrects it',
                flow([('Says it wrong', 'in Arabic', 'card'), ('Tutor corrects', 'word, "no", rule, hint', 'a'), ('= 1 mistake', 'counted', 'o')]),
                ['<b>Doesn\'t count:</b> asking how to say a word, using English, fixing it himself first, a correct local form, anything she let pass.',
                 'Only what the tutor actually corrected is counted.'],
                ('../grammar.html', 'Grammar Rules'), ('12-what-is-being-measured', '1.2 What is measured')),
        chapter('rs-key', 'Puzzle 3 · Grading', 'Even the answer key had mistakes',
                keybar(), ['<b>Answer key</b> = the right answers, like a teacher\'s answer sheet. The student re-listened to 3 lessons line by line.',
                           'He re-checked 4 of his own marks: 2 were wrong. 6 mistakes were counted twice under two labels.',
                           'The 20 extra came from one AI (Gemini 4 Argon). The tutor is now checking them blind.'],
                ('../tutor.html', 'Tutor › 49 moments to check'), ('56-the-answer-key', '5.6 The answer key')),
        chapter('rs-score', 'Finding mistakes · Results', 'Each side wins at something',
                scoreboard(), ['<b>Today\'s reader</b> (in the app now): two AIs, Claude Opus and Sonnet; a mistake is kept only if both flag it.',
                               '<b>Judge panel</b> (tested only): many AIs flag, 1–2 judge AIs vote on each flag.',
                               '<b>Precision</b> = of what it flagged, how much was real. <b>Recall</b> = of the real mistakes, how many it found. Scored on the student\'s first key (99).'],
                ('../progress.html', 'Progress &amp; Stats'), ('55-phase-4-readers-ensembles-and-judges', '5.5 Readers and judges')),
        chapter('rs-luck', 'Finding mistakes · Results', 'Too many tries, and no winner yet',
                coins(), ['Flip 112 coins and one lands heads 8 times: that is luck, not a magic coin.',
                          'After a fair luck check, no judge setup clearly beat today\'s reader.'],
                None, ('72-leakage-and-selection', '7.2 Leakage and selection')),
        chapter('rs-unfair', 'Finding mistakes · Results', 'One score, but an unfair test',
                one, ['<b>F0.5</b> = one 0–100 score that mixes both, with precision counting extra (a false "you made a mistake" breaks trust).',
                      'On the final key (119), Opus + Argon led. But 20 of those 119 were Argon\'s own finds: like grading a student with a key they helped write. <b>Not proven.</b>'],
                None, ('74-circularity-and-asymmetry-in-key-v3', '7.4 Circularity')),
        chapter('rs-money', 'Lessons learned', 'Money: a slip-up and a new rule',
                cost, ['A paid test drained credits with no spending limit.',
                       '<b>New rule:</b> monthly plans first; paid only with a dollar cap set ahead of time.'],
                None, ('75-money-and-access', '7.5 Money and access')),
        chapter('rs-next', 'What comes next', 'Pooled blind review by the tutor',
                flow([('Many AIs', 'hunt', 'a'), ('One pile', 'all finds', 'card'), ('Tutor checks', 'names hidden', 'o'), ('Win again', '3 new lessons', 'k')]),
                ['<b>Pooled</b> = every AI\'s finds go in one pile. <b>Blind</b> = the tutor can\'t see which AI found it, like a taste test with labels hidden.',
                 'A winner only counts if it wins again on 3 new lessons. Search-engine test sets (TREC) are built the same way.'],
                ('../tutor.html', 'Tutor'), ('8-proposed-protocol-for-the-next-lessons', '8. Protocol')),
    ]
    head = ('<section class="rs-intro"><span class="vp-eyebrow">The study in pictures · about 4 minutes</span>'
            '<p class="rs-lede"><b>Done:</b> the app now hears the student well (about 95%% of his words). '
            '<b>Open:</b> which AI best finds his mistakes — no winner yet. Scroll the pictures, or jump to the full paper.</p>'
            '<nav class="ar-jump" aria-label="Chapters">%s<a href="#paper">The full paper ↓</a></nav></section>') % ''.join(
        '<a href="#%s">%s</a>' % (c, t) for c, t in [('rs-goal', 'Goal'), ('rs-hear', 'Hearing'), ('rs-count', 'Counting'), ('rs-key', 'Answer key'),
                                                    ('rs-score', 'Results'), ('rs-money', 'Lessons learned'), ('rs-next', 'Next')])
    open(OUT, 'w', encoding='utf-8').write('<!-- Built by make_story (PG-55, 2026-10-19). Public: roles only. -->\n'
                                           + head + '\n' + '\n'.join(ch) + '\n')


build()
