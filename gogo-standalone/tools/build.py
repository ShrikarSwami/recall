"""Put the baked squirrel sprites into the page.

    python build.py        # reads ../lucia-lens-preview.src.html + ../assets/*, writes ../lucia-lens-preview.html
"""
import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
src = open(os.path.join(ROOT, "lucia-lens-preview.src.html"), encoding="utf-8").read()
png = base64.b64encode(open(os.path.join(ROOT, "assets", "squirrel_sheet.png"), "rb").read()).decode()
mp = json.load(open(os.path.join(ROOT, "assets", "squirrel_sheet.json")))
data = 'window.SQ_SHEET="data:image/png;base64,%s";window.SQ_MAP=%s;' % (png, json.dumps(mp, separators=(",", ":")))
assert "/*__SQ_DATA__*/" in src
open(os.path.join(ROOT, "lucia-lens-preview.html"), "w", encoding="utf-8").write(src.replace("/*__SQ_DATA__*/", data))
print("built lucia-lens-preview.html (%d KB)" % (os.path.getsize(os.path.join(ROOT, "lucia-lens-preview.html")) // 1024))
