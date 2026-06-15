"""
Interactive loop tracer.

Opens a window showing Conradi's parameter-space grid (img/grid.jpg), zoomed in
so his little "football" is big and centred. Click around the outline of the
football; each click drops a point. When you're happy, press ENTER. The traced
shape is converted from pixels to (a, b), lightly smoothed, and saved to
original/loop_config.json -- which animate.py then uses as the loop.

Run it yourself (needs a GUI window):
    python3 trace_loop.py
    python3 trace_loop.py --full       # trace on the whole grid, not zoomed

Controls:
    left click   - add a point
    right click  - remove the last point
    ENTER        - finish (or middle-click)

After saving, run  python3 review_grid.py  to build the review image so you can
check it (-> original/reviews/original_<hash>.png).
"""

import argparse
import os

import numpy as np
import matplotlib

# NOTE: do NOT force a non-interactive backend here -- we need a real window.
import matplotlib.pyplot as plt

import loops
import paths


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", default="img/grid.jpg")
    p.add_argument("--out", default=paths.config_path("original"))
    p.add_argument("--full", action="store_true",
                   help="show the whole grid instead of zooming on the football")
    p.add_argument("--smooth", type=int, default=5,
                   help="smoothing window for the traced outline (1 = none)")
    p.add_argument("--points", type=int, default=120,
                   help="number of resampled points stored in the config")
    args = p.parse_args()

    img = plt.imread(args.image)
    fig, ax = plt.subplots(figsize=(10, 9))
    ax.imshow(img)

    if not args.full:
        # Zoom to the football region (pixels), big and centred.
        ax.set_xlim(285, 440)
        ax.set_ylim(560, 450)        # inverted: image y grows downward
    ax.set_title("Click around the football outline, then press ENTER\n"
                 "(left = add, right = undo)")
    ax.set_xlabel("trace the loop with your mouse")

    print("\n=== loop tracer ===")
    print("Left-click points around the football outline.")
    print("Right-click to undo. Press ENTER (or middle-click) when done.\n")

    # ginput blocks, running the GUI event loop, until ENTER / middle-click.
    clicks = plt.ginput(n=-1, timeout=0, show_clicks=True,
                        mouse_add=1, mouse_pop=3, mouse_stop=2)

    if len(clicks) < 3:
        print(f"Only {len(clicks)} points -- need at least 3. Nothing saved.")
        return

    px = np.array([c[0] for c in clicks])
    py = np.array([c[1] for c in clicks])
    a, b = loops.px_to_ab(px, py)
    pts = np.column_stack([a, b])

    resampled = loops.resample_closed(pts, n=args.points, smooth_win=args.smooth)
    spec = {"type": "points", "points": resampled}
    path = loops.save_loop(spec, args.out)

    ca, cb = resampled[:, 0].mean(), resampled[:, 1].mean()
    print(f"\nTraced {len(clicks)} points -> saved {args.points} smoothed "
          f"points to {path}")
    print(f"loop center ~= (a={ca:.3f}, b={cb:.3f}), "
          f"a-range [{resampled[:,0].min():.3f}, {resampled[:,0].max():.3f}], "
          f"b-range [{resampled[:,1].min():.3f}, {resampled[:,1].max():.3f}]")

    # Draw the traced+smoothed loop back on the image for confirmation.
    rpx, rpy = loops.ab_to_px(resampled[:, 0], resampled[:, 1])
    rpx = np.append(rpx, rpx[0]); rpy = np.append(rpy, rpy[0])
    ax.plot(rpx, rpy, "r-", lw=2)
    ax.plot(px, py, "c.", ms=8)
    ax.set_title(f"saved to {path}  --  close this window")
    preview = os.path.join(paths.ROOT, "original", "reviews", "trace_preview.png")
    os.makedirs(os.path.dirname(preview), exist_ok=True)
    fig.savefig(preview, dpi=95)
    print(f"preview written to {preview}")
    plt.show()


if __name__ == "__main__":
    main()
