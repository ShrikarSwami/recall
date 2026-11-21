# Lucia — submission draft

Team BB: Shrikar, Abhiram, Isha and Sid. Built for the Worn Smart Glasses Hackathon on MicroLumin M6 glasses.

This is an editable draft for the team, not a submitted entry. Confirm the prior-work details below before submitting.

## Short description

Lucia gives people living with dementia a quiet way to ask for everyday reminders. Put on the glasses, say “Lucia, who is this?” or hold the right side, and hear a short, familiar answer while it appears on the lens. Ask again and get the same calm answer, without being tested or told that you already asked.

## Why we built it

Forgetting a name or why you entered a room can turn a small moment into a reason to depend on someone else. We want to support everyday independence while keeping a caregiver close when needed. The glasses put the reminder where the person already is, without requiring them to find a phone, remember a menu or learn a new routine.

Lucia is a hackathon prototype, not a treatment or a clinically validated safety device. Supporting independence is our goal; we have not measured patient outcomes.

## How it works

The M6 Android app sends camera frames, microphone audio and relevant sensor events to a Python hub on the Mac. The hub transcribes the question, matches an enrolled face when relevant, and selects an answer from the team's markdown knowledge base. The Mac generates speech and streams it back to the glasses alongside a short lens card.

Stored answers cover people, the current demo location, orientation and everyday questions. Repeating, slowing down or stopping an answer works through spoken phrases. The app can offer another fact about a person, with a spoken yes or a nod to accept. An optional private Ollama model handles supported off-script requests; the core stored-answer path does not need a model response for every question.

An iPhone Shortcut can report a place to the hub for location reminders. Distress phrases send a caregiver iMessage through the Mac's existing Messages app. Experimental fall detection also triggers an urgent caregiver alert. The caregiver web page shows questions and alerts. There is no claim that emergency services have been contacted.

## What we built and what we reused

Our project work includes the glasses-to-hub integration, lens and simulator experience, knowledge-based answer flow, teammate profiles, speech controls, caregiver feed, reminders and alert integration. The exact event-period contribution should be checked against the preparation work before submission.

Prior work to disclose, as recorded in [SPEC.md](SPEC.md#13-prior-work-must-be-disclosed-in-the-submission):

- **`face_id`:** Shrikar's pre-existing [face recognition library](https://github.com/ShrikarSwami/face_id), used for detection and face embeddings. We did not train a new face recognition model for this event.
- **`dementia-memory-assistant`:** Shrikar's earlier dementia app informed the data model and design principles. Confirm whether any source files were also reused and identify them here.
- **Preparation code:** the specification records hub and emulator preparation on Friday Nov 20 before hacking started. Confirm which parts remain in the final build and disclose their scope rather than describing the entire codebase as written during the event.
- **Existing tools and models:** Android platform APIs, MicroLumin hardware and developer support, FastAPI, mlx-whisper and pretrained speech/face models, optional Ollama models, macOS speech synthesis, and Apple Messages. Check the final dependency list and applicable licenses before submitting.

The private MicroLumin SDK kit, signing material, face enrollment photos and local configuration are excluded from the public repository.

## Privacy, in plain language

The main processing runs on our own devices. Face matching and speech transcription run on the Mac; configured optional model requests go to our own model hosts. We do not require a public cloud AI service for the stored-answer demo. Caregiver alerts use the Mac's existing iMessage service through Apple.

Enrollment photos and local configuration stay outside git. The hub keeps a local question/answer event log, and developer recording tools can save audio, images and sensor traces locally. These files stay on the configured devices until the team removes them. This prototype does not provide a production retention policy or a verified guarantee against data loss. Use consenting demo participants and demo information.

## What the demo shows

- A familiar face identified with a short answer on the lens and through the speaker.
- Everyday orientation questions answered from stored facts, with repeat/slow/stop support.
- A distress phrase producing an iMessage with time and available place context, plus a caregiver feed entry.
- A separate experimental fall alert, demonstrated using a synthetic event rather than requiring anyone to fall.

Voice clips for the greeting, teammate introductions and common orientation answers are prepared in the background when the hub starts. Cached clips avoid repeated speech synthesis for the exact same text; recognition, networking and playback still take time. Changed names and knowledge trigger another warmup. A changed schedule or place can produce a new greeting that still needs rendering.

## Before submitting

- Confirm event-period work versus preparation and earlier projects.
- Fill in any required full team names, submission links, video and screenshots.
- Rehearse the final build on the actual glasses and verify one caregiver iMessage arrives.
- Keep fall detection described as experimental; do not claim clinical validation or guaranteed emergency response.
