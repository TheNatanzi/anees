# -*- coding: utf-8 -*-
"""PG-33 (Medi 2026-10-07): on screen the tutor is "Tutor" and the student is "Student".

Scans what a viewer can read - text nodes and visible attributes in docs/*.html and docs/amal/*.html, and string
literals in docs/js/**/*.js (plus inline <script> blocks) - for the bare words "Amal" and "Medi".
Internal names are not looked at: comments, object keys, values compared in code, URLs and file names.
Words really written (a dated attribution, Arabic examples built on a name) are allowed only through ALLOW below.
A literal that is exactly a name ('Amal', 'Medi') is a data value (a speaker key); a page that shows one maps it at display.

    python scripts/screen_names.py          # list every hit (file:line  text)
"""
import glob, os, re, sys
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = re.compile(r"\b(Amal|Medi)\b")
VISIBLE_ATTRS = {"title", "placeholder", "aria-label", "alt", "data-tip"}

# Explicit allow-list: (file relative to docs/ or "*", a regex the literal / text must match). Keep it short; say why.
ALLOW = [
    ("*", r"\b(Amal|Medi),? 20\d\d-\d\d-\d\d"),         # a dated attribution, e.g. (Medi, 2026-09-05) / Added by Medi 2026-09-25
    ("amal/grammar-rules.html",                         # Arabic grammar examples built on a proper name (bait Medi = Medi's house)
     r"(el-)?(bab )?bait Medi|sayyaaret Medi|(the door of )?Medi's (house|car)"),
]


def _is_internal(s):
    """A literal that is code, not words: exactly a name used as a data value, a query, a URL or a file name."""
    t = s.strip()
    if t in ("Amal", "Medi"):
        return True                       # a speaker value stored or passed along; labels are mapped at display
    if re.search(r"(=eq\.|=)(Amal|Medi)\b", t) and "select=" in t:
        return True                       # a database query
    if re.fullmatch(r"[\w./:#?=&%-]+\.(html|json|js|css|mp3|m4a|webm|md)([?#][\w=&%.-]*)?", t):
        return True
    if t.startswith(("http://", "https://")):
        return True
    return False


def js_literals(src):
    """Yield (line, text, start, end, ctx) for every string literal / template-text part in JS source, skipping
    comments and regexes. start/end are offsets of the raw body in src; ctx is 'key' (an object key), 'cmp' (compared
    with == / === / != / !== or a case label) or None."""
    i, n, line = 0, len(src), 1
    prev, prev_word = "", ""               # last significant token (regex detection, key/comparison context)
    stack, depth = [], 0                   # template nesting: brace depth at each ${
    ws = " \t\r\n"

    def ctx_of(before, before_word, open_at, j):
        k = j
        while k < n and src[k] in ws:
            k += 1
        nxt = src[k:k + 3]
        if nxt[:1] == ":" and before in ("{", ","):
            return "key"
        if before_word == "case":
            return "cmp"
        b = src[max(0, open_at - 4):open_at].rstrip()
        if b.endswith(("==", "!=")) or nxt.startswith(("==", "!=")):
            return "cmp"
        return None

    while i < n:
        c = src[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c in " \t\r":
            i += 1; continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += src.count("\n", i, j); i = j
            continue
        if c == "/" and (prev == "" or prev in "(,=:[!&|?{};+-*%<>~^" or prev_word in ("return", "typeof", "case", "in", "of")):
            j, cls = i + 1, False                      # regex literal
            while j < n and src[j] != "\n":
                if src[j] == "\\": j += 2; continue
                if src[j] == "[": cls = True
                elif src[j] == "]": cls = False
                elif src[j] == "/" and not cls: break
                j += 1
            i = j + 1
            while i < n and src[i].isalpha(): i += 1
            prev, prev_word = ")", ""
            continue
        if c in "'\"":
            j, buf, start = i + 1, [], line
            while j < n and src[j] != c:
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1]); j += 2; continue
                if src[j] == "\n": line += 1
                buf.append(src[j]); j += 1
            yield start, "".join(buf), i + 1, j, ctx_of(prev, prev_word, i, j + 1)
            i = j + 1; prev, prev_word = '"', ""
            continue
        if c == "`" or (c == "}" and stack and stack[-1] == depth):
            if c == "}":
                stack.pop()
            j, buf, start = i + 1, [], line
            while j < n:
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1]); j += 2; continue
                if src[j] == "`" or (src[j] == "$" and j + 1 < n and src[j + 1] == "{"):
                    break
                if src[j] == "\n": line += 1
                buf.append(src[j]); j += 1
            if "".join(buf).strip():
                yield start, "".join(buf), i + 1, j, None
            if j < n and src[j] == "$":
                stack.append(depth); i = j + 2; prev, prev_word = "{", ""
            else:
                i = j + 1; prev, prev_word = '"', ""
            continue
        if c == "{": depth += 1
        elif c == "}": depth -= 1
        if c.isalnum() or c in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"): j += 1
            prev_word, prev = src[i:j], "a"; i = j
            continue
        prev, prev_word = c, ""
        i += 1


def js_strings(src):
    """(line, text) for every literal a viewer could read: object keys and compared values are code, not words."""
    return [(ln, t) for ln, t, _a, _b, ctx in js_literals(src) if ctx is None]


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.script = [], 0, None

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in VISIBLE_ATTRS and v:
                self.out.append((self.getpos()[0], v))
        if tag == "style":
            self.skip += 1
        if tag == "script":
            self.script = (self.getpos()[0], [])
            if any(k == "type" and v and "json" in v for k, v in attrs):
                self.script = None; self.skip += 1

    def handle_endtag(self, tag):
        if tag == "style" and self.skip:
            self.skip -= 1
        if tag == "script":
            if self.script:
                base, parts = self.script
                for ln, s in js_strings("".join(parts)):
                    self.out.append((base + ln - 1, s))
                self.script = None
            elif self.skip:
                self.skip -= 1

    def handle_data(self, data):
        if self.script is not None:
            self.script[1].append(data); return
        if not self.skip and data.strip():
            self.out.append((self.getpos()[0], data))


def visible_texts(path):
    src = open(path, encoding="utf-8").read()
    if path.endswith(".js"):
        return js_strings(src)
    p = _Page(); p.feed(src); p.close()
    return p.out


def files():
    d = os.path.join(REPO, "docs")
    out = glob.glob(os.path.join(d, "*.html")) + glob.glob(os.path.join(d, "amal", "*.html"))
    out += glob.glob(os.path.join(d, "js", "**", "*.js"), recursive=True)
    return sorted(out)


def strip_allowed(rel, text):
    """The text with every allow-listed part cut out (the rest must still be name-free)."""
    for f, rx in ALLOW:
        if f == "*" or f == rel:
            text = re.sub(rx, " ", text)
    return text


def hits():
    found = []
    for path in files():
        rel = os.path.relpath(path, os.path.join(REPO, "docs")).replace("\\", "/")
        for ln, text in visible_texts(path):
            if not NAME.search(text) or _is_internal(text) or not NAME.search(strip_allowed(rel, text)):
                continue
            found.append((rel, ln, text.strip()))
    return found


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    h = hits()
    for rel, ln, text in h:
        print(f"{rel}:{ln}  {text[:160]!r}")
    print(f"{len(h)} hit(s)")
