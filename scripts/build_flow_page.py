# -*- coding: utf-8 -*-
"""PG-56 - the whole Anees process as one flowchart page in AI Reports (Medi 2026-10-21: "add the flowchart to the ai
reports", after "Give me a full flowchart of our entire process start to finish (see coinbase onboarding)").

The flowchart's text is plan/ANEES-FLOW.fragment.html (phases A-G, numbered steps, decision diamonds, who / cost chips);
this wraps it in the AI Reports page shell (scripts/build_ai_reports.page) as docs/reports/anees-flow.html. Its look is
css/ai-reports.css .fl-* in the app's own colours, so it follows Light / Dark like every page.

    python scripts/build_flow_page.py
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_ai_reports as BR  # noqa: E402

SRC = os.path.join(REPO, "plan", "ANEES-FLOW.fragment.html")
OUT = os.path.join(REPO, "docs", "reports", "anees-flow.html")
TITLE = "Anees: from lesson to grade"


WORD = {'A': 'Record', 'B': 'Hear', 'C': 'Check', 'D': 'Count', 'E': 'Publish', 'F': 'Tutor', 'G': 'Study', 'H': 'Grade'}
ICONS = {'A': '🎙️', 'B': '👂', 'C': '🔍', 'D': '📒', 'E': '🌐', 'F': '✍️', 'G': '📚', 'H': '🏆'}   # one picture per phase


def dword(frag):
    """De-word (plan/OVERNIGHT-DEWORD-2026-10-22.md): each step shows its title, who and cost; the how-it-works sentence
    opens in place behind a small (i) on the step. A numbered strip of the 8 phases sits on top (tap one to jump)."""
    frag = re.sub(r'<p>(.*?)</p>(?=<div class="chips">)',
                  r'<details class="dw-info fl-more"><summary aria-label="How this step works">ⓘ</summary><div>\1</div></details>', frag)
    # each phase is one row that opens on tap: letter, name, when, how many steps, and who / cost chips
    def phase(m):
        color, code, head, body = m.groups()
        steps = len(re.findall(r'<li class="node(?! decision)', body))
        asks = len(re.findall(r'<li class="node decision', body))
        who = ''.join(c for c, k in (('<span class="chip amal">Tutor</span>', 'chip amal'), ('<span class="chip medi">Student</span>', 'chip medi'),
                                     ('<span class="chip money">$</span>', 'chip money')) if k in body)
        sumry = '<span class="fl-sum">%s</span>' % who   # who acts and what costs money; the step count opens with the row
        head = head.replace('</h2>', '</h2>' + sumry, 1)
        return ('<details class="phase" id="fl-%s" style="--pc:%s"><summary><header><span class="pcode">%s</span>%s</header></summary>%s</details>'
                % (code, color, code, head, body))
    frag = re.sub(r'<section class="phase" style="--pc:([^"]+)"><header><span class="pcode">(\w)</span>(.*?)</header>(.*?)</section>',
                  phase, frag, flags=re.S)
    # a step's studies fold into one pill ("3 studies") that opens in place
    def fold(m):
        n = m.group(0).count('<details class="study">')
        return (' <details class="fl-studies"><summary> <span class="stag">%d %s</span></summary>%s</details>'
                % (n, 'study' if n == 1 else 'studies', m.group(0)))
    frag = re.sub(r'(?:<details class="study">(?:(?!</details>).)*</details>)+', fold, frag, flags=re.S)
    # a step that is only automatic (no person, no cost) reads quieter: it is part of the path, not a job for anyone
    frag = re.sub(r'<li class="node">((?:(?!</li>).)*?<div class="chips"><span class="chip auto">Automatic</span></div>)',
                  r'<li class="node fl-quiet">\1', frag, flags=re.S)
    # the 5 building blocks (Meet, hourly job, tutor trigger, guard, plans) join the colour key behind one (i)
    m = re.search(r'\s*</div>\s*<div class="kit">(.*?)</div>\s*(?=<div class="warn">)', frag, re.S)
    if m:
        frag = frag[:m.start()] + ('<details class="dw-info fl-kit"><summary aria-label="The building blocks">ⓘ</summary>'
                                   '<div class="kit">%s</div></details></div>\n  ' % m.group(1).strip()) + frag[m.end():]
    # one picture of the path: 8 coloured stops, icon + one word each, A to H; tap one to open it below
    stops = re.findall(r'<details class="phase" id="fl-(\w)" style="--pc:([^"]+)">', frag)
    if stops:
        strip = ('<ol class="fl-path" aria-label="The 8 stops from the call to the grade">' +
                 ''.join('<li style="--pc:%s"><a href="#fl-%s"><span class="fl-dot">%s</span><b>%s</b></a></li>'
                         % (c, k, ICONS.get(k, k), WORD.get(k, k)) for k, c in stops) + '</ol>')
        frag = frag.replace('<div class="key">', strip + '\n  <div class="key">', 1)
    # "who decides" is the rule behind the whole path: it closes the page, under Done
    w = re.search(r'\s*<div class="warn">.*?</div>', frag, re.S)
    if w and '<div class="done">' in frag:
        frag = frag[:w.start()] + frag[w.end():]
        frag = frag.replace('<p class="loop">', w.group(0).strip() + '\n  <p class="loop">', 1)
    return frag


def build():
    frag = dword(io.open(SRC, encoding="utf-8").read())
    html = BR.page(TITLE, "", "ANEES-FLOW.fragment.html", "Claude", "2026-10-21", story=screen_roles(frag))
    html = html.replace('<link rel="stylesheet" href="../css/ai-reports.css?v=20261022-study">',
                        '<link rel="stylesheet" href="../css/ai-reports.css?v=20261022-study"><link rel="stylesheet" href="../css/dw-reports.css?v=1">')
    html = html.replace('<article class="ar-doc">\n\n</article>', "").replace('<div class="ab-sub">Built from ANEES-FLOW.fragment.html</div>', "")
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("built", os.path.relpath(OUT, REPO), "%d KB" % (len(html) // 1024))
    fill_tab(frag)
    for out, title, body in STUDIES:
        p = os.path.join(REPO, "docs", "reports", out)
        io.open(p, "w", encoding="utf-8").write(BR.page(title, body, out, "Claude", "2026-10-21"))
        print("built", out)
    return OUT


TAB = os.path.join(REPO, "docs", "ai-reports.html")

# PG-33: app pages show roles, not names; "Amal's hub" is a retired name (check_pages 'hub')
ROLES = [(r"Amal's hub", "the Tutor page"), (r"Amal \(tutor\)", "Tutor"), (r"Medi \(student\)", "Student"),
         (r"[Tt]he Amal trigger", "the tutor trigger"), (r"Amal's", "the tutor's"), (r"Medi's", "the student's"),
         (r"\bAmal\b", "the tutor"), (r"\bMedi\b", "the student")]


def screen_roles(html):
    for pat, role in ROLES:
        html = re.sub(pat, role, html)
    # a role that starts a sentence, a heading, a chip or a list item gets a capital letter
    return re.sub(r'((?:^|>|[.!?:]\s|"|→ )\s*)the (tutor|student|Tutor)', lambda m: m.group(1) + "The " + m.group(2), html)


def fill_tab(frag):
    """Medi 2026-10-22 ("make a new tab for the flowchart in the ai report"): the same flowchart is the first tab of
    AI Reports, between the FLOW markers of docs/ai-reports.html. Links are written for docs/reports/, so they are
    re-pointed from the page one level up."""
    body = frag.split("-->", 1)[1].strip()
    def fix(m):
        u = m.group(1)
        if re.match(r"(https?:|#|mailto:)", u):
            return m.group(0)
        return 'href="%s"' % (u[3:] if u.startswith("../") else "reports/" + u)
    body = re.sub(r'href="([^"]+)"', fix, body)
    body = screen_roles(body)
    page = io.open(TAB, encoding="utf-8").read()
    a, b = page.index("<!-- FLOW:start -->") + len("<!-- FLOW:start -->"), page.index("<!-- FLOW:end -->")
    head = ('<div class="ov-head"><span class="vp-eyebrow">From the Meet call to the grade book</span><h2 class="ov-h2">How Anees works</h2>'
            '<p class="ab-sub">Every step, who does it, what it costs.</p></div>')
    io.open(TAB, "w", encoding="utf-8").write(page[:a] + "\n" + head + "\n" + body + "\n" + page[b:])
    print("filled the How Anees works tab in", os.path.relpath(TAB, REPO))


# Short write-ups for flowchart studies that have no report of their own (Medi 2026-10-22: "put a link to the study")
STUDIES = [
    ("codex-double-check-2026-10-21.html", "Codex double-check: does it help?", """
<h1>Codex double-check: does it help?</h1>
<p><b>Question.</b> Step 7 asks Codex (GPT-6 Astra, ChatGPT plan) to listen again to each unsure mistake and say "real" or "not real". Does that make the count more right?</p>
<p><b>Test.</b> Its verdicts on the Oct 8, 9 and 10 exam lessons, checked against answer key v4 (Medi's full review + Amal's rulings).</p>
<table><thead><tr><th>Codex said</th><th>Right</th><th>Out of</th><th>Rate</th></tr></thead><tbody>
<tr><td>Real</td><td>48</td><td>55</td><td>87%</td></tr>
<tr><td>Not real</td><td>1</td><td>4</td><td>25%</td></tr>
</tbody></table>
<p><b>Compare.</b> 86% of the unsure candidates were real anyway, so "real" from Codex is about as good as always guessing "real".</p>
<p><b>Result.</b> Kept, because it never drops a mistake on its own: a "not real" goes to Amal. Too few lessons to judge it fairly yet; re-test when more lessons have a key.</p>
"""),
]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
