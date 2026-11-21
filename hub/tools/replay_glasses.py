"""Fake glasses: drive the hub exactly like the M6 does, with no hardware.

Connects to ws://<hub>/ws/glasses and sends the same binary/JSON the glasses app sends
(mic PCM16 16 kHz, camera JPEGs, key presses), then prints what Lucia shows and says.

    cd hub
    # speak a sentence (macOS `say` makes the audio) while "looking at" a photo:
    uv run python tools/replay_glasses.py --say "Lucia, who is this?" --frame ../faces/abhiram/IMG_3170.jpg
    # tap the temple first, then ask without the wake word:
    uv run python tools/replay_glasses.py --key tap --say "where are we"
    # replay a recording captured on the real glasses (tools/capture_session.py):
    uv run python tools/replay_glasses.py --recording data/recordings/voice_wearer
    # put the glasses "on" (greeting), or press any measured gesture:
    uv run python tools/replay_glasses.py --key worn
    uv run python tools/replay_glasses.py --key double_tap

Key names → codes are the real ones measured on the M6 (docs/HARDWARE.md).
Only one glasses client is active at a time: running this takes over from real glasses until it exits.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import websockets

KEYS = {"tap": 66, "double_tap": 142, "long_press": 141, "swipe_forward": 22, "swipe_back": 21, "back": 4, "worn": 301}
CHUNK = 3200  # 100 ms of 16 kHz PCM16


def tts_pcm(text: str) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "q.wav"
        subprocess.run(["say", "-o", str(out), "--data-format=LEI16@16000", text], check=True)
        with wave.open(str(out)) as w:
            return w.readframes(w.getnframes())


def silence(seconds: float) -> bytes:
    return b"\x00" * int(16000 * 2 * seconds)


async def listen(ws, until: float):
    while time.time() < until:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=until - time.time())
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            return
        if isinstance(msg, bytes):
            continue  # answer audio (PCM 22.05 kHz) — not played here
        m = json.loads(msg)
        if m.get("type") == "card":
            print(f"  LENS  [{m.get('intent')}] {m.get('title')}: {' / '.join(m.get('lines', []))}")
        elif m.get("type") == "state":
            print(f"  state {m.get('value')}")


async def stream_audio(ws, pcm: bytes, realtime: bool = True):
    for i in range(0, len(pcm), CHUNK):
        await ws.send(b"\x01" + pcm[i:i + CHUNK])
        if realtime:
            await asyncio.sleep(0.1)


async def send_key(ws, name: str):
    code = KEYS.get(name, int(name) if name.isdigit() else 0)
    if name == "worn":
        await ws.send(json.dumps({"type": "worn", "value": True}))
    await ws.send(json.dumps({"type": "key", "name": name, "code": code, "scan": -1, "device": "replay"}))
    print(f"→ key {name} ({code})")


async def main(a):
    url = a.hub.rstrip("/").replace("http", "ws") + "/ws/glasses"
    async with websockets.connect(url, max_size=None) as ws:
        await ws.send(json.dumps({"type": "hello", "model": "replay", "sdk": 0, "tts": False, "cameras": 1, "worn": True}))
        print(f"connected to {url} as fake glasses")
        listener = asyncio.create_task(listen(ws, time.time() + 3600))

        if a.frame:
            jpeg = Path(a.frame).read_bytes()
            for _ in range(3):                       # a few frames so the face is "seen"
                await ws.send(b"\x02" + jpeg)
                await asyncio.sleep(0.4)
            print(f"→ camera frame {a.frame}")
        for k in a.key or []:
            await send_key(ws, k)
            await asyncio.sleep(0.6)
        if a.say:
            print(f"→ says: {a.say!r}")
            await stream_audio(ws, silence(0.4) + tts_pcm(a.say) + silence(1.2))
        if a.recording:
            await replay(ws, Path(a.recording))

        await asyncio.sleep(a.wait)
        listener.cancel()


async def replay(ws, d: Path):
    """Replays mic, frames and keys of a recording with their original timing."""
    with wave.open(str(d / "mic.wav")) as w:
        pcm = w.readframes(w.getnframes())
    frames = sorted((d / "frames").glob("*.jpg"))
    keys = [json.loads(l) for l in (d / "keys.jsonl").read_text().splitlines()] if (d / "keys.jsonl").exists() else []
    dur = len(pcm) / 32000
    print(f"→ replaying {d.name}: {dur:.1f}s audio, {len(frames)} frames, {len(keys)} keys")
    t0 = time.time()
    fi = ki = 0
    for i in range(0, len(pcm), CHUNK):
        now = time.time() - t0
        if frames and fi < len(frames) and now >= fi * dur / len(frames):
            await ws.send(b"\x02" + frames[fi].read_bytes()); fi += 1
        while ki < len(keys) and keys[ki]["t"] <= now:
            k = keys[ki]; ki += 1
            await ws.send(json.dumps({"type": "key", "name": k["name"], "code": k["code"]}))
            print(f"  (key {k['name']} at {k['t']}s)")
        await ws.send(b"\x01" + pcm[i:i + CHUNK])
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hub", default="http://localhost:9100")
    p.add_argument("--say", help="sentence to speak into the fake mic")
    p.add_argument("--frame", help="JPEG to send as the camera view")
    p.add_argument("--key", action="append", help=f"gesture: {', '.join(KEYS)} (repeatable)")
    p.add_argument("--recording", help="hub/data/recordings/<step> folder to replay")
    p.add_argument("--wait", type=float, default=6.0, help="seconds to keep listening for answers")
    asyncio.run(main(p.parse_args()))
