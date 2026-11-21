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
| `speech.py` | VAD segmentation, mlx-whisper STT (~120–180 ms), fuzzy "Lucia" wake word, macOS `say` → PCM for the glasses speaker (the glasses have no TTS engine) |
| `faces.py` | `face_id` (ArcFace/MobileFaceNet ONNX, ~9 ms/frame on the Mac); enrolls `faces/<person_id>/*.jpg` |
| `alerts.py` | Caregiver iMessage through the Mac's Messages app (`osascript`), rate-limited |
| `export_kb.py` | Knowledge → JSON for the simulator (always uses `app.example.json`, never the private config) |

## Testing without glasses

```bash
curl -XPOST localhost:9100/api/ask -H 'content-type: application/json' -d '{"text":"where are we?"}'
```
Or use the simulator in **Live hub** mode.

## Rules

- Answers about people and places come **only** from `knowledge/`. The LLM may *choose* between stored answers,
  describe the scene, or answer general off-script questions. It never invents facts about the patient or people.
- Anything user-facing must read names from config (`placeholders()` in `config.py`).
- Add a test in `tests/` for any change to `brain.py`, `matcher.py` or `knowledge.py`.
