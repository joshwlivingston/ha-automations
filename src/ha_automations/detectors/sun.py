"""Sun elevation detector."""
from collections.abc import Callable
from typing import Literal

from ha_automations.config import Config
from ha_automations.detectors.base import Detector, Reading
from ha_automations.solar import sun_state


class SunDetector:
    """Sun elevation in degrees from `sun.sun`."""

    def __init__(self, app):
        self.app = app

    def read(self) -> Reading:
        return Reading(*sun_state(self.app))

    def listen(self, callback: Callable[[], object]) -> None:
        def on_change(entity, attribute, old, new, **kwargs):
            callback()

        self.app.listen_state(on_change, "sun.sun", attribute="elevation")


class Sun(Config):
    kind: Literal["sun"] = "sun"

    def build(self, app) -> Detector:
        return SunDetector(app)
