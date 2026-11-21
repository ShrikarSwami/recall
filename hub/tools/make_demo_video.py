"""Record a ~3-minute demo video with no glasses and no screen recording.

Drives the real hub exactly like the glasses (fake mic, camera frames, IMU, keys), captures what Go-go actually
shows and says, renders the real lens page (headless Chrome) and muxes it all with ffmpeg:

    cd hub && uv run python tools/make_demo_video.py            # hub must be running on 9100 (dry-run is fine)
    open data/video/lucia_demo.mp4

Output goes to hub/data/video/ (gitignored): the camera frames come from faces/ (private), and although the
video only shows names, never photos, keep it out of the public repo.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np
import websockets
from PIL import Image, ImageDraw, ImageFont

HUB = Path(__file__).resolve().parents[1]
ROOT = HUB.parent
sys.path.insert(0, str(HUB))
sys.path.insert(0, str(Path(__file__).parent))
from lucia.gestures import synth  # noqa: E402
from replay_glasses import CHUNK, KEYS  # noqa: E402

OUT = HUB / "data" / "video"
SR = 22050                 # output audio rate (= Go-go's voice rate)
W, H = 1280, 720
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
JUDGE_VOICE, NARRATOR_VOICE = "Fred", "Daniel"
GREEN, DIM, WHITE, GREY = (0, 255, 80), (0, 184, 58), (240, 240, 240), (140, 140, 140)


def font(size: int, bold: bool = False):
    for p in ("/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, size, index=1 if bold else 0)
        except Exception:
            pass
    return ImageFont.load_default()


def say_pcm(text: str, voice: str, rate: int) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "s.wav"
        subprocess.run(["say", "-v", voice, "-o", str(out), f"--data-format=LEI16@{rate}", text], check=True)
        with wave.open(str(out)) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def resample(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or len(x) == 0:
        return x
    n = int(len(x) * dst / src)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.int16)


class Recorder:
    """Timeline of what happened: audio clips, lens messages, captions, caregiver alerts."""

    def __init__(self):
        self.t0 = time.time()
        self.audio: list[tuple[float, np.ndarray]] = []     # (t, pcm @ SR)
        self.lens: list[tuple[float, dict]] = []            # (t, card/state/config msg)
        self.captions: list[tuple[float, str, str]] = []    # (t, who, text)
        self.alerts: list[tuple[float, str]] = []
        self.scenes: list[tuple[float, str]] = []           # (t, scene label)
        self.cards: list[tuple[float, float, str, str]] = []  # (t, dur, title, body) full-screen title cards
        self.repeat_note: list[tuple[float, str]] = []
        self.voice_buf: list[bytes] = []
        self.voice_t = 0.0
        self.voice_last = 0.0

    def now(self) -> float:
        return time.time() - self.t0

    def flush_voice(self):
        if self.voice_buf:
            pcm = np.frombuffer(b"".join(self.voice_buf), dtype=np.int16)
            self.audio.append((self.voice_t, pcm))
            self.voice_buf = []


async def glasses_listener(ws, rec: Recorder):
    async for msg in ws:
        t = rec.now()
        if isinstance(msg, bytes):
            if not rec.voice_buf or t - rec.voice_last > 0.6:
                rec.flush_voice()
                rec.voice_t = t
            rec.voice_buf.append(msg)
            rec.voice_last = t
            continue
        m = json.loads(msg)
        if m.get("type") in ("card", "state", "config", "clear"):
            rec.lens.append((t, m))


async def caregiver_listener(rec: Recorder):
    async with websockets.connect("ws://localhost:9100/ws/caregiver", max_size=None) as ws:
        async for msg in ws:
            ev = json.loads(msg)
            if ev.get("ts", 0) < rec.t0:
                continue                       # history replayed on connect
            t = rec.now()
            if ev.get("type") == "answer" and ev.get("speech"):
                rec.captions.append((t, "Go-go", ev["speech"]))
                if ev.get("repeat", 1) > 1 and ev.get("subject"):
                    rec.repeat_note.append((t, f"Asked about {ev['subject'].title()} {ev['repeat']}× in 10 min"))
            elif ev.get("type") == "alert":
                rec.alerts.append((t, ev.get("text", "")))


async def wait_quiet(rec: Recorder, extra: float = 1.0, timeout: float = 25):
    """Wait until Go-go has finished speaking (audio arrives faster than real time)."""
    start = time.time()
    await asyncio.sleep(1.2)
    while time.time() - start < timeout:
        if rec.voice_buf and rec.now() - rec.voice_last > 0.8:
            break
        await asyncio.sleep(0.2)
    rec.flush_voice()
    if rec.audio:
        t, pcm = rec.audio[-1]
        end = t + len(pcm) / SR
        await asyncio.sleep(max(0.0, end - rec.now()))
    await asyncio.sleep(extra)


async def judge(ws, rec: Recorder, text: str, wait: bool = True):
    pcm16 = say_pcm(text, JUDGE_VOICE, 16000)
    rec.captions.append((rec.now(), "Judge", text))
    rec.audio.append((rec.now(), resample(pcm16, 16000, SR)))
    data = b"\x00" * 9600 + pcm16.tobytes() + b"\x00" * 38400
    for i in range(0, len(data), CHUNK):
        await ws.send(b"\x01" + data[i:i + CHUNK])
        await asyncio.sleep(0.1)
    if wait:
        await wait_quiet(rec)


async def narrate(rec: Recorder, title: str, body: str, spoken: str, min_s: float = 4.0):
    pcm = say_pcm(spoken, NARRATOR_VOICE, SR)
    dur = max(min_s, len(pcm) / SR + 0.8)
    rec.cards.append((rec.now(), dur, title, body))
    rec.audio.append((rec.now() + 0.3, pcm))
    await asyncio.sleep(dur)


async def key(ws, name: str):
    if name == "worn":
        await ws.send(json.dumps({"type": "worn", "value": True}))
    await ws.send(json.dumps({"type": "key", "name": name, "code": KEYS[name], "scan": -1, "device": "demo"}))


async def head(ws, kind: str):
    rows = synth(kind, t0_ms=int(time.time() * 1000) % 10_000_000)
    for i in range(0, len(rows), 6):
        await ws.send(json.dumps({"type": "imu", "rows": rows[i:i + 6]}))
        await asyncio.sleep(0.1)


async def look_at(ws, person: str | None, rec: Recorder, seconds: float = 1.6):
    rec.scenes.append((rec.now(), f"camera: {person.title()} in view" if person else "camera: nobody in view"))
    if not person:
        return
    photos = sorted((ROOT / "faces" / person).glob("*.jp*g"))
    if not photos:
        print(f"  (no photo for {person}; skipping)")
        return
    jpeg = photos[0].read_bytes()
    end = time.time() + seconds
    while time.time() < end:
        await ws.send(b"\x02" + jpeg)
        await asyncio.sleep(0.4)


async def keep_looking(ws, person: str, stop: asyncio.Event):
    photos = sorted((ROOT / "faces" / person).glob("*.jp*g"))
    if not photos:
        return
    jpeg = photos[0].read_bytes()
    while not stop.is_set():
        await ws.send(b"\x02" + jpeg)
        await asyncio.sleep(0.8)


async def scenario(rec: Recorder):
    cg = asyncio.create_task(caregiver_listener(rec))
    await asyncio.sleep(0.5)
    async with websockets.connect("ws://localhost:9100/ws/glasses", max_size=None) as ws:
        lis = asyncio.create_task(glasses_listener(ws, rec))
        await narrate(rec, "Go-go", "Smart glasses for people living with dementia\nTeam BB · Worn Smart Glasses Hackathon",
                      "Go-go. Smart glasses for people living with dementia.", 5)
        await narrate(rec, "Before we start",
                      "We won't introduce ourselves.\nYou might have known us once.\nPut yourself in the shoes of someone who forgot.",
                      "Before we start, we're not going to introduce ourselves. You might have known us at some point. "
                      "We want to put you in the shoes of someone living with dementia.")

        rec.scenes.append((rec.now(), "putting the glasses on"))
        await ws.send(json.dumps({"type": "hello", "model": "demo", "sdk": 0, "tts": False, "cameras": 1, "worn": True}))
        await key(ws, "worn")
        await wait_quiet(rec, 1.5)

        # 1. proactive intro: a teammate walks up
        rec.scenes.append((rec.now(), "a teammate walks up · nobody says a word"))
        stop = asyncio.Event()
        looker = asyncio.create_task(keep_looking(ws, "abhiram", stop))
        await asyncio.sleep(0.2)
        rec.scenes.append((rec.now(), "camera: Abhiram in view"))
        await wait_quiet(rec, 0.8)
        rec.scenes.append((rec.now(), "the judge nods"))
        await head(ws, "nod")
        await wait_quiet(rec, 0.8)
        rec.scenes.append((rec.now(), "the judge shakes their head"))
        await head(ws, "shake")
        await wait_quiet(rec, 1.0)

        # 2. follow-ups + repeat-safe
        rec.scenes.append((rec.now(), "ask anything about the person in front of you"))
        await judge(ws, rec, "Go-go, where is he from?")
        await judge(ws, rec, "Go-go, what does he do?")
        rec.scenes.append((rec.now(), "same question again, on purpose"))
        await judge(ws, rec, "Go-go, who is this?")
        await judge(ws, rec, "no thanks")
        await judge(ws, rec, "Go-go, who is this?")
        await judge(ws, rec, "no")
        stop.set(); await looker

        # 3. second teammate
        rec.scenes.append((rec.now(), "another teammate steps in"))
        stop = asyncio.Event()
        looker = asyncio.create_task(keep_looking(ws, "shrikar", stop))
        await asyncio.sleep(1.5)
        await wait_quiet(rec, 1.0)
        stop.set(); await looker

        # 4. orientation
        rec.scenes.append((rec.now(), "where am I? what's going on?"))
        await judge(ws, rec, "Go-go, where are we?")
        await judge(ws, rec, "Go-go, what's my name?")
        rec.scenes.append((rec.now(), "holding the right side of the glasses instead of saying Go-go"))
        await key(ws, "long_press")
        await asyncio.sleep(0.6)
        await judge(ws, rec, "what am I doing here?")

        # 5. safety
        rec.scenes.append((rec.now(), "safety"))
        await judge(ws, rec, "Go-go, I want to go home.")
        await asyncio.sleep(1.5)

        await narrate(rec, "Private by design",
                      "Runs on the glasses and the family's own devices.\nNo cloud AI. Faces only with consent.\n"
                      "Never quizzes, never corrects. Every question is the first time.",
                      "Everything ran on the glasses and the family's own devices. No cloud AI, and faces are only "
                      "added with consent. Go-go never quizzes and never corrects, because for the person asking, "
                      "every question is the first time.", 6)
        await narrate(rec, "Go-go", "Team BB", "Thank you.", 3)
        lis.cancel()
    cg.cancel()


# ---------------------------------------------------------------- rendering
def render_lens_states(rec: Recorder, work: Path) -> dict[int, Path]:
    """Screenshot the real lens page (lens/) for every distinct card/state, via headless Chrome."""
    lens_html = (ROOT / "lens" / "index.html").read_text()
    shots: dict[int, Path] = {}
    state = {"config": None, "card": None, "status": "idle"}
    cfg_msg = next((m for _, m in rec.lens if m.get("type") == "config"), {"type": "config"})
    for i, (t, m) in enumerate(rec.lens):
        if m["type"] == "card":
            state["card"] = m
        elif m["type"] == "state":
            state["status"] = m["value"]
        elif m["type"] == "clear":
            state["card"] = None
        else:
            continue
        msgs = [dict(cfg_msg, now=int((rec.t0 + t) * 1000))]
        if state["card"]:
            msgs.append(dict(state["card"], ttl_ms=10 ** 9))
        msgs.append({"type": "state", "value": state["status"]})
        page = lens_html.replace('<script src="lens.js"></script>',
                                 '<script src="lens.js"></script><script>' +
                                 "".join(f"LuciaLens.render({json.dumps(x)});" for x in msgs) + "</script>")
        p = ROOT / "lens" / f"_demo_{i}.html"
        p.write_text(page)
        png = work / f"lens_{i}.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--screenshot={png}",
                        "--window-size=640,480", "--default-background-color=000000ff",
                        f"file://{p}?ws=off"], capture_output=True, timeout=60)
        p.unlink()
        if png.exists():
            shots[i] = png
    return shots


def wrap(draw, text: str, f, width: int) -> list[str]:
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            test = (line + " " + word).strip()
            if draw.textlength(test, font=f) <= width:
                line = test
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def compose(rec: Recorder, shots: dict[int, Path], t: float) -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 8, 10))
    d = ImageDraw.Draw(img)
    card = next(((t0, dur, ti, bo) for t0, dur, ti, bo in rec.cards if t0 <= t < t0 + dur), None)
    if card:
        _, _, title, body = card
        d.text((W // 2, 250), title, font=font(64, True), fill=GREEN, anchor="mm")
        y = 340
        for line in body.split("\n"):
            d.text((W // 2, y), line, font=font(30), fill=WHITE, anchor="mm")
            y += 46
        return img

    # lens (left)
    idx = max((i for i, (lt, _) in enumerate(rec.lens) if lt <= t and i in shots), default=None)
    lx, ly, lw, lh = 40, 70, 800, 600
    d.rounded_rectangle((lx - 6, ly - 6, lx + lw + 6, ly + lh + 6), 18, outline=(40, 40, 46), width=3)
    if idx is not None:
        img.paste(Image.open(shots[idx]).convert("RGB").resize((lw, lh)), (lx, ly))
    d.text((lx, 28), "What the wearer sees (the real lens UI, 640×480)", font=font(22), fill=GREY)

    # right panel
    rx, rw = 880, 360
    scene = next((s for st, s in reversed(rec.scenes) if st <= t), "")
    d.text((rx, 70), scene, font=font(22), fill=GREY)
    y = 120
    for ct, who, text in [c for c in rec.captions if c[0] <= t][-3:]:
        col = GREEN if who == "Go-go" else WHITE
        d.text((rx, y), who, font=font(22, True), fill=col)
        y += 30
        for line in wrap(d, f"“{text}”", font(24), rw)[:5]:
            d.text((rx, y), line, font=font(24), fill=col)
            y += 31
        y += 18

    # caregiver phone
    alerts = [a for a in rec.alerts if a[0] <= t]
    notes = [n for n in rec.repeat_note if n[0] <= t]
    if alerts or notes:
        py = 500
        d.rounded_rectangle((rx, py, rx + rw, py + 170), 16, fill=(24, 24, 30))
        d.text((rx + 16, py + 12), "Caregiver's phone", font=font(20, True), fill=GREY)
        yy = py + 44
        if alerts:
            d.rounded_rectangle((rx + 16, yy, rx + rw - 16, yy + 70), 14, fill=(10, 132, 255))
            for k, line in enumerate(wrap(d, alerts[-1][1], font(19), rw - 56)[:2]):
                d.text((rx + 28, yy + 10 + 24 * k), line, font=font(19), fill=WHITE)
            yy += 82
        if notes:
            d.text((rx + 16, yy), notes[-1][1], font=font(19), fill=WHITE)
    return img


def mix(rec: Recorder, total: float, path: Path):
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for t, pcm in rec.audio:
        s = int(t * SR)
        x = pcm.astype(np.float32)[: max(0, len(track) - s)]
        track[s:s + len(x)] += x
    track = np.clip(track, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(track.tobytes())


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("needs ffmpeg (brew install ffmpeg)")
    OUT.mkdir(parents=True, exist_ok=True)
    rec = Recorder()
    print("recording scenario against the live hub (about 3 minutes)…")
    asyncio.run(scenario(rec))
    total = rec.now()
    print(f"recorded {total:.0f}s: {len(rec.lens)} lens msgs, {len(rec.captions)} captions, {len(rec.alerts)} alerts")
    (OUT / "timeline.json").write_text(json.dumps({"captions": rec.captions, "alerts": rec.alerts,
                                                   "scenes": rec.scenes}, indent=1))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shots = render_lens_states(rec, work)
        fps = 10
        frames = work / "f"
        frames.mkdir()
        for n in range(int(total * fps)):
            t = n / fps
            im = compose(rec, shots, t)
            im.save(frames / f"{n:05d}.png")
        mix(rec, total, work / "audio.wav")
        out = OUT / "lucia_demo.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "%05d.png"),
                        "-i", str(work / "audio.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                        "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], check=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
