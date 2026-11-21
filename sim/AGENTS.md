# sim/: Go-go simulator (no glasses needed)

A browser page that shows the real `lens/index.html` at 640×480 with a fake status bar, green-waveguide and
see-through toggles, plus fake glasses inputs and the caregiver's phone.

## Run

- **Easiest:** double-click `sim/index.html` (works from `file://`).
- **Or serve the repo:** `python3 -m http.server 9200` from the repo root → http://localhost:9200/sim/
- **Or via the hub:** with the hub running, open http://localhost:9100/sim/

## Two modes

| Mode | Answers from | Needs |
|---|---|---|
| **Mock** (default) | `mock-brain.js` + `mock-kb.js` (generated from `knowledge/`) | nothing |
| **Live hub** | the real hub: real matching, local LLM for off-script questions, real voice on the glasses | a hub URL: `http://localhost:9100` if you run it, or Shrikar's Mac IP on the venue Wi-Fi, e.g. `http://10.3.194.140:9100` |

Refresh the mock knowledge after anyone edits `knowledge/`: `cd hub && uv run python -m lucia.export_kb`
(it writes `sim/mock-kb.json` and `sim/mock-kb.js`; commit both).

## Controls

| Control | Fakes |
|---|---|
| Tap temple (Enter/Space) | touchpad tap: starts listening for 8 s |
| Swipe ← / → (arrow keys), Back (Esc) | other touchpad gestures (no action yet) |
| Put glasses on | off-body sensor → greeting |
| Someone walks in / Stranger walks in | the camera recognising a teammate / an unknown face |
| Say box + question chips | the mic. Start with "Go-go, …" (wake word) or tap first. Chips = every question in the knowledge base. |
| Force a screen state | listening, thinking, clear, disconnected, distress, unknown person, long answer |
| Caregiver phone | shows the iMessage the caregiver would get (distress only) |

## Files

- `index.html`, `sim.css`, `sim.js`: the simulator shell (modern browsers only; not shipped to the glasses).
- `mock-brain.js`: offline copy of the hub's answer logic. Keep its behaviour roughly in sync with
  `hub/lucia/brain.py` (same intents, same wording rules), but it doesn't need to be perfect.
- `mock-kb.js` / `mock-kb.json`: generated, don't hand-edit.
