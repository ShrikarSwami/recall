# Content handoff and next steps

> Historical audit. Start with [FINAL_HANDOFF.md](FINAL_HANDOFF.md) for the current demo plan, merged work and hardware gates. The snapshots and recommendations below predate it.

Reviewed November 21, 2026 against main commit `0391b08d7066b458c7d11ce776658aa6853c7cef`.

This is a documentation handoff. No runtime behavior is changed. Check the current main branch before implementing any recommendation: other teammates are actively working in this repository. Follow the root and folder-specific agent instructions, and keep changes small ahead of the November 21, 2:00 PM ET code freeze.

## Start here: work already published

The bulk question bank, memory research, pantry comparison research, and fictional pantry fixture were merged in **PR #2**, commit `b40c676`. Shrikar's completed profile is also present on the reviewed main branch, with subsequent judge-facing introduction updates. Do not recreate or overwrite those changes.

| Resource | What it contains |
|---|---|
| [Personal memory research](PERSONAL_MEMORY_RESEARCH.md) | Sourced overview of notes, memory books, life-story records, and personal profiles; proposal for private fact entry and optional spoken saving |
| [Comparisons and pantry](COMPARISONS_AND_PANTRY.md) | Independence-focused positioning, fair comparisons, a pantry source review, and clear boundaries between the demo and a future live connection |
| [Fictional pantry fixture](fixtures/pantry_demo.json) | Eight synthetic items; fixed reference date November 21, 2026; no real household inventory |
| [Caregiver data guide](CAREGIVER_DATA.md) | Which information belongs in public demo content versus private runtime files |
| [Interview prompt](CHATGPT_INTERVIEW_PROMPT.md) | Teammate information collection workflow |
| [Knowledge instructions](../knowledge/AGENTS.md) | Q&A formatting, blank-answer behavior, export and reload steps |
| [Shrikar profile](../knowledge/people/shrikar.md) | 23 supplied answers, he/him pronouns, and name-hearing aliases; retain the current judge-facing introduction |
| [Demo script](DEMO.md) | Existing face introductions, repeated questions, yes/no offers, and caregiver demonstration |
| [iPhone place API](SHORTCUT_API.md) | Existing place updates and arrival reminders, including grocery reminders |
| [Glasses return checklist](GLASSES_RETURN.md) | Hardware and network preparation |

The knowledge directory also includes `comfort*.md`, `everyday*.md`, `leisure.md`, `technology*.md`, `design_questions.md`, `comparisons.md`, `independence.md`, `pantry.md`, and `pantry_demo.md`.

Snapshot counts from the actual loader: **497 answered entries, 2,895 stored question phrasings, and 2,827 distinct normalized wordings**. Person entries: Shrikar 23, Abhiram 18, Isha 2, Sid 2. Counts can change as teammates add content. Blank answers are skipped, so complete Sid and Isha's facts from their own supplied answers rather than inventing them.

## What is implemented versus proposed

“Implemented” means present in the inspected code, not newly verified on the physical glasses during this review.

| Capability | Current state | Evidence |
|---|---|---|
| Knowledge-first answers | Confident matches use prepared text; uncertain matches can consult the model | `hub/lucia/brain.py`, `matcher.py` |
| Face introductions and person follow-ups | Current face/topic context, name aliases, and stored personal answers | `brain.py`, `faces.py`, `speech.py`, `knowledge/people/` |
| Nod or spoken yes/no | Offers, gesture detection, debounce behavior, and follow-up answers exist | `brain.py`, `gestures.py`, `server.py` |
| Schedule questions and heads-ups | Day schedule and upcoming-event handling exist | `schedule.py`, `knowledge/schedule.md`, `server.py` |
| iPhone place and grocery arrival reminders | `/api/place` updates a coarse place; private reminder text can be read on arrival | `reminders.py`, `server.py`, `SHORTCUT_API.md` |
| Caregiver view | Events, repeated questions, connection state, alerts, and a name-setting form | `caregiver-web/index.html` |
| Remote write protection | Write endpoints require the configured token away from localhost; no token configured means development-open mode | `server.py:require_token` |
| Private personal-fact editor | Not implemented; the name endpoint changes memory rather than durably saving a full profile | `server.py:api_patient`, `PERSONAL_MEMORY_RESEARCH.md` |
| Spoken “remember my dog's name” | Design proposal; no dedicated confirmed-fact save flow inspected | `PERSONAL_MEMORY_RESEARCH.md` |
| Live pantry stock, dates, and grocery edits | Not implemented; prepared pantry demo answers are explicitly fictional | `knowledge/pantry*.md`, `COMPARISONS_AND_PANTRY.md` |
| Timed medication confirmations | Outline only; do not describe as working | `PILLS_OUTLINE.md` |
| Speech response cache | In-memory cache keyed by final text, limited to 300 rendered replies; not automatically prewarmed or persistent | `speech.py:Voice` |

A grocery arrival reminder already exists. A live stock-aware grocery assistant would extend it, rather than require a second place-detection system.

## Highest-value work before adding features

### 1. Make routing and alert wording truthful

In `brain.py`, `DISTRESS` includes an unqualified `help me`. A harmless request such as “help me with my shopping list” can enter distress handling before reaching the knowledge bank. Clock patterns can similarly catch a food-label question beginning “what is the date.” Tighten intent boundaries with meaningful positive and negative tests rather than adding more aliases to hide the problem.

Distress responses say that the caregiver knows the location and is being notified; a confirmed offer says “I've let {caregiver} know.” But `server.py:Hub.say` speaks first and only later calls `Alerts.send`. That send may be dry-run, rate-limited, or failed; the returned status is not proof the recipient read a message. Distinguish intent to send, successful send attempt, failure, and acknowledgment. Do not assert safety or a known location without evidence. Preserve the project's rule that distress is the only automatic caregiver text.

This audit did not send any messages or trigger a live alert.

### 2. Finish the people and rehearse the complete loop

Sid and Isha's files still have mostly blank answers. Getting their role, school, interests, and a conversation starter supplied is likely more useful to the immediate demo than another large set of generic phrases. Check the judge-facing wording: do not tell judges they have a shared personal history that was not supplied.

Rehearse on hardware: hold-right-side prompt, name recognition, two person follow-ups, a repeated question, a nod/yes response, an offline-model fallback, and the caregiver view. Unit tests do not establish venue audio quality or reliable device connectivity.

### 3. Warm a small set of common spoken answers

The system already avoids the LLM for confident matches, but the first text-to-speech rendering still costs time. Consider pre-rendering a small, measured set: greeting, teammate introductions, core person facts, and common orientation answers. Reuse `Voice` rather than creating a new audio pipeline.

Key any reusable audio by the actual final text and relevant voice settings. Names and personal facts can change, so never let an old profile's answer survive an edit. Account for the current 300-entry cache and memory use. Measure tap-to-first-audio, not just matching speed, before promising a latency improvement.

## Next product features, in suggested order

| Order | Small feature | Why it helps | Acceptance example |
|---|---|---|---|
| 1 | Private “About me” form | Gives the wearer and authorized supporters a way to supply meaningful personal facts | Save a current dog's name, restart, and answer several pet questions from that fact |
| 2 | Correct, remove, and undo a fact | Makes the profile maintainable and prevents a mistaken entry becoming permanent | Correct Buster to Baxter; old text and audio stop appearing; removal returns to unknown |
| 3 | Editable grocery checklist using existing place reminders | Makes the independence goal concrete without claiming autonomous shopping | Wearer chooses an item; authorized edit persists; grocery arrival reads the updated list once |
| 4 | Fresh pantry stock and recorded-date queries | Answers “do I already have this?” and “which listed dates are coming up?” | Used-up stock is excluded; estimates and month-only dates remain labeled; real questions never use the demo fixture |
| 5 | Caregiver unanswered-question review queue | Turns actual unmet requests into useful reviewed answers | Existing event feed supplies a question; an authorized person drafts, previews, saves, or dismisses an answer |

The first two features are described in detail in [the memory proposal](PERSONAL_MEMORY_RESEARCH.md). Start with forms and explicit save feedback; spoken capture can follow. Keep private values outside public Markdown and simulator exports. Follow the project's privacy requirements and do not turn casual speech into facts automatically.

For groceries, extend the existing private reminder file and arrival flow where practical. Keep choices with the person; no automatic purchases or claims that the wearer can shop alone. A pantry date is not a food-safety judgment. Read [the pantry design](COMPARISONS_AND_PANTRY.md) before importing any sheet.

For a review queue, the feed already logs questions and answers. Add a reviewed/unresolved state and authorized save flow rather than another telemetry pipeline. Routine unknown questions should not create an automatic caregiver text.

Medication functionality remains outside these suggested first changes. Its existing outline needs separate review; it must never guess a dose or infer that something was taken.

## Current validation

At the reviewed revision, **74 tests passed** using the existing virtual environment with alerts in dry-run mode. The first attempt could not collect the API tests because the execution environment set a SOCKS proxy but `socksio` was absent. Running the local suite without inherited proxy variables passed; no dependency installation or program edits were needed.

```bash
cd hub
env -u ALL_PROXY -u all_proxy -u HTTPS_PROXY -u https_proxy -u HTTP_PROXY -u http_proxy \
  LUCIA_DRY_RUN=1 .venv/bin/python -m pytest -q
```

This validates the existing unit/API suite, not the proposed features or a hardware rehearsal. The counts and implemented/proposed table above come from repository inspection. This handoff contains no credentials, private configuration, face images, household inventory, or confidential SDK files.
