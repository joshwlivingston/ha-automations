"""Sun elevation detector."""
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal

from astral import SunDirection

from ha_automations.config import Config
from ha_automations.detectors.base import Detector, Reading
from ha_automations.solar import sun_state


class SunDetector:
    """Sun elevation in degrees from `sun.sun`."""

    label = "sun"
    """Name in logs."""
    unit = "deg"
    """Unit in logs."""

    def __init__(self, app):
        self.app = app
        """AppDaemon app that reads `sun.sun`."""

    def read(self) -> Reading:
        """Current elevation and whether it is rising."""
        return Reading(*sun_state(self.app))

    def listen(self, callback: Callable[[], object]) -> None:
        """Call `callback` whenever the elevation changes."""

        def on_change(entity, attribute, old, new, **kwargs):
            callback()

        self.app.listen_state(on_change, "sun.sun", attribute="elevation")

    def passed_at(self, level: float, rising: bool) -> float | None:
        """Last time the sun passed elevation `level` in that direction, today or yesterday, from AppDaemon's location."""
        location = self.app.AD.sched.location
        direction = SunDirection.RISING if rising else SunDirection.SETTING
        now = datetime.now(UTC)
        today = location.today(local=True)
        for days in (0, 1):
            try:
                t = location.time_at_elevation(level, today - timedelta(days=days), direction)
            except ValueError:  # the sun does not reach `level` that day
                continue
            if t <= now:
                return t.timestamp()
        return None


class Sun(Config):
    """Settings for SunDetector."""

    kind: Literal["sun"] = "sun"
    """Detector kind."""

    def build(self, app) -> Detector:
        """A SunDetector that reads through `app`."""
        return SunDetector(app)
