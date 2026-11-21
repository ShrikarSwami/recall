"""Schedule + live place + reminders, through the Brain (no sockets)."""
import asyncio
from datetime import datetime

from lucia import reminders, schedule
from lucia.brain import Brain
from lucia.config import CONFIG_DIR, KNOWLEDGE_DIR, load_config
from lucia.knowledge import load

NOW = datetime(2026, 11, 21, 11, 50).timestamp()


def brain():
    b = Brain(load_config(CONFIG_DIR / "app.example.json"), load(KNOWLEDGE_DIR))
    b.clock = lambda: NOW
    b.events = schedule.load(KNOWLEDGE_DIR / "schedule.md")
    return b


def ask(b, q):
    return asyncio.run(b.answer(q))


def test_schedule_beats_clock_and_kb():
    b = brain()
    r = ask(b, "what time is lunch")
    assert r.intent == "schedule" and "12:30" in r.speech
    assert ask(b, "what time is it").intent == "time"
    assert ask(b, "what's next").speech.startswith("Next is Lunch")


def test_where_am_i_uses_fresh_iphone_place_then_falls_back():
    b = brain()
    b.place = {"name": "Whole Foods in Hoboken", "kind": "grocery", "home_min": 10, "at": NOW - 60}
    r = ask(b, "where am I?")
    assert r.intent == "where_live" and r.speech == "You're at Whole Foods in Hoboken. Home is about 10 minutes away."
    b.place["at"] = NOW - 3600                      # stale after 15 min -> the preset place (City Tech)
    assert "City Tech" in ask(b, "where am I?").speech


def test_greeting_mentions_next_event():
    g = brain().greeting()
    assert "Your next thing is Lunch at 12:30." in g.speech and "City Tech" in g.speech


def test_reminders_example_and_arrival_lines():
    r = reminders.load(CONFIG_DIR / "reminders.example.md")
    assert r["grocery"] == ["Whole milk", "Ground tofu", "Bananas"]
    assert reminders.arrival_lines("grocery", r) == "You need: whole milk, ground tofu and bananas."
    assert reminders.arrival_lines("home", r).startswith("Your keys go in the bowl")
    assert reminders.arrival_lines("gym", r) == ""


def test_greeting_card_fits_three_lines_and_speech_keeps_everything():
    g = brain().greeting()
    assert len(g.lines) <= 3 and not g.lines[-1].endswith("…")
    assert "Next: Lunch at 12:30." in " ".join(g.lines)
    assert 'Say "Go-go"' in g.speech and "Your next thing is Lunch at 12:30." in g.speech


def test_after_midnight_says_this_morning():
    at = datetime(2026, 11, 21, 1, 40)
    assert schedule.next_line(schedule.load(KNOWLEDGE_DIR / "schedule.md"), at) == \
        "Your next thing is Breakfast at 8 this morning."
