"""Ambient light detectors that fades read from.

A detector reports a light level (higher is brighter, in the detector's own
units) and whether that level is rising. Fade thresholds are in the same units
as the detector they are used with.
"""
from collections.abc import Callable
from typing import Protocol

from ha_automations.solar import sun_state


class Detector(Protocol):
    def read(self) -> tuple[float | None, bool | None]:
        """(level, rising). level is None if unavailable; rising is None if unknown."""
        ...

    def listen(self, callback: Callable[[], object]) -> None:
        """Call `callback` whenever the level may have changed."""
        ...


class SunDetector:
    """Sun elevation in degrees from `sun.sun`."""

    def __init__(self, app):
        self.app = app

    def read(self) -> tuple[float | None, bool | None]:
        return sun_state(self.app)

    def listen(self, callback: Callable[[], object]) -> None:
        def on_change(entity, attribute, old, new, **kwargs):
            callback()

        self.app.listen_state(on_change, "sun.sun", attribute="elevation")


DETECTORS: dict[str, Callable[..., Detector]] = {"sun": SunDetector}
DEFAULT_DETECTOR = "sun"


def make_detector(app, name: str = DEFAULT_DETECTOR) -> Detector:
    """Build the detector registered under `name` in DETECTORS."""
    try:
        factory = DETECTORS[name]
    except KeyError:
        raise ValueError(f"unknown detector {name!r}, expected one of {sorted(DETECTORS)}") from None
    return factory(app)
