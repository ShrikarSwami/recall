# Judge-first demo — three minutes

> **Superseded on Nov 21 by [DEMO_FLOW.md](DEMO_FLOW.md)** (faces → g grocery → c calendar → fall → caregiver page). The notes below still apply for wording and fallbacks.

One narrator, one operator, and one teammate in view at a time. Do not introduce the team before the face-recognition moment. Use the judge's first name only if they choose to provide it; otherwise explain the configured demo persona. The judge is trying a reminder interaction, not being diagnosed or tested.

## Before handing over the glasses

The operator completes the hardware gates in [FINAL_HANDOFF.md](FINAL_HANDOFF.md). Have the caregiver page and the receiving phone ready. Use the tested connection, keep USB available, and confirm the current APK and hub are running. Check `voice_warmup` in `/api/state`; `ready` means clips rendered, not that the glasses speaker was heard.

A name set through `/api/patient` lasts in memory and can be reset by a reload/restart. Set it before the final warmup check. Keep actual phone numbers and tokens in private config. No need to add a service or redesign the caregiver page.

## 0:00–0:25 — Set up the moment

> “We're not going to introduce ourselves just yet. Imagine seeing someone familiar and not being able to place their name, or forgetting why you came into a room. Even a small question can mean having to ask someone else for help.
>
> We built Go-go to give people living with dementia another way to get those reminders themselves. Put these on. Say ‘Go-go’ or hold the right side, then ask a question. That instruction stays on the lens.”

The demo name and wake word above are examples; use the configured values if changed. Let the greeting finish. Do not talk over the glasses.

## 0:25–0:45 — Let Go-go suggest the first question

Prompt only if needed: “You can ask, ‘Go-go, what can I ask you?’”

Go-go's prepared answer:

> “Say ‘Go-go,’ then ask ‘Who is this?’ or ‘Where am I?’ You can ask again whenever you need a reminder.”

Let the judge choose. This is a short help answer, not an autonomous tour or an automatic sequence of questions. If they choose location first, do location first, then invite them to look at the teammate.

## 0:45–1:20 — Meet a teammate

Use Shrikar or Abhiram for the main demonstration: both have supplied follow-up facts. One person stands in good light facing the glasses. Wait for an automatic introduction; if it does not arrive, the judge can ask “Who is this?”

Go-go identifies them as a presenter and may offer “Want to hear more?” Let the judge say yes or nod. Then one natural question, such as “What does he do?” or “What does he like doing?”

Use only facts that person supplied. Do not tell the judge they previously met us or that we are their family. Sid and Isha have basic introductions but mostly blank profile answers; do not promise a detailed conversation about them until they fill those in.

## 1:20–1:45 — Ask again, without embarrassment

> “You don't have to remember the answer. Ask the same question again.”

Let them repeat “Who is this?” or use “Go-go, say that again.” If they missed the voice, try “Go-go, say that again slowly.”

> “It gives you a calm reminder without saying you already asked. The goal is to make that small moment something you can handle yourself.”

A short “huh?” works in the 15-second follow-up window after an answer. During playback, use the wake word plus a control or hold the temple; do not promise every background “what?” interrupts.

## 1:45–2:05 — Orientation

If not already shown, ask “Where am I?” or “Why am I here?” A day/time question uses the Mac's actual clock; do not rehearse a fixed spoken time. Skip this section if the judge has already explored location.

## 2:05–2:35 — Support when needed

> “Independence doesn't mean having no one to turn to. For this next part, we're testing a distress alert. Try ‘Go-go, I want to go home.’”

Go-go responds and the operator checks both the caregiver feed and receiving phone. Hold up an actual received iMessage only after it arrives. The alert includes the time and available place. The caregiver feed is not proof an iMessage arrived.

> “The caregiver can see the question and check in, while ordinary reminders stay in the glasses.”

The current distress response speaks before attempting the text and can overstate notification or location. The operator must confirm the real result; do not claim delivery from the spoken response alone.

## 2:35–3:00 — Close on independence

> “We want everyday reminders to be something you can ask for yourself, with familiar support close by when you need it. You don't have to find a phone, learn a menu or explain that you forgot.
>
> Processing runs on our own devices, and caregiver alerts use iMessage. This is our working prototype; the next step is testing it with the people who would use it.”

Introduce the team now if useful. Use [SUBMISSION.md](SUBMISSION.md) for implementation and prior-work questions. Do not claim measured clinical benefit or guaranteed emergency response.

## Optional, after the core flow

Fall detection is a separate experimental demonstration, not a requirement for the three-minute flow. Include it only after a reliable rehearsal and if time allows. A synthetic/replayed fall must be described as such; do not imply a hardware event occurred. Nobody needs to perform a real fall to complete this demo. A second person or a hackathon/company question is also optional.

## Keep moving if something fails

| Observation | Next step |
|---|---|
| No greeting | Use the pinned instruction and ask the first question; do not wait silently for the wear sensor. |
| Wake word missed in venue noise | Hold the right side, pause for listening, then ask. |
| Face not recognized | One person, better light; then ask “Who is Shrikar?” as an explicitly named-person fallback. This does not prove face recognition. |
| Voice too quiet | Let the judge read the lens; operator fixes volume before another run. Temple input alone does not make output louder. |
| Link drops | Use the rehearsed USB fallback; if necessary show the simulator and say you are switching to it. |
| iMessage absent | Check the feed's send status; show the feed as the feed, without promising a later delivery. |
| Nod unreliable | Say yes. |
| Running long | Keep the first face, repeat and caregiver moment. Skip extra people, event trivia and falls. |
