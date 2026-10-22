# -*- coding: utf-8 -*-
"""PG-56 - the whole Anees process as one flowchart page in AI Reports (Medi 2026-10-21: "add the flowchart to the ai
reports", after "Give me a full flowchart of our entire process start to finish (see coinbase onboarding)").

The flowchart's text is plan/ANEES-FLOW.fragment.html (phases A-G, numbered steps, decision diamonds, who / cost chips);
this wraps it in the AI Reports page shell (scripts/build_ai_reports.page) as docs/reports/anees-flow.html. Its look is
css/ai-reports.css .fl-* in the app's own colours, so it follows Light / Dark like every page.

    python scripts/build_flow_page.py
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_ai_reports as BR  # noqa: E402

SRC = os.path.join(REPO, "plan", "ANEES-FLOW.fragment.html")
OUT = os.path.join(REPO, "docs", "reports", "anees-flow.html")
TITLE = "Anees: from lesson to grade"


def build():
    frag = io.open(SRC, encoding="utf-8").read()
    html = BR.page(TITLE, "", "ANEES-FLOW.fragment.html", "Claude", "2026-10-21", story=frag)
    html = html.replace('<article class="ar-doc">\n\n</article>', "")
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("built", os.path.relpath(OUT, REPO), "%d KB" % (len(html) // 1024))
    for out, title, body in STUDIES:
        p = os.path.join(REPO, "docs", "reports", out)
        io.open(p, "w", encoding="utf-8").write(BR.page(title, body, out, "Claude", "2026-10-21"))
        print("built", out)
    return OUT


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
