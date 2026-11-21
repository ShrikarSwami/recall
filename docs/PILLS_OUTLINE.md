# Pills / time-based reminders: implementation outline (for a teammate's coding agent)

**Status: not built.** This is the plan. Place reminders (`hub/lucia/reminders.py`, triggered by the iPhone) and the
schedule heads-ups (`hub/lucia/schedule.py`) already exist. Reuse them; don't start a third system.

## Product rules (from docs/SPEC.md §2 and §9)

- **Read back only what a caregiver typed**, word for word: "It's 1 o'clock. Time for your blue pill with water."
  Never dosage advice, never "you should", never infer anything about health.
- Every reminder stands alone (the patient may not remember the last one). Calm, one sentence.
- "Did I take my pills?": Go-go only knows what was *confirmed*. If unconfirmed: "I'm not sure. {caregiver} can help."
- Missed reminder (no confirmation in 20 min): tell the caregiver page, and send an iMessage only if the
  caregiver opted in. Distress stays the only automatic text.

## Data (caregiver-written, private)

Extend `config/reminders.local.md` (gitignored) with time sections, parsed alongside the place sections:

```markdown
## at 13:00
- Time for your blue pill, with a glass of water.
## at 20:30
- Time for your evening pill.
```

Demo copy (fictional) goes in `config/reminders.example.md`.

## Hub changes

1. `reminders.py`: parse `## at HH:MM` into `[(time, text)]`. Add `due(now, said) -> list[...]` (same shape as
   `schedule.heads_up`).
2. `server.py`: in `heads_up_loop`, also check `reminders.due(...)` and say it with intent `"pill"` (lens can style it).
   Keep the same guards: glasses connected, not mid-answer, once per day per reminder.
3. Confirmation, reusing the yes/no **offer** system already in `brain.py` (`_with_offer`, nod/shake via
   `gestures.py`): the reminder ends with "Have you taken it?" → yes/nod records `taken_at`; no/shake →
   "Okay. I'll remind you again in 10 minutes."; one re-remind max.
4. `brain.py`: intent "did I take my pill(s)" → answer from today's confirmations only.
5. Caregiver page: list today's reminders with taken / not yet / missed.

## Tests to write (`hub/tests/test_pills.py`)

Parse `## at` sections · due exactly once · confirmation via YES and via nod · "did I take my pill" before/after
confirming · nothing is ever said that isn't in the file.

## Demo

Set a reminder 2 minutes ahead, wear the glasses, nod when asked. Show the caregiver page flip to "taken".
