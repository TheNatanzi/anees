# -*- coding: utf-8 -*-
"""Word Bank clips with only one voice (word-bank-clips.json partial_coverage) re-cut from the lesson's full mix
(docs/lessons/<date>/audio/lesson.mp3, both voices - see remix_lesson_audio.py). Same file name and time window, so
every page that links the clip keeps working. Medi 2026-09-26: "for these clips we need the conversation with both of us".

    python scripts/recut_partial_word_clips.py
"""
import hashlib, json, os, subprocess
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(REPO, "docs", "data", "word-bank-clips.json")


def main():
    D = json.load(open(P, encoding="utf-8"))
    done, skipped, cut = 0, [], {}
    for c in D["clips"].values():
        if not c.get("partial_coverage"):
            continue
        src = os.path.join(REPO, "docs", "lessons", c["lesson"], "audio", "lesson.mp3")
        out = os.path.join(REPO, "docs", c["sentence_audio_url"])
        if not os.path.exists(src):
            skipped.append(c["event_id"]); continue
        if out not in cut:                     # several events can share one clip file
            tmp = out + ".part.mp3"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["start"]), "-i", src, "-t", str(c["end"] - c["start"]),
                            "-ar", "16000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "48k", tmp], check=True)
            os.replace(tmp, out)
            cut[out] = hashlib.sha256(open(out, "rb").read()).hexdigest()
        c.update(clip_sha256=cut[out], speakers=["Mixed"], partial_coverage=False, recut_from="lesson.mp3 (all recordings)")
        done += 1
    open(P, "w", encoding="utf-8").write(json.dumps(D, ensure_ascii=False, indent=2) + "\n")
    print("re-cut", done, "events,", len(cut), "files; skipped (no lesson.mp3):", len(skipped))


if __name__ == "__main__":
    main()
