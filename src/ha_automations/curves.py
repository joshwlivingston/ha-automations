"""Easing and interpolation math. No Home Assistant imports."""
import math

DIM_RATE = 0.0002
"""How fast decay_quartic falls. Larger dims sooner."""


def clamp(x, lo=0.0, hi=1.0):
    """`x` limited to between `lo` and `hi`."""
    return max(lo, min(hi, x))


def progress(x, start, end):
    """0.0 at `start`, 1.0 at `end` (works for descending ranges), clamped."""
    return clamp((x - start) / (end - start))


def ease_in(p, k=1.5):
    """k > 1 makes early steps more subtle."""
    return p ** k


def decay_quartic(x, d=DIM_RATE):
    """exp(-d * x**4). 1 at x = 0, falls smoothly toward 0."""
    return math.exp(-d * x ** 4)


def lerp(a, b, t):
    """The value fraction `t` of the way from `a` to `b`."""
    return a + (b - a) * t
