"""
Loop geometry shared by every module (no matplotlib backend pulled in here).

A loop spec is a dict, JSON-serialisable, one of:
  {"type": "ellipse", "center": [a0,b0], "major": .., "minor": .., "tilt_deg": ..}
  {"type": "points",  "points": [[a,b], [a,b], ...]}   # a closed, ordered path

loop_param(t, spec) maps t in [0,1) to (a, b) along the loop. For "points" loops
the path is parametrised by arc length so the dot moves at a steady geometric
pace around the traced outline.

The (a,b) <-> pixel calibration is for img/grid.jpg (Conradi's parameter-space
inset), used by the tracer to turn mouse clicks into (a,b) values.
"""

import json
import numpy as np

# Calibration of img/grid.jpg: pixel positions of the axis box corners.
# a runs 0..2pi across x_left..x_right; b runs 0..2pi across y_bot..y_top.
GRID_BOX = dict(x_left=285, x_right=910, y_top=95, y_bot=710)
TWO_PI = 2.0 * np.pi

# Conradi's football, measured off his inset -- used as the guide overlay in the
# custom tracer and as the fallback loop.
HIS_LOOP = dict(type="ellipse", center=(0.666, 2.166),
                major=0.30, minor=0.18, tilt_deg=-19)

# (a,b) window the coverage heatmap (img/coverage.npy) was computed over.
COV_RANGE = dict(arange=(0.2, 1.1), brange=(1.6, 2.4), n=34)


def px_to_ab(px, py, box=GRID_BOX):
    a = (np.asarray(px) - box["x_left"]) / (box["x_right"] - box["x_left"]) * TWO_PI
    b = (box["y_bot"] - np.asarray(py)) / (box["y_bot"] - box["y_top"]) * TWO_PI
    return a, b


def ab_to_px(a, b, box=GRID_BOX):
    px = box["x_left"] + np.asarray(a) / TWO_PI * (box["x_right"] - box["x_left"])
    py = box["y_bot"] - np.asarray(b) / TWO_PI * (box["y_bot"] - box["y_top"])
    return px, py


def circular_smooth(arr, win=5):
    """Periodic moving-average smoothing of a 1-D array."""
    if win <= 1:
        return arr
    out = np.zeros_like(arr, dtype=float)
    half = win // 2
    for d in range(-half, half + 1):
        out += np.roll(arr, d)
    return out / (2 * half + 1)


def resample_closed(points, n=120, smooth_win=5):
    """Resample a closed polygon to n points by arc length, lightly smoothed."""
    pts = np.asarray(points, dtype=float)
    closed = np.vstack([pts, pts[0]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    s = np.linspace(0.0, total, n, endpoint=False)
    a = np.interp(s, cum, closed[:, 0])
    b = np.interp(s, cum, closed[:, 1])
    a = circular_smooth(a, smooth_win)
    b = circular_smooth(b, smooth_win)
    return np.column_stack([a, b])


def _ellipse_param(t, spec):
    ang = TWO_PI * np.asarray(t)
    A, B = spec["major"], spec["minor"]
    th = np.radians(spec.get("tilt_deg", 0.0))
    u = A * np.cos(ang)
    v = B * np.sin(ang)
    a = spec["center"][0] + u * np.cos(th) - v * np.sin(th)
    b = spec["center"][1] + u * np.sin(th) + v * np.cos(th)
    return a, b


def _points_param(t, points):
    pts = np.asarray(points, dtype=float)
    closed = np.vstack([pts, pts[0]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    cum /= cum[-1]
    tt = np.asarray(t) % 1.0
    a = np.interp(tt, cum, closed[:, 0])
    b = np.interp(tt, cum, closed[:, 1])
    return a, b


def loop_param(t, spec):
    """t in [0,1) -> (a, b) on the loop (ellipse or traced points)."""
    if spec.get("type") == "points":
        return _points_param(t, spec["points"])
    return _ellipse_param(t, spec)


def loop_length(spec, n=20000):
    """Total arc length of the closed loop in (a, b) units. Used to auto-size
    the frame count so the dot travels at a fixed speed regardless of how big
    or small the traced loop is."""
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    a, b = loop_param(t, spec)
    a = np.append(a, a[0])
    b = np.append(b, b[0])
    return float(np.hypot(np.diff(a), np.diff(b)).sum())


def save_loop(spec, path="loop_config.json"):
    out = dict(spec)
    if "points" in out:
        out["points"] = np.asarray(out["points"]).tolist()
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    return path


def load_loop(path="loop_config.json"):
    """Return the loop spec from `path`, or None if it doesn't exist."""
    import os
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
