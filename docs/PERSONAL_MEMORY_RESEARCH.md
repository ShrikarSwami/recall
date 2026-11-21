# Personal memory: research and proposed fact entry

Research checked: **November 21, 2026**. Status: **design proposal, not an implemented feature**.

## Recommendation

Add a private personal profile that the wearer can contribute to, with support from a chosen caregiver. Pair simple phone forms with optional spoken fact capture. Keep the glasses interaction simple: ask a question, hear a short answer, and ask again whenever needed.

For example, an authorized person enters “My dog's name is Buster.” Once the intended fact is confirmed and saved, “What's my dog's name?” can receive “Your dog's name is Buster.” A positive answer to “Do I have a dog?” additionally requires that this is the wearer's **current** pet, not a childhood memory or another person's dog.

This is a natural extension of the question bank: reusable question phrasings resolve to private personal facts, rather than thousands of separately authored personal answers. Buster is a fictional example throughout this document; it must not become a fact about the demo wearer.

## Independence and everyday choices

The profile should support things the person wants to do: choosing groceries, taking part in plans, or finding a familiar reminder. Offer help where wanted without automatically taking over. Independence can include chosen support, and the person can prefer an ordinary written list. This is a design aim, not a demonstrated outcome of the prototype.

See [Independence, comparisons, and pantry demonstration](COMPARISONS_AND_PANTRY.md) for researched context, new comparison Q&A, a fictional food-inventory fixture, and the distinction between the working answer bank and a proposed live pantry connection.

## What people use now

These are approaches described in current dementia-support guidance, not a survey establishing how often every caregiver uses them. Needs and the usefulness of each aid vary by person.

| Approach | How it is used | Implication for our design |
|---|---|---|
| Notes, calendars, diaries, and whiteboards | Visible reminders record plans and tasks; daily journals can record recent events. Phone reminders and voice assistants are also described as options. [S1] | Support short reminders and familiar formats, with an optional printable copy. Distinguish a daily event from a lasting personal fact. |
| Memory books and photographs | Pictures and brief descriptions can record people and relationships; a supporter can write down a repeated answer. [S2] | Let a personal entry include an optional photo, a name, and a short relationship description. |
| Life-story work | A person records important experiences, people, and places, with help if wanted. Records can be books, photo albums, or digital materials. [S3] | Include past experiences and interests, with clear time context. The person's participation matters. |
| Personal support profiles | Alzheimer's Society's “This is me” records personal background, preferences, and routines for people providing care. Its form explicitly includes family, friends, pets, and valued possessions. [S4, S5] | A small, editable “About me” profile is grounded in an existing practice. Include who supplied the information and when it was reviewed. |
| Patient responses to repeated questions | Alzheimer's Association recommends calm repetition and meaningful notes, clocks, calendars, or photos; repeated questions can also express an emotional concern. [S6] | Give a useful answer each time. More facts alone will not address every need for reassurance or human support. |

**Who writes it?** The person may write or record information themselves, or work with family and care professionals. “This is me” specifically asks people who know the person well to complete it with the person's involvement wherever possible and to update it as needed. [S3, S5]

**What this supports:** a digital, accessible version of familiar personal records, available through a spoken question. Our inference is that the glasses might reduce the effort of finding a particular note. This research does not establish that our prototype improves memory, reduces caregiver workload, or is suitable for every stage of dementia. Those outcomes require evaluation with people using it.

## Current repository versus proposed feature

Snapshot checked against the repository on November 21, 2026:

| Area | Present now | Proposed addition |
|---|---|---|
| Saved answers | Markdown questions, alternate phrasings, and short answers loaded by `hub/lucia/knowledge.py` | Private, structured personal facts linked to reusable question types |
| Caregiver phone | Feed, alerts, state, and a patient-name form in `caregiver-web/index.html` | A simple personal-information form, corrections, and optional suggested-fact review |
| Name endpoint | `POST /api/patient` changes the in-memory name; it is not a durable personal-profile editor | Explicit persistence with save success/failure feedback |
| Spoken information | Questions are answered through the existing brain | Optional explicit fact capture, read-back, and confirmation |
| Knowledge export | `export_kb.py` uses example config for simulator files but loads the public knowledge directory | A separate private store that public exports cannot accidentally include |

The general facts editor mentioned in `SPEC.md` is a planned feature; the inspected phone page does not implement it. No runtime code, routes, private profiles, or saved-answer behavior were changed for this document.

## Suggested first version: a simple phone form

Start with a handful of optional sections. A wearer who wants to contribute can fill them in, independently or with support. Do not make completion a test or require every field.

| Section | Example prompts |
|---|---|
| About me | What name would you like to be called? What language do you prefer? |
| Important people | What is their name? How do you know each other? What would you like remembered? |
| Pets | Do you currently have a pet, have no current pets, or prefer to leave this unknown? What is its name and kind? Is this a current pet or a past memory? |
| Interests | What music, hobbies, work, or places would you like to talk about? |
| Comfort and communication | What usually feels comforting? Would you prefer quieter speech or more time to reply? |
| Optional reminders | What short reminder would you like available? Does it apply on a particular day or until a particular time? |

Use plain labels, optional fields, a clear **Save** button, and an easy **Change** or **Remove** action. Preview the short answer before saving. Include an optional photo only with permission. Passwords, payment details, and medication instructions are outside this first version.

Caregiver access must be authorized; anyone connected to the same Wi-Fi must not automatically gain permission to read or change a private profile. This is a requirement for the proposed feature, not an existing security claim.

## Optional spoken entry

A separate save action should be explicit. Ordinary speech must not automatically become a permanent fact.

Example proposed interaction, after “{wake}”:

1. Wearer: “Remember, my dog's name is Buster.”
2. Assistant: “Would you like me to remember Buster as your current dog's name?”
3. Wearer: “Yes.”
4. The system saves the fact durably if the person's configured permissions allow it.
5. Assistant, **only after a successful save**: “Saved. Your dog's name is Buster.”
6. Later: “What's my dog's name?” → “Your dog's name is Buster.”

If the wearer instead just says “My dog's name is Buster,” the assistant may offer the same optional save prompt once. Silence, an unclear answer, or a change of subject is not confirmation. Do not repeatedly prompt the wearer to complete a profile.

For people who choose it, low-risk, clearly confirmed self-reports can be active immediately and marked as self-reported. A caregiver can help review them. A supported-review setting can keep new spoken entries pending until an authorized supporter checks them; pending entries must not be presented as established facts. These are proposed user choices, not a rule that a caregiver must approve everything a person says.

For ambiguous names, offer a simple read-back or phone correction. Do not make the wearer spell a name or navigate a menu. “Save failed” must produce a gentle, truthful response rather than “Saved.”

## Information that needs context

| Input | Interpretation |
|---|---|
| “My dog is named Buster.” | Candidate fact about a dog; confirm ownership and current status before generating current-pet answers. |
| “My daughter has a dog named Buster.” | The daughter's dog, not the wearer's dog. |
| “I had a dog named Buster as a child.” | Historical memory; does not establish a current pet. |
| “Do I have a dog named Buster?” | A question, not evidence that Buster exists. |
| “I wish I had a dog named Buster.” | A wish, not a fact to activate. |
| “Buster lives with my daughter now.” | A living-arrangement update; do not infer the dog is nearby or that ownership changed. |
| “Actually, his name is Baxter.” | Resolve which pet is being discussed and confirm the correction; do not overwrite a different pet. |
| “I don't have a dog anymore.” | A possible current-status change. Keep the earlier record as history and resolve the update without arguing. |
| “I had lunch.” | A time-limited event, with date and source; not a permanent answer to whether lunch happened today. |

Do not force a disagreement between a wearer and caregiver into a confident answer. Keep conflicting versions separate for review, preserve the earlier history, and use a gentle unknown response until resolved. A person's preferences can change; a caregiver entry is not automatically more authoritative about what that person currently wants.

## What to store

Proposed per-fact metadata, kept privately rather than in the public question files:

| Field | Purpose |
|---|---|
| Wearer/profile ID and fact ID | Keep people and records separate |
| Subject and relationship | Distinguish the wearer's pet from another person's pet |
| Fact type and value | For example, pet name, pet kind, or preferred music |
| Current/past/unknown status | Avoid treating an old memory as a current situation |
| Source and author | Wearer self-report, authorized caregiver, or another explicit source |
| Confirmation/review state | Pending, active, conflicting, superseded, or removed |
| Created, updated, and reviewed times | Make the record's age and change history visible |
| Valid-from/valid-until when relevant | Keep appointments and daily events from becoming stale facts |
| Sharing and retention choice | Control who may use it and when it should be deleted |

Use precise state names. “Confirmed” means someone checked the intended wording; it is not independent proof that a factual claim is true. Repetition alone must not upgrade a claim's reliability. Raw audio and full conversations are not required to remember a pet name and should not be retained by default in this proposed flow.

Use a private runtime store, such as a future database under the already-ignored `hub/data/` directory. Merely putting data in an ignored folder is not encryption or access control. Public Markdown, public simulator exports, screenshots, and source-control history must not receive real profile data. Private profile export, if offered, must be an explicit authorized action.

## Fast answers from one fact

Bind question families to structured fields:

| Question family | Required information | Example answer |
|---|---|---|
| “Do I have a dog?” / “Have I got a pet dog?” | Current dog linked to this wearer | “Yes. Your dog's name is Buster.” |
| “What's my dog's name?” / “What do I call my dog?” | A single resolved current dog and its name | “Your dog's name is Buster.” |
| “Who is Buster?” / “Remind me about Buster.” | Resolved pet identity and relationship | “Buster is your dog.” |
| “What breed is Buster?” | Breed explicitly supplied | Unknown unless that detail is saved |
| “Where is Buster right now?” | Fresh, appropriate location information | Unknown unless that information is actually available |

Unknown is different from a confirmed absence. An empty pet list must not mean “You have no pets.” Multiple dogs require resolving which one, rather than randomly choosing a name.

Proposed lookup order: preserve the existing distress/time/face/scene handling where applicable; within personal-fact questions, prefer an eligible fact in the correct profile over the generic “I don't have that saved” response. Detect personal questions before allowing an LLM to invent or fill personal values. Keep model fallback for suitable other requests.

The existing fuzzy matcher does **not** yet guarantee this personal-fact precedence. Adding a competing personal Q&A entry beside a generic pet fallback is not enough to implement the design correctly.

On an authorized save, pre-render short answer templates, refresh affected lookup entries, and invalidate old text or speech caches for that profile and fact version. Unchanged facts can reuse their ready answers. An LLM may assist with an unfamiliar proposed entry, but need not run for every familiar pet question. Speech recognition and audio playback still take time; this is not an end-to-end instant-response guarantee.

## Scope and review criteria

Recommended sequence:

1. Design review with the team and people who would use the system; use fictional profiles for the hackathon.
2. Private phone-based entry for names, relationships, pets, interests, and comfort preferences.
3. Deterministic profile lookup, persistence, authorization, correction, deletion, and cache invalidation.
4. Optional spoken capture with read-back and the person's chosen review approach.
5. Evaluate usability and comfort before expanding to more sensitive information.

Before describing it as working, verify: facts survive restart; the right wearer gets the right answer; past pets don't become current pets; negation and corrections work; an unclear statement stays pending; conflicting facts don't silently overwrite; deletion removes the fact and derived cache entries; private facts stay out of public exports; and known personal questions avoid model calls. Include repeated questions without making the wearer feel tested.

This proposal supports access to personal information and conversation. It is not a memory-restoring treatment, a clinical assessment, or a replacement for human support.

## Sources

All accessed November 21, 2026. Research findings above are attributed; the proposed product flows and architecture are our design recommendations.

- **[S1] Alzheimer's Society — [Memory aids and tools](https://www.alzheimers.org.uk/get-support/living-with-dementia/memory-aids-and-tools).** Notes, diaries, journals, clocks, smartphones, smart devices, and apps.
- **[S2] Alzheimer's Society — [Practical tips for supporting someone with memory loss](https://www.alzheimers.org.uk/about-dementia/stages-and-symptoms/dementia-symptoms/memory-loss-support-tips).** Written answers, photographs, brief personal descriptions, and patient repetition.
- **[S3] Alzheimer's Society — [Therapy and approaches for memory loss support](https://www.alzheimers.org.uk/about-dementia/stages-and-symptoms/dementia-symptoms/approaches-therapy-memory-loss).** Life-story records created with the person, optionally supported by family or care professionals.
- **[S4] Alzheimer's Society — [This is me](https://www.alzheimers.org.uk/get-support/publications-factsheets/this-is-me).** Personal support profiles used across home and care settings.
- **[S5] Alzheimer's Society — [This is me: printable form](https://www.alzheimers.org.uk/sites/default/files/2020-03/This%20is%20me%201553_0.pdf).** Personal background, pets, routines, preferences, authorship, participation, and updates.
- **[S6] Alzheimer's Association — [Repetition](https://www.alz.org/help-support/caregiving/stages-behaviors/repetition).** Reassurance and meaningful external memory aids; attention to the concern behind a repeated question.
