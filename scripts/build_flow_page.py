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
# the same pictures drawn as flat SVG (white strokes on the phase colour), so they look the same on every device
_S = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">%s</svg>'
SVG_ICONS = {
    'A': _S % '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6"/>',
    'B': _S % '<path d="M7 10a5 5 0 0 1 10 0c0 3-3 4-3 7a3 3 0 0 1-6 0"/><path d="M10 10a2 2 0 0 1 4 0"/>',
    'C': _S % '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    'D': _S % '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
    'E': _S % '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    'F': _S % '<path d="M4 20l4-1 11-11-3-3L5 16z"/><path d="M14 6l3 3"/>',
    'G': _S % '<path d="M4 5h6v15H4zM10 5h5v15h-5zM15 6l4-1 2 14-4 1z"/>',
    'H': _S % '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4M12 14v4M8 20h8"/>',
}
ROBOT_ICON = _S % '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01M10 16h4"/>'
DONE_ICON = ('<svg class="fl-doneico" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.4" '
             'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M7 12.5l3.2 3L17 9"/></svg>')


def dword(frag):
    """De-word round 2 (Medi 2026-10-22: "I like look A but not how much data you cut"): every phase, step, study,
    building block and the who-decides rule stay in view, as before. Only a step's how-it-works sentence that holds no
    number opens behind a small (i); each phase gets its picture."""
    def info(m):
        txt = re.sub(r'<[^>]+>', '', m.group(1))
        if re.search(r'\d', txt) or len(txt.split()) <= 60:
            return m.group(0)   # a number in it is data, and a one-liner reads faster than a tap: it stays in view
        return '<details class="dw-info fl-more"><summary aria-label="How this step works">ⓘ</summary><div>%s</div></details>' % m.group(1)
    frag = re.sub(r'<p>(.*?)</p>(?=<div class="chips">)', info, frag)

    def phase(m):
        code = m.group(2)
        return m.group(0) + '<span class="fl-ico" aria-hidden="true">%s</span>' % (SVG_ICONS.get(code) or ICONS.get(code, ''))
    frag = re.sub(r'<section class="phase" style="--pc:([^"]+)"><header><span class="pcode">(\w)</span>', phase, frag)
    # steps 3 + 4 as one picture: the first transcript alone vs after the second listen (the numbers stay in the text too)
    acc = ('<div class="dw-bars fl-acc" role="img" aria-label="Words right: 61–69% from ElevenLabs alone, 94–95% after the second listen">'
           '<div><span>ElevenLabs alone</span><div class="dw-track"><i style="width:65%"></i></div><b>61–69%</b></div>'
           '<div><span>+ 3 listens, 2 agree</span><div class="dw-track"><i style="width:94.5%"></i></div><b>94–95%</b></div></div>'
           + '<div class="fl-mini"><span>🎧 3 listens</span><i>→</i><span>✓ 2 agree</span><i>→</i><span><b>94–95%</b> right</span></div>')
    frag = re.sub(r'(method A: 94–95%</b> right\.(?:(?!<div class="chips">).)*?)(<div class="chips">)', lambda m: m.group(1) + acc + m.group(2), frag, count=1, flags=re.S)
    # one picture of the path on top: 8 coloured stops, icon + one word each, A to H; a tap jumps to that phase
    stops = re.findall(r'<section class="phase" style="--pc:([^"]+)"><header><span class="pcode">(\w)</span>', frag)
    if stops:
        frag = re.sub(r'<section class="phase" style="--pc:[^"]+"><header><span class="pcode">(\w)</span>',
                      lambda m: m.group(0).replace('<section class="phase"', '<section class="phase" id="fl-%s"' % m.group(1), 1), frag)
        strip = ('<ol class="fl-path" aria-label="The %d stops from the call to the grade">' % len(stops) +
                 ''.join('<li style="--pc:%s"><a href="#fl-%s"><span class="fl-dot">%s</span><b>%s</b></a></li>'
                         % (c, k, SVG_ICONS.get(k, k), WORD.get(k, k)) for c, k in stops) + '</ol>')
        i = frag.find('<div class="fl">')
        i = i + len('<div class="fl">') if i >= 0 else frag.find('<section class="phase"')   # the path first, before the key and the building blocks
        frag = frag[:i] + strip + '\n  ' + frag[i:]
    frag = frag.replace("<div class=\"done\"><b>✓ Done</b>", "<div class=\"done\">" + DONE_ICON + "<b>Done</b>", 1)
    return frag


def build():
    frag = dword(io.open(SRC, encoding="utf-8").read())
    html = BR.page(TITLE, "", "ANEES-FLOW.fragment.html", "Claude", "2026-10-21", story=screen_roles(frag))
    html = html.replace('<link rel="stylesheet" href="../css/ai-reports.css?v=20261022-study">',
                        '<link rel="stylesheet" href="../css/ai-reports.css?v=20261022-study"><link rel="stylesheet" href="../css/dw-reports.css?v=2">')
    html = html.replace('<article class="ar-doc">\n\n</article>', "").replace('<div class="ab-sub">Built from ANEES-FLOW.fragment.html</div>', "").replace('‹ All AI reports</a>', '‹ Reports</a>')
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
