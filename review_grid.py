"""
Build the review image for the original loop (original/loop_config.json if
present, else the default ellipse), named after the loop shape ->
original/reviews/original_<hash>.png. Two panels:

  left  - our loop drawn (red) over Conradi's actual football in img/grid.jpg
  right - our loop on the coverage heatmap (bright = rich, dark = thin line)

    python3 review_grid.py
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import loops
import explore
from animate import LOOP as _DEFAULT_LOOP


def main(out="img/GRID_REVIEW.png", loop=None):
    LOOP = loop if loop is not None else _DEFAULT_LOOP
    ts = np.linspace(0, 1, 400)
    la, lb = loops.loop_param(ts, LOOP)

    fig, axs = plt.subplots(1, 2, figsize=(17, 7))

    # LEFT: his grid.jpg with our loop overlaid in his pixel space.
    img = plt.imread("img/grid.jpg")
    axs[0].imshow(img)
    px, py = loops.ab_to_px(la, lb)
    axs[0].plot(px, py, "r-", lw=2)
    axs[0].set_xlim(250, 950)
    axs[0].set_ylim(740, 60)
    axs[0].axis("off")
    axs[0].set_title("HIS grid.jpg  (red = our loop)")

    # RIGHT: coverage heatmap with our loop + travel-direction arrows.
    cov, rng = explore.compute_coverage()
    im = axs[1].imshow(cov, origin="lower", aspect="auto", cmap="magma",
                       extent=[rng["arange"][0], rng["arange"][1],
                               rng["brange"][0], rng["brange"][1]])
    axs[1].plot(la, lb, "c-", lw=2.5, label="our loop")
    a0, b0 = loops.loop_param(0.0, LOOP)
    axs[1].plot([a0], [b0], "co", ms=9)
    for tt in [0.0, 0.12, 0.25, 0.5, 0.75]:
        a1, b1 = loops.loop_param(tt, LOOP)
        a2, b2 = loops.loop_param(tt + 0.01, LOOP)
        axs[1].annotate("", xy=(a2, b2), xytext=(a1, b1),
                        arrowprops=dict(arrowstyle="->", color="cyan", lw=2))
    axs[1].set_xlabel("a")
    axs[1].set_ylabel("b")
    axs[1].legend(loc="lower left", fontsize=9)
    axs[1].set_title("our loop on coverage (bright=rich, dark=thin line)")
    fig.colorbar(im, ax=axs[1], label="coverage")

    fig.tight_layout()
    fig.savefig(out, dpi=95)
    plt.close(fig)
    kind = LOOP.get("type", "ellipse")
    print(f"wrote {out}  (loop type: {kind})")


if __name__ == "__main__":
    import paths
    spec = loops.load_loop(paths.config_path("original")) or _DEFAULT_LOOP
    main(out=paths.review_path("original", paths.loop_tag(spec)), loop=spec)
