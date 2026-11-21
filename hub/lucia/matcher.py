"""Maps a spoken question to a knowledge-base entry.

1. normalise ("where's" → "where is"), replace pronouns and the person's name with "X",
   so "where's he from", "where is Dev from" and "where does she come from" look alike;
2. fuzzy-score against every question + `also:` phrasing in scope (rapidfuzz, ~1 ms);
3. if the best score is unsure, the caller may ask the LLM to pick among the top few.
The answer is always the stored text: the model never writes facts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from .knowledge import Entry, Knowledge

CONTRACTIONS = {
    "what's": "what is", "where's": "where is", "who's": "who is", "how's": "how is",
    "when's": "when is", "that's": "that is", "it's": "it is", "he's": "he is", "she's": "she is",
    "they're": "they are", "i'm": "i am", "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "cannot", "isn't": "is not", "wasn't": "was not", "i've": "i have", "we're": "we are",
    "whats": "what is", "wheres": "where is", "whos": "who is",
}
PRONOUN_PHRASES = [
    "this person", "that person", "this guy", "that guy", "this girl", "that girl", "this man",
    "that man", "this woman", "that woman", "this lady", "that lady", "this dude", "that dude",
    "the person in front of me", "the person next to me", "this one", "that one",
]
PRONOUNS = {"he", "she", "him", "her", "his", "hers", "they", "them", "their", "theirs", "himself", "herself"}
FILLER = {"um", "uh", "hey", "okay", "ok", "so", "please", "can", "you", "tell", "me", "lucia"}

SURE = 82      # accept without asking the LLM
MAYBE = 62     # below this, don't accept even if the LLM is down


def normalise(text: str) -> str:
    t = text.lower().replace("’", "'")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    t = " ".join(CONTRACTIONS.get(w, w) for w in t.split())
    return t


def _canon(text: str, names: list[str]) -> str:
    t = " " + normalise(text) + " "
    for phrase in sorted(PRONOUN_PHRASES + [n.lower() for n in names if n], key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(phrase)}('s)?\b", "X", t)
    words = ["X" if w in PRONOUNS else w for w in t.split()]
    return " ".join(w for w in words if w not in FILLER) or "X"


def mentions_pronoun(text: str) -> bool:
    t = " " + normalise(text) + " "
    return any(f" {p} " in t for p in PRONOUNS) or any(p in t for p in PRONOUN_PHRASES)


def person_mentioned(text: str, kb: Knowledge) -> str | None:
    t = " " + normalise(text) + " "
    for pid, p in kb.people.items():
        for n in [p.name, p.first, *p.aliases]:
            if n and re.search(rf"\b{re.escape(n.lower())}\b", t):
                return pid
    return None


@dataclass
class Scored:
    score: float
    entry: Entry
    phrase: str


def candidates(text: str, kb: Knowledge, person: str | None, place: str | None) -> list[Scored]:
    pool: list[tuple[Entry, list[str]]] = []
    for e in kb.entries:
        if e.scope == "person":
            if e.subject != person:
                continue
            p = kb.people[person]
            pool.append((e, [p.name, p.first, *p.aliases]))
        elif e.scope == "place":
            if e.subject != place:
                continue
            pool.append((e, []))
        else:
            pool.append((e, []))
    names = [kb.people[person].name, kb.people[person].first, *kb.people[person].aliases] if person else []
    q = _canon(text, names)
    out: list[Scored] = []
    for e, ent_names in pool:
        best, best_phrase = 0.0, ""
        for phrase in e.questions:
            c = _canon(phrase, ent_names)
            s = 0.5 * fuzz.token_set_ratio(q, c) + 0.5 * fuzz.token_sort_ratio(q, c)
            if s > best:
                best, best_phrase = s, phrase
        if e.scope == "person":
            best += 4  # the person we're talking about wins ties
        out.append(Scored(min(best, 100.0), e, best_phrase))
    out.sort(key=lambda s: s.score, reverse=True)
    return out
