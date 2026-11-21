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
JUNK = re.compile(r"^\W*$|^\W*(thank you\.?|thanks for watching!?|you|bye\.?|\.+|\[.*\]|\(.*\))\W*$", re.I)


class Segmenter:
    """Cuts a continuous PCM16 stream into utterances with WebRTC VAD."""

    def __init__(self, aggressiveness: int = 2, end_silence_ms: int = 700, max_ms: int = 9000, min_ms: int = 120):
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
                if sum(self.ring) >= 3:  # Keep short words such as "huh", "what", and "stop".
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
        self.hint = ""      # names Whisper should expect (wake word, teammates), e.g. "Lucia. Abhiram, Sid."

    def _run(self, pcm: bytes) -> str:
        import mlx_whisper
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        t0 = time.perf_counter()
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=self.model, language="en",
                                   condition_on_previous_text=False, no_speech_threshold=0.5,
                                   initial_prompt=self.hint or None)
        self.last_ms = (time.perf_counter() - t0) * 1000
        text = r.get("text", "").strip()
        return "" if JUNK.match(text) else text

    async def transcribe(self, pcm: bytes) -> str:
        return await asyncio.get_running_loop().run_in_executor(self.pool, self._run, pcm)

    def warm(self) -> None:
        self._run(np.zeros(RATE, dtype=np.int16).tobytes())


def _is_wake(chunk: str, w: str, strict: bool) -> bool:
    squashed = re.sub(r"[^a-z]", "", chunk.lower())
    if not squashed:
        return False
    if fuzz.ratio(squashed, w) >= (80 if strict else 75):
        return True
    return not strict and len(squashed) >= 4 and fuzz.ratio(squashed[: len(w) + 1], w) >= 80


def split_wake(text: str, wake: str) -> tuple[bool, str]:
    """('Lucia, who is this?', 'Lucia') -> (True, 'who is this?'). Fuzzy, because STT hears
    'Lucia' as 'Lucy a', 'Lucía', 'Lucio', 'Luisa'...

    Checks the first 3 words (lenient), then anywhere in the sentence (stricter), e.g.
    'Team BB, who is this? Lucio, who is this?' -> (True, 'who is this?'). Uses the LAST mention,
    because that's usually the real question."""
    words = text.strip().split()
    w = wake.lower()
    for n in (1, 2, 3):
        if _is_wake(" ".join(words[:n]), w, strict=False):
            return True, " ".join(words[n:]).lstrip(" ,.!?-")
    for i in range(len(words) - 1, 2, -1):          # later in the sentence, last mention first
        for n in (1, 2):
            if i + n <= len(words) and _is_wake(" ".join(words[i:i + n]), w, strict=True):
                rest = " ".join(words[i + n:]).lstrip(" ,.!?-")
                if len(rest.split()) >= 2:          # mid-sentence only counts if a question follows
                    return True, rest
    return False, text


class Voice:
    """Text → PCM16 mono 22.05 kHz using macOS `say` (no TTS engine on the glasses)."""
    OUT_RATE = 22050

    def __init__(self, name: str = "Samantha", rate_wpm: int = 165):
        self.name, self.wpm = name, rate_wpm
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.cache: dict[tuple[str, int, str], bytes] = {}

    def _render(self, text: str, rate: float = 1.0) -> bytes:
        wpm = max(80, min(260, round(self.wpm * rate)))
        key = (self.name, wpm, text)
        if key in self.cache:
            return self.cache[key]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "s.wav"
            subprocess.run(["say", "-v", self.name, "-r", str(wpm),
                            f"--data-format=LEI16@{self.OUT_RATE}", "-o", str(out), text],
                           check=True, capture_output=True, timeout=20)
            with wave.open(str(out)) as w:
                pcm = w.readframes(w.getnframes())
        if pcm and len(self.cache) < 300:
            self.cache[key] = pcm
        return pcm

    async def pcm(self, text: str, rate: float = 1.0) -> bytes:
        return await asyncio.get_running_loop().run_in_executor(self.pool, self._render, text, rate)


def earcon(hz: float = 880, ms: int = 120, rate: int = Voice.OUT_RATE) -> bytes:
    """Short soft chime: 'I'm listening'."""
    t = np.arange(int(rate * ms / 1000)) / rate
    env = np.minimum(1, np.minimum(t / 0.01, (t[-1] - t) / 0.04))
    return (np.sin(2 * np.pi * hz * t) * env * 6000).astype(np.int16).tobytes()
