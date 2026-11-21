"""Loads config/app.local.json (falls back to app.example.json) and fills {placeholders}."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
CONFIG_DIR = ROOT / "config"
KNOWLEDGE_DIR = ROOT / "knowledge"
FACES_DIR = ROOT / "faces"
DATA_DIR = ROOT / "hub" / "data"


def load_config(path: Path | None = None) -> dict:
    if path is None:
        local = CONFIG_DIR / "app.local.json"
        path = local if local.exists() else CONFIG_DIR / "app.example.json"
    cfg = json.loads(Path(path).read_text())
    cfg.setdefault("server", {"host": "0.0.0.0", "port": 9100})
    cfg.setdefault("voice", {}).setdefault("name", "Samantha")
    return cfg


def placeholders(cfg: dict) -> dict:
    p, c = cfg["patient"], cfg["caregiver"]
    return {
        "app": cfg["appName"],
        "wake": cfg["wakeWord"],
        "patient": p.get("preferredName") or p["name"],
        "patient_full": p["name"],
        "caregiver": c["name"],
        "caregiver_relationship": c.get("relationship", ""),
    }


def fill(text: str, values: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), text)
