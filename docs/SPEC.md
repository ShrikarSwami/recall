# Recall: spec

> The assistant is called **Lucia**, and "Lucia" is also the wake word. The repo is `recall`. Both names live in `config/app.example.json` (`appName`, `wakeWord`, `idleHint`); never hard-code them.
> Team **BB** · Worn Smart Glasses Hackathon · Nov 20–21, 2026 · City Tech, Brooklyn · Track: **Natural Interaction**
> Status: draft v0.1 (Fri Nov 20). Open questions are at the bottom; edit freely.

> For a code-checked snapshot of implemented features, published content, and suggested next work, see [Content handoff and next steps](AGENT_HANDOFF.md) (reviewed Nov 21).

## 1. One-liner

A pair of glasses that a person living with dementia can put on like their everyday glasses. They ask "who is this?" or "where are we?" out loud, and get a calm, short, correct answer in their ear and on the lens. Nothing to learn, nothing to remember, and no patient data leaves their own devices.

## 2. The rule that decides every design choice

From judge D.J. Patel: **treat every single session as a brand-new user.** People living with dementia won't remember a tutorial, a menu or a gesture they learned yesterday. So:

- **One visible affordance, always on screen:** `Say "Lucia" or hold right side` (pinned in a corner of the lens at all times). Nothing else to discover.
- **No modes, no menus, no settings on the glasses.** All configuration happens on the caregiver's phone.
- **Every answer stands alone.** It never says "as I said before". Asking the same question ten times gets the same patient answer ten times.
- **Never contradict, never correct, never quiz.** "Somya, this is Dev. He's on your hackathon team," not "You should remember Dev."
- **Short.** At most 2 lines on the lens and 1–2 sentences spoken.
- **Fail gently.** "I'm not sure. Shrikar can help, I've let him know," never an error message.

## 3. Demo story (3 minutes)

The judge plays **Somya Gupta** (default patient, set in config). If we get the judge's own name in time, we swap it in so the glasses greet them personally; that's one config field. Somya is **he/him**.

1. The judge puts the glasses on. The lens shows `Say "Lucia" or hold right side` (pinned in a corner of the lens at all times) and a soft greeting: "Hi Somya. You're at City Tech in Brooklyn."
2. A teammate walks up. **Unprompted**, the lens shows `DEV · on your team` and the glasses say "This is Dev, he's on your team." *(proactive face intro, the wow moment)*
3. The judge taps and asks "Who is this?", then "Where's he from?", then "What does he do?" Each answer comes from the facts Dev filled in.
4. "Where are we?" → "You're at City Tech in Downtown Brooklyn, at a smart-glasses hackathon with your team."
5. "What day is it?" → "It's Saturday, November 21st. It's about 2 in the afternoon."
6. The judge asks "who is this?" again about the same person, on purpose. Same calm answer, no "I already told you". The caregiver page shows "Asked about Dev 2× in 5 min."
7. The judge says "I want to go home." → "You're safe, Somya. Shrikar knows where you are. I'm letting him know now." The caregiver gets a real iMessage, sent from the hub Mac. *(safety moment)*
8. We close on the caregiver phone: who he met, what he asked, all stored only on his devices.

## 4. Features and priority

| P | Feature | Notes |
|---|---|---|
| **P0** | Always-on idle hint on lens | `Say "Lucia" or hold right side` (pinned in a corner of the lens at all times) plus the time. Must survive app restarts. |
| **P0** | Tap-to-ask (temple touchpad / ring) | Most reliable trigger in a loud venue. Key codes: find them with `adb logcat`. |
| **P0** | Answer = voice + short text | Both on by default; each toggled in config. |
| **P0** | "Who is this?" via camera + face recognition | Uses [`face_id`](https://github.com/ShrikarSwami/face_id) (detect → align → ArcFace/MobileFaceNet embed → cosine match). |
| **P0** | Knowledge-base Q&A | Questions map to answers written in `knowledge/*.md`. Paraphrases map to the same answer. |
| **P0** | Where am I / what day / what time | Where comes from a preloaded place (demo data). Date and time come from the clock. |
| **P0** | Wake word "Lucia" | No custom wake-word model: the hub runs VAD + streaming STT and triggers when the transcript starts with the wake word, so renaming still works. The tap always works as a fallback. |
| **P1** | Proactive face intro | When an enrolled face is seen, introduce them once. Cooldown per person (default 120 s). |
| **P1** | Follow-up questions about the person in view | "Where's he from?" resolves "he" to the last recognised person. |
| **P1** | Caregiver phone page | Live feed of questions, repeat counts, alerts, add/edit people and facts. |
| **P1** | Distress / "I want to go home" handling | Reassure, plus a real iMessage to the caregiver (macOS Messages via `osascript`) and an alert on the caregiver page. |
| **P2** | Unknown face | "I don't think we've met them yet. You can ask their name." Never guess. |
| **P2** | "What was I doing?" | Answer from today's log, e.g. "You just met Dev and Ana." |
| **P2** | Scene description | VLM describes the room when there's no KB answer: "It looks like a classroom full of people with laptops." |
| **P2** | Judge-name swap | Set the patient name from the caregiver page in 10 seconds. |

## 5. What questions must work

Questions are **intents**. Any phrasing that means the same thing hits the same answer. The small local model only does two jobs: (1) map the utterance to `{intent, subject}`, and (2) lightly rephrase the KB answer so it sounds natural. **It never invents facts.** If the KB has no answer, we say so gently.

| Intent | Example phrasings | Source |
|---|---|---|
| `who_is_this` | who is this / who's that / do I know him / who am I talking to | camera → face → `knowledge/people/<id>.md` |
| `person_fact` | where's he from / what does she do / how do I know him / is he married | last recognised person + their facts |
| `where_am_i` | where are we / where am I / what is this place | `knowledge/places.md` → `currentPlace` |
| `what_time` | what day is it / what time is it / what's the date | clock |
| `who_am_i` | what's my name / who am I | `knowledge/patient.md` |
| `my_people` | who's my caregiver / who's taking care of me / call my grandson | `knowledge/patient.md` + config caregiver |
| `what_doing` | what am I doing here / why am I here / what was I doing | `knowledge/places.md` plus today's log |
| `distress` | I want to go home / I'm scared / where is everyone / I'm lost | fixed calm script + caregiver alert |
| `faq` | anything written in `knowledge/faq.md` | the Q/A pairs |
| `unknown` | — | "I'm not sure about that. Shrikar can help." (logged for the caregiver) |

## 6. Architecture

```
┌──────────── M6 glasses (Android 9, plain APK, no glasses SDK needed) ────────────┐
│ glasses-app/  Kotlin                                                              │
│  • full-screen black UI: idle hint, answer card (≤2 lines), "listening…" state    │
│  • Camera → JPEG frame every ~1 s (and on request)     ─┐                         │
│  • AudioRecord 16 kHz mono → PCM stream                 ├─ WebSocket over Wi-Fi ─┐│
│  • touchpad / ring key events                           ─┘                       ││
│  • plays answer audio (PCM from hub) or Android TextToSpeech if present          ││
└──────────────────────────────────────────────────────────────────────────────────┘│
                                                                                    ▼
┌──────────── hub/ on the MacBook (stands in for "the patient's phone") ───────────────┐
│ FastAPI + WebSocket                                                                  │
│  • "Lucia" wake word = VAD (Silero) + STT, trigger on the name in the transcript     │
│  • STT: mlx-whisper on the Mac (small.en 183 ms; large-v3-turbo 506 ms)               │
│  • face_id on the Mac: ~9 ms/frame (8.6 ms detect + 0.6 ms embed, CoreML)            │
│  • intent router: small LLM → {intent, subject}; answer from knowledge/ (grounded)    │
│  • TTS: Piper / macOS `say` → audio back to glasses                                  │
│  • event log (SQLite, local) → caregiver page                                        │
│  • serves caregiver-web/                                                             │
└───────────────┬──────────────────────────────────────────────┬───────────────────────┘
                │ Tailscale, ~80 ms RTT                        │ same Wi-Fi
                ▼                                              ▼
   EnverThor (NVIDIA Thor, 122 GB)                     caregiver phone (browser)
   Ollama: qwen2.5vl:7b (text + vision)                caregiver-web/: feed, alerts,
   fallback: local Ollama on the Mac                   people + facts editor
```

**Why the glasses app is a plain APK:** the kit says glasses apps are ordinary Android 9 apps installed with `adb`. The glasses-side SDK libraries aren't in the kit. So we use Android's own Camera2, AudioRecord and KeyEvent and talk to the hub over Wi-Fi. The phone-side SDK (BLE) isn't needed for the core loop.

**Model plan (measured Fri 8:40 PM, from the Mac over Tailscale):**

| Model on EnverThor | Cold (swap in) | Warm, ~20-token answer |
|---|---|---|
| `qwen2.5:14b` | ~6 s | ~2.0 s (19 tok/s) |
| `qwen2.5vl:7b` | ~6 s | ~1 s (32 tok/s) |

EnverThor's Ollama keeps **one model loaded at a time**: switching models costs ~5 s. So **use one model for everything: `qwen2.5vl:7b`** (text + vision), with `keep_alive` long, and warm it at startup. If a call exceeds `fallbackAfterMs` (2.5 s), the hub answers from the KB template directly with no rephrasing. That fallback is always correct, just less chatty. A local Mac model is the last resort.

**Where each piece runs (fastest wins; measured Fri night):**

| Piece | Runs on | Measured |
|---|---|---|
| Face detect + embed (`face_id`, buffalo_sc ONNX) | Mac, CoreML | 9 ms / frame |
| Speech-to-text (`mlx-whisper`) | Mac, Metal | 183 ms (small.en) / 506 ms (turbo) for a 3 s question |
| LLM intent + rephrase | EnverThor first, Mac Ollama (`qwen2.5:3b`) if > 2.5 s | ~1 s warm on EnverThor |
| TTS | Mac (`say` / Piper) → PCM to glasses, or glasses' own TTS if present | — |
| Caregiver alert | Mac Messages app via `osascript` (real iMessage) | — |

**Latency budget (tap → first audio):** STT 200 ms + intent/rephrase 1000 ms + TTS first chunk 300 ms + network 200 ms ≈ **< 2 s**. Faces run continuously in the background, so "who is this" doesn't wait on face matching.


## 6a. Hardware findings (probed on our M6, Fri Nov 20, 9:10 PM)

> **Full, newer measurements (gesture key codes, gyro axes, wear key 301, sensors): [`docs/HARDWARE.md`](HARDWARE.md).**

| What | Result |
|---|---|
| Device | `XNM_Glass`, Android 9 (API 28), Unisoc UWS6152 (1x A75 + 3x A55), 1.9 GB RAM, 640x480 @ 160 dpi |
| adb | Works after Developer Mode (MLDemo iOS → Glasses → Developer) + USB replug |
| Link to hub | **USB with `adb reverse tcp:9100 tcp:9100`** → glasses use `ws://127.0.0.1:9100`. No Wi-Fi needed (glasses Wi-Fi was off). Use a port above 9000: 8765 is taken by SLHJ, 8770 by macOS `sharingd`. |
| Camera | Works from a plain app (`android.hardware.Camera`, 1 back camera). 640x480 JPEG ~40–48 KB, ~1.2 fps at our throttle. Sizes up to 1920x1080. |
| Mic | Works (`AudioRecord`, 16 kHz mono, VOICE_RECOGNITION source); room audio arrives. Still to do: a deliberate speech test. |
| Text-to-speech | **No TTS engine on the glasses** → the hub must speak (macOS `say`/Piper) and stream PCM 22.05 kHz to the app. |
| Speaker | **Confirmed audible**: a PCM16 22.05 kHz tone streamed from the hub plays through the glasses speaker on each key press. |
| Display | The launcher draws a status bar (clock, BT, Wi-Fi, battery) over the top ~40 px that apps can't hide. Our pinned hint `Say "Lucia" or hold right side` sits **bottom-left**. |
| Touchpad / ring | Instant key events (~7 ms down→up), so map by key code, not timing: **66 ENTER = tap (ask)**, 142 F12 then 4 BACK (300 ms apart) = second gesture, 22/21 DPAD_RIGHT/LEFT = swipes. BACK is swallowed so nothing can close Lucia. |
| Sensors | Accelerometer, gyroscope, magnetometer, light, proximity, step counter, **off-body detect** (auto-greet when the glasses go on), pressure. |
| Built-in apps | `com.mlaixr.*` launcher, assistant, camera, recorder, translator, prompter, navigation, ring, audiocare. |

## 7. Knowledge base (the part everyone can edit)

Plain markdown in `knowledge/`, so non-coders can fill it in from Discord. The hub loads it at startup and on change.

- `knowledge/patient.md`: who the patient is, their people, routines.
- `knowledge/places.md`: places with an id; `currentPlace` in config picks one.
- `knowledge/people/<id>.md`: one file per person (teammates for the demo), from `docs/TEAM_TEMPLATE.md`.
- `knowledge/faq.md`: any extra Q/A pairs, with alternate phrasings.

Format rules (see the files for examples):

```markdown
# Q: Where's he from?
- also: where is he from / where does he live / what's his hometown
A: Dev grew up in Edison, New Jersey.
```

Each `# Q:` block is one intent. The `also:` lines are optional; the model handles paraphrases anyway, and they just make it more reliable.

## 7a. Proposed personal memory entry (research added Nov 21)

**Proposal only; not implemented.** Add an optional private profile that the wearer can contribute to, independently or with a chosen caregiver's help. Begin with a simple phone form for important people, current and past pets, interests, and comfort preferences. An optional later spoken flow could accept “Remember, my dog's name is Buster,” read it back, and save only after clear confirmation and a successful durable write. Buster is fictional example data.

This extends established memory-support practices: notes and journals, photo-based memory books, life-story records, and personal profiles such as Alzheimer's Society's “This is me,” which explicitly includes pets. These resources involve the person and people who know them; they do not establish effectiveness for this prototype. See the sourced review and design in [Personal memory: research and proposed fact entry](PERSONAL_MEMORY_RESEARCH.md).

- Keep ownership, current versus past status, source, review state, and dates. Never turn a question, wish, or overheard remark into an established personal fact.
- Respect the wearer's choices; offer supported review without requiring a caregiver to approve every low-risk self-report. Handle conflicts and corrections without silently overwriting or arguing.
- Use one eligible fact to fill short answer templates across many phrasings. A pet's name does not establish its breed or current location. Unknown is different from no pets.
- Personal-fact lookup must take precedence over the generic unknown response; the present fuzzy matcher does not implement that guarantee. Refresh affected answers and caches on edit or deletion.
- Store real profiles privately, outside public knowledge files and simulator exports, with authorized access. The existing name form is not a persistent fact editor.

Implementation is a separate team-scoped change; this research update does not change the backend, phone UI, or glasses behavior.

## 7b. Independence, comparisons, and pantry examples (content update Nov 21)

The aim is access to familiar information that supports everyday choices, including taking part in groceries, without assuming a person needs every task done for them. Repeated questions receive patient answers; the wearer retains a say in what support they prefer. Improved independence is a goal, not an outcome demonstrated by this prototype.

The bank now includes comparison and independence questions, pantry questions with honest current limitations, and an explicitly fictional food snapshot fixed to November 21, 2026. The snapshot does not sync the supplied spreadsheet or certify food safety. A live pantry, stock editing, and shopping-list updates remain proposed work.

See [Independence, comparisons, and pantry demonstration](COMPARISONS_AND_PANTRY.md) for the source review, fair comparison table, sample questions, and [fictional pantry fixture](fixtures/pantry_demo.json). No household inventory is added to the public knowledge files.

## 8. Faces

- Enroll each teammate from 3 photos (front, slight left, slight right) taken **at the venue, in venue lighting**. Photos go in `faces/<person_id>/` (gitignored, never pushed).
- Store **embeddings only** after enrollment; delete the raw photos after the event.
- Match threshold `faces.matchThreshold` (start at 0.55; tune at the venue). Below the threshold, say "not sure".
- Only people who opted in (filled the template) are enrolled. Unknown faces are never stored.

## 9. Privacy and safety (also the pitch)

- **Local-first:** patient data stays on the glasses, the patient's phone (the hub Mac in the demo) and a private compute box on the patient's own network (EnverThor). No cloud AI calls.
- **No medical advice.** Health questions → "That's a good question for your doctor. Shrikar can help you call." Medication *reminders* are only things a caregiver typed in, read back verbatim.
- **Consent:** faces enrolled only with that person's OK. One-tap "forget everything" on the caregiver page.
- **The SDK kit is confidential** and must not be committed; see `.gitignore`.
- **Real phone numbers** go only in `config/app.local.json` (gitignored). The example config has a placeholder.

## 10. Repo layout

| Path | What | Owner |
|---|---|---|
| `docs/SPEC.md` | this file | all |
| `docs/TEAM_TEMPLATE.md` | Discord fill-in for each teammate | all |
| `knowledge/` | patient, places, people, FAQ | content owner |
| `config/` | app name, patient, caregiver, models | hub owner |
| `glasses-app/` | Kotlin APK for the M6 | Android owner |
| `hub/` | Python FastAPI: STT, faces, intents, TTS, log | AI/backend owner |
| `caregiver-web/` | phone page (rough first, frontend devs polish) | frontend × 2 |
| `faces/` | enrollment photos, never committed | hub owner |

## 11. Workstreams (team BB)

1. **Glasses app (Android):** black full-screen UI, Camera2 frames, mic stream, keys → WebSocket. Start from the WebView thin client already built in the prep kit, or go native if camera access needs it.
2. **Hub + AI:** WebSocket server, STT, intent router, KB loader, TTS, EnverThor client + fallback.
3. **Faces:** wire `face_id` into the hub; enroll teammates; tune the threshold under venue lights.
4. **Frontend × 2:** lens UI polish (type size, contrast, layout on a 640×480 green waveguide) and the caregiver page.
5. **Content + pitch:** collect templates from Discord, write `knowledge/`, own the 3-minute script and backup video.

## 12. Timeline

| When | Goal |
|---|---|
| Fri 9:00–10:30 PM | Glasses on adb, hello-world on the lens, camera frame + mic reaching the hub. Everyone posts their template. |
| Fri night (remote) | Hub answers KB questions end to end in a laptop emulator; faces enrolled. |
| Sat 8–10 AM | Full loop on the glasses: tap → question → voice + lens answer. |
| Sat 10–12 | Proactive intro, wake word, caregiver page, distress flow. |
| Sat 12–1 PM | Feature freeze, 3× worn rehearsals. |
| Sat 1–2 PM | Backup video, submission text (with prior-work note), push. **2:00 code freeze.** |

## 13. Prior work (must be disclosed in the submission)

- `face_id` (Shrikar's own library, pre-existing).
- Data model and principles adapted from `dementia-memory-assistant` (Shrikar's earlier app).
- Prep-kit hub and emulator code written Fri Nov 20 before hacking started, if we reuse it.

## 14. Open questions

Tracked in the README of this repo until answered.
