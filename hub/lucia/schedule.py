"""The wearer's day, from knowledge/schedule.md: what's next, what's on today, when is X, and heads-ups.

Pure functions over a list of events plus "now", so everything is testable with a fixed clock.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from rapidfuzz import fuzz

HEADS_UP_MIN = 15

NEXT = re.compile(r"\b(what('s| is| do i have)? (next|coming up|after this)|what('s| is) (on|happening) (today|now|later)|"
                  r"what('s| is) (the )?(schedule|plan|agenda)|what (am i|are we) doing (today|next|later)|"
                  r"what do i have (today|next|later)|anything (coming up|later|today))\b", re.I)
WHEN = re.compile(r"\b(when('s| is| does| do| will)?|what time('s| is| does)?|how long (until|till|before))\b", re.I)


@dataclass(frozen=True)
class Event:
    start: datetime
    title: str
    detail: str = ""

    @property
    def key(self) -> str:
        return f"{self.start:%Y-%m-%d %H:%M} {self.title}"


def load(path: Path) -> list[Event]:
    if not path.exists():
        return []
    events: list[Event] = []
    day = None
    text = re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.S)
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})", line)
        if m:
            day = datetime.strptime(m.group(1), "%Y-%m-%d")
            continue
        m = re.match(r"^-\s*(\d{1,2}):(\d{2})\s+([^|]+?)\s*(?:\|\s*(.+))?$", line)
        if m and day is not None:
            start = day.replace(hour=int(m.group(1)), minute=int(m.group(2)))
            events.append(Event(start, m.group(3).strip(), (m.group(4) or "").strip()))
    return sorted(events, key=lambda e: e.start)


def say_time(t: datetime, now: datetime) -> str:
    """'at 12:30', 'at 2', 'tomorrow at 9'."""
    hm = t.strftime("%-I:%M").replace(":00", "")
    if t.date() == now.date():
        if now.hour < 6 and t.hour < 12:          # past midnight: "at 8" alone is ambiguous
            return f"at {hm} this morning"
        return f"at {hm}"
    if t.date() == (now + timedelta(days=1)).date():
        return f"tomorrow at {hm}"
    return f"on {t:%A} at {hm}"


def until(t: datetime, now: datetime) -> str:
    mins = round((t - now).total_seconds() / 60)
    if mins <= 1:
        return "right now"
    if mins < 60:
        return f"in about {mins} minutes"
    h, m = divmod(mins, 60)
    if h < 3:
        return f"in about {h} hour{'s' if h > 1 else ''}" + (f" and {m} minutes" if m >= 10 else "")
    return ""


def upcoming(events: list[Event], now: datetime, n: int = 3) -> list[Event]:
    return [e for e in events if e.start >= now - timedelta(minutes=5)][:n]


def find(events: list[Event], text: str) -> Event | None:
    """The event a question mentions ('when is lunch', 'what time do submissions close')."""
    t = text.lower()
    best, score = None, 0.0
    for e in events:
        s = fuzz.partial_ratio(e.title.lower(), t)
        if s > score:
            best, score = e, s
    return best if score >= 85 else None


def answer(events: list[Event], text: str, now: datetime) -> tuple[str, str] | None:
    """(speech, card title) for a schedule question, or None if it isn't one."""
    if not events:
        return None
    named = find(events, text) if WHEN.search(text) else None
    if named:
        same_today = [e for e in events if e.title == named.title]
        e = next((x for x in same_today if x.start >= now - timedelta(minutes=5)), same_today[-1])
        if e.start < now - timedelta(minutes=5):
            return f"{e.title} was {say_time(e.start, now)}.", e.title
        soon = until(e.start, now)
        extra = f" {e.detail}" if e.detail else ""
        return f"{e.title} is {say_time(e.start, now)}{', ' + soon if soon else ''}.{extra}", e.title
    if NEXT.search(text):
        up = upcoming(events, now)
        if not up:
            return "There's nothing else on your schedule today.", "Schedule"
        first = up[0]
        soon = until(first.start, now)
        lead = f"Next is {first.title.lower() if first.title.islower() else first.title} {say_time(first.start, now)}"
        lead += f", {soon}." if soon else "."
        rest = [e for e in up[1:] if e.start.date() == first.start.date()]
        if rest:
            lead += " After that, " + " and ".join(f"{e.title} {say_time(e.start, now)}" for e in rest) + "."
        return lead, "Coming up"
    return None


def next_line(events: list[Event], now: datetime) -> str:
    """For the greeting: 'Your next thing is Lunch at 12:30.'"""
    up = upcoming(events, now, 1)
    return f"Your next thing is {up[0].title} {say_time(up[0].start, now)}." if up else ""


def heads_up(events: list[Event], now: datetime, said: set[str], minutes: int = HEADS_UP_MIN) -> Event | None:
    """An event starting within `minutes` that hasn't been announced yet."""
    for e in events:
        if e.key not in said and timedelta(0) < e.start - now <= timedelta(minutes=minutes):
            return e
    return None
