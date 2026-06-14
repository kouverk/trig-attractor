"""
Render the trigonometric attractor as a still and/or an animation.

The animation walks the parameters (a, b) once around a small ellipse in
parameter space -- the same idea as the little loop drawn in the inset of the
original image -- and the attractor morphs as it goes.

Examples:
    python animate.py still                 # one frame -> still.png
    python animate.py movie                 # full loop  -> attractor.mp4
    python animate.py movie --frames 240 --quality high
"""

import argparse

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attractor import render, DOMAIN, ATTRACTOR_CMAP

# Center and radii of the (a, b) loop, plus the parameter-space box (0 .. 2pi).
# Small ellipse in (a, b) space, tuned to sweep across the dense-blob region
# (a~0.46), through the thin near-1D heart curves (a~0.7), and into the folded
# sheets / symmetric-fractal cores (a~0.9) -- the full morph the original shows.
LOOP_CENTER = (0.68, 1.85)
LOOP_RADII = (0.23, 0.22)
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


def loop_param(t):
    """t in [0, 1) -> (a, b) on the ellipse."""
    ang = 2.0 * np.pi * t
    a = LOOP_CENTER[0] + LOOP_RADII[0] * np.cos(ang)
    b = LOOP_CENTER[1] + LOOP_RADII[1] * np.sin(ang)
    return a, b


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

    a0, b0 = loop_param(0.0)
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

    ts = np.linspace(0, 1, 200)
    pts = np.array([loop_param(t) for t in ts])
    inset.plot(pts[:, 0], pts[:, 1], color="#2f5fa0", lw=1.0)
    dot, = inset.plot([a0], [b0], "o", color="#b03050", ms=5)

    def update(t):
        a, b = loop_param(t)
        img.set_data(render(a, b, **quality))
        dot.set_data([a], [b])
        return img, dot

    return fig, update


def cmd_still(args):
    quality = QUALITY[args.quality]
    fig, update = make_figure(quality)
    update(args.t)
    out = args.out or "still.png"
    fig.savefig(out, dpi=140, facecolor=fig.get_facecolor())
    print(f"wrote {out}  (a, b = {loop_param(args.t)})")


def cmd_movie(args):
    from matplotlib.animation import FuncAnimation, FFMpegWriter
    quality = QUALITY[args.quality]
    fig, update = make_figure(quality)
    ts = np.linspace(0, 1, args.frames, endpoint=False)

    def frame(i):
        print(f"\rframe {i + 1}/{args.frames}", end="", flush=True)
        return update(ts[i])

    anim = FuncAnimation(fig, frame, frames=args.frames, blit=False)
    out = args.out or "attractor.mp4"
    writer = FFMpegWriter(fps=args.fps, bitrate=6000)
    anim.save(out, writer=writer, dpi=140)
    print(f"\nwrote {out}  ({args.frames} frames @ {args.fps} fps)")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = dict()
    s = sub.add_parser("still", help="render a single frame")
    s.add_argument("--t", type=float, default=0.0, help="position on the loop, 0..1")
    s.add_argument("--quality", choices=QUALITY, default="medium")
    s.add_argument("--out")
    s.set_defaults(func=cmd_still)

    m = sub.add_parser("movie", help="render the full loop to mp4")
    m.add_argument("--frames", type=int, default=360)
    m.add_argument("--fps", type=int, default=30)
    m.add_argument("--quality", choices=QUALITY, default="medium")
    m.add_argument("--out")
    m.set_defaults(func=cmd_movie)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
