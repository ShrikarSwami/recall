"""Lucia care server: one small Python server (standard library only) for the demo.

    python care/server.py [--port 9300] [--host 127.0.0.1]

It does three jobs:
  1. serves the static files in this folder (the glasses lens, the simulator, the dashboard),
  2. keeps the care data (profile, 6-day goals, places) and the live event log, and
  3. looks up the weather (Open-Meteo, no key) and passes instructions from the dashboard to the glasses.

Real system: this is what the hub (hub/lucia/server.py) will do; the endpoints are written so they can move over.
"""
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA_FILE = os.path.join(HERE, "data.json")
LOCK = threading.Lock()

DEFAULTS = {
    "profile": {
        "name": "Mike", "age": 74, "gender": "man", "stage": "Middle",
        "limitations": "Forgets recent events. Needs one short instruction at a time. Can get anxious in crowds.",
        "remembers": "His wife Anna, old songs, fishing trips, his daughter's name.",
        "forgets": "What day it is, where he left his things, faces he met today.",
        "easy": "Walking short distances, washing his hands, sitting down at a table, drinking water.",
        "caregiver": "Anna (wife)", "notes": "Demo data. Likes to be called Mike."
    },
    "goals": [
        {"day": 1, "items": ["Freshen up and wash hands", "Get back to your seat", "Drink a glass of water"]},
        {"day": 2, "items": ["Short walk with a friend", "Lunch at the table"]},
        {"day": 3, "items": ["Call Anna", "Look through the photo album"]},
        {"day": 4, "items": ["Morning stretch", "Help set the table"]},
        {"day": 5, "items": ["Visit from Priya", "Afternoon tea"]},
        {"day": 6, "items": ["Garden walk", "Early dinner"]}
    ],
    "places": {
        "city": "CUNY, Brooklyn", "lat": 40.6955, "lon": -73.9872,
        "gate": "top right", "bag": "Right behind you", "seat": "Your seat, next to your bag",
        "routeToBathroom": [
            "Stand up slowly. Step back a little.",
            "Head to the gate, in the top right corner.",
            "Go through the gate, then turn left.",
            "The bathroom is the first door on your right."
        ],
        "routeBack": [
            "Turn around and head back to the gate.",
            "Walk straight, toward your friends.",
            "Your seat is the one with your bag."
        ]
    }
}

STATE = {}
EVENTS = []      # newest last
INBOX = []       # instructions for the glasses
SEQ = {"event": 0, "inbox": 0}
LIVE = {"location": "seat", "step": "", "lastLucia": "", "lensSeen": 0, "scene": "idle"}
WEATHER = {"at": 0, "data": None}


def load():
    global STATE
    if os.path.exists(DATA_FILE):
        try:
            STATE = json.load(open(DATA_FILE, encoding="utf-8"))
        except Exception:
            STATE = {}
    for k, v in DEFAULTS.items():
        STATE.setdefault(k, json.loads(json.dumps(v)))


def save():
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(STATE, f, indent=1)
    os.replace(tmp, DATA_FILE)


def add_event(etype, **kw):
    with LOCK:
        SEQ["event"] += 1
        ev = {"id": SEQ["event"], "ts": time.time()}
        ev.update(kw)
        ev["type"] = etype
        EVENTS.append(ev)
        if len(EVENTS) > 3000:
            del EVENTS[:500]
        if etype == "location":
            LIVE["location"] = kw.get("place", LIVE["location"])
        elif etype == "step":
            LIVE["step"] = kw.get("text", "")
            LIVE["scene"] = kw.get("scene", LIVE["scene"])
        elif etype == "lucia":
            LIVE["lastLucia"] = kw.get("text", "")
        return ev


# ---------------------------------------------------------------- weather
WMO = {0: "sunny", 1: "sunny", 2: "partly cloudy", 3: "cloudy", 45: "foggy", 48: "foggy", 51: "drizzly", 53: "drizzly", 55: "drizzly",
       56: "icy", 57: "icy", 61: "rainy", 63: "rainy", 65: "rainy", 66: "icy", 67: "icy", 71: "snowy", 73: "snowy", 75: "snowy", 77: "snowy",
       80: "rainy", 81: "rainy", 82: "rainy", 85: "snowy", 86: "snowy", 95: "stormy", 96: "stormy", 99: "stormy"}


def weather():
    now = time.time()
    if WEATHER["data"] and now - WEATHER["at"] < 600:
        return WEATHER["data"]
    p = STATE["places"]
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&temperature_unit=fahrenheit&timezone=auto"
           "&current=temperature_2m,apparent_temperature,weather_code,is_day" % (p["lat"], p["lon"]))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lucia-demo"}), timeout=5) as r:
            cur = json.load(r)["current"]
        code, feels, day = int(cur["weather_code"]), float(cur["apparent_temperature"]), int(cur.get("is_day", 1))
        sky = WMO.get(code, "cloudy")
        if sky == "sunny" and not day:
            sky = "clear"
        chill = ("freezing cold" if feels < 32 else "quite cold" if feels < 45 else "a little chilly" if feels < 58
                 else "pretty warm" if feels > 85 else "")
        data = {"ok": True, "sky": sky, "tempF": round(float(cur["temperature_2m"])), "feelsF": round(feels), "chill": chill,
                "isDay": bool(day), "city": p["city"], "source": "open-meteo.com"}
    except Exception as e:
        data = {"ok": False, "error": str(e)[:120]}
    WEATHER["at"], WEATHER["data"] = now, data
    return data


# ---------------------------------------------------------------- http
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if not u.path.startswith("/api/"):
            if u.path in ("/", ""):
                self.send_response(302); self.send_header("Location", "/dashboard/"); self.end_headers(); return
            return super().do_GET()
        if u.path == "/api/state":
            with LOCK:
                live = dict(LIVE)
            live["lensOnline"] = time.time() - live.get("lensSeen", 0) < 6
            return self._json({"profile": STATE["profile"], "goals": STATE["goals"], "places": STATE["places"], "live": live, "now": time.time()})
        if u.path == "/api/events":
            since = int(q.get("since", ["0"])[0])
            with LOCK:
                out = [e for e in EVENTS if e["id"] > since][-400:]
            return self._json({"events": out})
        if u.path == "/api/inbox":
            since = int(q.get("since", ["0"])[0])
            with LOCK:
                LIVE["lensSeen"] = time.time()
                out = [m for m in INBOX if m["id"] > since]
            return self._json({"items": out})
        if u.path == "/api/weather":
            return self._json(weather())
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        b = self._body()
        if u.path in ("/api/profile", "/api/goals", "/api/places"):
            key = u.path.split("/")[-1]
            with LOCK:
                STATE[key] = b.get(key, b)
                save()
            if key == "places":
                WEATHER["at"] = 0
            add_event("system", text="Care plan updated: %s" % key)
            return self._json({"ok": True})
        if u.path == "/api/event":
            kind = b.pop("type", "system")
            ev = add_event(kind, **b)
            return self._json({"ok": True, "id": ev["id"]})
        if u.path == "/api/instruct":
            text = (b.get("text") or "").strip()
            if not text:
                return self._json({"ok": False}, 400)
            with LOCK:
                SEQ["inbox"] += 1
                msg = {"id": SEQ["inbox"], "ts": time.time(), "kind": b.get("kind", "message"), "text": text, "speak": b.get("speak", True)}
                INBOX.append(msg)
            add_event("instruction", text=text, kind=msg["kind"], by=b.get("by", "Family dashboard"))
            return self._json({"ok": True, "id": msg["id"]})
        if u.path == "/api/reset":
            with LOCK:
                EVENTS.clear(); INBOX.clear()
                LIVE.update({"location": "seat", "step": "", "lastLucia": "", "scene": "idle"})
            return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)


def main():
    port, host = 9300, "127.0.0.1"
    a = sys.argv[1:]
    if "--port" in a:
        port = int(a[a.index("--port") + 1])
    if "--host" in a:
        host = a[a.index("--host") + 1]
    load()
    save()
    srv = ThreadingHTTPServer((host, port), Handler)
    print("Lucia care server on http://%s:%d  (dashboard: /dashboard/, simulator: /glasses/sim/)" % (host, port), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
