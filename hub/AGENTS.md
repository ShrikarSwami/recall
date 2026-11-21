# hub/: the brain (Python, runs on a Mac with Apple Silicon)

```bash
cd hub
uv sync                                  # first time
uv run pytest -q                         # 30+ tests, no hardware or network needed
LUCIA_DRY_RUN=1 uv run python -m lucia.server   # http://localhost:9100 (sim at /sim/, caregiver at /caregiver)
uv run python -m lucia.export_kb         # refresh sim/mock-kb.* after editing knowledge/
```

`LUCIA_DRY_RUN=1` logs caregiver iMessages instead of sending them. Leave it on unless you're demoing.
Face recognition needs `vendor/face_id` (gitignored): `git clone https://github.com/ShrikarSwami/face_id ../vendor/face_id`
plus its `buffalo_sc` weights (see `vendor/face_id/models/README.md`).

## Modules (`lucia/`)

| File | Job |
|---|---|
| `server.py` | FastAPI app on port **9100**: `/ws/glasses` (the app: mic, camera, keys, audio out), `/ws/lens` (display), `/ws/caregiver`, `/api/ask`, `/api/say`, `/api/state`, `/api/kb`, `/api/reload`, `/api/patient` |
| `brain.py` | Decides the answer: distress → time → who-is-this (faces) → scene (vision model) → knowledge base → LLM for off-script → gentle "not sure". **Pure logic, unit-tested.** |
| `matcher.py` | Fuzzy-matches questions to `knowledge/` entries; "he/she/they" resolve to whoever is in view or was just discussed |
| `knowledge.py` | Parses `knowledge/*.md` (see `knowledge/AGENTS.md`) |
| `llm.py` | Ollama: EnverThor (`qwen2.5vl:7b` over Tailscale) first, local Mac second, hard timeouts |
| `speech.py` | VAD segmentation, mlx-whisper STT (~120–180 ms), fuzzy "Go-go" wake word, macOS `say` → PCM for the glasses speaker (the glasses have no TTS engine) |
| `faces.py` | `face_id` (ArcFace/MobileFaceNet ONNX, ~9 ms/frame on the Mac); enrolls `faces/<person_id>/*.jpg` |
| `alerts.py` | Caregiver iMessage through the Mac's Messages app (`osascript`), rate-limited |
| `schedule.py` | `knowledge/schedule.md` → "what's next", "when is lunch", 15-min heads-ups, next item in the greeting |
| `reminders.py` | `config/reminders.local.md` (private) / `.example.md`: read once on arrival via `POST /api/place` (iPhone Shortcut, `docs/SHORTCUT_API.md`) |
| `export_kb.py` | Knowledge → JSON for the simulator (always uses `app.example.json`, never the private config) |

## Testing without glasses

Fake glasses (same protocol as the real app; see `docs/HARDWARE.md` for the measured key codes):
```bash
uv run python tools/replay_glasses.py --say "Go-go, who is this?" --frame ../faces/sid/IMG_3167.jpg
uv run python tools/replay_glasses.py --key tap --say "where are we"
uv run python tools/replay_glasses.py --recording data/recordings/voice_wearer   # a real capture
```
Record more real data when the glasses are around: `uv run python tools/capture_session.py` (Go-go speaks each step).


```bash
curl -XPOST localhost:9100/api/ask -H 'content-type: application/json' -d '{"text":"where are we?"}'
```
Or use the simulator in **Live hub** mode.

The hub quietly prewarms the greeting, teammate intros and common orientation speech at startup,
after `/api/reload`, and after `/api/patient` changes the name. `/api/state` includes `voice_warmup`
(`warming`, `ready`, `partial`, or `disabled`, with clip counts). No audio plays during warmup.
Only exact text is cached; changed place/schedule wording can still need a first render. A partial
warmup does not prevent startup; check that macOS `say` produces audio before the demo.
Caregiver alerts use the existing iMessage path, adding the Mac's local time and either the fresh
phone-reported place or the configured demo place, e.g. `Go-go: … · 1:40 AM · City Tech, Downtown Brooklyn`. `LUCIA_DRY_RUN=1` never sends a text.

## Rules

- Write endpoints (`/api/place`, `/api/say`, `/api/ask`, `/api/record`, `/api/reload`, `/api/patient`) are open to this Mac but need `X-Lucia-Token` (= `apiToken` in `config/app.local.json`) from anywhere else.

- Answers about people and places come **only** from `knowledge/`. The LLM may *choose* between stored answers,
  describe the scene, or answer general off-script questions. It never invents facts about the patient or people.
- Anything user-facing must read names from config (`placeholders()` in `config.py`).
- Add a test in `tests/` for any change to `brain.py`, `matcher.py` or `knowledge.py`.
