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

from . import matcher, schedule
from .config import fill, placeholders
from .knowledge import Knowledge

DISTRESS = re.compile(
    r"\b(go(ing)? home|want (to go )?home|take me home|scared|afraid|frightened|i('m| am) lost|"
    r"where is everyone|where('s| is) my (mom|mother|dad|father|wife|husband)|help me|i('m| am) confused|"
    r"don't know where i am|do not know where i am|get me out)\b", re.I)
TIME = re.compile(r"\b(what )?(time|day|date|year|month)\b.*\b(is it|today|now)\b|\bwhat day\b|\bwhat time\b|"
                  r"\bwhat('s| is) the date\b|\bwhat year\b|\bwhat month\b|\btoday's date\b", re.I)
WHERE = re.compile(r"\b(where (am i|are we|is this)|what (is|'s) this place|what place is this|where have i (got|gotten) to)\b", re.I)
PLACE_FRESH_S = 15 * 60   # an iPhone place report counts as "where you are now" for this long
WHO_THIS = re.compile(
    r"\b(who('s| is| are)? (this|that|he|she|they|it|in front of me|next to me|talking)|"
    r"who am i (talking|speaking) (to|with)|(?<!how )do i know (him|her|them|this|that)|"
    r"have we met|what('s| is) (his|her|their) name|who('s| is) (this|that) (person|guy|man|woman|lady|girl))\b", re.I)
SCENE = re.compile(r"\b(what am i (looking at|seeing)|what('s| is) (in front of me|around me|this place look)|"
                   r"what do you see|describe (this|what))\b", re.I)

YES = re.compile(r"^\W*(yes|yeah|yep|yup|sure|okay|ok|please|of course|yes please|go ahead|tell me|i do|sounds good)\b", re.I)
NO = re.compile(r"^\W*(no|nope|nah|not now|no thanks|no thank you|i'?m (ok|okay|fine|good)|that'?s (ok|okay|fine|all))\b", re.I)

SEEN_FRESH_S = 15        # a face counts as "in front of you" for this long
TOPIC_FRESH_S = 180      # "he"/"she" refers to the last person discussed for this long
OFFER_S = 10             # a yes/no offer stays open this long (the hub extends it past the spoken audio)
MORE_MAX = 3             # "want to hear more?" chains at most this many facts
OFFER_HOW = 'Nod or say "yes"  ·  shake or say "no"'


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
    offer: str | None = None       # "more" | "tell_caregiver": Lucia asked a yes/no question
    prompt: str | None = None      # lens line while an offer is open


@dataclass
class Offer:
    kind: str                      # "more" | "tell_caregiver"
    subject: str | None
    until: float
    question: str = ""             # what the wearer asked (for tell_caregiver)
    told: list = field(default_factory=list)   # fact keys already read out in this chain


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
    offer: Offer | None = None
    events: list = field(default_factory=list)                 # schedule.Event list (knowledge/schedule.md)
    place: dict | None = None                                  # live place from the iPhone: name, kind, home_min, at

    # ---------------------------------------------------------------- context
    def live_place(self) -> dict | None:
        if self.place and self.clock() - self.place.get("at", 0) < PLACE_FRESH_S:
            return self.place
        return None

    def where_line(self) -> str:
        p = self.live_place()
        if p:
            line = f"You're at {p['name']}."
            if p.get("home_min") is not None:
                m = int(p["home_min"])
                line += " Home is about a minute away." if m <= 1 else f" Home is about {m} minutes away."
            return line
        place = self.kb.places.get(self.cfg.get("currentPlace", ""), {})
        return f"You're at {place['name']}." if place.get("name") else ""
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
    def _reply(self, speech: str, title: str, intent: str, subject: str | None = None,
               card: str | None = None, **kw) -> Reply:
        """`card`: shorter text for the lens when the spoken sentence is too long for 3 lines."""
        speech = fill(speech, self.vals)
        key = f"{intent}:{subject}:{speech[:40]}"
        now = self.clock()
        self.history.append((now, key))
        repeats = sum(1 for t, k in self.history if k == key and now - t < 600)
        shown = fill(card, self.vals) if card else speech
        lines = textwrap.wrap(shown, 34)[:3]
        if len(textwrap.wrap(shown, 34)) > 3:
            lines[-1] = lines[-1][:31].rstrip() + "…"
        return Reply(speech, fill(title, self.vals)[:22], lines, intent, subject, repeat_count=repeats, **kw)

    def intro(self, pid: str) -> str:
        p = self.kb.people[pid]
        for e in self.kb.for_subject(pid):
            if matcher.normalise(e.questions[0]).startswith(("who is this", "who is that")):
                return e.answer
        return p.intro or f"This is {p.first}."

    # ---------------------------------------------------------------- yes/no offers
    def _more_facts(self, pid: str, told: list) -> list:
        skip = ("who is this", "who is that", "how do i know")
        return [e for e in self.kb.for_subject(pid)
                if not matcher.normalise(e.questions[0]).startswith(skip) and e.key not in told]

    def _with_offer(self, r: Reply, kind: str, subject: str | None, question: str = "",
                    told: list | None = None) -> Reply:
        """Append a yes/no question to the spoken answer (the lens keeps the answer + a nod/yes prompt)."""
        if kind == "more":
            if not self._more_facts(subject, told or []) or len(told or []) >= MORE_MAX:
                self.offer = None
                return r
            first = self.kb.people[subject].first
            ask, short = f" Want to hear more about {first}?", f"Hear more about {first}?"
        else:
            ask, short = " Should I let {caregiver} know?", "Tell {caregiver}?"
        r.speech += fill(ask, self.vals)
        r.offer, r.prompt = kind, fill(short, self.vals) + "\n" + OFFER_HOW
        self.offer = Offer(kind, subject, self.clock() + OFFER_S, question, list(told or []))
        return r

    def intro_reply(self, pid: str, intent: str = "who_is_this") -> Reply:
        r = self._reply(self.intro(pid), self.kb.people[pid].first, intent, pid)
        return self._with_offer(r, "more", pid)

    def gesture(self, name: str) -> Reply | None:
        """A nod/shake from the IMU. Only means something while an offer is open."""
        if not self.offer or self.clock() > self.offer.until:
            return None
        return self._resolve(name == "nod")

    def _resolve(self, yes: bool) -> Reply:
        o, self.offer = self.offer, None
        if not yes:
            return self._reply("Okay. I'm here whenever you need me.", "Okay", "offer_no", o.subject)
        if o.kind == "more":
            facts = self._more_facts(o.subject, o.told)
            if not facts:
                return self._reply("That's all I know for now.", self.kb.people[o.subject].first, "offer_yes", o.subject)
            e = facts[0]
            self.topic = (o.subject, self.clock())
            r = self._reply(e.answer, self.kb.people[o.subject].first, "offer_yes", o.subject)
            return self._with_offer(r, "more", o.subject, told=o.told + [e.key])
        r = self._reply("Okay. I've let {caregiver} know.", "Done", "offer_yes")
        r.alert = f"{self.vals['patient']} asked something I couldn't answer: \"{o.question}\""
        return r

    def greeting(self) -> Reply:
        where = self.where_line()
        nxt = schedule.next_line(self.events, datetime.fromtimestamp(self.clock()))
        parts = [f"Hi {{patient}}.", where, nxt, f'Say "{{wake}}" if you need anything.']
        # The lens already pins the "Say Lucia" hint, so the card keeps just where + next (fits 3 lines).
        card = " ".join(p for p in (where, nxt.replace("Your next thing is", "Next:")) if p)
        return self._reply(" ".join(p for p in parts if p), "Hi {patient}", "greeting", card=card or None)

    # ---------------------------------------------------------------- main entry
    async def answer(self, text: str) -> Reply:
        t = text.strip()
        if self.offer and self.clock() <= self.offer.until and len(t.split()) <= 5:
            if YES.search(t):
                return self._resolve(True)
            if NO.search(t):
                return self._resolve(False)
        self.offer = None

        if DISTRESS.search(t):
            r = self._reply("You're safe, {patient}. {caregiver} knows where you are, and I'm letting him know now.",
                            "You're safe", "distress")
            r.alert = f"{self.vals['patient']} said: \"{t}\""
            return r

        # Schedule before the clock, so "what time is lunch" isn't answered with the current time.
        sched = schedule.answer(self.events, t, datetime.fromtimestamp(self.clock()))
        if sched:
            return self._reply(sched[0], sched[1], "schedule")

        if WHERE.search(t) and self.live_place():
            return self._reply(self.where_line(), "Where you are", "where_live")

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
                return self.intro_reply(pid)
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
            return self.intro_reply(named, "who_is")

        cands = matcher.candidates(t, self.kb, person, self.cfg.get("currentPlace"))
        if person and cands and cands[0].entry.subject != person:
            # "what does he do?" is about the person, not Lucia's own FAQ ("what can you do?"): a close
            # match about the person in view wins over a slightly better generic one.
            mine = next((c for c in cands if c.entry.subject == person), None)
            if mine and mine.score >= matcher.MAYBE and mine.score >= cands[0].score - 6:
                cands = [mine] + [c for c in cands if c is not mine]
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
        r = self._reply("I'm not sure about that one.", "Not sure", "unknown", score=best.score if best else None)
        return self._with_offer(r, "tell_caregiver", None, question=t)
