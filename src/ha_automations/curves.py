"""Easing and interpolation math. No Home Assistant imports."""
import math

DECAY = 4
"""Steepness of decay. Larger falls sooner."""


def clamp(x, lo=0.0, hi=1.0):
    """`x` limited to between `lo` and `hi`."""
    return max(lo, min(hi, x))


def progress(x, start, end):
    """0.0 at `start`, 1.0 at `end` (works for descending ranges), clamped."""
    return clamp((x - start) / (end - start))


def ease_in(p, k=1.5):
    """k > 1 makes early steps more subtle."""
    return p ** k


def decay(p, k=DECAY):
    """exp(-k * p**4), scaled to 1 at p = 0 and 0 at p = 1. Holds, falls, then levels off."""
    floor = math.exp(-k)
    return (math.exp(-k * p ** 4) - floor) / (1 - floor)


def lerp(a, b, t):
    """The value fraction `t` of the way from `a` to `b`."""
    return a + (b - a) * t
