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


def test_a_new_question_during_an_offer_is_not_a_yes(brain):
    brain.saw("dev")
    ask(brain, "who is this")
    r = ask(brain, "tell me about Ana")
    assert r.subject == "ana" and r.intent != "offer_yes"


@pytest.mark.parametrize("q", ["yes", "Yes please.", "yeah, sure", "tell me more", "okay thanks"])
def test_yes_variants(brain, q):
    brain.saw("dev")
    ask(brain, "who is this")
    assert ask(brain, q).intent == "offer_yes"


def test_bystander_talk_during_an_offer_is_ignored():
    """Rehearsal 1: chatter during "Want to hear more?" was answered, each answer opened a new offer."""
    import asyncio
    import time
    from lucia import server
    hub, asked = server.hub, []

    async def fake_question(text):
        asked.append(text)

    async def run(text):
        async def tx(pcm):
            return text
        hub.stt.transcribe, hub.question = tx, fake_question
        hub.armed_until, hub.armed_by_offer = time.time() + 10, True
        await hub.utterance(b"")

    try:
        for said in ["Oh, it works. It works.", "Abhi, Abhi, Abhi", "Yes, that is my game of magnets."]:
            asyncio.run(run(said))
        assert asked == []
        for said in ["Yes.", "yeah sure", "no thanks"]:
            asyncio.run(run(said))
        assert asked == ["Yes.", "yeah sure", "no thanks"]
    finally:
        del hub.stt.transcribe, hub.question
        hub.armed_until, hub.armed_by_offer = 0.0, False


def test_standby_keeps_lucia_quiet_until_start_except_falls():
    import asyncio
    from lucia import server
    hub, sent = server.hub, []

    async def capture(msg):
        sent.append(msg if isinstance(msg, dict) else "pcm")
    hub.to_glasses = capture
    hub.cfg["voice"]["speakAnswers"] = False
    try:
        asyncio.run(hub.set_standby(True))
        assert {"type": "power", "on": False} in sent
        sent.clear()
        asyncio.run(hub.say(hub.brain._reply("Hello there.", "Hi", "kb:faq")))
        assert not [m for m in sent if isinstance(m, dict) and m.get("type") == "card"]
        asyncio.run(hub.set_standby(False))
        cards = [m for m in sent if isinstance(m, dict) and m.get("type") == "card"]
        assert {"type": "power", "on": True} in sent and cards[-1]["title"] == "Welcome"
    finally:
        del hub.to_glasses
        hub.cfg["voice"]["speakAnswers"] = True
        hub.standby = False


@pytest.mark.parametrize("said", ["Oh yeah!", "Uh-huh.", "yes I would", "Yeah, tell me more.", "Sure, why not."])
def test_natural_yes_replies_count(brain, said):
    from lucia.brain import YES
    assert YES.search(said)


@pytest.mark.parametrize("said", ["No, I'm good.", "Not really.", "Um, no.", "Nope."])
def test_natural_no_replies_count(brain, said):
    from lucia.brain import NO
    assert NO.search(said)
