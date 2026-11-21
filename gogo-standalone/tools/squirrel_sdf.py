"""A squirrel modelled as a signed-distance field (smooth blends of capsules and ellipsoids).

From that one model this file can
  * render flat "toon" sprites from any angle and pose (used for the glasses lens), and
  * export a real 3D mesh as a .glb file.

Front of the squirrel = +z, up = +y, right-of-screen (when it faces you) = +x. Units are roughly metres of a
2.3-tall squirrel. Run with:  python squirrel_sdf.py   (writes a preview contact sheet)
"""
import math
import numpy as np
from PIL import Image

# ------------------------------------------------------------------ palettes (indices below)
NAMES = ["fur", "furD", "tail", "tailD", "cream", "creamD", "dark", "inner", "eye", "hi", "nose", "out"]
IDX = {n: i for i, n in enumerate(NAMES)}
PALETTE = {
    # brighter than a screen palette on purpose: a waveguide only has brightness, so mid-greens look dim in a lit room
    "green": [(46, 214, 104), (22, 150, 70), (96, 242, 146), (44, 190, 96), (226, 255, 238), (170, 225, 192),
              (12, 78, 34), (170, 250, 200), (4, 24, 10), (240, 255, 245), (4, 24, 10), (0, 255, 110)],
    "natural": [(196, 86, 44), (141, 58, 31), (205, 96, 48), (150, 64, 34), (245, 222, 184), (214, 188, 150),
                (74, 32, 18), (240, 170, 150), (27, 14, 9), (255, 255, 255), (50, 22, 14), (90, 36, 20)],
}
SHADE = {"fur": "furD", "tail": "tailD", "cream": "creamD"}


# ------------------------------------------------------------------ signed distance helpers
def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def sd_ell(p, c, r):
    q = (p - c) / r
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / r, axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def sd_cone(p, a, b, r1, r2):
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = pa @ ba
    z = y - l2
    x2 = np.sum((pa * l2 - ba[None, :] * y[:, None]) ** 2, axis=1)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    return np.where(np.sign(z) * a2 * z2 > k, np.sqrt(x2 + z2) * il2 - r2,
                    np.where(np.sign(y) * a2 * y2 < k, np.sqrt(x2 + y2) * il2 - r1,
                             (np.sqrt(x2 * a2 * il2) + y * rr) * il2 - r1))


def A(*v):
    return np.array(v, dtype=float)


def cone(a, b, r1, r2, g, k=0.1):
    return {"t": "cone", "a": A(*a), "b": A(*b), "r1": r1, "r2": r2, "g": g, "k": k}


def ell(c, r, g, k=0.1):
    return {"t": "ell", "c": A(*c), "r": A(*r), "g": g, "k": k}


def prim_dist(p, pr):
    if pr["t"] == "cone":
        return sd_cone(p, pr["a"], pr["b"], pr["r1"], pr["r2"])
    return sd_ell(p, pr["c"], pr["r"])


def scene_dist(p, prims):
    d = np.full(len(p), 1e9)
    for pr in prims:
        d = smin(d, prim_dist(p, pr), pr["k"])
    return d


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# ------------------------------------------------------------------ poses
def arm_prims(side, S, E, W, g):
    s = (side * S[0], S[1], S[2]); e = (side * E[0], E[1], E[2]); w = (side * W[0], W[1], W[2])
    d = A(*w) - A(*e); d = d / np.linalg.norm(d)
    tip = A(*w) + d * 0.05
    return [cone(s, e, 0.12, 0.085, g, 0.08), cone(e, w, 0.085, 0.06, g, 0.06),
            ell(tip, (0.07, 0.065, 0.085), "paw", 0.03)]


def tail_prims(pts, rads):
    out = []
    for i in range(len(pts) - 1):
        out.append(cone(pts[i], pts[i + 1], rads[i], rads[i + 1], "tail", 0.1))
    return out


def sit_pose(arms=None, head=(0, 0, 0), pitch=0.0):
    """Sitting upright. arms = {'L': (S,E,W), 'R': (S,E,W)} with x given for the +x side."""
    arms = arms or {}
    rest = ((0.24, 1.10, 0.16), (0.32, 0.86, 0.30), (0.13, 0.86, 0.56))
    P = [cone((0, .40, -.16), (0, .78, -.02), .46, .42, "body", .14),
         cone((0, .78, -.02), (0, 1.12, .12), .42, .32, "body", .14),
         cone((0, 1.12, .12), (0, 1.40, .24), .32, .25, "body", .12)]
    hc = A(0, 1.62, .34) + A(*head)
    P += [ell(hc, (.40, .35, .39), "head", .12),
          cone(hc + A(0, -.03, .14), hc + A(0, -.10, .36), .21, .10, "snout", .10),
          ell(hc + A(0, -.10, .40), (.05, .04, .045), "nose", .02)]
    for s in (-1, 1):
        P += [ell(hc + A(s * .22, -.08, .10), (.15, .13, .17), "head", .10)]            # cheeks
        base = hc + A(s * .20, .22, -.05); tip = hc + A(s * .29, .54, -.10)
        P += [cone(base, tip, .13, .03, "ear", .05), cone(tip, tip + A(s * .02, .11, 0), .02, .005, "ear", .01)]
        P += [ell((s * .36, .42, -.10), (.26, .33, .38), "leg" + ("R" if s > 0 else "L"), .12),
              cone((s * .36, .12, .12), (s * .36, .075, .60), .095, .06, "foot", .06)]
        key = "R" if s > 0 else "L"
        S_, E_, W_ = arms.get(key, rest)
        P += arm_prims(s, S_, E_, W_, "arm" + key)
    P += tail_prims([(0, .46, -.42), (0, .50, -.78), (.10, .72, -1.00), (.08, 1.00, -.95), (-.02, 1.18, -.72), (-.12, 1.20, -.50)],
                    [.15, .20, .25, .25, .18, .06])
    cream = [(A(0, .92, .36), (.17, .50, .20)), (A(0, 1.40, .46), (.15, .22, .20))]
    return {"prims": P, "hc": hc, "pitch": pitch, "cream": cream, "ears": [(hc + A(s * .245, .38, -.075), s) for s in (-1, 1)],
            "kind": "sit", "cz": -0.1}


def run_pose(phase, bob=True):
    """Side-view gallop. phase in radians."""
    uf = (1 + math.sin(phase)) / 2
    uh = (1 + math.sin(phase - 1.7)) / 2
    dy = (abs(math.sin(phase)) * 0.06) if bob else 0.0
    P = [cone((0, .92 + dy, -.58), (0, .96 + dy, -.20), .36, .34, "body", .14),
         cone((0, .96 + dy, -.20), (0, 1.00 + dy, .28), .34, .30, "body", .14),
         cone((0, 1.00 + dy, .28), (0, 1.06 + dy, .60), .30, .24, "body", .12)]
    hc = A(0, 1.12 + dy, .84)
    P += [ell(hc, (.32, .29, .33), "head", .12),
          cone(hc + A(0, -.03, .12), hc + A(0, -.10, .36), .19, .09, "snout", .10),
          ell(hc + A(0, -.10, .40), (.045, .037, .04), "nose", .02)]
    for s in (-1, 1):
        key = "R" if s > 0 else "L"
        P += [ell(hc + A(s * .17, -.06, .08), (.12, .11, .14), "head", .10)]
        base = hc + A(s * .16, .19, -.08); tip = hc + A(s * .23, .46, -.13)
        P += [cone(base, tip, .11, .025, "ear", .05), cone(tip, tip + A(s * .02, .10, 0), .017, .005, "ear", .01)]
        hip = (s * .24, .84 + dy, -.44)
        knee = lerp((s * .25, .52, -.86), (s * .25, .50, -.25), uh)
        foot = lerp((s * .24, .22, -1.12), (s * .24, .17, .10), uh)
        P += [ell(hip, (.2, .26, .3), "leg" + key, .12), cone(hip, knee, .15, .10, "leg" + key, .08),
              cone(knee, foot, .10, .065, "leg" + key, .06), cone(foot, (foot[0], foot[1] - .02, foot[2] + .28), .07, .05, "foot", .05)]
        sh = (s * .20, .92 + dy, .38)
        el = lerp((s * .22, .76, .66), (s * .22, .66, .28), uf)
        wr = lerp((s * .20, .64, .98), (s * .20, .46, .40), uf)
        P += arm_prims(s, (abs(sh[0]), sh[1], sh[2]), (abs(el[0]), el[1], el[2]), (abs(wr[0]), wr[1], wr[2]), "arm" + key)
    w = math.sin(phase * 0.5) * 0.07
    P += tail_prims([(0, .98 + dy, -.80), (0, 1.04 + dy, -1.05), (w, 1.20 + dy, -1.30), (-w, 1.32 + dy, -1.50), (0, 1.34 + dy, -1.66)],
                    [.17, .23, .25, .19, .05])
    cream = [(A(0, .64 + dy, 0.0), (.22, .12, .75)), (A(0, .93 + dy, .74), (.14, .14, .25))]
    return {"prims": P, "hc": hc, "pitch": 0.0, "cream": cream, "ears": [(hc + A(s * .195, .32, -.105), s) for s in (-1, 1)],
            "kind": "run", "cz": -0.35}


# ------------------------------------------------------------------ face (tested in head-local coordinates)
def head_local(p, hc, pitch):
    q = p - hc
    c, s = math.cos(pitch), math.sin(pitch)
    return np.stack([q[:, 0], q[:, 1] * c + q[:, 2] * s, -q[:, 1] * s + q[:, 2] * c], axis=1)


def in_ell(q, c, r):
    return np.sum(((q - A(*c)) / A(*r)) ** 2, axis=1) < 1.0


def in_arc(q, c, R, t, upper, zr=0.06):
    d = q - A(*c)
    rr = np.sqrt(d[:, 0] ** 2 + d[:, 1] ** 2)
    ok = (np.abs(rr - R) < t) & (np.abs(d[:, 2]) < zr)
    return ok & ((d[:, 1] > 0) if upper else (d[:, 1] < 0))


def in_bar(q, c, half, tilt, t):
    d = q - A(*c)
    ca, sa = math.cos(tilt), math.sin(tilt)
    x = d[:, 0] * ca + d[:, 1] * sa
    y = -d[:, 0] * sa + d[:, 1] * ca
    return (np.abs(x) < half) & (np.abs(y) < t) & (np.abs(d[:, 2]) < 0.07)


EMOS = {
    "warm": ("open", None, "smile"), "happy": ("happy", None, "smile"), "proud": ("happy", "up", "open"),
    "curious": ("open", "up", "smile"), "concerned": ("open", "worry", "frown"), "sleepy": ("closed", None, "smile"),
    "calm": ("happy", None, "smile"), "alert": ("wide", "up", "o"),
}


def face_masks(q, emo, talk, kind):
    """Return dict of boolean masks (eye, hi, nose-ish extras) for points q in head-local space."""
    eye, brow, mouth = EMOS.get(emo, EMOS["warm"])
    if talk and mouth in ("smile", "open"):
        mouth = "open"
    m_eye = np.zeros(len(q), bool); m_hi = np.zeros(len(q), bool)
    ex, ey, ez = (0.165, 0.06, 0.30) if kind == "sit" else (0.15, 0.05, 0.27)
    for s in (-1, 1):
        c = (s * ex, ey, ez)
        if eye == "open":
            m_eye |= in_ell(q, c, (.062, .078, .06)); m_hi |= in_ell(q, (s * ex + .02, ey + .03, ez + .02), (.024, .026, .05))
        elif eye == "wide":
            m_eye |= in_ell(q, c, (.078, .098, .07)); m_hi |= in_ell(q, (s * ex + .025, ey + .04, ez + .02), (.03, .03, .06))
        elif eye == "happy":
            m_eye |= in_arc(q, c, .065, .017, True)
        elif eye == "closed":
            m_eye |= in_arc(q, (c[0], c[1] + .03, c[2]), .065, .017, False)
        if brow == "up":
            m_eye |= in_arc(q, (s * ex, ey + .09, ez - .02), .07, .013, True, .08)
        elif brow == "worry":
            m_eye |= in_bar(q, (s * ex, ey + .16, ez - .03), .075, -s * 0.38, .014)
    my = -0.20 if kind == "sit" else -0.17
    mz = 0.40 if kind == "sit" else 0.37
    if mouth == "smile":
        m_eye |= in_arc(q, (0, my + .035, mz), .05, .012, False, .09)
    elif mouth == "open":
        m_eye |= in_ell(q, (0, my, mz), (.045, .05, .06))
    elif mouth == "frown":
        m_eye |= in_arc(q, (0, my - .01, mz), .045, .012, True, .09)
    elif mouth == "o":
        m_eye |= in_ell(q, (0, my, mz), (.03, .04, .05))
    return m_eye, m_hi


# ------------------------------------------------------------------ rendering
def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


GROUPS_FUR = {"body", "head", "snout", "ear", "armL", "armR", "legL", "legR"}


def base_colors(p, prims, yaw):
    """Colour index per point from the nearest primitive group (far-side limbs are darker)."""
    names = [pr["g"] for pr in prims]
    D = np.stack([prim_dist(p, pr) for pr in prims], axis=1)
    near = np.argmin(D, axis=1)
    gid = np.array([names[i] for i in near])
    out = np.full(len(p), IDX["fur"], dtype=np.int32)
    s = math.sin(yaw)
    far = None
    if s > 0.35:
        far = {"armR", "legR"}
    elif s < -0.35:
        far = {"armL", "legL"}
    out[gid == "tail"] = IDX["tail"]
    for g in ("paw", "foot"):
        out[gid == g] = IDX["dark"]
    out[gid == "nose"] = IDX["nose"]
    if far:
        for g in far:
            out[gid == g] = IDX["furD"]
    return out


def render(pose, yaw_deg=0.0, emo="warm", talk=False, style="green", N=128, ss=2, span=3.5, cy=1.12, elev_deg=10.0,
           outline=True, light=(-0.45, 0.65, 0.62)):
    prims = pose["prims"]
    n = N * ss
    yaw = math.radians(yaw_deg)
    cxw = pose.get("cz", 0.0) * math.sin(yaw)                  # keep the whole animal centred in the cell
    xs = ((np.arange(n) + 0.5) / n - 0.5) * span + cxw
    ys = cy - ((np.arange(n) + 0.5) / n - 0.5) * span
    X, Y = np.meshgrid(xs, ys)
    X = X.ravel(); Y = Y.ravel()
    M = rot_y(-yaw) @ rot_x(-math.radians(elev_deg))          # world -> model
    live = ((X - cxw) ** 2 + (Y - 1.1) ** 2) < (2.1 ** 2)
    idx = np.nonzero(live)[0]
    t = np.zeros(len(idx))
    hit = np.zeros(len(X), bool)
    zhit = np.full(len(X), -9.0)
    z0 = 3.2
    for _ in range(70):
        if len(idx) == 0:
            break
        pw = np.stack([X[idx], Y[idx], z0 - t], axis=1)
        pm = pw @ M.T
        d = scene_dist(pm, prims)
        done = d < 0.004
        if done.any():
            hit[idx[done]] = True
            zhit[idx[done]] = (z0 - t)[done]
        keep = (~done) & (t < 6.4)
        t = (t + np.maximum(d, 0.004) * 0.92)[keep]
        idx = idx[keep]
    H = np.nonzero(hit)[0]
    img = np.zeros((n * n, 4), np.uint8)
    pal = np.array(PALETTE[style], np.uint8)
    if len(H):
        pw = np.stack([X[H], Y[H], zhit[H]], axis=1)
        pm = pw @ M.T
        e = 0.006
        g = np.zeros_like(pm)
        for k in range(3):
            o = np.zeros(3); o[k] = e
            g[:, k] = scene_dist(pm + o, prims) - scene_dist(pm - o, prims)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        nw = g @ M
        L = np.array(light, float); L /= np.linalg.norm(L)
        ndl = nw @ L
        col = base_colors(pm, prims, yaw)
        # cream patches
        for c, r in pose["cream"]:
            col[in_ell(pm, c, r)] = IDX["cream"]
        for ec, s in pose["ears"]:
            c2 = ec + A(0, 0, 0.055)
            mask = np.sum(((pm - c2) / A(.065, .17, .05)) ** 2, axis=1) < 1.0
            col[mask & (col == IDX["fur"])] = IDX["inner"]
        # face
        q = head_local(pm, pose["hc"], pose["pitch"])
        eye_m, hi_m = face_masks(q, emo, talk, pose["kind"])
        # shade
        for nm, sh in SHADE.items():
            sel = (col == IDX[nm]) & (ndl < 0.02)
            col[sel] = IDX[sh]
        col[eye_m] = IDX["eye"]
        col[hi_m] = IDX["hi"]
        rgb = pal[col]
        img[H, :3] = rgb
        img[H, 3] = 255
    img = img.reshape(n, n, 4)
    if outline:
        a = img[:, :, 3] > 0
        zz = zhit.reshape(n, n)
        edge = np.zeros_like(a)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(np.roll(a, dy, 0), dx, 1)
            zs = np.roll(np.roll(zz, dy, 0), dx, 1)
            edge |= a & (~sh)
            edge |= a & sh & (np.abs(zz - zs) > 0.16)
        thick = np.zeros_like(edge)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                thick |= np.roll(np.roll(edge, dy, 0), dx, 1)
        thick &= a | np.roll(a, 1, 0) | np.roll(a, -1, 0) | np.roll(a, 1, 1) | np.roll(a, -1, 1)
        oc = np.array(PALETTE[style][IDX["out"]], np.uint8)
        img[thick, :3] = oc
        img[thick, 3] = 255
    # downsample (premultiplied)
    f = img.astype(np.float32)
    al = f[:, :, 3:4] / 255.0
    pm_ = np.concatenate([f[:, :, :3] * al, al], axis=2)
    pm_ = pm_.reshape(N, ss, N, ss, 4).mean(axis=(1, 3))
    a2 = pm_[:, :, 3:4]
    rgb2 = np.where(a2 > 1e-4, pm_[:, :, :3] / np.maximum(a2, 1e-4), 0)
    out = np.concatenate([rgb2, a2 * 255.0], axis=2)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")


# ------------------------------------------------------------------ GLB export
def export_glb(path, pose=None, res=110, style="natural"):
    import trimesh
    from skimage import measure
    pose = pose or sit_pose()
    lo = np.array([-1.0, -0.1, -1.4]); hi = np.array([1.0, 2.5, 1.0])
    xs = np.linspace(lo[0], hi[0], res); ys = np.linspace(lo[1], hi[1], int(res * 1.3)); zs = np.linspace(lo[2], hi[2], int(res * 1.2))
    G = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1)
    flat = G.reshape(-1, 3)
    vol = np.concatenate([scene_dist(flat[i:i + 200000], pose["prims"]) for i in range(0, len(flat), 200000)]).reshape(G.shape[:3])
    sp = ((hi - lo) / (np.array(vol.shape) - 1)).tolist()
    v, f, nrm, _ = measure.marching_cubes(vol, 0.0, spacing=sp)
    v = v + lo
    col = base_colors(v, pose["prims"], 0.0)
    for c, r in pose["cream"]:
        col[in_ell(v, c, r)] = IDX["cream"]
    for ec, s in pose["ears"]:
        mask = np.sum(((v - (ec + A(0, 0, .055))) / A(.065, .17, .05)) ** 2, axis=1) < 1.0
        col[mask & (col == IDX["fur"])] = IDX["inner"]
    q = head_local(v, pose["hc"], pose["pitch"])
    eye_m, hi_m = face_masks(q, "warm", False, pose["kind"])
    col[eye_m] = IDX["eye"]; col[hi_m] = IDX["hi"]
    rgba = np.concatenate([np.array(PALETTE[style], np.uint8)[col], np.full((len(v), 1), 255, np.uint8)], axis=1)
    mesh = trimesh.Trimesh(vertices=v, faces=f, vertex_normals=-nrm if False else nrm, vertex_colors=rgba, process=False)
    mesh.export(path)
    return len(v), len(f)


if __name__ == "__main__":
    import sys, time
    t0 = time.time()
    cells = []
    for yaw in (0, 45, 90, 180):
        cells.append(render(sit_pose(), yaw))
    for ph in (0.0, 1.6, 3.2, 4.8):
        cells.append(render(run_pose(ph), 90))
    N = cells[0].size[0]
    sheet = Image.new("RGBA", (N * 4, N * 2), (5, 8, 5, 255))
    for i, c in enumerate(cells):
        sheet.alpha_composite(c, ((i % 4) * N, (i // 4) * N))
    out = sys.argv[1] if len(sys.argv) > 1 else "preview.png"
    sheet.save(out)
    print("saved", out, round(time.time() - t0, 1), "s")
