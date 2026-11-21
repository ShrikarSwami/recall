"""Import the Gemini stamp art (gogo-stamps/art/s-<id>.svg) into the lens as <symbol id="s-<id>"> blocks.

    python tools/import_stamps.py "<path to gogo-stamps>" [--lens glasses/lens/index.html]

Checks every file against STAMP_SPEC.md (allowed shapes, class-only colours, size), strips metadata,
and replaces the old s-* symbols in the lens page. Prints what it did.
"""
import glob
import os
import re
import sys

ALLOWED_TAGS = {"path", "circle", "ellipse", "rect"}
ALLOWED_CLASSES = {"k1", "k2", "k3", "k4", "kl", "kl4"}


def clean(svg):
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg, flags=re.S)
    m = re.search(r"<svg\b[^>]*>(.*)</svg>", svg, flags=re.S)
    body = m.group(1).strip()
    body = re.sub(r"></(path|circle|ellipse|rect)>", "/>", body)          # <path ...></path> -> <path .../>
    return re.sub(r">\s+<", "><", body)


def check(name, body):
    problems = []
    tags = re.findall(r"<([a-zA-Z0-9]+)\b", body)
    for t in set(tags) - ALLOWED_TAGS:
        problems.append("tag <%s>" % t)
    for c in re.findall(r'class="([^"]*)"', body):
        if set(c.split()) - ALLOWED_CLASSES:
            problems.append("class %s" % c)
    for bad in ("style=", "opacity", "gradient", "filter", "<text"):
        if bad in body:
            problems.append(bad)
    if len(tags) > 30:
        problems.append("%d shapes" % len(tags))
    if len(body) > 2600:
        problems.append("%d bytes" % len(body))
    return problems, len(tags)


def main():
    src = sys.argv[1]
    lens = "glasses/lens/index.html"
    if "--lens" in sys.argv:
        lens = sys.argv[sys.argv.index("--lens") + 1]
    symbols, report = [], []
    for f in sorted(glob.glob(os.path.join(src, "art", "s-*.svg"))):
        sid = os.path.basename(f)[:-4]
        body = clean(open(f, encoding="utf-8").read())
        problems, n = check(sid, body)
        report.append((sid, n, len(body), problems))
        symbols.append('    <symbol id="%s" viewBox="0 0 70 70">%s</symbol>' % (sid, body))
    html = open(lens, encoding="utf-8").read()
    html, removed = re.subn(r'[ \t]*<symbol id="s-[^"]*"[^>]*>.*?</symbol>\s*', "", html, flags=re.S)
    marker = html.index('<symbol id="i-shield"')
    marker = html.rindex("\n", 0, marker) + 1
    html = html[:marker] + "\n".join(symbols) + "\n" + html[marker:]
    open(lens, "w", encoding="utf-8").write(html)
    print("replaced %d old stamp symbols with %d new ones" % (removed, len(symbols)))
    for sid, n, size, problems in report:
        print("%-18s %2d shapes %5d B %s" % (sid, n, size, ("PROBLEMS: " + ", ".join(problems)) if problems else "ok"))


main()
