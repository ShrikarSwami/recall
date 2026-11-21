"""Hardware probe server: proves the glasses' camera, mic, keys and speaker all reach the laptop.

    uv run python probe.py            # listens on ws://0.0.0.0:8765/ws/glasses
    adb shell am start -n com.bb.lucia/.MainActivity --es hub ws://<mac-ip>:8765/ws/glasses

Writes probe_out/frame_*.jpg and probe_out/mic.wav, logs every key, and answers each key press
with a card plus a 1-second test tone so you can check the display and the speaker.
"""
import asyncio
import json
import math
import struct
import time
import wave
from pathlib import Path

import websockets

OUT = Path(__file__).parent / "probe_out"
OUT.mkdir(exist_ok=True)


def tone(seconds=0.6, hz=660, rate=22050) -> bytes:
    n = int(seconds * rate)
    return b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * hz * i / rate))) for i in range(n))


async def handler(ws):
    print("glasses connected", ws.remote_address)
    await ws.send(json.dumps({"type": "config", "hint": 'Say "Lucia" to ask'}))
    await ws.send(json.dumps({"type": "card", "title": "Hi Somya", "lines": ["Lucia is connected."], "ttl_ms": 6000}))
    mic = wave.open(str(OUT / "mic.wav"), "wb")
    mic.setnchannels(1); mic.setsampwidth(2); mic.setframerate(16000)
    frames = audio_bytes = 0
    t0 = time.time()
    try:
        async for msg in ws:
            if isinstance(msg, bytes):
                tag, data = msg[0], msg[1:]
                if tag == 1:
                    audio_bytes += len(data)
                    if audio_bytes < 16000 * 2 * 15:  # keep first 15 s
                        mic.writeframes(data)
                    peak = max(abs(v) for v in struct.unpack(f"<{len(data)//2}h", data)) if data else 0
                    if audio_bytes % 32000 < len(data):
                        print(f"mic {audio_bytes/32000:.0f}s  peak={peak}")
                elif tag == 2:
                    frames += 1
                    (OUT / f"frame_{frames % 5}.jpg").write_bytes(data)
                    print(f"frame {frames}: {len(data)//1024} KB  ({frames/(time.time()-t0):.2f} fps)")
            else:
                m = json.loads(msg)
                print("<-", m)
                if m.get("type") == "key":
                    await ws.send(json.dumps({"type": "card", "title": m["name"].upper(),
                                              "lines": [f"key code {m.get('code')}"], "ttl_ms": 4000}))
                    await ws.send(json.dumps({"type": "say", "text": "This is the glasses speaker."}))
                    await ws.send(tone())
    finally:
        mic.close()
        print("disconnected; wrote", OUT)


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765, max_size=None):
        print("probe listening on ws://0.0.0.0:8765/ws/glasses")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
