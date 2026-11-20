"""Easing and interpolation math. No Home Assistant imports."""
import math

LOG_OFFSET = 0.4
"""Offset that keeps ease_out_log finite at 0. Gives it the same average as ease_in reversed."""


def clamp(x, lo=0.0, hi=1.0):
    """`x` limited to between `lo` and `hi`."""
    return max(lo, min(hi, x))


def progress(x, start, end):
    """0.0 at `start`, 1.0 at `end` (works for descending ranges), clamped."""
    return clamp((x - start) / (end - start))


def ease_in(p, k=1.5):
    """k > 1 makes early steps more subtle."""
    return p ** k


def ease_out_log(p, eps=LOG_OFFSET):
    """-log(p) scaled from 1 at p = 0 to 0 at p = 1. Falls fast early and slowly at the end."""
    return math.log((p + eps) / (1 + eps)) / math.log(eps / (1 + eps))


def lerp(a, b, t):
    """The value fraction `t` of the way from `a` to `b`."""
    return a + (b - a) * t
