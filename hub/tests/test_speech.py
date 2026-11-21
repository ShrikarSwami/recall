import numpy as np
import pytest

from lucia.speech import RATE, Segmenter, split_wake


@pytest.mark.parametrize("text,rest", [
    ("Lucia, who is this?", "who is this?"),
    ("lucia who is this", "who is this"),
    ("Lucía, where are we?", "where are we?"),
    ("Lucy a, what day is it", "what day is it"),
    ("Lucia.", ""),
    ("Yo Lucia, who is this?", "who is this?"),
    ("Team BB, who is this? Lucio, who is this?", "who is this?"),   # heard live on the glasses
    ("okay so um Lucia where are we", "where are we"),
])
def test_wake_word_variants(text, rest):
    woke, r = split_wake(text, "Lucia")
    assert woke and r == rest


@pytest.mark.parametrize("text", ["who is this", "let's get lunch", "I lost my keys", "Louis is here",
                                  "We used to work on improving that, but that should shoot the life by in front of us.",
                                  "I think we should ask Lucia.", "Can you see it? It should be able to see a person."])
def test_no_false_wake(text):
    assert split_wake(text, "Lucia")[0] is False


def _tone(seconds, amp=0.4):
    t = np.arange(int(RATE * seconds)) / RATE
    # voice-like: a few harmonics with amplitude modulation
    x = sum(np.sin(2 * np.pi * f * t) for f in (180, 360, 540, 900)) / 4
    x *= 0.6 + 0.4 * np.sin(2 * np.pi * 4 * t)
    return (x * amp * 32767).astype(np.int16).tobytes()


def test_segmenter_cuts_one_utterance():
    seg = Segmenter()
    silence = np.zeros(int(RATE * 1.0), dtype=np.int16).tobytes()
    out = []
    for chunk in (silence, _tone(1.5), silence):
        for i in range(0, len(chunk), 3200):
            out += seg.feed(chunk[i:i + 3200])
    assert len(out) == 1 and 1.2 < len(out[0]) / 2 / RATE < 2.6


def test_voice_rate_keeps_rendered_audio_separate(monkeypatch):
    """Changing rate must affect the renderer and must not reuse the normal-speed clip."""
    import asyncio
    import wave
    from lucia.speech import Voice

    def render_file(args, **kwargs):
        rate = int(args[args.index('-r') + 1])
        with wave.open(args[args.index('-o') + 1], 'wb') as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(22050)
            out.writeframes(bytes([rate % 255]) * 200)

    monkeypatch.setattr('lucia.speech.subprocess.run', render_file)

    async def run():
        voice = Voice()
        try:
            normal = await voice.pcm('An answer.')
            slow = await voice.pcm('An answer.', rate=0.72)
            assert normal != slow
            assert await voice.pcm('An answer.') == normal
        finally:
            voice.pool.shutdown(wait=True)

    asyncio.run(run())


def test_segmenter_keeps_a_short_huh_or_what():
    """A 120 ms word must not vanish before the command recognizer sees it."""
    class ClassifiedFrames:
        def is_speech(self, frame, rate):
            return any(frame)

    seg = Segmenter()
    seg.vad = ClassifiedFrames()  # Controlled VAD decisions; exercise our real onset/end buffering.
    silence = b'\0' * 960
    voice = b'\1\0' * 480
    utterances = []
    for frame in [silence] * 10 + [voice] * 4 + [silence] * 30:
        utterances.extend(seg.feed(frame))
    assert len(utterances) == 1
    assert voice * 4 in utterances[0]
