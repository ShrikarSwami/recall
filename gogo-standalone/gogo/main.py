r"""Gogo standalone server (no Go-go hub needed).

    gogo\.venv\Scripts\python.exe gogo\main.py [--port 9300] [--host 0.0.0.0]

Serves the lens, the simulator and the dashboard, keeps the care data (profile, goals, places, events),
and runs Gogo's guided flow. The glasses app connects to /ws/glasses (keys, worn state in; voice out),
the lens page connects to /ws/lens (what to draw).
"""
import asyncio
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "care"))

import server as care            # the care data and weather (mockup/care/server.py)
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from flow import Flow, LENS_HINT

TAP_KEYS = {"tap", "double_tap", "long_press", "swipe_forward", "swipe_back"}
TAP_CODES = {66, 142, 141, 22, 21}

app = FastAPI()
care.load()
care.save()
flow = None


@app.on_event("startup")
async def _startup():
    global flow
    flow = Flow(care)


@app.middleware("http")
async def no_cache(request: Request, call_next):
    r = await call_next(request)
    r.headers["Cache-Control"] = "no-store"
    return r


# ---------------------------------------------------------------- sockets
@app.websocket("/ws/lens")
async def ws_lens(ws: WebSocket):
    await ws.accept()
    flow.lenses.add(ws)
    care.LIVE["lensSeen"] = time.time()
    await flow.replay_to(ws)
    try:
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        flow.lenses.discard(ws)


@app.websocket("/ws/glasses")
async def ws_glasses(ws: WebSocket):
    await ws.accept()
    flow.glasses = ws
    await ws.send_text(json.dumps({"type": "config", "hint": LENS_HINT}))
    care.add_event("system", text="Glasses connected")
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                continue                          # mic audio and camera frames: not used in the standalone build
            if not msg.get("text"):
                continue
            try:
                m = json.loads(msg["text"])
            except ValueError:
                continue
            t = m.get("type")
            if t == "hello":
                if m.get("worn"):
                    await flow.play("demo")
            elif t == "worn":
                if m.get("value"):
                    if not flow.awake:
                        await flow.play("demo")
                else:
                    await flow.sleep_lens()
            elif t == "key":
                name, code = m.get("name"), m.get("code")
                care.add_event("key", name=name, code=code)
                if code == 301:                   # "glasses put on" from the wear sensor
                    if not flow.awake:
                        await flow.play("demo")
                elif name in TAP_KEYS or code in TAP_CODES:
                    await flow.on_tap()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if flow.glasses is ws:
            flow.glasses = None
        care.add_event("system", text="Glasses disconnected")


# ---------------------------------------------------------------- api (same shapes as care/server.py)
@app.get("/")
async def root():
    return RedirectResponse("/dashboard/")


@app.get("/api/state")
async def api_state():
    live = dict(care.LIVE)
    live["lensOnline"] = len(flow.lenses) > 0 or time.time() - live.get("lensSeen", 0) < 6
    live["glassesOnline"] = flow.glasses is not None
    return {"profile": care.STATE["profile"], "goals": care.STATE["goals"], "places": care.STATE["places"], "live": live, "now": time.time()}


@app.get("/api/events")
async def api_events(since: int = 0):
    with care.LOCK:
        return {"events": [e for e in care.EVENTS if e["id"] > since][-400:]}


@app.get("/api/inbox")
async def api_inbox(since: int = 0):
    with care.LOCK:
        return {"items": [m for m in care.INBOX if m["id"] > since]}


@app.get("/api/weather")
async def api_weather():
    return await asyncio.to_thread(care.weather)


@app.post("/api/profile")
@app.post("/api/goals")
@app.post("/api/places")
async def api_set(request: Request):
    key = request.url.path.split("/")[-1]
    b = await request.json()
    with care.LOCK:
        care.STATE[key] = b.get(key, b)
        care.save()
    if key == "places":
        care.WEATHER["at"] = 0
    care.add_event("system", text="Care plan updated: %s" % key)
    return {"ok": True}


@app.post("/api/event")
async def api_event(request: Request):
    b = await request.json()
    kind = b.pop("type", "system")
    return {"ok": True, "id": care.add_event(kind, **b)["id"]}


@app.post("/api/instruct")
async def api_instruct(request: Request):
    b = await request.json()
    text = (b.get("text") or "").strip()
    if not text:
        return JSONResponse({"ok": False}, 400)
    with care.LOCK:
        care.SEQ["inbox"] += 1
        msg = {"id": care.SEQ["inbox"], "ts": time.time(), "kind": b.get("kind", "message"), "text": text, "speak": b.get("speak", True)}
        care.INBOX.append(msg)
    care.add_event("instruction", text=text, kind=msg["kind"], by=b.get("by", "Family dashboard"))
    await flow.deliver(msg)                      # straight to the lens and the speaker
    return {"ok": True, "id": msg["id"]}


@app.post("/api/reset")
async def api_reset():
    with care.LOCK:
        care.EVENTS.clear()
        care.INBOX.clear()
        care.LIVE.update({"location": "seat", "step": "", "lastLucia": "", "scene": "idle"})
    return {"ok": True}


# ---------------------------------------------------------------- flow control (for testing and the demo operator)
@app.get("/api/flow")
async def api_flow():
    return flow.status()


@app.post("/api/flow/start")
async def api_flow_start():
    await flow.play("demo")
    return flow.status()


@app.post("/api/flow/next")
async def api_flow_next():
    await flow.on_tap()
    return flow.status()


@app.post("/api/flow/stop")
async def api_flow_stop():
    await flow.sleep_lens()
    return flow.status()


@app.post("/api/flow/options")
async def api_flow_options(request: Request):
    b = await request.json()
    if "voice" in b:
        flow.voice = bool(b["voice"])
    if "auto" in b:
        flow.auto = bool(b["auto"])
    return flow.status()


app.mount("/", StaticFiles(directory=ROOT, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    a = sys.argv[1:]
    port = int(a[a.index("--port") + 1]) if "--port" in a else 9300
    host = a[a.index("--host") + 1] if "--host" in a else "0.0.0.0"
    print("Gogo server on http://%s:%d  (dashboard /dashboard/, lens /glasses/lens/, simulator /glasses/sim/)" % (host, port), flush=True)
    uvicorn.run(app, host=host, port=port, log_level="warning")
