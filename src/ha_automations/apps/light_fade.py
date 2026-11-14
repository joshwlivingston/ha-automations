"""Brighten a light as a detector's light level moves between two levels.

The fade rises or falls depending on whether to_level is above or below
from_level. Subclasses may set DEFAULTS, DEFAULT_START and DETECTOR.

Usage
-----
bedroom_fade:
    module: light_fade
    class: LightFadeApp
    light: light.bedroom_lamp
    detector: sun
    from_level: -6
    to_level: 0
    off_level: 4
    start:
      - daily: "05:45:00"

Settings
--------
setting          default     meaning
light            required    light entity to control
detector         sun         light level source, a key of detectors.DETECTORS;
                             not settable when the subclass sets DETECTOR
start            []          trigger specs that arm the fade (see triggers.py); empty means always armed
from_level       required    level where brightening starts
to_level         required    level where max_brightness is reached
off_level        unset       level where the light turns off; unset means never
min_brightness   5           starting brightness, percent
max_brightness   50          brightness at to_level, percent
off_transition   300         fade-out length, seconds

Settings not given come from the subclass DEFAULTS, then from LightFade.

Testing
-------
Settings > Tools > Events, Event type `<app name>` plus EVENT_SUFFIX > Fire event.
This runs the same check as a start trigger.
"""
from typing import Any, ClassVar

import appdaemon.plugins.hass.hassapi as hass

from ha_automations.detectors import DEFAULT_DETECTOR, make_detector
from ha_automations.fades import LightFade
from ha_automations.lights import HassLight
from ha_automations.settings import settings_for
from ha_automations.triggers import EventTrigger, make_triggers

# LightFade fields not read from settings.
NOT_SETTINGS = ("detector", "light", "triggered")
REQUIRED = ("from_level", "to_level")
EVENT_SUFFIX = "_start"


class LightFadeApp(hass.Hass):
    DEFAULTS: ClassVar[dict[str, Any]] = {}
    DEFAULT_START: ClassVar[list[dict[str, Any]]] = []
    DETECTOR: ClassVar[str | None] = None

    def initialize(self):
        a = self.args
        start = a.get("start", self.DEFAULT_START)
        settings = settings_for(LightFade, {**self.DEFAULTS, **a}, exclude=NOT_SETTINGS)
        if missing := [k for k in REQUIRED if k not in settings]:
            raise ValueError(f"{self.name}: missing settings {missing}")
        self.fade = LightFade(
            detector=make_detector(self, self._detector_name()),
            light=HassLight(self, a["light"]),
            triggered=bool(start),
            **settings,
        )
        for trigger in [*make_triggers(self, start), EventTrigger(self, self.event)]:
            trigger.listen(self._start)
        self.fade.detector.listen(self.fade.update)
        f = self.fade
        self.log(f"{self.name} loaded: {a['light']}, {f.from_level} to {f.to_level}, start {start or 'always'}, test event {self.event}")

    @property
    def event(self) -> str:
        """Event that runs a start check for this app instance."""
        return self.name + EVENT_SUFFIX

    def _detector_name(self) -> str:
        if self.DETECTOR is None:
            return self.args.get("detector", DEFAULT_DETECTOR)
        if "detector" in self.args:
            raise ValueError(f"{self.name}: detector is fixed to {self.DETECTOR!r}")
        return self.DETECTOR

    def _start(self):
        if not self.fade.start():
            self.log(f"{self.name}: outside fade, nothing to do")
