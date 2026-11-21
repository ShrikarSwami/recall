"""Bake the squirrel model into a sprite sheet for the lens (and export a .glb).

    python bake_sprites.py            # writes ../assets/squirrel_sheet.png, squirrel_sheet.json, squirrel.glb
"""
import json
import math
import os
import sys
import time

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from squirrel_sdf import export_glb, render, run_pose, sit_pose  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")
os.makedirs(OUT, exist_ok=True)

N = int(os.environ.get("CELL", "160"))
SPAN = 3.9
COLS = 10
R_SH = (0.24, 1.10, 0.16)

frames = []   # (name, image)
KEEP = [x for x in os.environ.get("KEEP", "").split(",") if x]      # bake only these frames (e.g. a big, sharp set for the intro)
OUTNAME = os.environ.get("OUTNAME", "squirrel_sheet")


def add(name, pose, yaw=0.0, emo="warm", talk=False):
    if KEEP and name not in KEEP:
        return
    t0 = time.time()
    frames.append((name, render(pose, yaw, emo=emo, talk=talk, N=N, span=SPAN)))
    print("  %-16s %.1fs" % (name, time.time() - t0), flush=True)


def arms_R(E, W):
    return {"R": (R_SH, E, W)}


# idle at five angles (the lens mirrors the other three)
for yaw in (0, 45, 90, 135, 180):
    add("idle_%d" % yaw, sit_pose(), yaw)

# moods, facing you
for emo in ("warm", "happy", "proud", "curious", "concerned", "calm"):
    add("emo_" + emo, sit_pose(), 0, emo)
add("emo_sleepy", sit_pose(head=(0, -0.10, 0.05), pitch=0.28), 0, "sleepy")
add("emo_alert", sit_pose(arms=arms_R((0.34, 1.12, 0.50), (0.30, 1.42, 0.66))), 0, "alert")
add("emo_warm_talk", sit_pose(), 0, "warm", True)
add("emo_happy_talk", sit_pose(), 0, "happy", True)

# gestures, facing you
for i, dx in enumerate((-0.12, 0.0, 0.12, 0.0)):
    add("wave_%d" % i, sit_pose(arms=arms_R((0.50, 1.22, 0.30), (0.62 + dx, 1.55, 0.28))), 0, "happy", i % 2 == 1)
for i, dy in enumerate((-0.08, 0.0, 0.08, 0.0)):
    arms = {"R": (R_SH, (0.46, 1.30, 0.22), (0.52, 1.66 + dy, 0.16)), "L": (R_SH, (0.46, 1.30, 0.22), (0.52, 1.66 - dy, 0.16))}
    add("cheer_%d" % i, sit_pose(arms=arms), 0, "proud", i % 2 == 1)
add("pointR", sit_pose(arms=arms_R((0.50, 1.10, 0.30), (0.84, 1.08, 0.30))), 0, "warm")

# the end of the Lucia twirl: a small bow
add("bow_0", sit_pose(head=(0, -0.12, 0.06), pitch=0.22), 0, "happy")
add("bow_1", sit_pose(head=(0, -0.26, 0.12), pitch=0.38), 0, "happy")

# running, from five angles x six steps
for yaw in (0, 45, 90, 135, 180):
    for k in range(6):
        add("run_%d_%d" % (yaw, k), run_pose(k * 2 * math.pi / 6), yaw, "warm")

rows = (len(frames) + COLS - 1) // COLS
sheet = Image.new("RGBA", (COLS * N, rows * N), (0, 0, 0, 0))
manifest = {"cell": N, "cols": COLS, "frames": {}}
for i, (name, im) in enumerate(frames):
    c, r = i % COLS, i // COLS
    sheet.paste(im, (c * N, r * N))
    manifest["frames"][name] = [c, r]
sheet.save(os.path.join(OUT, OUTNAME + ".png"), optimize=True)
with open(os.path.join(OUT, OUTNAME + ".json"), "w") as f:
    json.dump(manifest, f)
print("sheet", sheet.size, "frames", len(frames))

if "--no-glb" not in sys.argv:
    t0 = time.time()
    nv, nf = export_glb(os.path.join(OUT, "squirrel.glb"), sit_pose(), res=100)
    print("glb: %d vertices, %d triangles, %.1fs" % (nv, nf, time.time() - t0))
