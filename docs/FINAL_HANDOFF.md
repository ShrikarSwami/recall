# Lucia: final handoff to Claude and the team

Reviewed November 21, 2026, against clean main `1f310813b6c8cf15570fbea0e01d26f79f7de30e` (PR #21 merged). This handoff also describes the small judge-opening fix and revised demo script delivered alongside it. Check current git status and main before changing anything: teammates are working concurrently.

## The decision now

The core demo path is implemented. Stop expanding features and move to physical glasses testing. Completion means a judge can wear the current build, get useful short reminders, repeat a question, and produce a caregiver alert that actually arrives. Passing software tests alone does not complete that loop.

The user wants a judge-first presentation: **do not introduce ourselves**, explain an everyday moment of forgetting a familiar name, let the judge ask “what can I ask you?”, and let Lucia suggest a first question. Explain the motivation through what happens: supporting everyday independence without making someone find a phone, learn menus or depend on another person for each small reminder. This interaction illustrates the idea; it does not simulate the experience of dementia.

The running order and actual narrator words are in [DEMO.md](DEMO.md). Use that document for rehearsals instead of creating another competing pitch.

## What is available now

| Part | State and practical boundary |
|---|---|
| Glasses → Mac hub → lens and voice | End-to-end operation on the M6 was previously reported in the repo. The latest combined build still needs a physical rehearsal. |
| Face introductions and follow-ups | Stored personal facts, face context and yes/no offers exist. Use a consenting enrolled teammate; it does not identify arbitrary strangers. |
| Judge asks for examples | This handoff's small fix gives concrete “Who is this?” / “Where am I?” prompts. Capability questions no longer become distress simply because they contain “help me.” Bare calls for help and explicit distress still alert. |
| Repeat, slower, stop | Broad tested phrase coverage; slower replay is 72% of ordinary rate. Stop flushes device audio and cancels a pending answer when the matching APK is installed. |
| Wake-free follow-up | Recognized controls accepted for 15 seconds after an answer. During playback use wake word + control or temple input. This is not unrestricted always-on interruption. |
| Orientation, schedule, event Q&A | Prepared answers and live clock/schedule logic. Event/judge facts are sourced content, not judge-face enrollment. |
| Caregiver alerts and feed | Existing macOS Messages / iMessage integration; no new messaging provider. Distress is rate-limited, urgent fall alerts bypass the normal limit. |
| Alert context | Main uses simple `App: message · time · place` formatting. Fresh phone place wins; configured demo place is the fallback; unknown place is omitted. Keep this simplicity. It is not a new tracking system. |
| Voice prewarming | Startup, knowledge/config reload and patient-name changes prepare exact-text clips quietly in the background. `/api/state` exposes counts. Dynamic wording may miss the cache. |
| Fall detector | Experimental IMU logic and urgent alert flow exist. Not required for the core demo and not clinically validated. |
| Simulator | Offline mock and live-hub options exist; generated knowledge is refreshed. An offline simulator is an openly labeled fallback, not proof of hardware readiness. |

### Read-only observations during this review

- `adb devices` returned **no attached devices**. This does not rule out a glasses device on a separate network, but no hardware session was available through adb.
- Live `http://127.0.0.1:9100/api/state` returned **`glasses: false`**, **525 answers**, and **11/11 voice clips ready**.
- Live enrollment counts were Abhiram 3, Shrikar 3, Sid 3. Isha was absent from that enrollment result. These are counts, not proof of recognition under venue light.
- No live process was restarted/reloaded and no app was installed by this review. The judge-opening source/content edit still needs to be loaded into the demo hub. Do not confuse edited files with deployed code.
- No real messages were sent, and no physical audio, wake word, touch, nod or fall was tested in this review.

The live warmup result is encouraging. An earlier direct `say` probe in this tool environment produced empty audio, so the actual rendered clips and glasses speaker still need an audible check. Do not rebuild speech infrastructure just because that isolated probe failed.

## The remaining gates, in order

Record pass/fail on the actual setup, not assumptions. Start from [GLASSES_RETURN.md](GLASSES_RETURN.md) and [glasses-app/AGENTS.md](../glasses-app/AGENTS.md).

| Gate | Acceptance on the real setup | If it fails |
|---|---|---|
| 1. Current build and link | Latest APK installed; current hub loaded; `/api/state` shows glasses connected. The pinned instruction is visible. | Establish USB first; fix only the deployment/link problem. |
| 2. Audible first answer | Ask for examples and hear the complete answer while the lens stays readable. Check the speaker, not just PCM counts. | Check voice rendering, volume and transport separately. |
| 3. A real face | One enrolled teammate is identified without naming them in the question, in venue light. | Lighting/enrollment/threshold checks. Named lookup is a fallback, not a face test. |
| 4. One follow-up | A supplied fact about Shrikar or Abhiram is spoken correctly. Yes works; nod is tested separately. | Correct context or content; use spoken yes if the nod is unreliable. |
| 5. Repeat and control | Same question is calm; replay repeats; slower is audibly slower; stop promptly clears current output. | Confirm current APK supports flush, then isolate microphone versus playback. |
| 6. Caregiver completion | One rehearsed distress question yields the right feed event and one **received** iMessage with time/place. | Check configured recipient, dry-run, rate limit, Messages sign-in and macOS automation permission. Keep the existing iMessage system. |
| 7. Full timed run | Two consecutive core runs at or below three minutes, with intelligible audio and no operator rescue beyond agreed prompts. | Remove optional beats and fix only observed blockers. |

Start rehearsals with `LUCIA_DRY_RUN=1`. A real caregiver text requires an explicitly coordinated receiving person and deliberate live-message test. This handoff does not authorize messaging arbitrary contacts. For the actual demo, verify dry-run is off, the private recipient is correct, and the phone is ready. Ordinary distress has a 60-second rate limit; do not assume two rapid rehearsals will produce two messages.

Do not run `tools/replay_glasses.py` while someone is using the glasses: it takes over the single glasses connection. Use it as an explicit separate fallback/test. Keep logs private; there is no need to delete real logs for this handoff.

Useful checks:

```bash
cd hub
env -u ALL_PROXY -u all_proxy -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy \
  LUCIA_DRY_RUN=1 .venv/bin/python -m pytest -q
.venv/bin/python -m lucia.export_kb
# From the repo root:
node sim/test-playback.cjs
# With the real demo hub running:
curl --noproxy '*' -s http://127.0.0.1:9100/api/state
```

Full Gradle APK assembly was blocked in the earlier tool session by cache/socket permissions; direct Kotlin compilation passed. Neither is an installed-build claim. Build/install in the normal Mac session following the Android instructions. Do not disturb a teammate's active demo hub without coordinating.

## Content and choices from this conversation

- The user wanted roughly 1,000–5,000 prepared phrasings so common answers avoid relying on a local LLM. Current loader snapshot: **525 answered entries** and **3,127 stored phrasings** (**3,059 distinct normalized wordings**) after this change. Prepared text is the primary path; phrase count is not a guarantee of understanding every transcription or sentence.
- Before this change there were 3,119 phrasings / 3,051 distinct normalized wordings. Eight aliases were added to the existing capability answer, not a new answer bank. Recount with the loader if content changes.
- Shrikar's profile has **23** supplied answers and Abhiram's has **18**. Sid and Isha each have **2**, mostly introductions; their remaining answers are blank. Fill those from the people themselves, not guesses. Shrikar's facts include his software role, Stevens CS, hobbies and OTTO; the file is the current source of truth.
- Judge-facing introductions describe teammates as presenters. Do not restore fictional shared history such as “we met at this hackathon” for a judge.
- Keep the lens simple: one pinned instruction, existing answer card, at most three short lines. The user explicitly does not want crowded UI, new menus or permanent conversation panels. Short voice-requested help/comfort fits the existing card.
- Private personal-fact entry (for example, “my dog's name is Buster”) is **deferred**. `/api/patient` only changes the demo name in memory; it is not a durable profile editor or a spoken fact-saving feature.
- Pantry questions, grocery independence and comparisons were explored. There is an existing place/arrival reminder flow; there is **no live pantry sheet integration**, stock editor or automatic shopping. The pantry fixture is fictional. Do not import the real household sheet into public git.
- The user wants standard iMessage for the demo. No new privacy infrastructure, messaging provider, location service or architecture rewrite. Describe processing as running on their devices and acknowledge iMessage when relevant; do not promise verified prevention of data loss.
- Comfort, event, company and judge questions have prepared content. Broader casual conversation and recaps should remain short, grounded and requested; a timeline or diary UI is not part of this handoff.
- Tailscale phone access needs a connected phone and an accepted machine share when accounts differ. Existing addresses/tokens in old chat screenshots are not deployment instructions; get current values privately. Use [SHORTCUT_API.md](SHORTCUT_API.md).

## Source map: the rest of the chat is already documented

| Document/source | Use it for |
|---|---|
| [SUBMISSION.md](SUBMISSION.md) | Editable submission text, motivation, built vs reused, practical privacy description. Confirm earlier-work scope; not yet a submitted entry. |
| [SPEECH_CONTROLS_AND_EVENT_QA.md](SPEECH_CONTROLS_AND_EVENT_QA.md) | Speech grammar, limitations, sourced Worn/MicroLumin/judge facts, prior validation. |
| [PERSONAL_MEMORY_RESEARCH.md](PERSONAL_MEMORY_RESEARCH.md) | Existing memory aids and private fact/profile proposal. Research, not a finished editor. |
| [COMPARISONS_AND_PANTRY.md](COMPARISONS_AND_PANTRY.md) | Independence positioning, fair comparisons, pantry source and fictional-demo boundaries. |
| [CAREGIVER_DATA.md](CAREGIVER_DATA.md) | Content locations and caregiver workflow. Its older absolute privacy claims should be read against SUBMISSION.md and actual code. |
| [CHATGPT_INTERVIEW_PROMPT.md](CHATGPT_INTERVIEW_PROMPT.md), [TEAM_TEMPLATE.md](TEAM_TEMPLATE.md) | Questions for collecting Sid/Isha facts in their own words. |
| [knowledge/people/](../knowledge/people/) | Current supplied teammate facts; public demo information only. |
| [HARDWARE.md](HARDWARE.md) | Measured M6 facts; distinguish from product-family marketing. |
| [SPEC.md](SPEC.md) | Architecture and prior work: pre-existing `face_id`, earlier dementia app and preparation code must be disclosed. |
| [AGENT_HANDOFF.md](AGENT_HANDOFF.md) | Historical content audit. Counts, cache status and priorities there predate this handoff. |

A casual request the user can send themselves: “hey can you fill in your questions with short answers in your own words? role, school, hobbies, favorite food and a fun fact are a good start. it's so the glasses can answer when the judge asks about you.” Do not send it on their behalf.

## Known limits to preserve

The distress response currently speaks before `Alerts.send` and can claim the caregiver knows the location or was notified before the send outcome is known. A failed, dry-run or rate-limited send is not delivery. The fall reassurance also says help is on the way without a dispatch acknowledgment. Do not use those spoken lines as evidence; the operator checks the actual result. Treat any wording correction as a small observed demo fix, not a notification-system rewrite.

Fall detection is experimental. The submission draft currently mentions a staged teammate fall; reconcile that with what the team actually rehearses. It is optional, and nobody needs to perform a real fall. Do not promise a two-second physical detection/receipt time without measuring it.

Avoid absolute pitch statements copied from older drafts: no public cloud AI is required for core stored answers, but iMessage uses Apple; face enrollment photos exist locally; logs are stored locally. Prior-work disclosure remains necessary.

## Validation and finish line

Final verification in this review: **374 Python tests passed**, with actual messaging disabled, and `node sim/test-playback.cjs` passed the shared speech corpus and opening/distress checks. New opening regressions cover capability questions without a model, renamed wake words, continued true-distress alerts, and prewarming the example answer. These checks do not establish physical audio, face recognition under venue light, or delivered iMessages.

Once the seven gates pass: stop coding, rehearse the delivery, confirm submission fields and prior-work disclosure, and capture a backup video. The code freeze is Saturday November 21 at **2:00 PM ET**. Do not turn the remaining time into another feature sprint.

## Short prompt to start Claude

> read docs/FINAL_HANDOFF.md and docs/DEMO.md first. we're done adding features; help us finish the judge-first demo on the actual glasses. check current main and don't overwrite teammates' changes. verify the build, voice, face intro, follow-up, replay/slow/stop and one coordinated iMessage test. fix only real blockers, keep the existing iMessage setup and simple lens, then run two timed rehearsals. no private fact editor or UI redesign. commit fixes on a feature branch; don't push or merge unless I ask.
