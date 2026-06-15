"""
Fast iteration harness -- preview loops WITHOUT rendering a whole movie.

Two tools:
  coverage_map(...)  -> heatmap of parameter space. Low coverage = thin single
                        line (the boring frames we want to avoid); high coverage
                        = rich filled structure. Overlays a candidate loop so we
                        can see exactly which regimes it crosses.
  contact(spec, ...) -> a grid of frames sampled around a candidate loop, each
                        labelled with (t, a, b), so we can eyeball the morph.

A loop is a tilted ellipse:  spec = dict(center=(a0,b0), major, minor, tilt_deg).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from attractor import render, iterate_density, DOMAIN
from loops import loop_param  # noqa: F401  (re-exported for callers)


PREVIEW_Q = dict(n_points=220_000, n_iter=150, burn_in=20, res=440)


def contact(spec, k=12, q=PREVIEW_Q, out="img/preview_contact.png"):
    """Render k frames around the loop into one contact sheet."""
    cols = 4
    rows = (k + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.2, rows * 3.4))
    for i, ax in enumerate(axes.ravel()):
        if i < k:
            t = i / k
            a, b = loop_param(t, spec)
            ax.imshow(render(a, b, **q), origin="lower", extent=DOMAIN)
            ax.set_title(f"t={t:.2f}  a={a:.3f} b={b:.3f}", fontsize=8)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=80)
    plt.close(fig)
    print("wrote", out)


COV_RANGE = dict(arange=(0.2, 1.1), brange=(1.6, 2.4), n=34)


def compute_coverage(cache="img/coverage.npy", **rng):
    """Coverage grid over (a,b), cached to .npy so loop tests are instant."""
    import os
    rng = {**COV_RANGE, **rng}
    if os.path.exists(cache):
        return np.load(cache), rng
    A = np.linspace(*rng["arange"], rng["n"])
    B = np.linspace(*rng["brange"], rng["n"])
    cov = np.zeros((rng["n"], rng["n"]))
    for i, b in enumerate(B):
        for j, a in enumerate(A):
            h = iterate_density(a, b, n_points=35_000, n_iter=80,
                                burn_in=12, res=170)
            cov[i, j] = (h > 0).mean()
    np.save(cache, cov)
    return cov, rng


def overlay_loops(specs, out="img/coverage.png"):
    """Draw one or more candidate loops on the cached coverage heatmap."""
    cov, rng = compute_coverage()
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cov, origin="lower", aspect="auto", cmap="magma",
                   extent=[rng["arange"][0], rng["arange"][1],
                           rng["brange"][0], rng["brange"][1]])
    fig.colorbar(im, ax=ax, label="coverage (low = thin single line)")
    colors = ["c", "lime", "white", "red"]
    ts = np.linspace(0, 1, 300)
    if isinstance(specs, dict):
        specs = [specs]
    for spec, c in zip(specs, colors):
        a, b = loop_param(ts, spec)
        ax.plot(a, b, "-", color=c, lw=2, label=spec.get("name", ""))
        a0, b0 = loop_param(0.0, spec)
        ax.plot([a0], [b0], "o", color=c, ms=7)
    ax.set_xlabel("a")
    ax.set_ylabel("b")
    ax.set_title("parameter-space coverage")
    if any(s.get("name") for s in specs):
        ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=95)
    plt.close(fig)
    print("wrote", out)


def loop_thin_fraction(spec, k=72, thresh=0.06):
    """Fraction of the loop (by arc) whose coverage is below `thresh` -- i.e.
    the proportion of frames that will look like a thin single line."""
    cov, rng = compute_coverage()
    A0, A1 = rng["arange"]
    B0, B1 = rng["brange"]
    n = rng["n"]
    ts = np.linspace(0, 1, k, endpoint=False)
    a, b = loop_param(ts, spec)
    ja = np.clip(((a - A0) / (A1 - A0) * (n - 1)).astype(int), 0, n - 1)
    ib = np.clip(((b - B0) / (B1 - B0) * (n - 1)).astype(int), 0, n - 1)
    vals = cov[ib, ja]
    return float((vals < thresh).mean()), float(vals.mean())


if __name__ == "__main__":
    spec = dict(center=(0.61, 2.05), major=0.30, minor=0.15, tilt_deg=35,
                name="his-est")
    overlay_loops(spec)
    contact(spec, k=12)
