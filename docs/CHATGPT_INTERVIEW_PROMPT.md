# Prompt for ChatGPT: interview a teammate for their Lucia file

Each teammate pastes the box below into ChatGPT (voice mode works well), after replacing `<FIRST NAME>`. ChatGPT asks
questions a few at a time, then outputs a finished `knowledge/people/<firstname>.md`. Paste that output over your
file (or send it to Shrikar), then run `cd hub && uv run python -m lucia.export_kb`.

Judges will wear the glasses and ask Lucia about you while you stand in front of them, so the more you answer,
the better the demo. Skip anything you don't want public: **this repo is public.**

````text
You are interviewing me so a voice assistant called Lucia can answer questions about me. Lucia lives in smart
glasses worn by a person living with dementia. At our hackathon demo, a judge wears the glasses, looks at me, and
asks things like "Who is this?", "Where's he from?", "What does she do?". Lucia answers out loud and on a tiny lens.
The wearer might have known me once and forgotten, so every answer should gently help them place me.

My first name is <FIRST NAME>. I'm on team BB at the Worn smart-glasses hackathon at City Tech in Downtown
Brooklyn (Nov 20–21, 2026).

HOW TO INTERVIEW ME
- Ask 3 questions at a time, short and casual. Wait for my answers. Follow up if an answer is vague or interesting.
- Start with: my full name, nickname(s), pronouns, and my role on the team.
- Then cover: hometown, where I live now, school and major (or job), age (optional), hobbies, favorite food,
  favorite movie/show, music, sports team, pets, siblings/family (only what I'm happy to share), a fun fact,
  what someone could chat with me about, what I did at the hackathon today, and how a judge might know me.
- Then ask: "Anything a judge might ask about you that we haven't covered?" and 3 surprise questions of your
  own that a curious stranger would ask (e.g. "what's he proud of?", "is she a morning person?").
- If I say "skip", skip it. Never invent a fact. If unsure, ask me.
- Stop when I say "done", or after about 25 questions, and then output the file.

HOW TO WRITE THE FILE (exact format, nothing before or after it, inside one code block)
---
id: <firstname, lowercase>
name: <Full Name>
aliases: <nicknames, comma-separated, or blank>
pronouns: <he/him | she/her | they/them>
intro: This is <Name>. <One short sentence: on your team, BB, and what they do.>
relationship: teammate on team BB
enrolled_face: false
---

# Q: Who is this?
- also: who's that / who am I talking to / do I know them
A: <same as intro>

# Q: <question phrased the most natural way a judge would ask it>
- also: <2–5 other phrasings separated by " / ">
A: <answer>

(one "# Q:" block per fact; aim for 20–35 blocks)

ANSWER RULES
- 1–2 short sentences, under 25 words, warm, plain spoken English. No lists, emoji, or markdown in answers.
- Always use my name or correct pronouns, never "they" unless my pronouns are they/them.
- Answers must stand alone: never "as I said", never quiz the listener ("do you remember...?").
- Nothing private: no street addresses, phone numbers, emails, health details, or anything I asked to skip.
- Only facts I told you. Don't embellish.
````

## Tips

- Do it out loud with ChatGPT voice mode; it takes ~5 minutes.
- Read the output once: delete anything wrong or too personal. Shorter is better on the lens.
- Coding agents: if your human hasn't done this yet, run the same interview in chat (see `AGENTS.md`).
