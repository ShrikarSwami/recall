"""Place-tagged reminders read once when the wearer arrives somewhere (iPhone Shortcut → POST /api/place).

File: config/reminders.local.md (private, gitignored) if it exists, else config/reminders.example.md (demo).

    ## grocery
    - Whole milk
    - Ground tofu
    ## home
    - Your keys go in the bowl by the door.

Section names are place *kinds* the Shortcut sends ("grocery", "home", "pharmacy", "work", ...).
Grocery items are read as a shopping list ("You need: whole milk and ground tofu."); other kinds are read
as sentences. Time-based reminders (pills) are a separate, planned feature: see docs/PILLS_OUTLINE.md.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import CONFIG_DIR

LIST_KINDS = {"grocery", "store", "supermarket", "pharmacy"}


def source() -> Path:
    local = CONFIG_DIR / "reminders.local.md"
    return local if local.exists() else CONFIG_DIR / "reminders.example.md"


def load(path: Path | None = None) -> dict[str, list[str]]:
    path = path or source()
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    kind = None
    for line in re.sub(r"<!--.*?-->", "", path.read_text(), flags=re.S).splitlines():
        line = line.strip()
        if line.startswith("## "):
            kind = line[3:].strip().lower()
            out.setdefault(kind, [])
        elif line.startswith("- ") and kind:
            item = line[2:].strip()
            if item:
                out[kind].append(item)
    return out


def _join(items: list[str]) -> str:
    items = [i.rstrip(".") for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def arrival_lines(kind: str, reminders: dict[str, list[str]], max_items: int = 6) -> str:
    items = reminders.get((kind or "").lower(), [])
    if not items:
        return ""
    if kind.lower() in LIST_KINDS:
        shown = items[:max_items]
        more = f", and {len(items) - max_items} more on your phone" if len(items) > max_items else ""
        return f"You need: {_join([i[0].lower() + i[1:] if i[:1].isupper() and not i[:2].isupper() else i for i in shown])}{more}."
    return " ".join(i if i.endswith(".") else i + "." for i in items[:3])
