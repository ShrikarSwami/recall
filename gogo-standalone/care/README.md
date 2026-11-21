# Lucia Care: dashboard + care server (demo)

```
python mockup/care/server.py          # http://localhost:9300
```

| URL | What |
|---|---|
| `/dashboard/` | For family, friends and clinicians: live view (location map, attention, what he looks at, conversation, activity), profile, 6-day plan, places and route, and "Send to Lucia". |
| `/glasses/sim/` | The glasses simulator. Press **Run the demo day**. It reads the profile, plan and route from the server and logs everything it does. |
| `/glasses/lens/` | The page the M6 shows (no controls). |

## What is real and what is demo

- **Real:** the care data (saved in `data.json`), the weather (Open-Meteo, looked up by the server from the place's coordinates: nothing else is sent), the instructions from the dashboard to the lens (polled every 1.5 s), the event log.
- **Demo / simulated:** location (the simulator reports it step by step), "looking around" vs "walking straight" and "what he is looking at" (marked *demo* on the dashboard). On the glasses these come from the head-motion sensor and the camera; that is not built yet.
- **Placeholders to confirm at the venue:** the gate, bathroom and seat directions (Places tab).

## API (what the hub will take over)

`GET /api/state` · `POST /api/profile|goals|places` · `GET /api/events?since=N` · `POST /api/event` · `POST /api/instruct` · `GET /api/inbox?since=N` · `GET /api/weather` · `POST /api/reset`
