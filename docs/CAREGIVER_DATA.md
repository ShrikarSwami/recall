# How a caregiver fills in what Lucia knows

Lucia never makes up facts about the patient or the people in their life. Everything personal comes from a
caregiver (or the patient, with help). For the hackathon these are plain files on the hub Mac. A real product
would put the same fields behind a simple caregiver phone form. The demo persona (`knowledge/patient.md`) is
deliberately almost empty: **the point is that a caregiver fills it in**.

| What | Where | Who edits | Public in this repo? |
|---|---|---|---|
| The patient: name, who looks after them, home, routines, life stories | `knowledge/patient.md` (Q&A blocks) | caregiver | demo persona only. A real patient's file must stay private. |
| People they know: name, relationship, how they met, things to talk about | `knowledge/people/<id>.md` | caregiver, or the person themself | teammates only (opt-in) |
| Their faces (so Lucia can say who's in front of them) | `faces/<id>/*.jpg`, 3 photos | caregiver, with that person's consent | **never** (gitignored; embeddings stay in memory) |
| Their day: appointments, visits, meals | `knowledge/schedule.md` | caregiver | demo day only |
| Place reminders and shopping list | `config/reminders.local.md` (`## grocery`, `## home`, …) | caregiver | **never** (gitignored). Demo copy: `config/reminders.example.md` |
| Pills / timed reminders | planned: `config/reminders.local.md` `## at HH:MM` (see `docs/PILLS_OUTLINE.md`) | caregiver | **never** |
| Patient's name, caregiver's name and phone | `config/app.local.json` | caregiver | **never** (gitignored). Example: `config/app.example.json` |
| Live: who they met, what they asked, alerts | caregiver page `http://<hub>:9100/caregiver` | read-only | logs stay on the hub (`hub/data/`, gitignored) |

## Writing good entries

- Format and rules: `knowledge/AGENTS.md`. Short (1–2 sentences, spoken aloud), warm, plain words, no
  medical advice, placeholders like `{patient}` and `{caregiver}` instead of names that might change.
- Life stories ("Tell me about my wedding") are ordinary `# Q:` blocks in `patient.md`, written *by the family*.
  Lucia reads them back exactly. Research on why this matters (memory books, life-story work, "This is me"
  profiles): `docs/PERSONAL_MEMORY_RESEARCH.md`.
- After editing: `curl -XPOST localhost:9100/api/reload` (hub Mac) or press reload on the caregiver page.

## Privacy rules (also the pitch)

Patient data lives on the patient's own devices: the glasses, the hub (stands in for their phone), and an
optional private home server for the AI model. Nothing goes to the cloud. Faces are stored as numbers, not
photos. Bystander speech is never saved. A caregiver can delete everything by deleting these files.
