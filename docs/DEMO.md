# Demo script (3 minutes) — draft v1

> Draft for the team to workshop. Speaker roles are letters, not names, until we decide who says what.
> **A** = opener / narrator · **B, C, D** = teammates who get "recognized" · **Op** = operator at the laptop
> (hub + caregiver page), standing slightly back. Everything the judge hears from Lucia is real and live.

## Before they arrive (Op, 20 s)

- Hub running (`uv run python -m lucia.server`), glasses connected, faces enrolled, `LUCIA_DRY_RUN` **off**.
- Caregiver page open on the phone that receives the iMessage (`http://<mac>:9100/caregiver`).
- Optional: ask the judge's first name while they walk up and swap it in (caregiver page, or
  `curl -XPOST localhost:9100/api/patient -d '{"name":"<Name>"}' -H 'content-type: application/json'`).
  Lucia then greets them by name. If there's no time, they play **Somya**.

## 0:00 — Paint the picture (A, ~25 s, glasses still in hand)

> "Before we start, we want to paint a picture. We're **not** going to introduce ourselves, and that's on
> purpose. We want to put you in the shoes of someone living with dementia. You might have known all of us at
> some point. Maybe we worked together, maybe we're family. But right now, you don't remember.
>
> These glasses are called Lucia. There's nothing to learn: if you ever need anything, just say **'Lucia'**, or
> touch the right side of the glasses. That's the only instruction, and it's always written on the lens."

Hand them the glasses.

## 0:25 — Putting them on (Lucia, automatic)

Lens + voice: *"Hi {Name}. You're at City Tech, Downtown Brooklyn. Say 'Lucia' if you need anything."*

A (quietly): "Look around at us."

## 0:35 — The wow moment: it recognizes us (B steps in front)

Lucia, unprompted: *"This is B. He's on your team, BB…"* (lens: name + one line)

A: "Go ahead, ask it anything about any of us."
Prompt the judge only if they freeze: "Who is this?" · "Where's she from?" · "What does he do?" · "How do I know him?"

C and D step in one at a time; each gets introduced. **Same question twice gets the same calm answer** —
A can point that out: "Ask again. It will never say 'I already told you.'"

## 1:15 — Where am I, what day is it (judge)

A: "Now imagine you just lost track of where you are."
- "Lucia, where are we?" → *"You're at City Tech in Downtown Brooklyn, at a smart-glasses hackathon with your team."*
- "What day is it?" → *"It's Saturday, November 21st. It's about 2 in the afternoon."*

## 1:35 — Yes or no, the way you'd naturally answer (judge)

Lucia sometimes offers something: *"Want to hear more about C?"* and the lens shows
`Nod or say "yes"`. The judge can nod, shake their head, or just say yes/no. No new gesture to learn: it's what
people do anyway.

## 1:55 — Safety (judge)

A: "Last one. Say: 'I want to go home.'"
- Lucia: *"You're safe, {Name}. Shrikar knows where you are, and I'm letting him know now."*
- **Op holds up the phone: the real iMessage just arrived.** The caregiver page shows the alert.

## 2:15 — The caregiver side (Op, phone in hand)

> "This is what the caregiver sees: who you met, what you asked, and how often. You asked about C twice in two
> minutes; that's useful for a family, and the patient is never made to feel it."

## 2:35 — Close (A)

> "Everything you just saw ran on the glasses and on the family's own devices. No cloud AI, no patient data
> leaving home. Faces are only added with that person's consent. Lucia never quizzes, never corrects, and
> treats every question as the first time, because for the person asking, it is."

Pause. "Thank you."

## If something breaks (say it calmly, keep going)

| Problem | Do this |
|---|---|
| Voice not heard (loud room) | "You can also just touch the side." Touch → ask. |
| Face not recognized | Step closer, face the camera, good light. Or ask "Who is B?" by name. |
| Wi-Fi / link drops | Op restarts the glasses app; meanwhile show the simulator (`/sim/`) on the laptop. |
| iMessage slow | Show the caregiver page alert; the message lands a few seconds later. |

## Flagship moments (for the pitch and the video)

1. **"We won't introduce ourselves"** framing + automatic face introductions.
2. **Same question, same calm answer** (repeat-safe).
3. **Distress → real iMessage** to the caregiver.
4. Nod / say yes to an offer (natural, nothing to learn).
5. Local-first privacy.
