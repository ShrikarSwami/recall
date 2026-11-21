# Recall

Glasses for people living with dementia. Put them on like your everyday glasses, tap the side (or say
"Hey Recall") and ask "who is this?" or "where are we?". You get a calm, short answer in your ear and on
the lens. Built by **team BB** at the Worn Smart Glasses Hackathon (Nov 20–21, 2026) on MicroLumin M6 glasses.

**Start here:** [docs/SPEC.md](docs/SPEC.md) (the full plan) · [docs/TEAM_TEMPLATE.md](docs/TEAM_TEMPLATE.md) (fill this in on Discord)

## Status

Spec stage. Nothing runs yet. The layout:

| Folder | What goes here |
|---|---|
| `glasses-app/` | Kotlin app that runs on the glasses (Android 9, installed with `adb`) |
| `hub/` | Python server on the laptop: speech, faces, answers, voice |
| `caregiver-web/` | Phone page for the caregiver (rough first; the frontend devs polish it) |
| `knowledge/` | Everything the glasses know, in plain markdown. **Anyone can edit.** |
| `config/` | App name, patient, caregiver, model hosts. Copy `app.example.json` → `app.local.json`. |
| `faces/` | Enrollment photos. Local only, never committed. |

## ⚠️ Two rules

1. **Never commit the MicroLumin SDK kit** (`Microlumin_Ship/`). It's confidential and this repo is public. `.gitignore` blocks the usual paths; double-check `git status` before every push.
2. **No real personal data in git.** Phone numbers, keys and photos go in gitignored files (`config/app.local.json`, `.env`, `faces/`).

## Renaming

The product name, wake word and idle hint all come from `config/app.*.json` (`appName`, `wakeWord`,
`idleHint`). Change them there; never hard-code "Recall" in UI code.

## Open questions

- [ ] Does anyone on the team have an iPhone + Xcode? MLDemo (iOS) is the only way to turn on the glasses' Developer Mode.
- [ ] Do the M6's camera and mic work from a plain Android app via Camera2 / AudioRecord? Test Friday night with `adb`.
- [ ] Does the glasses' Android image include a TextToSpeech engine, or do we stream audio from the hub?
- [ ] Touchpad and ring key codes (`adb logcat` while pressing).
- [ ] Does venue Wi-Fi let the glasses reach the laptop (client isolation)? Fallback: phone hotspot.
- [ ] EnverThor Ollama: allow 2 loaded models (`OLLAMA_MAX_LOADED_MODELS=2`), or stick to one `qwen2.5vl:7b`?
