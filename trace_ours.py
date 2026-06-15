"""
Custom loop tracer -- draw OUR OWN loop on the richness heatmap.

Opens the coverage map (bright = rich, structured attractor; dark = thin single
line), with Conradi's football overlaid as a dashed guide. Click your own loop
in (a, b) space: borrow parts of his path, then wander out into the bright rich
regions. Press ENTER to finish. The loop is saved to ours/loop_config.json,
which animate_ours.py reads -- completely separate from the "his" project.

Run it yourself (needs a GUI window):
    python3 trace_ours.py

Controls:
    left click   - add a point
    right click  - remove the last point
    ENTER        - finish (or middle-click)

Because the axes ARE the (a, b) plane, your clicks are taken directly as (a, b)
coordinates -- no pixel calibration needed. After saving, build the review image
with:  python3 review_ours.py  (-> ours/reviews/ours_<hash>.png)
"""

import argparse
import os

import numpy as np
import matplotlib.pyplot as plt          # interactive backend on purpose

import loops
import paths


def load_or_build_coverage(cache="img/coverage.npy"):
    """Load the cached richness map, or compute it (slow) if it's missing."""
    if os.path.exists(cache):
        return np.load(cache)
    print("no cached coverage map -- computing it once (~1 min) ...")
    from attractor import iterate_density            # backend-neutral import
    R = loops.COV_RANGE
    A = np.linspace(*R["arange"], R["n"])
    B = np.linspace(*R["brange"], R["n"])
    cov = np.zeros((R["n"], R["n"]))
    for i, b in enumerate(B):
        for j, a in enumerate(A):
            h = iterate_density(a, b, n_points=35_000, n_iter=80,
                                burn_in=12, res=170)
            cov[i, j] = (h > 0).mean()
    np.save(cache, cov)
    return cov


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=paths.config_path("ours"))
    p.add_argument("--smooth", type=int, default=5,
                   help="smoothing window for the traced outline (1 = none)")
    p.add_argument("--points", type=int, default=140,
                   help="number of resampled points stored in the config")
    args = p.parse_args()

    cov = load_or_build_coverage()
    R = loops.COV_RANGE
    extent = [R["arange"][0], R["arange"][1], R["brange"][0], R["brange"][1]]

    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(cov, origin="lower", aspect="auto", cmap="magma",
                   extent=extent)
    fig.colorbar(im, ax=ax, label="richness (bright = rich, dark = thin line)")

    # His football as a dashed guide.
    ts = np.linspace(0, 1, 300)
    ha, hb = loops.loop_param(ts, loops.HIS_LOOP)
    ax.plot(ha, hb, "c--", lw=1.5, label="his loop (guide)")
    ax.legend(loc="upper right")

    ax.set_xlabel("a")
    ax.set_ylabel("b")
    ax.set_title("Click YOUR loop in (a, b). Bright = rich.\n"
                 "left = add, right = undo, ENTER = done")

    print("\n=== custom loop tracer ===")
    print("Click points to draw your loop on the richness map.")
    print("Right-click to undo. ENTER (or middle-click) when done.\n")

    clicks = plt.ginput(n=-1, timeout=0, show_clicks=True,
                        mouse_add=1, mouse_pop=3, mouse_stop=2)

    if len(clicks) < 3:
        print(f"Only {len(clicks)} points -- need at least 3. Nothing saved.")
        return

    pts = np.array(clicks)               # already (a, b)
    resampled = loops.resample_closed(pts, n=args.points, smooth_win=args.smooth)
    spec = {"type": "points", "points": resampled}
    path = loops.save_loop(spec, args.out)

    ca, cb = resampled[:, 0].mean(), resampled[:, 1].mean()
    print(f"\nTraced {len(clicks)} points -> saved {args.points} smoothed "
          f"points to {path}")
    print(f"loop center ~= (a={ca:.3f}, b={cb:.3f}), "
          f"a-range [{resampled[:,0].min():.3f}, {resampled[:,0].max():.3f}], "
          f"b-range [{resampled[:,1].min():.3f}, {resampled[:,1].max():.3f}]")

    closed = np.vstack([resampled, resampled[0]])
    ax.plot(closed[:, 0], closed[:, 1], "lime", lw=2.5)
    ax.plot(pts[:, 0], pts[:, 1], "w.", ms=8)
    ax.set_title(f"saved to {path}  --  close this window")
    preview = os.path.join(paths.ROOT, "ours", "reviews", "trace_preview.png")
    os.makedirs(os.path.dirname(preview), exist_ok=True)
    fig.savefig(preview, dpi=95)
    print(f"preview written to {preview}")
    plt.show()


if __name__ == "__main__":
    main()
