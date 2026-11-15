"""Ambient light detectors that fades read from.

A detector reports a light level (higher is brighter, in the detector's own
units) and whether that level is rising. Fade thresholds are in the same units
as the detector they are used with. Detectors are configured as DetectorConfig
models, for example `{"kind": "sun"}`, and each config builds its detector.
"""
from collections.abc import Callable
from typing import Literal, Protocol

from ha_automations.config import Config
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


class Sun(Config):
    kind: Literal["sun"] = "sun"

    def build(self, app) -> Detector:
        return SunDetector(app)


# Make this a union discriminated on `kind` when a second detector is added.
DetectorConfig = Sun
