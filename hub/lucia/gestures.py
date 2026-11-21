"""Head nod / shake from the M6 gyroscope.

Only used while Go-go has just offered something ("Want to hear more about Sid?"), so a natural nod while
chatting is never misread. Calibrated on our real recordings (docs/HARDWARE.md, hub/data/recordings):
M6 gyro axes are x = yaw (shake "no"), y = pitch (nod "yes"). Nods peak ~50-120 deg/s RMS on y, shakes
~230-290 deg/s on x; temple touches, the ring test and putting the glasses on never cross these rules.

IMU rows from the glasses app: [sensor_type, t_ms, x, y, z(, w)]; type 4 = gyroscope in rad/s.
"""
from __future__ import annotations

import math
from collections import deque

GYRO = 4
WINDOW_S = 1.5
SWING = 30.0          # deg/s: a direction change only counts past this speed


def _swings(vals: list[float]) -> int:
    sign, n = 0, 0
    for v in vals:
        if abs(v) < SWING:
            continue
        s = 1 if v > 0 else -1
        if sign and s != sign:
            n += 1
        sign = s
    return n


def classify(samples: list[tuple[float, float, float]]) -> str | None:
    """samples: (t_seconds, yaw_dps, pitch_dps). Returns "nod", "shake" or None."""
    if len(samples) < 20:
        return None
    rx = math.sqrt(sum(s[1] ** 2 for s in samples) / len(samples))
    ry = math.sqrt(sum(s[2] ** 2 for s in samples) / len(samples))
    if ry >= 50 and ry >= 2 * rx and _swings([s[2] for s in samples]) >= 2:
        return "nod"
    if rx >= 80 and rx >= 2 * ry and _swings([s[1] for s in samples]) >= 2:
        return "shake"
    return None


class HeadGestures:
    def __init__(self):
        self.buf: deque[tuple[float, float, float]] = deque()

    def reset(self) -> None:
        self.buf.clear()

    def feed(self, rows: list) -> str | None:
        for r in rows:
            if len(r) >= 5 and r[0] == GYRO:
                self.buf.append((r[1] / 1000.0, math.degrees(r[2]), math.degrees(r[3])))
        if not self.buf:
            return None
        newest = self.buf[-1][0]
        while self.buf and newest - self.buf[0][0] > WINDOW_S:
            self.buf.popleft()
        g = classify(list(self.buf))
        if g:
            self.buf.clear()
        return g


def synth(kind: str, seconds: float = 1.6, hz: float = 2.0, rate: int = 60, t0_ms: int = 0) -> list[list]:
    """Fake gyro rows for a nod or shake (replay tool, simulator, tests)."""
    amp = math.radians(140 if kind == "nod" else 300)
    rows = []
    for i in range(int(seconds * rate)):
        t = i / rate
        v = amp * math.sin(2 * math.pi * hz * t)
        x, y = (0.02, v) if kind == "nod" else (v, 0.02)
        rows.append([GYRO, t0_ms + int(t * 1000), x, y, 0.0])
    return rows
