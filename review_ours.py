"""
Build the review image for our custom loop (ours/loop_config.json), named after
the loop shape -> ours/reviews/ours_<hash>.png (matches the movie's prefix):

  left  - our custom loop (red) over Conradi's football in img/grid.jpg
  right - our custom loop on the richness heatmap

    python3 review_ours.py
"""

import loops
import paths
import review_grid

CONFIG = paths.config_path("ours")


def main():
    spec = loops.load_loop(CONFIG)
    if spec is None:
        print(f"no {CONFIG} found -- run trace_ours.py first.")
        return
    review_grid.main(out=paths.review_path("ours", paths.loop_tag(spec)), loop=spec)


if __name__ == "__main__":
    main()
