"""Lucia hub. One process on the Mac; the glasses connect over USB (adb reverse) or Wi-Fi.

    cd hub && uv run python -m lucia.server            # ws://0.0.0.0:9100/ws/glasses, http://localhost:9100/caregiver

Glasses protocol: see glasses-app/.../MainActivity.kt. Caregiver page: /caregiver (live feed + alerts).
"""
from __future__ import annotations

import asyncio
import os
from copy import deepcopy
from datetime import datetime
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import knowledge, reminders, schedule, playback
from .export_kb import export_kb
from .alerts import Alerts
from .brain import OFFER_S, Brain, Reply
from .config import DATA_DIR, FACES_DIR, KNOWLEDGE_DIR, ROOT, fill, load_config, placeholders
from .faces import Faces
from .falls import FallDetector
from .gestures import HeadGestures
from .llm import LLM
from .brain import NO, YES
from .speech import Segmenter, Transcriber, Voice, earcon, split_wake

ARM_S = 8                 # after a tap / bare wake word, the next utterance is the question
GREET_GAP_S = 90
AUDIO_LEAD_S = 0.6        # how far audio streaming runs ahead of playback (stop flushes at most this much)
# Any touch on the temple asks (the wearer never has to remember which gesture). "back" is the system's
# echo after a double tap, so it is not a touch of its own.
TOUCH_KEYS = {"tap", "long_press", "double_tap", "swipe_forward", "swipe_back"}


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
        self.lenses: set[WebSocket] = set()      # lens pages (glasses WebView, simulator)
        self.armed_until = 0.0
        self.armed_by_offer = False
        self.standby = os.environ.get("LUCIA_STANDBY") == "1"   # stage demo: lens dark and Lucia quiet until the operator starts it
        self.playing_until = 0.0
        self.worn: bool | None = None
        self.last_greet = 0.0
        self.introduced: dict[str, float] = {}
        self.face_busy = False
        self.speak_lock = asyncio.Lock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = DATA_DIR / "events.jsonl"
        self.rec: dict | None = None
        self.reminders: dict[str, list[str]] = {}
        self.arrived_at: dict[str, float] = {}   # active hardware recording (see /api/record)
        self.head = HeadGestures()
        self.imu_for_offer = False
        self.gesture_quiet_until = 0.0
        self.output_generation = 0
        self.followup_until = 0.0
        self.answer_tasks: set[asyncio.Task] = set()
        self.falls = FallDetector()
        self.voice_warm_task: asyncio.Task | None = None
        self.voice_warmup = {"state": "idle", "ready": 0, "total": 0}

    # ------------------------------------------------------------------ recording (glasses-free dev)
    async def record_start(self, label: str, seconds: float, imu: bool):
        import wave
        d = DATA_DIR / "recordings" / label
        (d / "frames").mkdir(parents=True, exist_ok=True)
        w = wave.open(str(d / "mic.wav"), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        self.rec = {"label": label, "dir": d, "wav": w, "frames": 0, "t0": time.time(),
                    "imu": (d / "imu.jsonl").open("w"), "keys": (d / "keys.jsonl").open("w")}
        if imu:
            await self.to_glasses({"type": "imu", "on": True})
        await self.event("record", label=label, state="start", seconds=seconds)
        asyncio.get_running_loop().call_later(seconds, lambda: asyncio.ensure_future(self.record_stop()))

    async def record_stop(self):
        r, self.rec = self.rec, None
        if not r:
            return
        await self.imu_wanted()
        r["wav"].close(); r["imu"].close(); r["keys"].close()
        meta = {"label": r["label"], "seconds": round(time.time() - r["t0"], 1), "frames": r["frames"]}
        (r["dir"] / "meta.json").write_text(json.dumps(meta))
        await self.event("record", state="stop", **meta)

    def record_audio(self, pcm: bytes):
        if self.rec:
            self.rec["wav"].writeframes(pcm)

    def record_frame(self, jpeg: bytes):
        if self.rec:
            self.rec["frames"] += 1
            (self.rec["dir"] / "frames" / f"{self.rec['frames']:04d}.jpg").write_bytes(jpeg)

    def record_line(self, kind: str, obj: dict):
        if self.rec:
            self.rec[kind].write(json.dumps({"t": round(time.time() - self.rec["t0"], 3), **obj}) + "\n")

    # ------------------------------------------------------------------ setup
    def load_day(self):
        """Schedule + place reminders (knowledge/schedule.md, config/reminders*.md)."""
        self.brain.events = schedule.load(KNOWLEDGE_DIR / "schedule.md")
        self.reminders = reminders.load()

    async def heads_up_loop(self):
        """A calm heads-up ~15 minutes before each schedule item, once each."""
        said: set[str] = set()
        while True:
            await asyncio.sleep(20)
            try:
                now = datetime.fromtimestamp(time.time())
                e = schedule.heads_up(self.brain.events, now, said)
                if not e or self.glasses is None or self.worn is False:
                    continue
                if time.time() < self.playing_until or time.time() < self.armed_until or self.speak_lock.locked():
                    continue
                said.add(e.key)
                mins = round((e.start - now).total_seconds() / 60)
                r = self.brain._reply(f"Just so you know, {e.title} is in about {mins} minutes.", e.title, "heads_up")
                await self.say(r)
            except Exception as ex:  # never let the reminder loop die
                print(f"[hub] heads-up error: {ex!r}")

    async def arrive(self, name: str, kind: str, home_min, force: bool = False, remember: bool = True) -> str:
        """iPhone says we're somewhere. Remember it; on a *new* arrival, say where and read that place's reminders once."""
        now = time.time()
        key = f"{kind}:{name}".lower()
        prev = self.brain.place
        self.brain.place = {"name": name, "kind": kind, "home_min": home_min, "at": now}
        new_arrival = not prev or f"{prev.get('kind')}:{prev.get('name')}".lower() != key or now - self.arrived_at.get(key, 0) > 30 * 60
        if not (new_arrival or force):
            return ""
        self.arrived_at[key] = now
        speech = " ".join(p for p in (self.brain.where_line(), reminders.arrival_lines(kind, self.reminders)) if p)
        if not remember:                    # stage demo key: show the moment, keep the real location
            self.brain.place = prev
        await self.say(self.brain._reply(speech, (name[:1].upper() + name[1:])[:22], "arrival"))
        return speech

    async def start(self):
        self.load_day()
        self.queue_voice_warmup()
        asyncio.create_task(self.heads_up_loop())
        self.enrolled = self.faces.enroll_all() if FACES_DIR.exists() else {}
        print(f"[hub] knowledge: {len(self.kb.entries)} answers, people={list(self.kb.people)}, faces={self.enrolled}")
        self.stt_names()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.stt.pool, self.stt.warm)
        asyncio.create_task(self.llm.warm())

    def stt_names(self):
        """Bias speech-to-text toward names it would otherwise mangle ("Abhiram" -> "a pyrom")."""
        names = [self.cfg["wakeWord"]] + [n for p in self.kb.people.values() for n in [p.name] + p.aliases if n]
        self.stt.hint = ", ".join(dict.fromkeys(names)) + "."

    def reload(self):
        self.cfg = load_config()
        self.kb = knowledge.load(KNOWLEDGE_DIR)
        self.brain.cfg, self.brain.kb = self.cfg, self.kb
        self.stt_names()
        self.load_day()
        self.enrolled = self.faces.enroll_all() if FACES_DIR.exists() else {}
        self.queue_voice_warmup()
        return {"answers": len(self.kb.entries), "people": list(self.kb.people), "faces": self.enrolled,
                "schedule": len(self.brain.events), "reminder_kinds": list(self.reminders)}

    def queue_voice_warmup(self):
        """Refresh exact-text audio without holding up startup or a name change."""
        if self.voice_warm_task and not self.voice_warm_task.done():
            self.voice_warm_task.cancel()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # reload can also be used by offline tools
            return
        self.voice_warm_task = loop.create_task(self.warm_voice())

    async def warm_voice(self):
        if not self.cfg["voice"].get("speakAnswers", True):
            self.voice_warmup = {"state": "disabled", "ready": 0, "total": 0}
            return
        # A preview brain must never replace the wearer's last answer or open an offer.
        preview = Brain(deepcopy(self.cfg), self.kb, clock=self.brain.clock)
        preview.events = list(self.brain.events)
        preview.place = deepcopy(self.brain.place)
        texts = [preview.greeting().speech]
        texts.extend(preview.intro_reply(pid).speech for pid in self.kb.people)
        for question in ("where are we", "why am I here", "what is my name",
                         "who takes care of me", "who are you", "how do I use this", "what can I ask you"):
            preview.offer = None
            reply = await preview.answer(question)
            if not reply.alert:
                texts.append(reply.speech)
        texts = list(dict.fromkeys(text for text in texts if text))[:24]
        status = {"state": "warming", "ready": 0, "total": len(texts)}
        self.voice_warmup = status
        for text in texts:  # sequential: leave the second TTS worker free for live answers
            try:
                if await self.voice.pcm(text):
                    status["ready"] += 1
            except Exception as ex:
                print(f"[hub] voice warmup: {type(ex).__name__}")
        status["state"] = "ready" if status["ready"] == status["total"] else "partial"
        print(f"[hub] voice cache: {status['ready']}/{status['total']} ({status['state']})")

    def alert_text(self, message: str) -> str:
        """'Lucia: <message> · 1:40 AM · City Tech, Downtown Brooklyn'. Place = the phone's fresh place, else
        the configured demo place; left out when unknown. No extra tracking."""
        stamp = datetime.fromtimestamp(self.brain.clock()).astimezone().strftime("%-I:%M %p")
        place = self.brain.live_place()
        where = (place or {}).get("name") or self.kb.places.get(self.cfg.get("currentPlace", ""), {}).get("name")
        return " · ".join(x for x in (f"{self.cfg['appName']}: {message}", stamp, where) if x)

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
        """Audio + control go to the glasses app; display messages also go to every lens page."""
        if not isinstance(msg, bytes):
            for ws in list(self.lenses):
                try:
                    await ws.send_text(json.dumps(msg))
                except Exception:
                    self.lenses.discard(ws)
        if self.glasses is None:
            return
        try:
            if isinstance(msg, bytes):
                await self.glasses.send_bytes(msg)
            else:
                await self.glasses.send_text(json.dumps(msg))
        except Exception:
            pass

    async def interrupt(self):
        """Flush the device without waiting for rendering, a model, or the speech lock."""
        self.output_generation += 1
        self.playing_until = self.armed_until = self.followup_until = 0.0
        self.brain.offer = None
        for task in tuple(self.answer_tasks):
            task.cancel()
        await self.to_glasses({"type": "audio_stop"})
        await self.to_glasses({"type": "clear"})
        await self.to_glasses({"type": "avatar", "talking": False, "perk": True})   # lens character perks up
        if self.imu_for_offer:
            self.imu_for_offer = False
            await self.imu_wanted()

    async def _stop_talking(self, generation: int, until: float):
        await asyncio.sleep(max(0.0, until - time.time()))
        if generation == self.output_generation and time.time() >= self.playing_until - 0.05:
            await self.to_glasses({"type": "avatar", "talking": False})

    async def set_standby(self, on: bool):
        """Stage demo: on = lens dark, Lucia quiet. off = welcome the wearer and start fresh."""
        self.standby = on
        await self.interrupt()
        await self.to_glasses({"type": "power", "on": not on})
        if on:
            return
        self.introduced.clear()          # everyone gets introduced again for the new judge
        welcome = self.cfg.get("demoWelcome", "Welcome! I'm {app}, here to help you remember. "
                                              "Look at someone, and I'll tell you who they are.")
        await self.event("demo_start")
        await self.say(self.brain._reply(welcome, "Welcome", "greeting",
                                         card=self.cfg.get("demoWelcomeCard", "I'm here to help you remember.")))

    async def say(self, reply: Reply, question: str = ""):
        if reply.intent == "speech_stop":
            await self.interrupt()
            return
        if self.standby and reply.intent != "fall":
            return                       # demo not started yet (falls always go through)
        generation = self.output_generation
        alert = self.alert_text(reply.alert) if reply.alert else None
        async with self.speak_lock:
            if generation != self.output_generation:
                return
            ttl = max(6000, 450 * len(reply.speech.split()) + 3000) + (OFFER_S * 1000 if reply.offer else 0)
            await self.to_glasses({"type": "card", "title": reply.title, "lines": reply.lines, "intent": reply.intent,
                                   "prompt": reply.prompt or "", "ttl_ms": ttl})
            await self.to_glasses({"type": "state", "value": "idle"})
            if self.cfg["voice"].get("speakAnswers", True):
                pcm = await self.voice.pcm(reply.speech, rate=reply.speech_rate)
                if generation != self.output_generation:
                    return
                self.playing_until = time.time() + len(pcm) / 2 / Voice.OUT_RATE + 0.4
                await self.to_glasses({"type": "avatar", "talking": True})   # lens character talks while audio plays
                asyncio.create_task(self._stop_talking(generation, self.playing_until))
                # Pace chunks so "stop" only has a small device buffer to flush, but stay ~0.6 s ahead of
                # playback so Wi-Fi jitter never starves the speaker (exact real-time pacing stutters).
                t_start = time.monotonic()
                for i in range(0, len(pcm), 8820):
                    if generation != self.output_generation:
                        return
                    await self.to_glasses(pcm[i:i + 8820])
                    ahead = (i + 8820) / (2 * Voice.OUT_RATE) - (time.monotonic() - t_start)
                    if ahead > AUDIO_LEAD_S:
                        await asyncio.sleep(ahead - AUDIO_LEAD_S)
            if generation != self.output_generation:
                return
            self.followup_until = max(time.time(), self.playing_until) + 15
            if reply.offer and self.brain.offer:
                await self.open_offer()
        await self.event("answer", question=question, speech=reply.speech, intent=reply.intent,
                         subject=reply.subject, repeat=reply.repeat_count, score=reply.score)
        if alert:
            status = await self.alerts.send(alert)
            await self.event("alert", text=alert, status=status)

    # ------------------------------------------------------------------ yes/no offers (nod or say "yes")
    async def open_offer(self):
        """Lucia just asked a yes/no question: listen for "yes"/"no" (no wake word needed) and a nod/shake."""
        until = max(time.time(), self.playing_until) + OFFER_S
        self.brain.offer.until = until
        self.armed_until = until
        self.armed_by_offer = True       # only a yes/no is taken without the wake word
        self.head.reset()
        if not self.imu_for_offer:
            self.imu_for_offer = True
            await self.to_glasses({"type": "imu", "on": True})
        await self.event("offer", offer=self.brain.offer.kind, subject=self.brain.offer.subject)
        asyncio.create_task(self._close_offer_later(until))

    async def _close_offer_later(self, until: float):
        await asyncio.sleep(max(0.0, until - time.time()) + 0.2)
        if self.brain.offer and self.brain.offer.until > time.time():
            return  # a newer offer is open
        self.brain.offer = None
        if self.imu_for_offer:
            self.imu_for_offer = False
            await self.imu_wanted()

    async def head_gesture(self, name: str, source: str = "imu"):
        reply = self.brain.gesture(name)
        await self.event("gesture", name=name, source=source, used=reply is not None)
        if reply:
            self.armed_until = 0
            await self.say(reply, f"({name})")

    # ------------------------------------------------------------------ falls (instant caregiver alert)
    @property
    def falls_on(self) -> bool:
        return bool(self.cfg.get("falls", {}).get("enabled", True))

    async def imu_wanted(self):
        """IMU streams whenever falls are on (or during an offer / a recording)."""
        await self.to_glasses({"type": "imu", "on": bool(self.falls_on or self.imu_for_offer or self.rec)})

    async def fall(self, source: str = "sensor"):
        """Text first (seconds matter), then reassure the wearer."""
        vals = placeholders(self.cfg)
        text = fill(self.cfg.get("falls", {}).get(
            "message", "WARNING: {patient} may have fallen. Please check on them urgently!"), vals)
        text = self.alert_text(text)
        await self.event("fall", source=source)
        status = await self.alerts.send(text, urgent=True)
        await self.event("alert", text=text, status=status, urgent=True)
        r = self.brain._reply("{patient}, are you okay? I've let {caregiver} know. Help is on the way.",
                              "Are you okay?", "fall")
        await self.interrupt()          # cut off whatever Lucia was saying; the fall comes first
        await self.say(r)

    def imu(self, rows: list):
        if self.falls_on:
            worn = self.worn is not False
            for row in rows:
                if self.falls.feed(row, worn=worn) == "fall":
                    asyncio.create_task(self.fall())
        now = time.time()
        if not self.brain.offer or now > self.brain.offer.until:
            return
        if now < self.gesture_quiet_until or now < self.playing_until - 1.5:
            self.head.reset()   # one nod = one answer; ignore motion while the reply is being made/spoken
            return
        g = self.head.feed(rows)
        if g:
            self.gesture_quiet_until = now + 3.0
            asyncio.create_task(self.head_gesture(g))

    # ------------------------------------------------------------------ input
    async def arm(self, why: str):
        if self.speak_lock.locked() or time.time() < self.playing_until:
            await self.interrupt()
        self.armed_until = time.time() + ARM_S
        self.armed_by_offer = False
        await self.to_glasses({"type": "state", "value": "listening"})
        await self.to_glasses({"type": "snap"})
        await self.to_glasses(earcon())
        self.playing_until = time.time() + 0.2
        await self.event("listening", why=why)

    async def question(self, text: str):
        control = playback.command(text, self.cfg["wakeWord"])
        if control == "stop":
            await self.interrupt()
            await self.event("answer", question=text, speech="", intent="speech_stop", repeat=1)
            return
        if control in ("repeat", "slow"):
            pending = self.brain.offer
            await self.interrupt()
            self.brain.offer = pending
        generation = self.output_generation
        self.armed_until = 0
        await self.to_glasses({"type": "state", "value": "thinking"})
        t0 = time.perf_counter()
        task = asyncio.create_task(self.brain.answer(text))
        self.answer_tasks.add(task)
        try:
            reply = await task
        except asyncio.CancelledError:
            return
        finally:
            self.answer_tasks.discard(task)
        if generation != self.output_generation:
            return
        await self.event("timing", brain_ms=round((time.perf_counter() - t0) * 1000), stt_ms=round(self.stt.last_ms),
                         llm_ms=round(self.llm.last_ms or 0))
        await self.say(reply, text)

    async def utterance(self, pcm: bytes, during_playback: bool = False):
        text = await self.stt.transcribe(pcm)
        if not text:
            return
        armed = time.time() < self.armed_until
        woke, rest = split_wake(text, self.cfg["wakeWord"])
        if armed and self.armed_by_offer and not woke and not (YES.search(text) or NO.search(text)):
            armed = False                # bystander talk during "Want to hear more?" is not an answer
        control = playback.command(rest if woke else text, self.cfg["wakeWord"])
        playback_finished = time.time() >= self.playing_until and not self.speak_lock.locked()
        followup = bool(control and time.time() < self.followup_until
                        and (not during_playback or playback_finished))
        if during_playback and not armed and not (woke and control) and not followup:
            await self.event("heard", ignored=True, words=len(text.split()))
            return
        if not (armed or woke or followup):
            # Bystander talk: never stored or shown. Only a word count, so we can debug "it didn't hear me".
            await self.event("heard", ignored=True, words=len(text.split()))
            return
        await self.event("heard", text=text, armed=armed, wake=woke)
        if armed or followup:
            await self.question(rest if woke else text)
        elif woke:
            if control or len(rest.split()) >= 2:
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
        if self.standby or self.worn is False or now - self.introduced.get(pid, 0) < cooldown or pid not in self.kb.people:
            return
        if now < self.playing_until or now < self.armed_until or self.speak_lock.locked():
            return
        self.introduced[pid] = now
        self.brain.topic = (pid, now)
        await self.say(self.brain.intro_reply(pid, "proactive_intro"))

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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
WEB = ROOT / "caregiver-web"
app.mount("/lens", StaticFiles(directory=ROOT / "lens", html=True), name="lens")
app.mount("/sim", StaticFiles(directory=ROOT / "sim", html=True), name="sim")


@app.websocket("/ws/lens")
async def ws_lens(ws: WebSocket):
    """Display-only feed for the lens page: config, card, state, tick. Lens pages may also send
    {"type":"key","name":"tap"} and {"type":"ask","text":...} (simulator controls)."""
    await ws.accept()
    hub.lenses.add(ws)
    await ws.send_text(json.dumps({"type": "config", "hint": fill(hub.cfg["idleHint"], placeholders(hub.cfg)),
                                   "app": hub.cfg["appName"], "patient": placeholders(hub.cfg)["patient"],
                                   "now": int(time.time() * 1000),  # the glasses' clock/timezone are wrong (set to China)
                                   "tz": int(__import__("datetime").datetime.now().astimezone().utcoffset().total_seconds() // 60)}))
    if hub.standby:
        await ws.send_text(json.dumps({"type": "power", "on": False}))
    try:
        while True:
            m = json.loads(await ws.receive_text())
            if m.get("type") == "key" and m.get("name") in TOUCH_KEYS:
                await hub.arm(m.get("name") + " (lens)")
            elif m.get("type") == "gesture" and m.get("name") in ("nod", "shake"):
                asyncio.create_task(hub.head_gesture(m["name"], "lens"))
            elif m.get("type") == "ask":
                asyncio.create_task(hub.question(m.get("text", "")))
            elif m.get("type") == "seen":
                hub.brain.saw(m.get("person"))
                if m.get("person"):
                    await hub.maybe_introduce(m["person"])
            elif m.get("type") == "worn" and m.get("value"):
                hub.worn = True
                await hub.greet()
    except WebSocketDisconnect:
        pass
    finally:
        hub.lenses.discard(ws)


@app.get("/api/kb")
async def api_kb():
    """The whole knowledge base as JSON (the simulator's mock mode uses an exported copy)."""
    return export_kb(hub.kb, hub.cfg)


@app.websocket("/ws/glasses")
async def ws_glasses(ws: WebSocket):
    await ws.accept()
    previous = hub.glasses          # e.g. real glasses, while a replay tool briefly takes over
    hub.glasses = ws
    seg = Segmenter()
    segment_generation = hub.output_generation
    echo_segment = False
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
                    hub.record_audio(b[1:])
                    if segment_generation != hub.output_generation:
                        seg = Segmenter()
                        segment_generation = hub.output_generation
                        echo_segment = False
                    playing = time.time() < hub.playing_until
                    echo_segment = echo_segment or playing
                    for utt in seg.feed(b[1:]):
                        asyncio.create_task(hub.utterance(utt, during_playback=echo_segment))
                        echo_segment = playing
                    if not seg.speaking:
                        echo_segment = False
                elif b[0] == 2:
                    hub.record_frame(b[1:])
                    asyncio.create_task(hub.frame(b[1:]))
            elif msg.get("text"):
                m = json.loads(msg["text"])
                t = m.get("type")
                if t == "hello":
                    hub.worn = m.get("worn") if m.get("worn") is not None else hub.worn
                    await hub.imu_wanted()
                    await hub.event("hello", **{k: v for k, v in m.items() if k != "type"})
                    await hub.greet()
                elif t == "imu":
                    hub.record_line("imu", {"rows": m.get("rows", [])})
                    hub.imu(m.get("rows", []))
                elif t == "key":
                    hub.record_line("keys", m)
                    await hub.event("key", name=m.get("name"), code=m.get("code"), scan=m.get("scan"), device=m.get("device"))
                    if m.get("name") in TOUCH_KEYS:
                        await hub.arm(m.get("name"))
                elif t == "worn":
                    hub.worn = bool(m.get("value"))
                    await hub.event("worn", value=hub.worn)
                    if hub.worn:
                        await hub.greet()
    except WebSocketDisconnect:
        pass
    finally:
        if hub.glasses is ws:
            hub.glasses = previous if previous is not None and previous.client_state.name == "CONNECTED" else None
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
async def root():
    return RedirectResponse("/sim/")


@app.get("/caregiver")
async def caregiver_page():
    return FileResponse(WEB / "index.html")


def require_token(request: Request):
    """Write endpoints: open to this Mac (sim, tools), token-protected for anything on the network
    (the iPhone Shortcut, a teammate's laptop). Token = "apiToken" in config/app.local.json,
    sent as header X-Lucia-Token or ?token=. With no apiToken configured, everything is open (dev)."""
    host = request.client.host if request.client else ""
    if host in ("127.0.0.1", "::1", "localhost"):
        return
    want = hub.cfg.get("apiToken")
    if want and (request.headers.get("x-lucia-token") or request.query_params.get("token")) != want:
        raise HTTPException(401, "missing or wrong X-Lucia-Token")


@app.post("/api/place", dependencies=[Depends(require_token)])
async def api_place(body: dict):
    """iPhone Shortcut: {"name": "Whole Foods in Hoboken", "kind": "grocery", "home_min": 10}.
    Only the name/kind/minutes are kept (in memory); never coordinates or the home address."""
    name = str(body.get("name", "")).strip()[:60]
    if not name:
        raise HTTPException(400, "name is required")
    kind = str(body.get("kind", "place")).strip().lower()[:20] or "place"
    home_min = body.get("home_min")
    try:
        home_min = None if home_min in (None, "") else max(0, round(float(home_min)))
    except (TypeError, ValueError):
        home_min = None
    said = await hub.arrive(name, kind, home_min, force=bool(body.get("force")), remember=body.get("remember", True) is not False)
    await hub.event("place", name=name, place_kind=kind, home_min=home_min, announced=bool(said))
    return {"ok": True, "said": said}


@app.post("/api/fall", dependencies=[Depends(require_token)])
async def api_fall():
    """Stage demo: an iPhone Shortcut stands in for the fall sensor. Same alert + voice as a real fall."""
    await hub.fall(source="api")
    return {"ok": True}


@app.post("/api/demo/start", dependencies=[Depends(require_token)])
async def api_demo_start():
    """Operator key s: lens on, WELCOME, Lucia introduces people from here."""
    await hub.set_standby(False)
    return {"ok": True}


@app.post("/api/demo/standby", dependencies=[Depends(require_token)])
async def api_demo_standby():
    """Operator key b: lens dark and Lucia quiet between judges (fall alerts still work)."""
    await hub.set_standby(True)
    return {"ok": True}


@app.post("/api/ask", dependencies=[Depends(require_token)])
async def api_ask(body: dict):
    """Type a question as if spoken (testing, or a teammate driving the demo)."""
    await hub.question(body.get("text", ""))
    return {"ok": True}


@app.post("/api/say", dependencies=[Depends(require_token)])
async def api_say(body: dict):
    r = hub.brain._reply(body.get("text", ""), body.get("title", hub.cfg["appName"]), "manual")
    await hub.say(r)
    return {"ok": True}


@app.post("/api/record", dependencies=[Depends(require_token)])
async def api_record(body: dict):
    """Record raw glasses data for offline development: mic.wav, frames/*.jpg, imu.jsonl, keys.jsonl
    in hub/data/recordings/<label>/ (gitignored, local only). {"label": "nod", "seconds": 15, "imu": true}"""
    if hub.rec:
        await hub.record_stop()
    label = "".join(c for c in body.get("label", "take") if c.isalnum() or c in "-_") or "take"
    await hub.record_start(label, float(body.get("seconds", 15)), bool(body.get("imu", True)))
    return {"recording": label}


@app.post("/api/reload", dependencies=[Depends(require_token)])
async def api_reload():
    return hub.reload()


@app.post("/api/patient", dependencies=[Depends(require_token)])
async def api_patient(body: dict):
    """Swap the patient's name live (e.g. to the judge's name)."""
    name = body.get("name", "").strip()
    if name:
        hub.cfg["patient"]["name"] = name
        hub.cfg["patient"]["preferredName"] = name.split()[0]
        hub.queue_voice_warmup()
    return {"patient": hub.cfg["patient"]}


@app.get("/api/state")
async def api_state():
    return {"glasses": hub.glasses is not None, "worn": hub.worn, "faces": hub.enrolled,
            "people": list(hub.kb.people), "answers": len(hub.kb.entries),
            "in_view": hub.brain.in_view(), "patient": hub.cfg["patient"]["name"],
            "llm_ms": hub.llm.last_ms, "stt_ms": hub.stt.last_ms, "voice_warmup": hub.voice_warmup}


def main():
    import uvicorn
    s = load_config().get("server", {})
    uvicorn.run(app, host=s.get("host", "0.0.0.0"), port=s.get("port", 9100), log_level="warning")


if __name__ == "__main__":
    main()
