"""Sun elevation detector."""
from collections.abc import Callable
from typing import Literal

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


class Sun(Config):
    """Settings for SunDetector."""

    kind: Literal["sun"] = "sun"
    """Detector kind."""

    def build(self, app) -> Detector:
        """A SunDetector that reads through `app`."""
        return SunDetector(app)
