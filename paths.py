"""
Per-project output layout + shape-based versioning, shared by both projects.

There are two parallel projects in this repo that share the same engine:

  "original" -> Conradi's football loop      (original/ folder)
  "ours"     -> our own traced loop          (ours/ folder)

Each project folder holds its (overwritable) loop_config.json plus three output
subfolders: videos/, reviews/, stills/. Outputs are named after a short hash of
the loop SHAPE, so a review image and the movie rendered from the same shape
share a prefix (e.g. ours_a1b2c3d4.png <-> ours_a1b2c3d4.mp4). Trace a new
shape and you get a new prefix -- nothing old is overwritten. The config is the
only thing that gets overwritten when you re-trace.

All paths are resolved against this file's directory, so the scripts work no
matter which directory you run them from.
"""

import hashlib
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

PROJECTS = {
    "original": "original",
    "ours": "ours",
}


def _p(*parts):
    return os.path.join(ROOT, *parts)


def _ensure(directory):
    os.makedirs(directory, exist_ok=True)
    return directory


def config_path(project):
    """Path to a project's (overwritable) loop config."""
    return _p(PROJECTS[project], "loop_config.json")


def loop_tag(spec, n=8):
    """Short, stable hash of a loop shape. Same shape -> same tag, so reviews
    and movies built from the same loop line up by filename."""
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"), default=float)
    return hashlib.sha1(payload.encode()).hexdigest()[:n]


def review_path(project, tag):
    """<project>/reviews/<project>_<tag>.png  (overwrites for the same shape)."""
    d = _ensure(_p(PROJECTS[project], "reviews"))
    return os.path.join(d, f"{project}_{tag}.png")


def video_path(project, tag, suffix=""):
    """<project>/videos/<project>_<tag><suffix>.mp4, auto-bumped (_2, _3, ...)
    if a file is already there so a re-render never clobbers an old movie."""
    d = _ensure(_p(PROJECTS[project], "videos"))
    base = f"{project}_{tag}{suffix}"
    path = os.path.join(d, base + ".mp4")
    i = 2
    while os.path.exists(path):
        path = os.path.join(d, f"{base}_{i}.mp4")
        i += 1
    return path


def still_path(project, tag, t):
    """<project>/stills/<project>_<tag>_t<t>.png."""
    d = _ensure(_p(PROJECTS[project], "stills"))
    return os.path.join(d, f"{project}_{tag}_t{t:.3f}.png")
