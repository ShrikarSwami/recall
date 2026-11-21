# Lucia demo flow (final plan, Nov 21) — start here for slides

**The one thing we sell: independence for people living with dementia.** Lucia lets someone handle the small
moments themselves (who is this, what do I need, what's next) instead of asking someone else every time. When they
do need help, their caregiver knows right away. For patients *and* caregivers, it's as easy as putting on your
glasses every morning.

Lucia is the voice and the squirrel on the lens. Our hub on the Mac is the source of truth: faces, answers, voice,
alerts. The squirrel is how Lucia looks on the lens. It talks while Lucia speaks, waves when it introduces someone,
points at lists and the schedule, and looks concerned after a fall.

## The demo, beat by beat (about 3 minutes)

| # | What the judge sees | Who does what | What is real |
|---|---|---|---|
| 1 | Judge puts on the glasses. **No wires.** The lens is dark. Then WELCOME: the squirrel waves and Lucia says "Welcome! I'm Lucia, here to help you remember. Look at someone, and I'll tell you who they are." | Operator unplugs USB, hands the glasses over, then presses **s** on the caregiver page. | Glasses run on Wi-Fi to the hub. |
| 2 | Judge looks at Shrikar, then Sid, then Abhi. Lucia says who each one is ("This is Shrikar, one of the presenters of this project"), and the squirrel waves. Judge can nod or say "yes" to hear more. | One teammate at a time, facing the judge in good light. | Real face recognition from the glasses camera, real voice, real nod detection. |
| 3 | "What if you're grocery shopping?" The lens shows the grocery list and Lucia reads what to buy. | Operator presses **g** on the caregiver page. | The list and the voice are real. In daily life the family's phone says "you arrived at the store"; on stage the key stands in for that. |
| 4 | "Or you have a busy day." The lens shows what's next on the hackathon schedule. | Operator presses **c**. | The real schedule and the real clock. The judge can also just ask "Lucia, what's next?" |
| 5 | "This helps caregivers too. Say I'm a person with dementia and I fall." Shrikar falls. The glasses ask "are you okay?" and a text arrives on Shrikar's iPhone. | Shrikar falls. If the alert doesn't come within a few seconds, the operator presses **f**. | Real iMessage, sent in under a second with the time and place. The fall sensor is experimental; **f** is the backup. |
| 6 | Operator turns the laptop: the caregiver page shows the conversation, who was recognised and the fall alert in red. | Operator shows the page. | Live data from the glasses. |
| 7 | Close: "We want people living with dementia to stay independent, and caregivers to have peace of mind. It's as easy as putting on your glasses every morning." | Narrator. | — |

The caregiver page is also the **operator's remote**. With it in front, these keys change what's on the glasses
(ignored while typing in a field):

| Key | Does |
|---|---|
| **s** | Start: lens on, WELCOME, then Lucia introduces whoever the judge looks at |
| **g** | Grocery list |
| **c** | Calendar: what's next today |
| **f** | Fall alert (backup if the real fall isn't detected): "are you okay?" + text to the caregiver |
| **x** | Stop Lucia talking |
| **b** | Blank: lens dark and Lucia quiet until **s** (between judges). Falls still alert. |

During "Want to hear more?" Lucia only takes a nod, "yes" or "no". Other talk nearby is ignored unless someone
says "Lucia" or touches the temple.

## For the slides

- **Problem:** small everyday moments (a familiar face, a shopping trip, what's next today) mean asking someone for
  help, again and again. That chips away at independence and wears out caregivers.
- **Solution:** glasses that quietly give the reminder when it's needed, and tell the caregiver only when it matters.
- **What the wearer gets:** who's in front of them, where they are, what to buy, what's next, the same answer as many
  times as they ask with no embarrassment, and help after a fall.
- **What the caregiver gets:** an instant text for falls or distress, plus a page showing how the day is going.
- **How it works:** MicroLumin M6 glasses (camera, mic, speaker, motion sensor, lens) → our hub on a home computer
  (face recognition, speech, prepared answers, a local AI model for anything else) → caregiver alerts by iMessage.
  Processing runs on the family's own devices, not a public cloud AI.
- **Built at the hackathon:** the glasses app, hub, lens with the squirrel guide, caregiver page, fall detection,
  head-nod answers and 500+ prepared answers. Prior work (pre-existing face_id code) is disclosed in `docs/SPEC.md`.
- **Honest limits:** fall detection is experimental; on stage the grocery arrival comes from a key, not the phone;
  it's a working prototype, and the next step is testing with people living with dementia and their families.

## Operator setup (5 minutes before)

```bash
cd ~/Projects/recall/hub && LUCIA_STANDBY=1 .venv/bin/python3 -u -m lucia.server > data/hub.log   # real texts, lens dark until s
cd ~/Projects/recall/gogo-standalone && python3 care/server.py                   # caregiver page
open http://127.0.0.1:9300/dashboard/
```

- Glasses on the same Wi-Fi as the Mac and pointed at the hub (see `docs/GLASSES_RETURN.md` §3).
  `curl -s localhost:9100/api/state` shows `"glasses": true`.
- Battery charged, volume up, iPhone unlocked and nearby for the text.
- If Wi-Fi drops: plug USB back in; the glasses switch over by themselves.
