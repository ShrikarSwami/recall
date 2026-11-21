# knowledge/: everything Lucia knows (anyone can edit)

Lucia only states facts written here. More good answers = a better demo, since the judges will try to stump it.

## Files

| File | About | Who fills it |
|---|---|---|
| `people/<firstname>.md` | one teammate (or a judge) | that person. **Agents: ask your human to fill theirs in.** |
| `patient.md` | the patient (demo persona, name from config) | content owner |
| `places.md` | places; `config` → `currentPlace` picks the active one | content owner |
| `faq.md` | the glasses/app itself, privacy, how-to, anything else | content owner |
| `people/_example.md`, `people/_judge.md` | templates (files starting with `_` are ignored) | — |

## Format

```markdown
---
id: abhiram            # must match the filename and faces/<id>/ photo folder
name: Abhiram Kandadi
aliases: Abhi          # nicknames, comma-separated
pronouns: he/him
intro: This is Abhiram. He's on your team and builds the backend.
---

# Q: Where is he from?
- also: what's his hometown / where did he grow up      ← optional extra phrasings, separated by /
A: Abhiram grew up in Edison, New Jersey.
```

- One `# Q:` block = one answer. Write the question the most natural way; the matcher handles paraphrases
  and he/she/they. `also:` lines make it more reliable.
- **Blank `A:` lines are skipped**, so unanswered template questions are harmless.
- Answers are **spoken aloud and shown on a tiny lens**: 1–2 short sentences, warm, plain words, no lists.
- Use placeholders instead of names that might change: `{patient}`, `{caregiver}`, `{caregiver_relationship}`, `{app}`.
- No real health details, addresses, phone numbers or anything private. This repo is public.
- After editing: `cd hub && uv run python -m lucia.export_kb` (refreshes the simulator) and, if the hub is
  running, `curl -XPOST localhost:9100/api/reload`.

## Bulk answers

`docs/CHATGPT_KB_PROMPT.md` is a ready prompt that has ChatGPT generate hundreds of Q&A blocks in this exact
format for `patient.md`, `places.md` and `faq.md`. Paste its output into the right file, skim it, and run the
tests (`cd hub && uv run pytest -q`).
