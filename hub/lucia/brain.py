"""Decides what Lucia says. Pure logic: no audio, no sockets, so it's easy to test.

Order: distress → time/date → who-is-this (faces) → scene description → knowledge base → gentle "not sure".
Every answer is short, calm, and the same every time it's asked (each session = a brand-new user).
"""
from __future__ import annotations

import re
import textwrap
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from . import matcher
from .config import fill, placeholders
from .knowledge import Knowledge

DISTRESS = re.compile(
    r"\b(go(ing)? home|want (to go )?home|take me home|scared|afraid|frightened|i('m| am) lost|"
    r"where is everyone|where('s| is) my (mom|mother|dad|father|wife|husband)|help me|i('m| am) confused|"
    r"don't know where i am|do not know where i am|get me out)\b", re.I)
TIME = re.compile(r"\b(what )?(time|day|date|year|month)\b.*\b(is it|today|now)\b|\bwhat day\b|\bwhat time\b|"
                  r"\bwhat('s| is) the date\b|\bwhat year\b|\bwhat month\b|\btoday's date\b", re.I)
WHO_THIS = re.compile(
    r"\b(who('s| is| are)? (this|that|he|she|they|it|in front of me|next to me|talking)|"
    r"who am i (talking|speaking) (to|with)|(?<!how )do i know (him|her|them|this|that)|"
    r"have we met|what('s| is) (his|her|their) name|who('s| is) (this|that) (person|guy|man|woman|lady|girl))\b", re.I)
SCENE = re.compile(r"\b(what am i (looking at|seeing)|what('s| is) (in front of me|around me|this place look)|"
                   r"what do you see|describe (this|what))\b", re.I)

SEEN_FRESH_S = 15        # a face counts as "in front of you" for this long
TOPIC_FRESH_S = 180      # "he"/"she" refers to the last person discussed for this long


@dataclass
class Reply:
    speech: str
    title: str
    lines: list[str]
    intent: str
    subject: str | None = None
    alert: str | None = None
    repeat_count: int = 1
    score: float | None = None


@dataclass
class Brain:
    cfg: dict
    kb: Knowledge
    llm: object | None = None
    seen: dict[str, float] = field(default_factory=dict)       # person id -> last seen
    unknown_face_at: float = 0.0
    topic: tuple[str, float] | None = None                     # (person id, when)
    history: deque = field(default_factory=lambda: deque(maxlen=200))
    latest_frame: bytes | None = None
    clock: object = time.time

    # ---------------------------------------------------------------- context
    @property
    def vals(self) -> dict:
        return placeholders(self.cfg)

    def in_view(self) -> str | None:
        now = self.clock()
        fresh = [(t, pid) for pid, t in self.seen.items() if now - t < SEEN_FRESH_S]
        return max(fresh)[1] if fresh else None

    def context_person(self) -> str | None:
        p = self.in_view()
        if p:
            return p
        if self.topic and self.clock() - self.topic[1] < TOPIC_FRESH_S:
            return self.topic[0]
        return None

    def saw(self, person_id: str | None) -> None:
        if person_id:
            self.seen[person_id] = self.clock()
        else:
            self.unknown_face_at = self.clock()

    # ---------------------------------------------------------------- formatting
    def _reply(self, speech: str, title: str, intent: str, subject: str | None = None, **kw) -> Reply:
        speech = fill(speech, self.vals)
        key = f"{intent}:{subject}:{speech[:40]}"
        now = self.clock()
        self.history.append((now, key))
        repeats = sum(1 for t, k in self.history if k == key and now - t < 600)
        lines = textwrap.wrap(speech, 34)[:3]
        if len(textwrap.wrap(speech, 34)) > 3:
            lines[-1] = lines[-1][:31].rstrip() + "…"
        return Reply(speech, fill(title, self.vals)[:22], lines, intent, subject, repeat_count=repeats, **kw)

    def intro(self, pid: str) -> str:
        p = self.kb.people[pid]
        for e in self.kb.for_subject(pid):
            if matcher.normalise(e.questions[0]).startswith(("who is this", "who is that")):
                return e.answer
        return p.intro or f"This is {p.first}."

    def greeting(self) -> Reply:
        place = self.kb.places.get(self.cfg.get("currentPlace", ""), {})
        where = f" You're at {place['name']}." if place.get("name") else ""
        return self._reply(f"Hi {{patient}}.{where} Say \"{{wake}}\" if you need anything.", "Hi {patient}", "greeting")

    # ---------------------------------------------------------------- main entry
    async def answer(self, text: str) -> Reply:
        t = text.strip()
        if DISTRESS.search(t):
            r = self._reply("You're safe, {patient}. {caregiver} knows where you are, and I'm letting him know now.",
                            "You're safe", "distress")
            r.alert = f"{self.vals['patient']} said: \"{t}\""
            return r

        if TIME.search(t) and not matcher.person_mentioned(t, self.kb):
            now = datetime.fromtimestamp(self.clock())
            part = ("in the morning" if now.hour < 12 else "in the afternoon" if now.hour < 17
                    else "in the evening" if now.hour < 21 else "at night")
            day = now.day
            suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
            hm = now.strftime("%-I:%M").replace(":00", " o'clock")
            return self._reply(f"It's {now:%A}, {now:%B} {day}{suffix}. It's about {hm} {part}.",
                               f"{now:%a} {now:%-I:%M}", "time")

        named = matcher.person_mentioned(t, self.kb)
        if WHO_THIS.search(t) and not named:
            pid = self.in_view()
            if pid:
                self.topic = (pid, self.clock())
                return self._reply(self.intro(pid), self.kb.people[pid].first, "who_is_this", pid)
            if self.clock() - self.unknown_face_at < SEEN_FRESH_S:
                return self._reply("I don't think we've met them yet. It's okay to ask their name.",
                                   "Someone new", "who_is_this")
            return self._reply("I don't see anyone in front of you right now.", "No one here", "who_is_this")

        if SCENE.search(t) and self.llm is not None and self.latest_frame:
            desc = await self.llm.describe(self.latest_frame)
            if desc:
                return self._reply(desc, "Around you", "scene")

        person = named or (self.context_person() if matcher.mentions_pronoun(t) else None)
        if named and named != (self.topic or ("", 0))[0]:
            self.topic = (named, self.clock())
        if named and re.search(r"\bwho\b", t, re.I) and len(matcher.normalise(t).split()) <= 5:
            return self._reply(self.intro(named), self.kb.people[named].first, "who_is", named)

        cands = matcher.candidates(t, self.kb, person, self.cfg.get("currentPlace"))
        best = cands[0] if cands else None
        chosen = None
        if best and best.score >= matcher.SURE:
            chosen = best
        elif best and best.score >= 45 and self.llm is not None:
            top = cands[:6]
            k = await self.llm.choose(t, [c.phrase if c.entry.scope != "person" else
                                          f"{c.phrase} (about {self.kb.people[c.entry.subject].first})" for c in top])
            if k is not None and k >= 0:
                chosen = top[k]
            elif k is None and best.score >= matcher.MAYBE:  # LLM unreachable: trust a decent fuzzy match
                chosen = best
        elif best and best.score >= matcher.MAYBE:
            chosen = best

        if chosen:
            e = chosen.entry
            if e.scope == "person":
                self.topic = (e.subject, self.clock())
                title = self.kb.people[e.subject].first
            else:
                title = {"place": "Where you are", "patient": "{patient}", "faq": "{app}"}[e.scope]
            return self._reply(e.answer, title, f"kb:{e.scope}", e.subject, score=chosen.score)

        if self.llm is not None:
            recent = [k for _, k in list(self.history)[-4:]]
            free = await self.llm.freeform(t, self.vals["patient"], recent)
            if free:
                return self._reply(free, "{app}", "freeform", score=best.score if best else None)
        return self._reply("I'm not sure about that one. {caregiver} can help you with it.",
                           "Not sure", "unknown", score=best.score if best else None)
