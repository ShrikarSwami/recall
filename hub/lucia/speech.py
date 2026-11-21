"""Mic stream → utterances → text, wake word, and text → PCM for the glasses speaker."""
from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import webrtcvad
from rapidfuzz import fuzz

RATE = 16000
FRAME = 480                 # 30 ms @ 16 kHz
FRAME_BYTES = FRAME * 2

# Whisper's favourite hallucinations on silence/noise.
JUNK = re.compile(r"^\W*(thank you\.?|thanks for watching!?|you|bye\.?|\.+|\[.*\]|\(.*\))\W*$", re.I)


class Segmenter:
    """Cuts a continuous PCM16 stream into utterances with WebRTC VAD."""

    def __init__(self, aggressiveness: int = 2, end_silence_ms: int = 700, max_ms: int = 9000, min_ms: int = 350):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.buf = b""
        self.voiced: list[bytes] = []
        self.ring: list[bool] = []
        self.active = False
        self.silence = 0
        self.end_frames = end_silence_ms // 30
        self.max_frames = max_ms // 30
        self.min_frames = min_ms // 30

    def feed(self, pcm: bytes) -> list[bytes]:
        out: list[bytes] = []
        self.buf += pcm
        while len(self.buf) >= FRAME_BYTES:
            f, self.buf = self.buf[:FRAME_BYTES], self.buf[FRAME_BYTES:]
            speech = self.vad.is_speech(f, RATE)
            if not self.active:
                self.ring = (self.ring + [speech])[-8:]
                self.voiced = (self.voiced + [f])[-8:]  # keep ~240 ms of lead-in
                if sum(self.ring) >= 5:
                    self.active, self.silence = True, 0
            else:
                self.voiced.append(f)
                self.silence = 0 if speech else self.silence + 1
                if self.silence >= self.end_frames or len(self.voiced) >= self.max_frames:
                    if len(self.voiced) - self.silence >= self.min_frames:
                        out.append(b"".join(self.voiced))
                    self.active, self.voiced, self.ring = False, [], []
        return out

    @property
    def speaking(self) -> bool:
        return self.active


class Transcriber:
    """mlx-whisper on the Mac's GPU. One worker thread: MLX isn't happy with concurrent calls."""

    def __init__(self, model: str):
        self.model = model
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.last_ms = 0.0

    def _run(self, pcm: bytes) -> str:
        import mlx_whisper
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        t0 = time.perf_counter()
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=self.model, language="en",
                                   condition_on_previous_text=False, no_speech_threshold=0.5)
        self.last_ms = (time.perf_counter() - t0) * 1000
        text = r.get("text", "").strip()
        return "" if JUNK.match(text) else text

    async def transcribe(self, pcm: bytes) -> str:
        return await asyncio.get_running_loop().run_in_executor(self.pool, self._run, pcm)

    def warm(self) -> None:
        self._run(np.zeros(RATE, dtype=np.int16).tobytes())


def split_wake(text: str, wake: str) -> tuple[bool, str]:
    """('Lucia, who is this?', 'Lucia') -> (True, 'who is this?'). Fuzzy, because STT hears
    'Lucia' as 'Lucy a', 'Lucía', 'Lucha', 'Luisa'... Looks at the first 3 words only."""
    words = text.strip().split()
    w = wake.lower()
    for n in (1, 2, 3):
        head = re.sub(r"[^a-z ]", "", " ".join(words[:n]).lower())
        squashed = head.replace(" ", "")
        if fuzz.ratio(squashed, w) >= 75 or (len(squashed) >= 4 and fuzz.ratio(squashed[: len(w) + 1], w) >= 80):
            rest = " ".join(words[n:]).lstrip(" ,.!?-")
            return True, rest
    return False, text


class Voice:
    """Text → PCM16 mono 22.05 kHz using macOS `say` (no TTS engine on the glasses)."""
    OUT_RATE = 22050

    def __init__(self, name: str = "Samantha", rate_wpm: int = 165):
        self.name, self.wpm = name, rate_wpm
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.cache: dict[str, bytes] = {}

    def _render(self, text: str) -> bytes:
        if text in self.cache:
            return self.cache[text]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "s.wav"
            subprocess.run(["say", "-v", self.name, "-r", str(self.wpm),
                            f"--data-format=LEI16@{self.OUT_RATE}", "-o", str(out), text],
                           check=True, capture_output=True, timeout=20)
            with wave.open(str(out)) as w:
                pcm = w.readframes(w.getnframes())
        if len(self.cache) < 300:
            self.cache[text] = pcm
        return pcm

    async def pcm(self, text: str) -> bytes:
        return await asyncio.get_running_loop().run_in_executor(self.pool, self._render, text)


def earcon(hz: float = 880, ms: int = 120, rate: int = Voice.OUT_RATE) -> bytes:
    """Short soft chime: 'I'm listening'."""
    t = np.arange(int(rate * ms / 1000)) / rate
    env = np.minimum(1, np.minimum(t / 0.01, (t[-1] - t) / 0.04))
    return (np.sin(2 * np.pi * hz * t) * env * 6000).astype(np.int16).tobytes()
