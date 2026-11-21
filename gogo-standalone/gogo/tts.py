"""Text to speech for the glasses (they have no TTS engine): render a sentence to 22.05 kHz mono 16-bit PCM.

Windows: System.Speech through PowerShell. macOS: `say`. If neither works, synth() returns None and the flow just waits
for the estimated reading time. Results are cached by text.
"""
import asyncio
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import wave

RATE = 22050
_cache = {}
_state = {"ok": None}

PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = -1
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile($args[1], $fmt)
$s.Speak([System.IO.File]::ReadAllText($args[0]))
$s.Dispose()
"""


def ready():
    return _state["ok"]


def _render(text):
    d = tempfile.mkdtemp(prefix="gogo-tts-")
    try:
        txt, out = os.path.join(d, "t.txt"), os.path.join(d, "o.wav")
        with open(txt, "w", encoding="utf-8") as f:
            f.write(text)
        if sys.platform.startswith("win"):
            ps1 = os.path.join(d, "s.ps1")
            with open(ps1, "w", encoding="utf-8") as f:
                f.write(PS)
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, txt, out],
                           check=True, capture_output=True, timeout=30)
        elif shutil.which("say"):
            subprocess.run(["say", "-o", out, "--data-format=LEI16@%d" % RATE, "-f", txt], check=True, capture_output=True, timeout=30)
        else:
            return None
        with wave.open(out, "rb") as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != RATE:
                return None
            return w.readframes(w.getnframes())
    except Exception:
        return None
    finally:
        shutil.rmtree(d, ignore_errors=True)


async def synth(text):
    k = hashlib.sha1(text.encode("utf-8")).hexdigest()
    if k in _cache:
        return _cache[k]
    pcm = await asyncio.to_thread(_render, text)
    _state["ok"] = bool(pcm) if _state["ok"] is None or pcm else _state["ok"]
    if pcm:
        _cache[k] = pcm
    return pcm
