# caregiver-web/: the caregiver's phone page

`index.html` is served by the hub at `http://<hub>:9100/caregiver`. It's deliberately rough. Frontend devs:
make it calm, clear and phone-first.

What it shows (from `ws://<hub>/ws/caregiver` events + `GET /api/state`):
- **Alerts:** only distress ("I want to go home", "I'm scared"). The caregiver also gets a real iMessage.
- **Right now:** glasses connected, being worn, who's in front of them.
- **What they asked:** each question + Go-go's answer, with "asked N× in 10 min" for repeats (a useful signal
  for caregivers, never shown to the patient).
- **Patient name:** `POST /api/patient {"name": "..."}` swaps the patient's name live (e.g. to a judge's).

Event shapes (one JSON object per message):
```js
{"type":"answer", "ts":..., "question":"who is this", "speech":"This is Sid...", "intent":"who_is_this", "repeat":2}
{"type":"alert",  "ts":..., "text":"Somya said: \"I want to go home\"", "status":"sent|dry-run|rate-limited"}
{"type":"heard"|"seen"|"worn"|"glasses"|"listening"|"timing"|"key", ...}
```
Modern browsers only (it runs on a phone, not the glasses). Keep it a single static file unless it really
needs more. The simulator's right panel mimics the phone's Messages app for the demo.
