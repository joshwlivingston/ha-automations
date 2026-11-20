"""Easing and interpolation math. No Home Assistant imports."""

DIM_DEPTH = 0.1
"""Share of brightness ease_out_quartic removes by p = 1."""


def clamp(x, lo=0.0, hi=1.0):
    """`x` limited to between `lo` and `hi`."""
    return max(lo, min(hi, x))


def progress(x, start, end):
    """0.0 at `start`, 1.0 at `end` (works for descending ranges), clamped."""
    return clamp((x - start) / (end - start))


def ease_in(p, k=1.5):
    """k > 1 makes early steps more subtle."""
    return p ** k


def ease_out_quartic(p, d=DIM_DEPTH):
    """1 - d * p**4. Holds near 1, then falls to 1 - d at p = 1."""
    return 1 - d * p ** 4


def lerp(a, b, t):
    """The value fraction `t` of the way from `a` to `b`."""
    return a + (b - a) * t
