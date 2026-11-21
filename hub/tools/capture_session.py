"""Guided hardware capture: Go-go speaks each instruction on the glasses, then records that step.

    cd hub && uv run python tools/capture_session.py            # all steps (~4 min)
    cd hub && uv run python tools/capture_session.py nod shake  # only some steps

Output: hub/data/recordings/<step>/ (mic.wav, frames/*.jpg, imu.jsonl, keys.jsonl, meta.json). Local only.
Replay them later without glasses: tools/replay_glasses.py.
"""
import sys
import time

import httpx

HUB = "http://localhost:9100"

STEPS = [
    ("still",        8,  "Hold still and look straight ahead.", "Look ahead, hold still"),
    ("right_temple", 22, "Right side of the glasses. Tap once. Double tap. Long press. Swipe forward. Swipe back. Swipe up and down.",
                         "Right temple: tap, double, hold, swipes"),
    ("left_temple",  15, "Now the left side. Tap, double tap, long press, and swipes.", "Left temple: tap, double, hold, swipes"),
    ("ring",         15, "If you have the ring, press every ring button once, slowly.", "Ring: each button once"),
    ("frame_button", 10, "Short press any button on the frame. Not a long power press.", "Frame button: short press"),
    ("nod",          10, "Nod yes, three times.", "Nod yes x3"),
    ("shake",        10, "Shake your head no, three times.", "Shake no x3"),
    ("tilt",         10, "Tilt your head to the left shoulder, then the right.", "Tilt left, then right"),
    ("look_around",  12, "Slowly look left, then center, then right, then up, then down.", "Look L, C, R, up, down"),
    ("walk",         12, "Walk a few steps and come back.", "Walk a few steps"),
    ("voice_wearer", 25, "Ask me questions out loud, like: Go-go, who is this? Go-go, where are we? What time is it?",
                         "Ask me questions out loud"),
    ("voice_other",  20, "Now someone else, about one meter away, asks a few questions.", "Someone else asks questions"),
    ("noise",        15, "Stay quiet. I'm recording the room noise.", "Quiet: recording room noise"),
    ("faces",        25, "Look at each teammate's face for three seconds, one by one, from one meter away.",
                         "Look at each teammate, 3 s each"),
    ("off_on",       15, "Take the glasses off, set them down for five seconds, then put them back on.", "Off for 5 s, then back on"),
]


def say(c: httpx.Client, text: str, title: str):
    c.post(f"{HUB}/api/say", json={"text": text, "title": title}, timeout=30)


def main(only: list[str]):
    with httpx.Client() as c:
        state = c.get(f"{HUB}/api/state").json()
        if not state["glasses"]:
            sys.exit("Glasses aren't connected to the hub.")
        steps = [s for s in STEPS if not only or s[0] in only]
        say(c, f"Recording session. {len(steps)} short steps. Just follow my voice.", "Recording")
        time.sleep(4)
        for i, (label, secs, speech, card) in enumerate(steps, 1):
            print(f"[{i}/{len(steps)}] {label} ({secs}s): {card}")
            say(c, speech, f"{i}/{len(steps)} {card}"[:22])
            time.sleep(max(2.5, len(speech.split()) * 0.38))      # let the instruction finish
            c.post(f"{HUB}/api/record", json={"label": label, "seconds": secs, "imu": True})
            time.sleep(secs + 1)
            c.post(f"{HUB}/api/say", json={"text": "Okay.", "title": "Done"})
            time.sleep(1.2)
        say(c, "All done. Thank you.", "All done")
        print("done → hub/data/recordings/")


if __name__ == "__main__":
    main(sys.argv[1:])
