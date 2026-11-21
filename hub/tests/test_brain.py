import asyncio
import shutil
from pathlib import Path

import pytest

from lucia.brain import Brain
from lucia.config import KNOWLEDGE_DIR, load_config
from lucia.knowledge import load

FIXED_NOW = 1795320000.0  # a fixed Saturday afternoon, so time answers are stable


@pytest.fixture()
def brain(tmp_path):
    kb_dir = tmp_path / "knowledge"
    shutil.copytree(KNOWLEDGE_DIR, kb_dir)
    shutil.copy(kb_dir / "people" / "_example.md", kb_dir / "people" / "dev.md")
    (kb_dir / "people" / "dev.md").write_text((kb_dir / "people" / "dev.md").read_text().replace("id: example", "id: dev"))
    (kb_dir / "people" / "ana.md").write_text(
        "---\nid: ana\nname: Ana Lopez\npronouns: she/her\n---\n"
        "# Q: Who is this?\nA: This is Ana. She leads the design on your team.\n\n"
        "# Q: Where's she from?\n- also: what's her hometown\nA: Ana is from Queens.\n\n"
        "# Q: Does she have pets?\nA:\n")  # unanswered: must be skipped
    cfg = load_config()
    b = Brain(cfg, load(kb_dir))
    b.clock = lambda: FIXED_NOW
    return b


def ask(b, text):
    return asyncio.run(b.answer(text))


def test_loader_skips_blank_answers_and_examples(brain):
    subjects = {e.subject for e in brain.kb.entries}
    assert {"dev", "ana", "patient", "faq", "city_tech"} <= subjects
    assert "example" not in subjects
    assert not any(e.subject == "ana" and "pets" in e.questions[0] for e in brain.kb.entries)
    assert all(e.answer.strip() for e in brain.kb.entries)
    assert not any("AGENTS" in e.source or "README" in e.source for e in brain.kb.entries)


def test_who_is_this_uses_face_in_view(brain):
    brain.saw("dev")
    r = ask(brain, "Go-go, who is this?")
    assert r.intent == "who_is_this" and "Dev" in r.speech and r.title == "Dev"


@pytest.mark.parametrize("q", ["where's he from", "where is he from?", "what's his hometown", "where did he grow up"])
def test_pronoun_follow_up_resolves_to_person_in_view(brain, q):
    brain.saw("dev")
    assert "Edison" in ask(brain, q).speech


def test_named_person_without_face(brain):
    assert "Queens" in ask(brain, "where is Ana from").speech
    # topic carries over to the next pronoun question
    assert "Queens" in ask(brain, "what's her hometown").speech


def test_nobody_in_view(brain):
    r = ask(brain, "who is that")
    assert "don't see anyone" in r.speech
    brain.saw(None)
    assert "met them yet" in ask(brain, "who's this?").speech


@pytest.mark.parametrize("q", ["where are we", "where am I", "what is this place", "what building is this"])
def test_place(brain, q):
    assert "City Tech" in ask(brain, q).speech


def test_patient_and_placeholders(brain):
    r = ask(brain, "what's my name")
    assert "Somya" in r.speech and "{" not in r.speech


def test_time(brain):
    r = ask(brain, "what day is it")
    assert r.intent == "time" and "It's" in r.speech


@pytest.mark.parametrize("q", ["I want to go home", "I'm scared", "where is everyone", "take me home"])
def test_distress_alerts(brain, q):
    r = ask(brain, q)
    assert r.intent == "distress" and r.alert and "safe" in r.speech


def test_unknown_is_gentle(brain):
    r = ask(brain, "what is the airspeed velocity of a swallow")
    assert r.intent == "unknown" and "not sure" in r.speech


def test_repeats_are_counted_and_answer_is_identical(brain):
    brain.saw("dev")
    a, b, c = (ask(brain, "who is this") for _ in range(3))
    assert a.speech == b.speech == c.speech and c.repeat_count == 3


def test_card_lines_fit_lens(brain):
    r = ask(brain, "what are these glasses")
    assert 1 <= len(r.lines) <= 3 and all(len(l) <= 34 for l in r.lines)


def test_how_do_i_know_him_is_not_who_is_this(brain):
    brain.saw("dev")
    r = ask(brain, "how do I know him?")
    assert r.intent.startswith("kb") and "hackathon" in r.speech


def test_tell_me_about_named_person_gives_intro(brain):
    r = ask(brain, "tell me about Dev")
    assert r.subject == "dev" and r.speech.startswith("This is Dev")


@pytest.mark.parametrize("q", ["who is a pyrom", "do you know Margaret", "who is my son", "tell me about my wife"])
def test_unknown_people_never_guessed(brain, q):
    r = ask(brain, q)
    assert r.intent == "unknown_person" and r.offer == "tell_caregiver"


@pytest.mark.parametrize("q", ["how much medicine should I take", "my chest hurts a bit", "should I take my pills"])
def test_health_goes_to_doctor_and_caregiver(brain, q):
    r = ask(brain, q)
    assert r.intent in ("health", "distress", "kb:faq") and ("doctor" in r.speech or r.alert)


def test_caregiver_text_says_what_was_asked(brain):
    ask(brain, "who is a pyrom")
    y = ask(brain, "yes")
    assert y.alert == 'Somya has a question: "who is a pyrom"'


def test_model_down_does_not_guess_from_a_loose_match():
    import asyncio
    from lucia import server
    b = server.hub.brain

    class Down:
        async def choose(self, *a, **k):
            return None

        async def freeform(self, *a, **k):
            return None
    llm, b.llm = b.llm, Down()
    try:
        r = asyncio.run(b.answer("what is the capital of France?"))
        assert "home computer" not in r.speech
        r = asyncio.run(b.answer("where is the bathroom?"))
        assert "bathroom" in r.speech.lower()
    finally:
        b.llm = llm
