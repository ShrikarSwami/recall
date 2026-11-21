"""Yes/no offers: "Want to hear more about Dev?" answered by voice or a head nod/shake."""
import json
from pathlib import Path

import pytest

from lucia.gestures import HeadGestures, classify, synth
from tests.test_brain import ask, brain  # noqa: F401  (fixture)

REC = Path(__file__).resolve().parents[1] / "data" / "recordings"


def test_intro_offers_more_and_yes_reads_next_fact(brain):
    brain.saw("dev")
    r = ask(brain, "who is this")
    assert r.offer == "more" and "hear more about Dev" in r.speech and 'Nod or say "yes"' in r.prompt
    assert len(r.lines) <= 3 and "hear more" not in " ".join(r.lines)   # lens keeps the answer itself
    nxt = ask(brain, "yes")
    assert nxt.intent == "offer_yes" and nxt.subject == "dev" and "Who is this" not in nxt.speech


def test_same_question_same_offer(brain):
    brain.saw("dev")
    assert ask(brain, "who is this").speech == ask(brain, "who is this").speech


def test_nod_and_shake_resolve(brain):
    brain.saw("dev")
    ask(brain, "who is this")
    assert brain.gesture("nod").intent == "offer_yes"
    ask(brain, "who is this")
    assert brain.gesture("shake").intent == "offer_no"
    assert brain.gesture("nod") is None          # nothing open: a nod means nothing


def test_offer_expires_and_normal_questions_still_work(brain):
    brain.saw("dev")
    ask(brain, "who is this")
    brain.clock = lambda: 1795320000.0 + 60
    assert brain.gesture("nod") is None
    assert ask(brain, "yes").intent != "offer_yes"


def test_new_question_closes_offer(brain):
    brain.saw("dev")
    ask(brain, "who is this")
    assert "City Tech" in ask(brain, "where are we").speech
    assert brain.offer is None


def test_more_chain_is_bounded(brain):
    brain.saw("dev")
    r = ask(brain, "who is this")
    n = 0
    while r.offer and n < 10:
        r = ask(brain, "yeah")
        n += 1
    assert n <= 3


def test_unknown_offers_to_tell_caregiver(brain):
    r = ask(brain, "what is the airspeed velocity of a swallow")
    assert r.offer == "tell_caregiver" and "let Shrikar know" in r.speech
    y = ask(brain, "yes please")
    assert y.alert and "swallow" in y.alert
    ask(brain, "what is the airspeed velocity of a swallow")
    assert ask(brain, "no").alert is None


@pytest.mark.parametrize("kind", ["nod", "shake"])
def test_synthetic_gestures_classify(kind):
    h = HeadGestures()
    rows = synth(kind)
    got = [g for i in range(0, len(rows), 6) if (g := h.feed(rows[i:i + 6]))]
    assert got and got[0] == kind


def _gyro(name):
    out = []
    for line in (REC / name / "imu.jsonl").read_text().splitlines():
        for r in json.loads(line)["rows"]:
            if r[0] == 4:
                out.append(r)
    return out


@pytest.mark.skipif(not (REC / "nod").exists(), reason="real recordings are private (Shrikar's Mac only)")
@pytest.mark.parametrize("name,want", [("nod", "nod"), ("shake", "shake"), ("right_temple", None),
                                       ("ring", None), ("off_on", None)])
def test_real_recordings(name, want):
    h = HeadGestures()
    rows = _gyro(name)
    got = {g for i in range(0, len(rows), 6) if (g := h.feed(rows[i:i + 6]))}
    assert (want in got) if want else not got


def test_still_is_nothing():
    assert classify([(i / 60, 2.0, -1.5) for i in range(90)]) is None
