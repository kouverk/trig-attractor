# Trigonometric attractor

A recreation of the Simone Conradi animation:

```
x_{n+1} = sin(x_n^2 - y_n^2 + a)
y_{n+1} = cos(2 x_n y_n + b)
```

Since `(x^2 - y^2, 2xy)` are the real/imaginary parts of `z^2` (with `z = x + iy`),
this is really `z -> ( sin(Re z^2 + a), cos(Im z^2 + b) )`.

## How it works

Every starting point is pulled onto the same attractor, so each frame scatters a
large cloud of random initial points, iterates the map, discards a short burn-in,
and accumulates every visited position into a 2D histogram. That density is
log-scaled, gamma-lifted, and run through a custom pale-yellow -> green -> teal ->
navy colormap.

The animation walks the parameters `(a, b)` once around a small ellipse in
parameter space — the little loop drawn in the top-right inset — and the attractor
morphs as it goes.

## Usage

```bash
python3 animate.py still                          # one frame -> still.png
python3 animate.py still --t 0.25 --quality high  # pick a point on the loop
python3 animate.py movie                          # full loop -> attractor.mp4
python3 animate.py movie --frames 240 --fps 30 --quality high
```

Quality presets (`draft` / `medium` / `high`) trade render time for point count
and resolution. The `(a, b)` loop lives near `a ≈ 0.55`, `b ∈ [1.0, 2.0]`, a
region where the attractor stays rich and structured — tune `LOOP_CENTER` /
`LOOP_RADII` at the top of `animate.py` to explore elsewhere.

## Files

- `attractor.py` — the map, density accumulation, colormap, rendering
- `animate.py` — figure layout (equation + inset + signature) and the still/movie CLI

Requires `numpy`, `matplotlib`, and `ffmpeg` (for the movie).
