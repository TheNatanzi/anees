# -*- coding: utf-8 -*-
"""Deploy the note reader's Supabase Edge Function (supabase/functions/parse-correction: index.ts + prompt.ts) to the Anees
project, so the page's instant read of Medi's notes uses the same prompt as the hourly job (TR-30, Medi 2026-10-10
"deploy"). Rebuilds prompt.ts from scripts/correction_parse_prompt.md first. Keeps the function's current JWT setting.

    python scripts/deploy_parse_correction.py            # deploy and print the new version
    python scripts/deploy_parse_correction.py --dry-run  # show what would be sent
"""
import json, os, subprocess, sys
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import anees_env as E  # noqa: E402

SLUG = "parse-correction"
DIR = os.path.join(REPO, "supabase", "functions", SLUG)
API = "https://api.supabase.com/v1/projects/%s/functions" % E.SUPABASE_REF


def main():
    dry = "--dry-run" in sys.argv
    subprocess.run([sys.executable, os.path.join(HERE, "correction_parse.py"), "build-prompt"], check=True, cwd=REPO)
    h = {"Authorization": "Bearer " + E.ACCESS_TOKEN}
    cur = requests.get("%s/%s" % (API, SLUG), headers=h, timeout=30).json()
    meta = {"name": SLUG, "entrypoint_path": "index.ts", "verify_jwt": bool(cur.get("verify_jwt"))}
    names = ["index.ts", "prompt.ts"]
    print("now: version %s (%s), verify_jwt %s; sending %s" % (cur.get("version"), cur.get("status"), meta["verify_jwt"], names))
    if dry:
        return 0
    files = [("file", (n, open(os.path.join(DIR, n), "rb").read(), "application/typescript")) for n in names]
    r = requests.post("%s/deploy?slug=%s" % (API, SLUG), headers=h, files=files, data={"metadata": json.dumps(meta)}, timeout=180)
    if r.status_code >= 300:
        print("deploy failed: %s %s" % (r.status_code, r.text[:300]))
        return 1
    new = requests.get("%s/%s" % (API, SLUG), headers=h, timeout=30).json()
    print("deployed: version %s (%s)" % (new.get("version"), new.get("status")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
