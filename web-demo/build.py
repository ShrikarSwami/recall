"""Assemble the static web demo (lens + caregiver page + prepared answers) into web-demo/dist/.

    python3 web-demo/build.py          # then: npx vercel deploy web-demo/dist --prod

Only public, already-committed files are copied: lens/, sim/mock-brain.js + mock-kb.js (generated from
knowledge/), the caregiver dashboard and its demo data. Never faces/, config/*.local.*, hub/data/.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web-demo"
OUT = SRC / "dist"

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
for f in ("index.html", "demo.js", "demo.css", "mock-api.js"):
    shutil.copy(SRC / f, OUT / f)
shutil.copytree(ROOT / "lens", OUT / "lens", ignore=shutil.ignore_patterns("AGENTS.md"))
(OUT / "brain").mkdir()
for f in ("mock-brain.js", "mock-kb.js"):
    shutil.copy(ROOT / "sim" / f, OUT / "brain" / f)
shutil.copy(ROOT / "gogo-standalone" / "care" / "data.json", OUT / "data.json")

care = (ROOT / "gogo-standalone" / "dashboard" / "index.html").read_text(encoding="utf-8")
care = care.replace("<script>", '<script src="../mock-api.js"></script>\n<script>', 1)
care = care.replace('href="../glasses/sim/index.html"', 'href="../" target="_top"').replace(
    "Open the glasses simulator", "Back to the demo")
(OUT / "caregiver").mkdir()
(OUT / "caregiver" / "index.html").write_text(care, encoding="utf-8")
(OUT / "vercel.json").write_text('{ "cleanUrls": true, "trailingSlash": true }\n')

for bad in ("faces", "app.local", "api_token", "events.jsonl", "recordings"):
    assert not list(OUT.rglob(f"*{bad}*")), bad
print("built", OUT, sum(1 for _ in OUT.rglob("*") if _.is_file()), "files")
