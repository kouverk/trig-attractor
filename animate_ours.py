"""
Render OUR custom loop -- the parallel project.

Identical rendering engine to animate.py (same warp, progress bar, quality
presets, QuickTime-ready output), but it reads our own traced loop from
ours/loop_config.json and writes versioned output into ours/videos/ and
ours/stills/. animate.py is never touched, so "his" and "ours" stay completely
independent.

    python3 trace_ours.py                      # draw the loop first
    python3 animate_ours.py movie              # render it -> ours/videos/ours_<hash>_<quality>.mp4
    python3 animate_ours.py movie --quality draft --frames 240
    python3 animate_ours.py still --t 0.25     # one frame -> ours/stills/
"""

import argparse

import animate          # reuse the engine (sets Agg, defines render funcs)
import loops
import paths

CONFIG = paths.config_path("ours")


def _load_our_loop():
    spec = loops.load_loop(CONFIG)
    if spec is None:
        print(f"** no {CONFIG} found -- run trace_ours.py first. "
              f"Falling back to his loop as a placeholder. **")
        spec = loops.HIS_LOOP
    # Point the engine at our loop + our project folder; make_figure /
    # warp_schedule read animate.LOOP, the output paths read animate.PROJECT.
    animate.LOOP = spec
    animate.PROJECT = "ours"
    return spec


def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("still", help="render a single frame from our loop")
    s.add_argument("--t", type=float, default=0.25)
    s.add_argument("--quality", choices=animate.QUALITY, default="medium")
    s.add_argument("--out", default=None)
    s.set_defaults(func=animate.cmd_still)

    m = sub.add_parser("movie", help="render our loop to mp4")
    m.add_argument("--frames", type=int, default=None,
                   help="total frames; omit to auto-size for a fixed speed "
                        "(video lengthens for a longer loop)")
    m.add_argument("--speed", type=float, default=1.0,
                   help="morph speed when auto-sizing; 1.0 = reference, "
                        "2.0 = twice as fast (half as long)")
    m.add_argument("--fps", type=int, default=30)
    m.add_argument("--quality", choices=animate.QUALITY, default="medium")
    m.add_argument("--warp", type=float, default=1.4,
                   help="speed-warp strength (dwell on rich frames); 0 = constant")
    m.add_argument("--no-warp", action="store_true", help="constant dot speed")
    m.add_argument("--out", default=None)
    m.set_defaults(func=animate.cmd_movie)

    args = p.parse_args()
    spec = _load_our_loop()
    kind = spec.get("type", "ellipse")
    print(f"using OUR loop ({kind}, shape {paths.loop_tag(spec)}) from {CONFIG}")
    args.func(args)


if __name__ == "__main__":
    main()
