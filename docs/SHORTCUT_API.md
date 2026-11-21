# iPhone Shortcut → hub: the place contract (owner: Abhiram)

The wearer's iPhone tells the hub where they are. The hub keeps only a **place name, a kind, and minutes to
home**: never coordinates, and never the home address (that stays on the phone; the Shortcut computes the
travel time itself).

## Endpoint

```
POST http://<hub-ip>:9100/api/place
Header: X-Lucia-Token: <apiToken from config/app.local.json on the hub Mac>   (or ?token=... in the URL)
Content-Type: application/json

{"name": "Whole Foods in Hoboken", "kind": "grocery", "home_min": 10}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | What Lucia says: "You're at **Whole Foods in Hoboken**." Max 60 chars. |
| `kind` | no (default `place`) | Picks the reminder section in `config/reminders*.md`: `grocery`, `home`, `pharmacy`, `work`, … |
| `home_min` | no | Minutes to home, a number (string numbers are fine). Omit if unknown. |

Response: `{"ok": true, "said": "You're at Whole Foods in Hoboken. Home is about 10 minutes away. You need: whole milk and ground tofu."}`
(`said` is `""` when it's the same place again within 30 minutes: no repeats.)
Errors: `401` wrong/missing token · `400` no name. Requests from the hub Mac itself need no token.

## What the wearer gets

- **On arrival** (new place, or same place after 30 min): the glasses say where they are, how far home is,
  and that place kind's reminders once. For `grocery`, the reminders are read as a shopping list.
- **"Lucia, where am I?"** for the next 15 minutes answers from this place:
  "You're at Whole Foods in Hoboken. Home is about 10 minutes away." After that it falls back to the preset
  place in config (City Tech for the demo).

## Building the Shortcut (iOS Shortcuts app)

1. **Get Current Location**.
2. **Get Details of Locations** → *Name* (or set a fixed name for the demo, e.g. "Whole Foods in Hoboken").
3. **Get Travel Time** from Current Location to your Home contact/address → *Duration* (in minutes).
   Home stays on the phone; only the minutes are sent.
4. **Get Contents of URL**: `http://<hub-ip>:9100/api/place`, Method **POST**, Headers `X-Lucia-Token`,
   Request Body **JSON**: `name` = step 2, `kind` = `grocery` (text), `home_min` = step 3.
5. Optional automation: Shortcuts → Automation → **Arrive** at a location → run this Shortcut.

For the stage demo, tap **Run** on the Shortcut: a fixed `name` + `kind` is the most reliable.

## Demo: Fall

A second Shortcut stands in for the fall sensor on stage. It sends the urgent caregiver text and says
"are you okay" on the glasses. The event is logged with source `api`, so the caregiver feed shows it was a demo trigger.

```
POST http://<hub>:9100/api/fall?token=<apiToken>
```

No body. Response: `{"ok": true}`. Errors: `401` wrong or missing token.
Set `LUCIA_DRY_RUN=1` on the hub to rehearse without sending a real text.

## Testing without the phone

```bash
curl -XPOST localhost:9100/api/place -H 'content-type: application/json' \
  -d '{"name":"Whole Foods in Hoboken","kind":"grocery","home_min":10}'
```
Tests: `hub/tests/test_place_api.py` (token, once-per-arrival, bad input), `hub/tests/test_day.py`.

## Network

Everything is on the venue Wi-Fi **"event"**: the iPhone posts to the hub Mac's IP on that network
(`ipconfig getifaddr en0` on the Mac). If the Wi-Fi blocks device-to-device traffic, use the Mac's phone hotspot
or Tailscale (`http://<mac-tailscale-ip>:9100`).
