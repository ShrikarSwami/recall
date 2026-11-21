import numpy as np
import pytest

from lucia.speech import RATE, Segmenter, split_wake


@pytest.mark.parametrize("text,rest", [
    ("Lucia, who is this?", "who is this?"),
    ("lucia who is this", "who is this"),
    ("Lucía, where are we?", "where are we?"),
    ("Lucy a, what day is it", "what day is it"),
    ("Lucia.", ""),
])
def test_wake_word_variants(text, rest):
    woke, r = split_wake(text, "Lucia")
    assert woke and r == rest


@pytest.mark.parametrize("text", ["who is this", "let's get lunch", "I lost my keys", "Louis is here"])
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
