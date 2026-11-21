# Replay, slower speech, stop, and event questions

Updated November 21, 2026. This change adds response controls and sourced event Q&A. It adds no lens panels, menus, permanent conversation feed, or settings for the wearer.

## What to try

| Intent | Natural examples | Behavior |
|---|---|---|
| Replay | “Say that again”, “say that”, “what?”, “huh?”, “pardon?”, “come again”, “I didn't catch that” | Reuse the previous answer's text; no model call and no repeated caregiver alert |
| Slower replay | “Speak slower”, “not so fast”, “a little slower”, “say it again but slower” | Same answer at 72% of the ordinary speech rate, within the renderer's bounded words-per-minute range |
| Stop | “Stop”, “stop talking”, “enough”, “that's all”, “be quiet”, “cancel that”, “never mind”, “mute the audio” | Stop the current output, clear the answer and pending offer, and remain silent |

The wake word comes from configuration. After an answer, a 15-second follow-up window accepts recognized controls without saying the wake word again. Short words such as “what” are anchored whole utterances, not substring matches: “what time is it” remains a clock question and “where is the bus stop” remains an ordinary question.

Outside that window, use the configured wake word or hold the right side. While audio is playing, voice interruption requires the wake word plus a recognized control, or an explicitly armed microphone. A temple touch/hold interrupts the old output and arms the next question. A plain “huh” from bystanders is not a global always-listening command. Stop cancels the current response; “mute” here does not persistently change microphone or voice settings.

Replay preserves a current yes/no offer without advancing it. An expired offer is not silently brought back. Replaying a distress response does not resend its alert. There is a gentle response when no earlier answer exists.

## Implementation boundaries

- `hub/lucia/playback.py`: anchored grammar, polite wrappers, configured wake-word handling, and exported grammar data. No LLM classification for these controls.
- `brain.py`: last answer, replay state, rate, silent stop, and active-offer handling.
- `server.py`: output generation guard, cancellation of pending model answers, paced 200 ms audio chunks, device flush, and bounded wake-free follow-up handling.
- `speech.py`: rate-aware audio cache keyed by voice, rendered rate, and final text. Short-word segmentation no longer requires the previous long speech onset.
- `MainActivity.kt`: `audio_stop` pauses and flushes the existing AudioTrack; `clear` also clears native fallback text. No new visual controls.
- Simulator: the same exported grammar, repeat/slow/stop behavior, short follow-ups, and browser speech cancellation. Generated knowledge files are refreshed through `export_kb.py`.

During output, the hub may transcribe microphone audio to identify an explicitly woken control. It rejects non-control playback transcripts instead of turning the assistant's own voice into a new question. Ignored transcripts are not logged as text. This is not a claim of acoustic echo cancellation: overlapping voices and venue noise require testing on the actual glasses. Recognition still takes VAD and transcription time; “stop” means stop promptly once recognized, not a zero-latency guarantee.

Integration was checked against main `21d1346` (PR #18), including the newly merged fall detector. Stopping a voice offer uses the upstream IMU ownership function, so it does not disable ongoing fall monitoring. A regression test protects that shared behavior.

The real glasses must run the matching updated app so buffered audio can be flushed. Source changes alone do not update the installed APK or an already-running Python process. Coordinate deployment with whoever is driving the live demo.

## Phrase coverage and tests

`hub/tests/test_playback.py` covers 76 authored replay phrasings, 41 slower phrasings, 95 stop phrasings, and 23 negative examples. It also exercises 1,008 combinations of natural requests and polite wrappers. Coverage is broad, not a guarantee of understanding every possible sentence or transcription error.

`hub/tests/fixtures/playback_phrases.json` is an independently authored test corpus, not the source used to build the production grammar. `sim/test-playback.cjs` runs the same corpus against the actual JavaScript classifier and tests offline answer behavior.

Hub tests cover stop during audio rendering and streaming, pending model cancellation, slower-render dispatch, one-word woken commands, bounded “huh” follow-ups, and rejecting non-control playback echo. Speech tests cover rate-separated clips and retaining a short word before recognition.

Verification completed in this environment:

- All **352 Python tests passed** against the integrated main version, with alert sends in dry-run mode and execution-environment proxy variables removed. Existing recorded fixtures were reused locally and are not part of this change.
- Node offline simulator behavior and the authored cross-language grammar corpus.
- Direct Kotlin compilation of `MainActivity.kt` against the cached Android/OkHttp dependencies; existing deprecated Android camera/audio APIs emit warnings.
- All 286 phrasings in `event.md` and `event_more.md` reached their intended prepared answers without model calls in a fresh brain context.

Limitations to preserve in the handoff:

- Full Gradle APK assembly was blocked by the environment: the normal cache is read-only; an isolated cache got past that but the Gradle daemon could not open its local socket. Do not label this an assembled or installed build.
- A direct macOS `say` audio probe returned empty PCM here, so audible playback and the actual perceived slowdown remain unverified on hardware. Renderer argument/rate/cache behavior is covered with controlled audio fixtures.
- The live hub was not restarted and the installed glasses app was not replaced during this work.

## Expanded event and glasses knowledge

`knowledge/event_more.md` adds 28 answers with 224 phrasings covering public judge roles, the three tracks, event rules, MicroLumin/MLVision, M5 versus M6, modular hardware, and the new response controls. These are ordinary short answers; they do not enroll judges' faces or infer that a named judge is physically in view.

Public sources checked November 21, 2026:

1. [Worn event site](https://worn-hacks.com/) and [judge profiles](https://worn-hacks.com/judges). The site renders from a JavaScript bundle; public judge-role fields were read from the bundle linked by the page, not a private API.
2. [Organizer's Luma event listing](https://luma.com/smart-glass-hack-nyc), linked from the event context.
3. [MicroLumin's English site](https://microlumin.net/en/) and [M6/M5 product overview](https://microlumin.net/en/h-col-119.html).
4. [Measured hardware findings](HARDWARE.md) for this particular M6 pair. Product-family advertising is not a measurement of our display-equipped hardware.

**Roster discrepancy:** Worn's current judge page has nine public profiles; Luma additionally lists D.J. Patel. Answers acknowledge this rather than asserting an unverified final attendance count. Several biographies also differ in detail, so use the current Worn profile's short role rather than merging incompatible career claims. Confirm changes with organizers.

**Hardware distinction:** the manufacturer's 36.8 g figure refers to M6 Air, not a measured weight of our complete display setup. M6 modules vary; our demo uses green lens text. No all-day battery runtime or product superiority is established by these sources.

The existing hardware-return answer now distinguishes returning devices after use from the final 6 PM return/wrap-up.

## Recaps and comfort without crowding the lens

These remain a proposed interaction policy, not new implemented recap/profile features:

- A recap is requested by voice and shown in the existing answer card, one or two short spoken sentences. No permanent timeline, new icon, or additional panel.
- Recaps use only recorded observations. Seeing a face does not prove a conversation happened.
- Comfort or casual chat uses the same card and a short response. It does not add proactive chatter or keep asking follow-up questions indefinitely.
- The pinned instruction stays visible. The current answer replaces the previous card and times out normally; stop clears it.
- Personalized comfort requires the person's chosen information and the separately proposed private profile. Existing generic small talk remains available now.

Longer term, breadth can grow through voice requests and grounded information, in the spirit of an ordinary voice assistant. More features should not mean more interface elements or more facts the wearer must remember.
