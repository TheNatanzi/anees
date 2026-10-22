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
    return OUT


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
