"""Gogo's guided flow, run on the server (a Python port of sim/flow.js).

It builds the steps from the care plan (profile, places, weather), sends them to the lens as messages
(card / avatar / arrows / tapnote / ring / splash), speaks them through the glasses speaker, and waits for a tap.
The lens never knows who is driving it. Nothing here touches the Lucia hub.
"""
import asyncio
import json
import re
import time

import tts

LENS_HINT = "Tap the side when you need me"


def cap(s):
    s = str(s or "")
    return s[:1].upper() + s[1:]


def lower_first(s):
    s = str(s or "")
    return s[:1].lower() + s[1:]


def wrap_lines(text, n):
    """A sentence -> up to 3 short lens lines."""
    out, cur = [], ""
    for w in str(text).split():
        if cur and len((cur + " " + w).strip()) > n:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    if len(out) > 3:
        out = out[:3]
        out[2] = re.sub(r"\s*\S*$", "", out[2]) + "…"
    return out


class Flow:
    def __init__(self, care):
        self.care = care                  # the care module (profile, weather, events, inbox)
        self.lenses = set()               # lens WebSockets
        self.glasses = None               # the glasses app WebSocket (audio out, keys in)
        self.awake = False
        self.task = None
        self.scene = ""
        self.last = {}                    # last message of each kind, replayed to a lens that connects late
        self.skip_ev = asyncio.Event()
        self.cfg = {"name": "Mike", "partner": "Anna", "age": "74", "charm": "handsome", "place": "CUNY, Brooklyn",
                    "bag": "Right behind you", "gate": "top right", "goals": [], "routeTo": [], "routeBack": [],
                    "sky": "sunny", "chill": "", "temp": ""}
        self.voice = True
        self.auto = False                 # auto-advance tap steps after 6 s (for demos with nobody tapping)

    # ------------------------------------------------------------ output to the lens and the glasses
    async def send(self, m):
        t = m.get("type")
        if t in ("card", "avatar", "arrows", "tapnote", "battery", "power", "config"):
            if t == "avatar" and "avatar" in self.last:
                self.last["avatar"] = dict(self.last["avatar"], **m)       # avatar messages are partial updates
            else:
                self.last[t] = m
        if t == "clear":
            for k in ("card", "arrows", "tapnote"):
                self.last.pop(k, None)
        data = json.dumps(m)
        for ws in list(self.lenses):
            try:
                await ws.send_text(data)
            except Exception:
                self.lenses.discard(ws)

    async def replay_to(self, ws):
        await ws.send_text(json.dumps({"type": "config", "hint": LENS_HINT}))
        await ws.send_text(json.dumps({"type": "power", "on": self.awake}))
        if self.awake:
            for k in ("card", "avatar", "arrows", "tapnote", "battery"):
                if k in self.last:
                    await ws.send_text(json.dumps(self.last[k]))

    async def wake(self):
        if not self.awake:
            self.awake = True
            await self.send({"type": "power", "on": True})

    async def sleep_lens(self):
        self.stop(idle=False)
        self.awake = False
        self.last.clear()
        await self.send({"type": "power", "on": False})

    async def to_idle(self):
        await self.send({"type": "clear"})
        await self.send({"type": "battery", "on": False})
        await self.send({"type": "avatar", "pose": "idle", "emo": None, "talking": False, "pos": "center", "far": 0, "face": "user", "size": "normal"})

    # ------------------------------------------------------------ the care plan -> template values
    def refresh_derived(self):
        c = self.cfg
        h = time.localtime().tm_hour
        c["daypart"] = "morning" if h < 12 else "afternoon" if h < 17 else "evening"
        sky, chill = c["sky"], c["chill"]
        icons = {"sunny": "sun", "clear": "moon", "partly cloudy": "cloud", "cloudy": "cloud", "foggy": "cloud", "drizzly": "rain",
                 "rainy": "rain", "stormy": "rain", "icy": "rain", "snowy": "cloud"}
        c["skyIcon"] = icons.get(sky, "cloud")
        c["skyTitle"] = "Clear night" if sky == "clear" else cap(sky)
        c["weatherSay"] = ("It's a clear night out" if sky == "clear" else "It's %s out" % sky) + (", but %s" % chill if chill else "") + "."
        c["chillLine"] = cap(chill) if chill else "Nice out there"
        c["skyTag"] = "%s°F" % c["temp"] if c["temp"] != "" else str(sky).upper()
        c["bagSay"] = lower_first(c["bag"])
        c["goal1"] = c["goals"][0] if c["goals"] else "get ready for the day"

    async def load_care(self):
        st = self.care.STATE
        p, pl = st.get("profile", {}), st.get("places", {})
        c = self.cfg
        c["name"] = p.get("name") or c["name"]
        c["age"] = str(p.get("age") or c["age"])
        c["charm"] = "beautiful" if p.get("gender") == "woman" else "handsome"
        cg = str(p.get("caregiver") or "")
        c["partner"] = re.sub(r"\s*\(.*\)", "", cg) or c["partner"]
        c["place"] = pl.get("city") or c["place"]
        c["bag"] = pl.get("bag") or c["bag"]
        c["gate"] = pl.get("gate") or c["gate"]
        c["routeTo"] = pl.get("routeToBathroom") or []
        c["routeBack"] = pl.get("routeBack") or []
        g = (st.get("goals") or [None])[0]
        c["goals"] = g["items"] if g else []
        try:
            w = await asyncio.wait_for(asyncio.to_thread(self.care.weather), 6)
        except Exception:
            w = {"ok": False}
        if w.get("ok"):
            c["sky"], c["chill"], c["temp"] = w["sky"], w["chill"], w["tempF"]
        else:
            c["temp"] = ""
        self.refresh_derived()

    def fill(self, s):
        def rep(m):
            k = m.group(1)
            if k == "time":
                return time.strftime("%I:%M %p").lstrip("0")
            v = self.cfg.get(k)
            return str(v) if v is not None else m.group(0)
        return re.sub(r"\{(\w+)\}", rep, str(s))

    # ------------------------------------------------------------ the demo day (same steps as the simulator)
    def build_demo(self):
        self.refresh_derived()
        c = self.cfg
        gate_pos = "left" if re.search("left", c["gate"], re.I) else "right"
        other = "right" if gate_pos == "left" else "left"
        S = [{"splash": 5000}]
        S.append({"t": "Hi, I'm Gogo", "l": [], "big": True, "pose": "idle", "pos": "center", "action": "greet", "say": "Hi, I'm Gogo.", "dur": 4000, "loc": "seat",
                  "ev": [{"type": "gaze", "label": "a friendly squirrel", "sim": True}]})
        S.append({"t": "I'm with you", "l": ["I'll get you through", "the day"], "icon": "shield", "tag": "WITH YOU", "pose": "wave", "say": "I'll get you through the day.", "hold": 1200})
        S.append({"t": "You're {name}", "l": ["{age} years young,", "and very {charm}"], "icon": "person", "tag": "YOU", "pose": "cheer",
                  "say": "You're {name}. {age} years young, and still very {charm}.", "hold": 1400})
        S.append({"t": "You're here", "l": ["at {place}", "with your friends"], "icon": "friends", "tag": "FRIENDS", "pose": "idle",
                  "say": "You're at {place}, in the middle of a bunch of your friends.", "hold": 1600,
                  "ev": [{"type": "attention", "mode": "looking_around", "secs": 6, "sim": True}, {"type": "gaze", "label": "your friends", "sim": True}]})
        S.append({"t": "{skyTitle}", "l": ["{chillLine}"], "icon": "{skyIcon}", "tag": "{skyTag}", "pose": "idle", "say": "{weatherSay}", "hold": 1500})
        S.append({"t": "Your bag", "l": ["{bag}"], "icon": "bag", "tag": "SAFE", "pose": "point", "face": "left", "say": "Your bag is {bagSay}.", "hold": 1500,
                  "ev": [{"type": "gaze", "label": "his bag", "sim": True}]})
        S.append({"t": "You're safe", "l": ["Your friends know"], "icon": "shield", "tag": "SAFE", "pose": "idle", "emo": "warm", "say": "Your friends know you're safe.", "hold": 1300})
        S.append({"t": "Today", "l": wrap_lines(c["goal1"], 24), "icon": "timer", "tag": "TODAY", "pose": "idle", "say": "Today, we'll " + lower_first(c["goal1"]) + ".", "hold": 1500})
        S.append({"t": "Let's freshen up", "l": ["I'll show you the way"], "icon": "drop", "tag": "FRESH UP", "pose": "cheer", "say": "Let's get you freshened up.", "hold": 1000})
        S.append({"t": "Where to?", "l": ["Tap, and I'll show you", "where the bathroom is"], "icon": "bath", "tag": "ASK ME", "pose": "idle", "emo": "curious",
                  "say": "When you'd like to know where the bathroom is, give a little tap.", "tap": True, "tapHint": "Tap to see the way"})
        S.append({"t": "The bathroom", "l": ["Through the gate,", c["gate"] + " corner"], "icon": "bath", "tag": "THIS WAY", "arrows": gate_pos, "pose": "point", "face": gate_pos,
                  "say": "The bathroom is through the gate, in the " + c["gate"] + " corner. I'll show you.", "hold": 1600})
        to, ticons = c["routeTo"], ["chair-stand", "gate", "forward", "bath"]
        for i, line in enumerate(to):
            st = {"t": "Step %d of %d" % (i + 1, len(to)), "l": wrap_lines(line, 26), "icon": ticons[min(i, 3)], "tag": "STEP %d" % (i + 1), "say": line, "tap": True, "tapHint": "Tap when you've done it"}
            if i == 0:
                st.update(pose="idle", pos="center", loc="seat")
            elif i == 1:
                st.update(pose="walk", far=0.75, face="away", pos=gate_pos, arrows=gate_pos, loc="walking",
                          ev=[{"type": "attention", "mode": "walking_straight", "secs": 18, "sim": True}, {"type": "gaze", "label": "the walkway", "sim": True}])
            elif i < len(to) - 1:
                st.update(pose="wave", far=0.75, pos=gate_pos, face="user", arrows=other, loc="gate",
                          ev=[{"type": "attention", "mode": "looking_around", "secs": 9, "sim": True}, {"type": "gaze", "label": "the gate", "sim": True}])
            else:
                st.update(pose="point", far=0.75, pos=gate_pos, face=other, arrows=other, loc="walking", ev=[{"type": "gaze", "label": "the bathroom door", "sim": True}])
            S.append(st)
        S.append({"t": "You made it", "l": ["Well done, {name}"], "icon": "shield", "tag": "MADE IT", "pose": "cheer", "say": "You made it. Well done, {name}.", "hold": 1100, "loc": "bathroom"})
        S.append({"t": "Turn the tap on", "l": ["Wet your hands"], "icon": "drop-wash", "tag": "WASH 1", "pose": "idle", "say": "Turn the tap on, and wet your hands.", "tap": True, "tapHint": "Tap when you've done it",
                  "ev": [{"type": "gaze", "label": "the sink", "sim": True}]})
        S.append({"t": "Rub, rub, rub", "l": ["20 seconds"], "ring": 1, "countdown": 20, "pose": "calm", "say": "Now add a little soap. Rub your hands together for twenty seconds. I'll count with you."})
        S.append({"t": "Rinse", "l": ["Under the water"], "icon": "drop-wash", "tag": "WASH 3", "pose": "idle", "say": "Now rinse your hands under the water.", "tap": True, "tapHint": "Tap when you've done it"})
        S.append({"t": "Dry your hands", "l": ["Turn the tap off first"], "icon": "hands", "tag": "WASH 4", "pose": "idle", "say": "Turn the tap off, and dry your hands.", "tap": True, "tapHint": "Tap when you've done it"})
        S.append({"t": "All clean", "l": ["Well done, {name}"], "icon": "shield", "tag": "CLEAN", "pose": "cheer", "say": "All clean. Well done, {name}.", "hold": 1300})
        back, bicons = c["routeBack"], ["gate", "forward", "chair"]
        for i, line in enumerate(back):
            sb = {"t": "Back to your seat", "l": wrap_lines(line, 26), "icon": bicons[min(i, 2)], "tag": "STEP %d" % (i + 1), "say": line, "tap": True, "tapHint": "Tap when you've done it"}
            if i == 0:
                sb.update(pose="walk", far=0.6, face="away", pos=gate_pos, loc="walking", ev=[{"type": "attention", "mode": "walking_straight", "secs": 14, "sim": True}])
            elif i < len(back) - 1:
                sb.update(pose="wave", far=0.4, face="user", pos="center", loc="walking",
                          ev=[{"type": "attention", "mode": "looking_around", "secs": 8, "sim": True}, {"type": "gaze", "label": "his friends", "sim": True}])
            else:
                sb.update(pose="point", face="left", pos="center", loc="walking")
            S.append(sb)
        S.append({"t": "Your seat", "l": ["Next to your bag"], "icon": "chair", "tag": "SIT", "pose": "idle", "say": "This is your seat, next to your bag. Sit down slowly.", "tap": True,
                  "tapHint": "Tap when you're sitting", "loc": "seat", "ev": [{"type": "attention", "mode": "still", "secs": 20, "sim": True}]})
        S.append({"t": "Well done, {name}", "l": ["You did it"], "icon": "shield", "tag": "DONE", "pose": "cheer", "action": "twirl",
                  "say": "Well done, {name}. You did it. I'm right here with you.", "hold": 2600})
        return S

    def instruction_step(self, kind, text):
        if kind == "warning":
            return {"t": "Careful", "l": wrap_lines(text, 24), "icon": "warn", "tag": "WARNING", "alert": True, "pose": "alert", "emo": "alert", "say": "{name}, careful. " + text, "hold": 3000}
        if kind == "reminder":
            return {"t": "A reminder", "l": wrap_lines(text, 24), "icon": "timer", "tag": "REMINDER", "pose": "wave", "emo": "warm", "say": "{name}, a quick reminder. " + text, "hold": 3000}
        return {"t": "From your family", "l": wrap_lines(text, 24), "icon": "person", "tag": "MESSAGE", "pose": "wave", "emo": "happy", "say": text, "hold": 3000}

    # ------------------------------------------------------------ the engine
    def log(self, etype, **kw):
        self.care.add_event(etype, **kw)

    def skip(self):
        self.skip_ev.set()

    def stop(self, idle=True):
        if self.task and not self.task.done():
            self.task.cancel()
        self.task = None
        self.skip_ev.set()
        if idle and self.awake:
            asyncio.ensure_future(self.to_idle())

    async def race(self, aw):
        """Wait for aw, or for a tap (skip)."""
        t = asyncio.ensure_future(aw)
        s = asyncio.ensure_future(self.skip_ev.wait())
        try:
            await asyncio.wait({t, s}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for x in (t, s):
                if not x.done():
                    x.cancel()

    async def pause(self, ms):
        await self.race(asyncio.sleep(ms / 1000))

    async def speak(self, text):
        pcm = await tts.synth(text) if self.voice else None
        if not pcm:
            await asyncio.sleep(max(1.2, len(text.split()) * 0.38) + 0.4)
            return
        dur = len(pcm) / 2 / tts.RATE
        t0 = time.monotonic()
        try:
            for i in range(0, len(pcm), 8820):
                g = self.glasses
                if g is not None:
                    try:
                        await g.send_bytes(pcm[i:i + 8820])
                    except Exception:
                        self.glasses = None
                ahead = (i + 8820) / (2 * tts.RATE) - (time.monotonic() - t0)
                if ahead > 0.6:
                    await asyncio.sleep(ahead - 0.6)
            left = dur - (time.monotonic() - t0)
            if left > 0:
                await asyncio.sleep(left + 0.2)
        except asyncio.CancelledError:
            if self.glasses is not None:
                try:
                    await self.glasses.send_text(json.dumps({"type": "audio_stop"}))
                except Exception:
                    pass
            raise

    async def apply_step(self, s):
        f = self.fill
        await self.send({"type": "card", "title": f(s["t"]), "lines": [f(x) for x in s.get("l", [])],
                         "icon": None if s.get("ring") else (f(s["icon"]) if s.get("icon") else None),
                         "tag": f(s["tag"]) if s.get("tag") else s.get("tag"), "alert": bool(s.get("alert")), "ring": bool(s.get("ring"))})
        await self.send({"type": "arrows", "value": s.get("arrows", "")})
        await self.send({"type": "battery", "on": bool(s.get("battery")), "pct": 15})
        av = {"type": "avatar", "size": "big" if s.get("big") else "normal", "pose": s.get("pose", "idle"), "emo": s.get("emo"),
              "dir": "left" if s.get("face") == "left" else "right", "far": s.get("far", 0), "face": "away" if s.get("face") == "away" else "user"}
        if s.get("pos"):
            av["pos"] = s["pos"]
        await self.send(av)
        if s.get("action"):
            await self.send({"type": "avatar", "action": s["action"]})

    async def ring_run(self, cycles):
        for _ in range(cycles):
            await self.send({"type": "ring", "phase": "in", "label": "Breathe in…"})
            await self.pause(4000)
            await self.send({"type": "ring", "phase": "out", "label": "…and out"})
            await self.pause(4000)

    async def countdown(self, n):
        for sec in range(n, 0, -1):
            await self.send({"type": "ring", "phase": "in" if sec % 2 else "out", "label": "%d seconds" % sec})
            await self.pause(1000)

    async def _play(self, steps, scene):
        self.scene = scene
        try:
            for s in steps:
                self.skip_ev = asyncio.Event()
                t0 = time.monotonic()
                if s.get("splash"):
                    await self.send({"type": "splash", "on": True, "ms": s["splash"]})
                    await self.pause(s["splash"] + 250)
                    continue
                await self.apply_step(s)
                said = self.fill(s["say"])
                self.log("step", text=self.fill(s["t"]), scene=scene)
                self.log("lucia", text=said)
                if s.get("loc"):
                    self.log("location", place=s["loc"], sim=True)
                for e in s.get("ev", []):
                    e = dict(e)
                    self.log(e.pop("type"), **e)
                await self.send({"type": "avatar", "talking": True})
                await self.race(self.speak(said))
                await self.send({"type": "avatar", "talking": False})
                if s.get("ring") and not s.get("countdown"):
                    self.skip_ev = asyncio.Event()
                    await self.ring_run(s["ring"])
                if s.get("countdown"):
                    self.skip_ev = asyncio.Event()
                    await self.countdown(s["countdown"])
                if s.get("dur"):
                    self.skip_ev = asyncio.Event()
                    await self.pause(max(0, s["dur"] - (time.monotonic() - t0) * 1000))
                if s.get("hold"):
                    self.skip_ev = asyncio.Event()
                    await self.pause(s["hold"])
                if s.get("tap"):
                    self.skip_ev = asyncio.Event()
                    await self.send({"type": "tapnote", "text": s.get("tapHint") or "Tap when you're ready"})
                    try:
                        await asyncio.wait_for(self.skip_ev.wait(), 6 if self.auto else None)
                    except asyncio.TimeoutError:
                        pass
                    await self.send({"type": "tapnote", "text": ""})
            await asyncio.sleep(1.5)
            await self.to_idle()
        except asyncio.CancelledError:
            raise
        finally:
            self.scene = "" if self.scene == scene else self.scene

    async def play(self, name):
        await self.wake()
        if name == "demo":
            await self.load_care()
            self.log("system", text="Demo day started for %s" % self.cfg["name"])
            steps = self.build_demo()
        else:
            raise ValueError("unknown scene " + name)
        self.stop(idle=False)
        self.task = asyncio.ensure_future(self._play(steps, name))

    async def deliver(self, item):
        """A dashboard instruction: interrupt whatever is on screen and say it."""
        await self.wake()
        step = self.instruction_step(item.get("kind", "message"), item["text"])
        self.stop(idle=False)
        self.task = asyncio.ensure_future(self._play([step], "instruction"))

    async def on_tap(self):
        if self.task and not self.task.done():
            self.skip()
        else:
            if self.awake:
                await self.send({"type": "avatar", "pose": "wave", "emo": "happy"})

    def status(self):
        return {"awake": self.awake, "running": bool(self.task and not self.task.done()), "scene": self.scene,
                "lenses": len(self.lenses), "glasses": self.glasses is not None, "voice": self.voice, "ttsReady": tts.ready()}
