# AGENTS.md: read this first (for coding agents and humans)

You're working on **Lucia** (repo: `recall`): smart glasses for people living with dementia, built by
team **BB** (Shrikar, Abhiram, Isha, Sid) at the Worn hackathon on MicroLumin M6 glasses.
**Code freeze: Saturday Nov 21, 2:00 PM ET.** Prefer small, working changes over big rewrites.

The wearer puts the glasses on, says **"Lucia, who is this?"** (or taps the temple), and hears a calm,
short answer while it appears on the lens.

## The one design rule

**The patient forgets how to use the app every few minutes.** Every screen must be obvious to someone
seeing it for the first time, every time:
- One pinned instruction, always visible: `Say "Lucia" or hold right side` (bottom-left of the lens).
- No menus, modes, settings, gestures to learn, or "as I said before". Same question → same answer.
- At most **3 short lines** on the lens; 1–2 spoken sentences. Never contradict or quiz the patient.
- No medical advice. Only distress ("I want to go home", "I'm scared") texts the caregiver.

## Map

| Folder | What | Read |
|---|---|---|
| `lens/` | **The UI on the glasses** (HTML/CSS/JS, 640×480). Frontend devs own this. | `lens/AGENTS.md` |
| `sim/` | Browser simulator: the lens + fake glasses controls + caregiver phone. No hardware needed. | `sim/AGENTS.md` |
| `caregiver-web/` | Caregiver phone page (alerts, what was asked) | `caregiver-web/AGENTS.md` |
| `hub/` | Python server on the Mac: speech-to-text, faces, answers, voice, alerts | `hub/AGENTS.md` |
| `glasses-app/` | Thin Android 9 app: camera/mic/keys → hub, shows `lens/` in a WebView | `glasses-app/AGENTS.md` |
| `knowledge/` | Everything Lucia knows, in markdown Q&A. **Anyone can edit.** | `knowledge/AGENTS.md` |
| `config/` | App name, wake word, patient, caregiver, model hosts | `config/app.example.json` |
| `docs/` | `SPEC.md` (full plan), **`HARDWARE.md` (measured M6 facts: keys, sensors, camera)**, `CHATGPT_KB_PROMPT.md` | |

## Quick start by role

- **Frontend (no glasses needed):** open `sim/index.html` in a browser (double-click works). Edit `lens/`
  and reload. Details: `sim/AGENTS.md`.
- **Backend:** `cd hub && uv sync && uv run pytest -q && uv run python -m lucia.server` (Mac, Apple Silicon).
  No glasses? `uv run python tools/replay_glasses.py --say "Lucia, who is this?"` acts as them.
- **Content:** fill in `knowledge/people/<your-name>.md`, then run `cd hub && uv run python -m lucia.export_kb`
  so the simulator picks it up.

## Hard rules (break these and we lose the demo or leak data)

1. **Never commit the MicroLumin SDK kit** (`Microlumin_Ship/`, `*.aar`, `sdkappkey.jks`). It's confidential and
   this repo is public. Check `git status` before every commit.
2. **No private data in git:** `config/app.local.json`, `.env`, `faces/` photos, `hub/data/` logs are gitignored.
   Keep them that way. Real phone numbers only go in `config/app.local.json`.
3. **Never hard-code "Lucia", the patient's or caregiver's name** in UI or code. They come from config
   (`appName`, `wakeWord`, `idleHint`, `patient`, `caregiver`) and may change (e.g. to a judge's name).
4. **The lens runs in Chrome 74** (Android 9 WebView). No `?.`, no `??`, no flexbox `gap`, no build step
   required. See `lens/AGENTS.md`.
5. **Ports:** the hub uses **9100**. Don't use 8765 (Shrikar's other project) or 8770 (macOS uses it).
6. **Git:** work on a branch named `<your-name>/<thing>`, open a PR to `main`, keep PRs small. Pull before you
   start. Don't force-push `main`.

## If you are a coding agent helping a teammate

Before finishing your first task, check `knowledge/people/<their-first-name>.md`. If its `A:` lines are mostly
blank, **ask your human to answer them** (a few at a time, in chat), write their answers into the file, then run
`cd hub && uv run python -m lucia.export_kb`. Judges will ask Lucia about every teammate, so every answer counts.
Keep answers to 1–2 short, warm sentences. Don't invent facts about anyone.
