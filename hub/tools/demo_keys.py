"""Operator hotkeys for the stage demo: one key press = one demo moment on the glasses.

    cd hub && .venv/bin/python tools/demo_keys.py            # hub on this Mac
    .venv/bin/python tools/demo_keys.py --hub http://<ip>:9100 --token <apiToken>

Keep this terminal window focused and press:
    g  grocery: "You're at the store" + the grocery list (config/reminders*.md, ## grocery)
    c  calendar: what's next on today's schedule (knowledge/events, live clock)
    f  fall: the same urgent caregiver text + "are you okay?" as a detected fall (marked as a demo trigger)
    s  stop: cut Lucia off and clear the lens
    q  quit
Everything goes through the hub's normal endpoints, so the lens, voice, caregiver feed and texts behave
exactly as in the real flow. Real texts are only sent when the hub runs without LUCIA_DRY_RUN.
"""
from __future__ import annotations

import argparse
import json
import sys
import termios
import threading
import tty
import urllib.request

STORE = {"name": "the grocery store", "kind": "grocery", "force": True, "remember": False}


def keys() -> dict:
    return {
        "g": ("grocery list", "/api/place", STORE),
        "c": ("today's schedule", "/api/ask", {"text": "what's next on my schedule?"}),
        "f": ("FALL alert", "/api/fall", {}),
        "s": ("start: welcome", "/api/demo/start", {}),
        "x": ("stop talking", "/api/ask", {"text": "stop"}),
        "b": ("blank: lens off until s", "/api/demo/standby", {}),
    }


def post(hub: str, path: str, body: dict, token: str | None) -> str:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Lucia-Token"] = token
    req = urllib.request.Request(hub + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode()[:120]
    except Exception as e:  # keep the demo going; show what went wrong
        return f"ERROR {e}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hub", default="http://127.0.0.1:9100")
    ap.add_argument("--token", default=None)
    a = ap.parse_args()
    hub = a.hub.rstrip("/")
    table = keys()
    print("Demo keys: " + "  ".join(f"[{k}] {v[0]}" for k, v in table.items()) + "  [q] quit", flush=True)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            k = sys.stdin.read(1).lower()
            if k in ("q", "\x03", "\x04"):
                break
            if k in table:
                label, path, body = table[k]
                print(f"{k} → {label}", flush=True)
                threading.Thread(target=lambda label=label, path=path, body=body: print(f"   {label}: {post(hub, path, body, a.token)}", flush=True),
                                 daemon=True).start()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    main()
