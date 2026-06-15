"""
Render the trigonometric attractor as a still and/or an animation.

The animation walks the parameters (a, b) once around a small tilted "football"
loop in parameter space -- matching Simone Conradi's inset -- and the attractor
morphs as it goes. The loop is positioned so the top of the football passes
through the spiral-core "heart", and the dot's SPEED is warped by local richness:
it lingers on the structured frames and zips through the thin single-line arc, so
very little screen time is wasted on the boring near-1D states.

Examples:
    python animate.py still                 # one frame -> original/stills/
    python animate.py still --t 0.5         # a point on the loop (warped time)
    python animate.py movie                 # full loop  -> original/videos/
    python animate.py movie --frames 810 --quality high
    python animate.py movie --no-warp       # constant dot speed
"""

import argparse
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attractor import render, iterate_density, DOMAIN, ATTRACTOR_CMAP
from loops import loop_param, load_loop, loop_length
import paths

# Which project this run belongs to ("original" or "ours"). animate_ours.py
# flips this to "ours" before rendering; everything else stays the default.
PROJECT = "original"

# Loop in (a, b) space. If the project's loop_config.json exists (e.g. traced
# with trace_loop.py), use it; otherwise fall back to the ellipse measured off
# Conradi's inset (img/grid.jpg): center (0.666,2.166), tilted -19 deg.
DEFAULT_LOOP = dict(type="ellipse", center=(0.666, 2.166),
                    major=0.30, minor=0.18, tilt_deg=-19)
LOOP = load_loop(paths.config_path("original")) or DEFAULT_LOOP
PARAM_BOX = (0.0, 2.0 * np.pi)

EQUATION = (
    r"$x_{n+1} = \sin(x_n^2 - y_n^2 + a)$" "\n"
    r"$y_{n+1} = \cos(2\,x_n y_n + b)$"
)
SIGNATURE = "after Simone Conradi"

QUALITY = {
    "draft":  dict(n_points=300_000, n_iter=120, burn_in=15, res=600),
    "medium": dict(n_points=700_000, n_iter=200, burn_in=25, res=1000),
    "high":   dict(n_points=1_600_000, n_iter=240, burn_in=30, res=1300),
}

# Fixed morph speed: how many frames to spend per unit of (a, b) arc length.
# Calibrated so the original football (arc ~1.541) -> ~810 frames, i.e. the dot
# moves at the same pace no matter how big or small the traced loop is. When
# --frames isn't given, the movie auto-sizes its length from this. --speed
# scales it (2.0 = twice as fast = half as many frames).
FRAMES_PER_UNIT = 525.0


def auto_frames(loop, speed=1.0, fps=30):
    """Frame count that holds a constant dot speed for a loop of any length."""
    n = max(1, round(loop_length(loop) * FRAMES_PER_UNIT / max(speed, 1e-6)))
    return n


def _fmt(secs):
    secs = int(max(secs, 0))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


class ProgressBar:
    """Tiny dependency-free terminal progress bar with rate + ETA."""

    def __init__(self, total, label="", width=34):
        self.total = total
        self.label = label
        self.width = width
        self.n = 0
        self.start = time.time()
        self.done = False

    def update(self, n=None):
        if self.done:
            return
        self.n = self.n + 1 if n is None else n
        self.n = min(self.n, self.total)
        frac = self.n / self.total if self.total else 1.0
        filled = int(round(self.width * frac))
        bar = "#" * filled + "-" * (self.width - filled)
        elapsed = time.time() - self.start
        rate = self.n / elapsed if elapsed > 0 else 0.0
        eta = (self.total - self.n) / rate if rate > 0 else 0.0
        sys.stdout.write(
            f"\r{self.label} [{bar}] {self.n}/{self.total} "
            f"{frac * 100:5.1f}%  {rate:4.2f}/s  elapsed {_fmt(elapsed)}  "
            f"ETA {_fmt(eta)}   "
        )
        sys.stdout.flush()
        if self.n >= self.total:
            self.done = True
            sys.stdout.write("\n")
            sys.stdout.flush()


def circular_smooth(w, win=11):
    """Periodic moving-average smoothing."""
    out = np.zeros_like(w)
    half = win // 2
    for d in range(-half, half + 1):
        out += np.roll(w, d)
    return out / (2 * half + 1)


def warp_schedule(n_frames, strength=1.4, floor=0.16, samples=260):
    """Frame times in [0,1) spaced so the dot dwells on rich (high-coverage)
    parts of the loop and rushes through thin (low-coverage) parts.

    Returns an array of n_frames warped t-values. With strength=0 this is just
    uniform spacing (constant speed).
    """
    ts = np.linspace(0.0, 1.0, samples, endpoint=False)
    if strength <= 0:
        return np.linspace(0.0, 1.0, n_frames, endpoint=False)

    # Cheap local "richness" = attractor coverage at each sample point.
    w = np.empty(samples)
    bar = ProgressBar(samples, label="speed schedule")
    for i, t in enumerate(ts):
        a, b = loop_param(t, LOOP)
        h = iterate_density(a, b, n_points=15_000, n_iter=60, burn_in=10, res=120)
        w[i] = (h > 0).mean()
        bar.update()
    w = circular_smooth(w / w.max(), win=11)
    w = w ** strength + floor                    # frame density weight

    # Time spent up to each sample = integral of weight (then normalize to 0..1).
    dt = 1.0 / samples
    cum = np.concatenate([[0.0], np.cumsum(w) * dt])
    cum /= cum[-1]
    grid_t = np.concatenate([ts, [1.0]])

    frac = np.linspace(0.0, 1.0, n_frames, endpoint=False)
    return np.interp(frac, cum, grid_t)


def make_figure(quality):
    """Build the figure once; return (fig, updater) where updater(t) draws frame t."""
    bg = ATTRACTOR_CMAP(0.0)
    fig = plt.figure(figsize=(7.5, 7.5), dpi=140)
    fig.patch.set_facecolor(bg)

    # Main attractor axes sit in the lower part, leaving a clean top band for
    # the equation and the parameter-space inset. imshow keeps a square aspect,
    # so the attractor stays centered with margins around it.
    ax = fig.add_axes([0.04, 0.03, 0.92, 0.74])
    ax.set_facecolor(bg)
    ax.axis("off")

    a0, b0 = loop_param(0.0, LOOP)
    img = ax.imshow(render(a0, b0, **quality), origin="lower",
                    extent=DOMAIN, interpolation="bilinear")

    # Equation, top-left; signature, bottom-right (figure coords).
    fig.text(0.05, 0.95, EQUATION, va="top", ha="left",
             fontsize=15, color="#3a3a2e")
    fig.text(0.95, 0.04, SIGNATURE, va="bottom", ha="right",
             fontsize=11, style="italic", color="#5a6a7a")

    # Parameter-space inset, top-right.
    inset = fig.add_axes([0.70, 0.74, 0.22, 0.22])
    inset.set_facecolor("none")
    lo, hi = PARAM_BOX
    inset.set_xlim(lo, hi)
    inset.set_ylim(lo, hi)
    inset.set_xticks([0, hi]); inset.set_xticklabels(["0", r"$2\pi$"], fontsize=8)
    inset.set_yticks([0, hi]); inset.set_yticklabels(["0", r"$2\pi$"], fontsize=8)
    inset.set_xlabel("a", fontsize=10); inset.set_ylabel("b", fontsize=10)
    inset.tick_params(length=2)

    ts = np.linspace(0, 1, 240)
    la, lb = loop_param(ts, LOOP)
    inset.plot(la, lb, color="#2f5fa0", lw=1.0)
    dot, = inset.plot([a0], [b0], "o", color="#b03050", ms=5)

    def update(t):
        a, b = loop_param(t, LOOP)
        img.set_data(render(a, b, **quality))
        dot.set_data([a], [b])
        return img, dot

    return fig, update


def cmd_still(args):
    quality = QUALITY[args.quality]
    fig, update = make_figure(quality)
    update(args.t)
    out = args.out or paths.still_path(PROJECT, paths.loop_tag(LOOP), args.t)
    fig.savefig(out, dpi=140, facecolor=fig.get_facecolor())
    print(f"wrote {out}  (a, b = {loop_param(args.t, LOOP)})")


def cmd_movie(args):
    from matplotlib.animation import FuncAnimation, FFMpegWriter
    quality = QUALITY[args.quality]

    # If --frames wasn't given, auto-size the video so the dot travels at a
    # fixed speed -- a longer loop simply makes a longer video.
    if args.frames is None:
        args.frames = auto_frames(LOOP, speed=args.speed, fps=args.fps)
        L = loop_length(LOOP)
        print(f"auto length: loop arc {L:.2f} (a,b units), speed {args.speed}x "
              f"-> {args.frames} frames @ {args.fps}fps = "
              f"{args.frames / args.fps:.1f}s")

    strength = 0.0 if args.no_warp else args.warp
    print(f"building speed schedule (warp strength={strength}) ...")
    times = warp_schedule(args.frames, strength=strength)

    fig, update = make_figure(quality)

    print(f"rendering {args.frames} frames at quality '{args.quality}' ...")
    bar = ProgressBar(args.frames, label="rendering    ")

    def frame(i):
        result = update(times[i])
        bar.update()
        return result

    anim = FuncAnimation(fig, frame, frames=args.frames, blit=False)
    # Name the movie after the loop shape + quality so it lines up with the
    # matching review image and never clobbers an earlier render.
    out = args.out or paths.video_path(
        PROJECT, paths.loop_tag(LOOP), suffix=f"_{args.quality}")
    # yuv420p + faststart -> opens directly in QuickTime, no transcode needed.
    writer = FFMpegWriter(fps=args.fps, bitrate=6000,
                          extra_args=["-pix_fmt", "yuv420p",
                                      "-movflags", "+faststart"])
    anim.save(out, writer=writer, dpi=140)
    dur = args.frames / args.fps
    print(f"wrote {out}  ({args.frames} frames @ {args.fps} fps = {dur:.1f}s)")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("still", help="render a single frame")
    s.add_argument("--t", type=float, default=0.25, help="position on the loop, 0..1")
    s.add_argument("--quality", choices=QUALITY, default="medium")
    s.add_argument("--out")
    s.set_defaults(func=cmd_still)

    m = sub.add_parser("movie", help="render the full loop to mp4")
    m.add_argument("--frames", type=int, default=None,
                   help="total frames; omit to auto-size for a fixed speed "
                        "(video lengthens for a longer loop)")
    m.add_argument("--speed", type=float, default=1.0,
                   help="morph speed when auto-sizing; 1.0 = reference, "
                        "2.0 = twice as fast (half as long)")
    m.add_argument("--fps", type=int, default=30)
    m.add_argument("--quality", choices=QUALITY, default="medium")
    m.add_argument("--warp", type=float, default=1.4,
                   help="speed-warp strength (dwell on rich frames); 0 = constant")
    m.add_argument("--no-warp", action="store_true", help="constant dot speed")
    m.add_argument("--out")
    m.set_defaults(func=cmd_movie)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
