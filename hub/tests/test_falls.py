"""Fall detector tests on synthetic 50 Hz IMU data (fixed timestamps, no randomness)."""
from lucia import gestures
from lucia.falls import ACCEL, FallDetector, G, GYRO

DT = 20  # ms, 50 Hz


def accel(t, g):
    return [ACCEL, t, 0.0, 0.0, g * G]


def gyro(t, rad=0.02):
    return [GYRO, t, rad, 0.0, 0.0]


def stream(segments, t0=10_000):
    """segments: (seconds, accel_g or fn(i)->g, gyro_rad). Returns rows (accel + gyro per tick)."""
    rows, t = [], t0
    for secs, g, w in segments:
        for i in range(round(secs * 1000 / DT)):
            gv = g(i) if callable(g) else g
            rows += [gyro(t, w), accel(t, gv)]
            t += DT
    return rows


def run(rows, worn=True):
    det = FallDetector()
    return [e for r in rows if (e := det.feed(r, worn=worn))], det


def fall_rows(t0=10_000, lead=1.0):
    return stream([(lead, 1.0, 0.02), (0.3, 0.1, 0.3), (0.06, 3.5, 2.0),
                   (0.2, lambda i: 1.4 if i % 2 else 0.7, 1.5), (3.0, 1.0, 0.05)], t0)


def test_real_fall():
    events, _ = run(fall_rows())
    assert events == ["fall"]


def test_standing_still():
    assert run(stream([(30, 1.0, 0.02)]))[0] == []


def test_walking():
    walk = lambda i: 1.0 + 0.35 * (1 if (i // 12) % 2 else -1) * ((i % 12) / 12)
    assert run(stream([(30, walk, 0.8)]))[0] == []


def test_sitting_down_hard_has_no_free_fall():
    rows = stream([(1, 1.0, 0.02), (0.1, 0.8, 0.3), (0.06, 3.5, 1.0), (4, 1.0, 0.05)])
    assert run(rows)[0] == []


def test_nod_and_shake_gyro_only():
    for kind in ("nod", "shake"):
        rows = []
        for r in gestures.synth(kind, seconds=3, rate=50, t0_ms=10_000):
            rows += [r, accel(r[1], 1.0)]
        assert run(rows)[0] == []


def test_dropped_while_not_worn():
    assert run(fall_rows(), worn=False)[0] == []


def test_not_worn_resets_a_fall_in_progress():
    det = FallDetector()
    rows = fall_rows()
    cut = len(rows) // 2
    got = [det.feed(r) for r in rows[:cut]] + [det.feed(r, worn=False) for r in rows[cut:cut + 4]]
    got += [det.feed(r) for r in rows[cut + 4:]]
    assert "fall" not in got


def test_short_free_fall_is_ignored():
    rows = stream([(1, 1.0, 0.02), (0.04, 0.1, 0.3), (0.06, 3.5, 2.0), (4, 1.0, 0.05)])
    assert run(rows)[0] == []


def test_still_enough_but_no_stillness_after_impact():
    rows = stream([(1, 1.0, 0.02), (0.3, 0.1, 0.3), (0.06, 3.5, 2.0), (4, 1.0, 3.0)])
    assert run(rows)[0] == []


def test_two_falls_inside_cooldown_fire_once():
    first = fall_rows(t0=10_000)
    second = fall_rows(t0=first[-1][1] + DT)       # starts seconds later, well inside 60 s
    assert run(first + second)[0] == ["fall"]


def test_fall_after_cooldown_fires_again():
    first = fall_rows(t0=10_000)
    second = fall_rows(t0=first[-1][1] + 61_000)
    assert run(first + stream([(61, 1.0, 0.02)], t0=first[-1][1] + DT) + second)[0] == ["fall", "fall"]
