"""POST /api/place: the iPhone Shortcut contract (docs/SHORTCUT_API.md)."""
import os

from fastapi.testclient import TestClient

from lucia import reminders
from lucia.config import CONFIG_DIR
from lucia.server import app, hub

client = TestClient(app)   # requests come from host "testclient", i.e. "the network", so the token applies


def setup_module():
    import tempfile
    from pathlib import Path
    hub.log_path = Path(tempfile.mkdtemp()) / "events.jsonl"   # never write test events into the real caregiver feed
    hub.cfg["apiToken"] = "test-token"
    hub.cfg["voice"]["speakAnswers"] = False
    hub.reminders = reminders.load(CONFIG_DIR / "reminders.example.md")
    hub.brain.place = None
    hub.arrived_at.clear()


def test_requires_token_from_network():
    assert client.post("/api/place", json={"name": "Whole Foods"}).status_code == 401
    assert client.post("/api/say", json={"text": "hi"}).status_code == 401


def test_arrival_reads_list_once():
    h = {"X-Lucia-Token": "test-token"}
    body = {"name": "Whole Foods in Hoboken", "kind": "grocery", "home_min": "10.4"}
    first = client.post("/api/place", json=body, headers=h).json()
    assert first["said"] == ("You're at Whole Foods in Hoboken. Home is about 10 minutes away. "
                             "You need: whole milk, ground tofu and bananas.")
    again = client.post("/api/place", json=body, headers=h).json()
    assert again["said"] == ""                    # same place again: no repeat
    assert hub.brain.place["home_min"] == 10


def test_token_in_query_and_bad_input():
    assert client.post("/api/place?token=test-token", json={"kind": "grocery"}).status_code == 400
    r = client.post("/api/place?token=test-token", json={"name": "CVS", "kind": "pharmacy", "home_min": "soon"})
    assert r.status_code == 200 and hub.brain.place["home_min"] is None


def test_fall_requires_token():
    assert client.post("/api/fall").status_code == 401


def test_fall_with_token_alerts_in_dry_run():
    assert hub.alerts.dry
    r = client.post("/api/fall?token=test-token")
    assert r.status_code == 200 and r.json() == {"ok": True}
