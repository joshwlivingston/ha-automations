"""Easing and interpolation math. No Home Assistant imports."""


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def progress(x, start, end):
    """0.0 at `start`, 1.0 at `end` (works for descending ranges), clamped."""
    return clamp((x - start) / (end - start))


def ease_in(p, k=1.5):
    """k > 1 makes early steps more subtle."""
    return p ** k


def lerp(a, b, t):
    return a + (b - a) * t
