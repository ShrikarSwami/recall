from datetime import datetime

import pytest

from lucia import schedule
from lucia.config import KNOWLEDGE_DIR

EV = schedule.load(KNOWLEDGE_DIR / "schedule.md")
AT_11 = datetime(2026, 11, 21, 11, 50)


def test_loads_both_days():
    assert len(EV) >= 15 and EV[0].start.day == 20 and EV[-1].title == "Hardware return"


def test_whats_next():
    speech, title = schedule.answer(EV, "what's next?", AT_11)
    assert speech.startswith("Next is Lunch at 12:30, in about 40 minutes.") and "Submissions close at 2" in speech


@pytest.mark.parametrize("q,expect", [
    ("when is lunch", "Lunch is at 12:30, in about 40 minutes."),
    ("what time do submissions close", "Submissions close is at 2"),
    ("when is the pitch workshop", "Pitch workshop was at 11."),
    ("when are the awards", "Awards is at 5:30"),
])
def test_when_is(q, expect):
    assert schedule.answer(EV, q, AT_11)[0].startswith(expect)


@pytest.mark.parametrize("q", ["what time is it", "when is my birthday", "who is this", "where are we"])
def test_not_schedule_questions(q):
    assert schedule.answer(EV, q, AT_11) is None


def test_heads_up_once():
    said: set[str] = set()
    at = datetime(2026, 11, 21, 12, 17)
    e = schedule.heads_up(EV, at, said)
    assert e and e.title == "Lunch"
    said.add(e.key)
    assert schedule.heads_up(EV, at, said) is None


def test_greeting_line_and_end_of_day():
    assert schedule.next_line(EV, AT_11) == "Your next thing is Lunch at 12:30."
    assert "nothing else" in schedule.answer(EV, "what's next", datetime(2026, 11, 21, 19, 0))[0]


def test_calendar_phrasings_reach_the_schedule():
    for q in ["what's on my schedule today?", "what's on my calendar", "Lucia, what's my schedule",
              "read me today's agenda", "what's on the calendar today"]:
        assert schedule.NEXT.search(q), q
