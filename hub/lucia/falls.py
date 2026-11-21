"""Fall detection from the M6 accelerometer and gyroscope (rule based, standard library only).

A fall is three things in a row: free fall, then an impact, then the wearer lies still.
IMU rows from the glasses app: [sensor_type, t_ms, x, y, z(, w)];
type 1 = accelerometer in m/s^2, type 4 = gyroscope in rad/s (same rows as gestures.py).
While the glasses are not worn (worn=False) every row is ignored and the detector resets, so glasses
tossed on a desk never count.

NOTE: every number below is an untuned guess until we test it on real recordings of falls
(and of walking, sitting down hard and taking the glasses off).
"""
from __future__ import annotations

import math

ACCEL = 1
GYRO = 4
G = 9.81                      # m/s^2

FREE_FALL_G = 0.5             # accel magnitude below this = free fall
FREE_FALL_MIN_MS = 80         # ... for at least this long
IMPACT_G = 2.5                # accel magnitude above this = impact
IMPACT_WITHIN_MS = 1000       # impact must come this soon after free fall ends
STILL_G_BAND = 0.15           # still = accel magnitude within 1 g +/- this
STILL_GYRO = 0.5              # rad/s (~29 deg/s): gyro magnitude below this = still head
STILL_MS = 2000               # must stay still this long ...
STILL_WINDOW_MS = 4000        # ... and finish within this long after the impact
COOLDOWN_MS = 60_000          # after a "fall" event, stay quiet this long

_IDLE, _FALLING, _IMPACT = 0, 1, 2


class FallDetector:
    def __init__(self):
        self.cooldown_until = -math.inf
        self.reset()

    def reset(self) -> None:
        self.state = _IDLE
        self.ff_start: float | None = None      # start of the current free-fall run
        self.ff_end = 0.0                       # last free-fall sample time
        self.impact_t = 0.0
        self.still_start: float | None = None
        self.gyro = 0.0                         # latest gyro magnitude, rad/s
        self.last_t = -math.inf

    def feed(self, row: list, worn: bool = True) -> str | None:
        """Feed one IMU row. Returns "fall" once per event, else None."""
        if not worn:
            self.reset()
            return None
        if len(row) < 5:
            return None
        kind, t = row[0], float(row[1])
        if kind not in (ACCEL, GYRO) or t < self.last_t:
            return None
        self.last_t = t
        mag = math.sqrt(row[2] ** 2 + row[3] ** 2 + row[4] ** 2)
        if kind == GYRO:
            self.gyro = mag
            return None
        if t < self.cooldown_until:
            return None
        g = mag / G

        if self.state == _IDLE:
            if g < FREE_FALL_G:
                if self.ff_start is None:
                    self.ff_start = t
                self.ff_end = t
                if t - self.ff_start >= FREE_FALL_MIN_MS:
                    self.state = _FALLING
            else:
                self.ff_start = None
        elif self.state == _FALLING:
            if g < FREE_FALL_G:
                self.ff_end = t
            elif g > IMPACT_G:
                self.state, self.impact_t, self.still_start = _IMPACT, t, None
            if self.state == _FALLING and t - self.ff_end > IMPACT_WITHIN_MS:
                self.reset_keep_clock(t)
        elif self.state == _IMPACT:
            if t - self.impact_t > STILL_WINDOW_MS:
                self.reset_keep_clock(t)
                return None
            if abs(g - 1.0) <= STILL_G_BAND and self.gyro < STILL_GYRO:
                if self.still_start is None:
                    self.still_start = t
                if t - self.still_start >= STILL_MS:
                    self.cooldown_until = t + COOLDOWN_MS
                    self.reset_keep_clock(t)
                    return "fall"
            else:
                self.still_start = None
        return None

    def reset_keep_clock(self, t: float) -> None:
        gyro = self.gyro
        self.reset()
        self.gyro, self.last_t = gyro, t
