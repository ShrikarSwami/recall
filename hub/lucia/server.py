"""Lucia hub. One process on the Mac; the glasses connect over USB (adb reverse) or Wi-Fi.

    cd hub && uv run python -m lucia.server            # ws://0.0.0.0:9100/ws/glasses, http://localhost:9100/caregiver

Glasses protocol: see glasses-app/.../MainActivity.kt. Caregiver page: /caregiver (live feed + alerts).
"""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from . import knowledge
from .alerts import Alerts
from .brain import Brain, Reply
from .config import DATA_DIR, FACES_DIR, KNOWLEDGE_DIR, ROOT, fill, load_config, placeholders
from .faces import Faces
from .llm import LLM
from .speech import Segmenter, Transcriber, Voice, earcon, split_wake

ARM_S = 8                 # after a tap / bare wake word, the next utterance is the question
GREET_GAP_S = 90


class Hub:
    def __init__(self):
        self.cfg = load_config()
        self.kb = knowledge.load(KNOWLEDGE_DIR)
        self.llm = LLM(self.cfg)
        self.brain = Brain(self.cfg, self.kb, self.llm)
        self.stt = Transcriber(self.cfg.get("stt", {}).get("model", "mlx-community/whisper-small.en-mlx"))
        self.voice = Voice(self.cfg["voice"].get("name", "Samantha"))
        self.alerts = Alerts(self.cfg)
        self.faces = Faces(FACES_DIR, self.cfg.get("faces", {}).get("matchThreshold", 0.45))
        self.enrolled: dict[str, int] = {}
        self.glasses: WebSocket | None = None
        self.caregivers: set[WebSocket] = set()
        self.armed_until = 0.0
        self.playing_until = 0.0
        self.worn: bool | None = None
        self.last_greet = 0.0
        self.introduced: dict[str, float] = {}
        self.face_busy = False
        self.speak_lock = asyncio.Lock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = DATA_DIR / "events.jsonl"

    # ------------------------------------------------------------------ setup
    async def start(self):
        self.enrolled = self.faces.enroll_all() if FACES_DIR.exists() else {}
        print(f"[hub] knowledge: {len(self.kb.entries)} answers, people={list(self.kb.people)}, faces={self.enrolled}")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.stt.pool, self.stt.warm)
        asyncio.create_task(self.llm.warm())

    def reload(self):
        self.cfg = load_config()
        self.kb = knowledge.load(KNOWLEDGE_DIR)
        self.brain.cfg, self.brain.kb = self.cfg, self.kb
        self.enrolled = self.faces.enroll_all() if FACES_DIR.exists() else {}
        return {"answers": len(self.kb.entries), "people": list(self.kb.people), "faces": self.enrolled}

    # ------------------------------------------------------------------ output
    async def event(self, kind: str, **data):
        ev = {"ts": time.time(), "type": kind, **data}
        with self.log_path.open("a") as f:
            f.write(json.dumps(ev) + "\n")
        dead = []
        for ws in self.caregivers:
            try:
                await ws.send_text(json.dumps(ev))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.caregivers.discard(ws)

    async def to_glasses(self, msg: dict | bytes):
        if self.glasses is None:
            return
        try:
            if isinstance(msg, bytes):
                await self.glasses.send_bytes(msg)
            else:
                await self.glasses.send_text(json.dumps(msg))
        except Exception:
            pass

    async def say(self, reply: Reply, question: str = ""):
        async with self.speak_lock:
            await self.to_glasses({"type": "card", "title": reply.title, "lines": reply.lines,
                                   "ttl_ms": max(6000, 450 * len(reply.speech.split()) + 3000)})
            await self.to_glasses({"type": "state", "value": "idle"})
            if self.cfg["voice"].get("speakAnswers", True):
                pcm = await self.voice.pcm(reply.speech)
                self.playing_until = time.time() + len(pcm) / 2 / Voice.OUT_RATE + 0.4
                for i in range(0, len(pcm), 8820):  # 200 ms chunks
                    await self.to_glasses(pcm[i:i + 8820])
        await self.event("answer", question=question, speech=reply.speech, intent=reply.intent,
                         subject=reply.subject, repeat=reply.repeat_count, score=reply.score)
        if reply.alert:
            status = await self.alerts.send(f"{self.cfg['appName']}: {reply.alert}")
            await self.event("alert", text=reply.alert, status=status)

    # ------------------------------------------------------------------ input
    async def arm(self, why: str):
        self.armed_until = time.time() + ARM_S
        await self.to_glasses({"type": "state", "value": "listening"})
        await self.to_glasses({"type": "snap"})
        await self.to_glasses(earcon())
        self.playing_until = time.time() + 0.2
        await self.event("listening", why=why)

    async def question(self, text: str):
        self.armed_until = 0
        await self.to_glasses({"type": "state", "value": "thinking"})
        t0 = time.perf_counter()
        reply = await self.brain.answer(text)
        await self.event("timing", brain_ms=round((time.perf_counter() - t0) * 1000), stt_ms=round(self.stt.last_ms),
                         llm_ms=round(self.llm.last_ms or 0))
        await self.say(reply, text)

    async def utterance(self, pcm: bytes):
        text = await self.stt.transcribe(pcm)
        if not text:
            return
        armed = time.time() < self.armed_until
        woke, rest = split_wake(text, self.cfg["wakeWord"])
        await self.event("heard", text=text, armed=armed, wake=woke)
        if armed:
            await self.question(rest if woke else text)
        elif woke:
            if len(rest.split()) >= 2:
                await self.question(rest)
            else:
                await self.arm("wake word")

    async def frame(self, jpeg: bytes):
        self.brain.latest_frame = jpeg
        if self.face_busy:
            return
        self.face_busy = True
        try:
            found, pid, score = await self.faces.identify(jpeg)
            if not found:
                return
            self.brain.saw(pid)
            if pid:
                await self.event("seen", person=pid, score=round(score, 3))
                await self.maybe_introduce(pid)
        finally:
            self.face_busy = False

    async def maybe_introduce(self, pid: str):
        cooldown = self.cfg.get("faces", {}).get("introCooldownSec", 120)
        now = time.time()
        if self.worn is False or now - self.introduced.get(pid, 0) < cooldown or pid not in self.kb.people:
            return
        if now < self.playing_until or now < self.armed_until or self.speak_lock.locked():
            return
        self.introduced[pid] = now
        self.brain.topic = (pid, now)
        r = self.brain._reply(self.brain.intro(pid), self.kb.people[pid].first, "proactive_intro", pid)
        await self.say(r)

    async def greet(self):
        if time.time() - self.last_greet < GREET_GAP_S:
            return
        self.last_greet = time.time()
        await self.say(self.brain.greeting())


hub = Hub()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await hub.start()
    yield


app = FastAPI(title="Lucia hub", lifespan=lifespan)
WEB = ROOT / "caregiver-web"


@app.websocket("/ws/glasses")
async def ws_glasses(ws: WebSocket):
    await ws.accept()
    hub.glasses = ws
    seg = Segmenter()
    vals = placeholders(hub.cfg)
    await ws.send_text(json.dumps({"type": "config", "hint": fill(hub.cfg["idleHint"], vals)}))
    await hub.event("glasses", connected=True)
    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                b = msg["bytes"]
                if b[0] == 1:
                    if time.time() < hub.playing_until:
                        seg.feed(b"\x00" * (len(b) - 1))  # don't transcribe Lucia's own voice
                        continue
                    for utt in seg.feed(b[1:]):
                        asyncio.create_task(hub.utterance(utt))
                elif b[0] == 2:
                    asyncio.create_task(hub.frame(b[1:]))
            elif msg.get("text"):
                m = json.loads(msg["text"])
                t = m.get("type")
                if t == "hello":
                    hub.worn = m.get("worn") if m.get("worn") is not None else hub.worn
                    await hub.event("hello", **{k: v for k, v in m.items() if k != "type"})
                    await hub.greet()
                elif t == "key":
                    await hub.event("key", name=m.get("name"), code=m.get("code"))
                    if m.get("name") == "tap":
                        await hub.arm("tap")
                elif t == "worn":
                    hub.worn = bool(m.get("value"))
                    await hub.event("worn", value=hub.worn)
                    if hub.worn:
                        await hub.greet()
    except WebSocketDisconnect:
        pass
    finally:
        if hub.glasses is ws:
            hub.glasses = None
        await hub.event("glasses", connected=False)


@app.websocket("/ws/caregiver")
async def ws_caregiver(ws: WebSocket):
    await ws.accept()
    hub.caregivers.add(ws)
    if hub.log_path.exists():
        for line in hub.log_path.read_text().splitlines()[-60:]:
            await ws.send_text(line)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.caregivers.discard(ws)


@app.get("/")
@app.get("/caregiver")
async def caregiver_page():
    return FileResponse(WEB / "index.html")


@app.post("/api/ask")
async def api_ask(body: dict):
    """Type a question as if spoken (testing, or a teammate driving the demo)."""
    await hub.question(body.get("text", ""))
    return {"ok": True}


@app.post("/api/say")
async def api_say(body: dict):
    r = hub.brain._reply(body.get("text", ""), body.get("title", hub.cfg["appName"]), "manual")
    await hub.say(r)
    return {"ok": True}


@app.post("/api/reload")
async def api_reload():
    return hub.reload()


@app.post("/api/patient")
async def api_patient(body: dict):
    """Swap the patient's name live (e.g. to the judge's name)."""
    name = body.get("name", "").strip()
    if name:
        hub.cfg["patient"]["name"] = name
        hub.cfg["patient"]["preferredName"] = name.split()[0]
    return {"patient": hub.cfg["patient"]}


@app.get("/api/state")
async def api_state():
    return {"glasses": hub.glasses is not None, "worn": hub.worn, "faces": hub.enrolled,
            "people": list(hub.kb.people), "answers": len(hub.kb.entries),
            "in_view": hub.brain.in_view(), "patient": hub.cfg["patient"]["name"],
            "llm_ms": hub.llm.last_ms, "stt_ms": hub.stt.last_ms}


def main():
    import uvicorn
    s = load_config().get("server", {})
    uvicorn.run(app, host=s.get("host", "0.0.0.0"), port=s.get("port", 9100), log_level="warning")


if __name__ == "__main__":
    main()
