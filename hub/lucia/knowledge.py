"""Parses knowledge/*.md into question → answer entries.

Format (see knowledge/people/_example.md):

    ---
    id: dev
    name: Dev Example
    aliases: Devvy, D
    intro: Dev, he's on your team.
    ---
    # Q: Where's he from?
    - also: where is he from / what's his hometown
    A: Dev grew up in Edison, New Jersey.

Entries with an empty `A:` are skipped, so half-filled templates are safe to commit.
Files starting with "_" (examples/templates) are ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Entry:
    scope: str          # "person" | "patient" | "place" | "faq"
    subject: str        # person id, place id, "patient" or "faq"
    questions: list[str]
    answer: str
    source: str

    @property
    def key(self) -> str:
        return f"{self.subject}:{self.questions[0]}"


@dataclass
class Person:
    id: str
    name: str
    first: str
    aliases: list[str] = field(default_factory=list)
    intro: str = ""
    relationship: str = ""
    pronouns: str = ""


@dataclass
class Knowledge:
    entries: list[Entry] = field(default_factory=list)
    people: dict[str, Person] = field(default_factory=dict)
    places: dict[str, dict] = field(default_factory=dict)

    def for_subject(self, subject: str) -> list[Entry]:
        return [e for e in self.entries if e.subject == subject]


_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _frontmatter(text: str) -> tuple[dict, str]:
    m = _FM.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def _blocks(body: str, scope: str, subject: str, source: str) -> list[Entry]:
    out: list[Entry] = []
    q: str | None = None
    also: list[str] = []
    ans: list[str] = []

    def flush():
        a = " ".join(x.strip() for x in ans).strip()
        if q and a:
            out.append(Entry(scope, subject, [q, *also], a, source))

    in_answer = False
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("# Q:"):
            flush()
            q, also, ans, in_answer = line[4:].strip(), [], [], False
        elif q is not None and line.lower().startswith("- also:"):
            also.extend(p.strip() for p in line[7:].split("/") if p.strip())
        elif q is not None and line.startswith("A:"):
            ans, in_answer = [line[2:]], True
        elif in_answer and line and not line.startswith("#"):
            ans.append(line)
        elif line.startswith("## "):  # section header (places) ends a block
            flush()
            q, ans, in_answer = None, [], False
    flush()
    return out


def _places(text: str, source: str) -> tuple[dict[str, dict], list[Entry]]:
    places: dict[str, dict] = {}
    entries: list[Entry] = []
    parts = re.split(r"^## (\w+)\s*$", text, flags=re.M)
    for pid, chunk in zip(parts[1::2], parts[2::2]):
        meta = {}
        for line in chunk.splitlines():
            m = re.match(r"^(\w+):\s*(.+)$", line.strip())
            if m and not line.startswith("A:"):
                meta[m.group(1)] = m.group(2)
        places[pid] = meta
        entries.extend(_blocks(chunk, "place", pid, source))
    return places, entries


def load(knowledge_dir: Path) -> Knowledge:
    kb = Knowledge()
    for path in sorted(knowledge_dir.rglob("*.md")):
        if path.name.startswith("_") or path.name.upper().startswith("README"):
            continue
        text = _COMMENT.sub("", path.read_text())
        rel = str(path.relative_to(knowledge_dir))
        if path.parent.name == "people":
            meta, body = _frontmatter(text)
            pid = meta.get("id") or path.stem
            name = meta.get("name") or pid.title()
            kb.people[pid] = Person(
                id=pid, name=name, first=name.split()[0],
                aliases=[a.strip() for a in meta.get("aliases", "").split(",") if a.strip()],
                intro=meta.get("intro", ""), relationship=meta.get("relationship", ""),
                pronouns=meta.get("pronouns", ""),
            )
            kb.entries.extend(_blocks(body, "person", pid, rel))
        elif path.stem == "places":
            places, entries = _places(text, rel)
            kb.places.update(places)
            kb.entries.extend(entries)
        elif path.stem == "patient":
            _, body = _frontmatter(text)
            kb.entries.extend(_blocks(body, "patient", "patient", rel))
        else:
            _, body = _frontmatter(text)
            kb.entries.extend(_blocks(body, "faq", "faq", rel))
    return kb
