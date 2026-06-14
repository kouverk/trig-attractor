"""
Trigonometric attractor (after Simone Conradi).

    x_{n+1} = sin(x_n^2 - y_n^2 + a)
    y_{n+1} = cos(2 * x_n * y_n + b)

Note that (x^2 - y^2, 2xy) are the real/imag parts of z^2 with z = x + iy, so
the map is essentially z -> ( sin(Re z^2 + a), cos(Im z^2 + b) ).

Every initial point is sucked onto the same attractor, so we scatter a big cloud
of starting points, throw away a short burn-in, then accumulate every visited
position into a 2D histogram. That density, log-scaled and run through a custom
colormap, is one frame. Walking (a, b) around a small loop in parameter space
morphs the attractor -- that's the animation.
"""

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

# Outputs are sin/cos, so the attractor always lives in [-1, 1] x [-1, 1].
DOMAIN = (-1.0, 1.0, -1.0, 1.0)

# Pale-yellow paper -> green -> teal -> blue -> dark navy, matching the original.
ATTRACTOR_CMAP = LinearSegmentedColormap.from_list(
    "conradi",
    [
        (0.000, "#f7f8d8"),  # background paper
        (0.040, "#eef2c2"),
        (0.180, "#bcd99a"),
        (0.380, "#6fc2ad"),
        (0.600, "#2f8fc4"),
        (0.800, "#1f4fa8"),
        (1.000, "#0a1342"),  # densest cores
    ],
)


def iterate_density(a, b, n_points=700_000, n_iter=200, burn_in=25,
                    res=1000, domain=DOMAIN, seed=0):
    """Accumulate visited points into a (res x res) density histogram.

    Uses float32 math and bincount accumulation -- both several times faster
    than the float64 + np.add.at approach, which lets us push n_iter high enough
    to resolve the thin near-1D curves and the fine symmetric-fractal cores.
    """
    rng = np.random.default_rng(seed)
    xmin, xmax, ymin, ymax = domain

    # Random cloud of starting points across the domain.
    x = rng.uniform(xmin, xmax, n_points).astype(np.float32)
    y = rng.uniform(ymin, ymax, n_points).astype(np.float32)
    a = np.float32(a)
    b = np.float32(b)

    flat = np.zeros(res * res, dtype=np.float64)
    ix_scale = res / (xmax - xmin)
    iy_scale = res / (ymax - ymin)
    cells = res * res

    for n in range(n_iter):
        xn = np.sin(x * x - y * y + a)
        yn = np.cos(2.0 * x * y + b)
        x, y = xn, yn

        if n < burn_in:
            continue

        # Map points to pixel bins and accumulate via bincount (fast).
        ix = ((x - xmin) * ix_scale).astype(np.int32)
        iy = ((y - ymin) * iy_scale).astype(np.int32)
        np.clip(ix, 0, res - 1, out=ix)
        np.clip(iy, 0, res - 1, out=iy)
        idx = iy * res + ix
        flat += np.bincount(idx, minlength=cells)

    return flat.reshape(res, res)


def density_to_rgb(hist, gamma=0.62, cmap=ATTRACTOR_CMAP):
    """Log-scale + gamma the density and run it through the colormap -> RGB uint8."""
    d = np.log1p(hist)
    peak = d.max()
    if peak > 0:
        d /= peak
    d = np.power(d, gamma)          # lift the faint outer filaments
    rgba = cmap(d)                  # (res, res, 4) float in [0, 1]
    return (rgba[..., :3] * 255).astype(np.uint8)


def render(a, b, **kw):
    """Convenience: parameters -> RGB image array."""
    iter_kw = {k: kw[k] for k in
               ("n_points", "n_iter", "burn_in", "res", "domain", "seed") if k in kw}
    rgb_kw = {k: kw[k] for k in ("gamma", "cmap") if k in kw}
    return density_to_rgb(iterate_density(a, b, **iter_kw), **rgb_kw)
