# Gogo standalone (Sid)

Self-contained version of the Gogo guided flow. Does not use the Go-go hub.

- `gogo/` Python server (FastAPI): `main.py` (lens + glasses sockets, care API), `flow.py` (guided flow), `tts.py` (voice for the glasses). `pip install -r gogo/requirements.txt`, then `python gogo/main.py --port 9310`. See `gogo/README.md`.
- `glasses/lens/` the lens (the same files are in the repo's top-level `lens/`), `glasses/sim/` the simulator, `glasses/STAMP_SPEC.md` stamp spec.
- `care/` + `dashboard/` care data, weather, events and the family dashboard. `tools/` sprite/model/stamp builders and the Chromium 74 test driver. `assets/` the squirrel model and sheets.
- Stamp art import: `python tools/import_stamps.py <gogo-stamps folder>`.
