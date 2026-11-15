"""Brighten a light as a detector's light level moves between two levels.

The fade rises or falls depending on whether to_level is above or below
from_level. Subclasses may set Settings to a LightFadeSettings subclass with
other defaults.

Usage
-----
bedroom_fade:
    module: light_fade
    class: LightFadeApp
    light: light.bedroom_lamp
    detector:
      kind: sun
    from_level: -6
    to_level: 0
    off_level: 4
    start:
      - daily: "05:45:00"

Settings
--------
setting          default       meaning
light            required      light entity to control
detector         required      light level source, a detectors.DetectorConfig
start            []            triggers that arm the fade (see triggers.py); empty means always armed
from_level       required      level where brightening starts
to_level         required      level where max_brightness is reached
off_level        unset         level where the light turns off; unset means never
min_brightness   5             starting brightness, percent
max_brightness   50            brightness at to_level, percent
off_transition   300           fade-out length, seconds

Unknown settings are an error.

Testing
-------
Settings > Tools > Events, Event type `<app name>` plus EVENT_SUFFIX > Fire event.
This runs the same check as a start trigger.
"""
from typing import ClassVar

import appdaemon.plugins.hass.hassapi as hass
from appdaemon.models.config.app import AppConfig
from pydantic import Field

from ha_automations.config import Config
from ha_automations.detectors import DetectorConfig
from ha_automations.fades import (
    MAX_BRIGHTNESS,
    MIN_BRIGHTNESS,
    OFF_TRANSITION,
    LightFade,
)
from ha_automations.lights import HassLight
from ha_automations.triggers import Event, Trigger, TriggerConfig

# Keys AppDaemon itself puts in app args.
APPDAEMON_KEYS = frozenset(f.alias or name for name, f in AppConfig.model_fields.items())
EVENT_SUFFIX = "_start"


class LightFadeSettings(Config):
    light: str
    detector: DetectorConfig
    start: tuple[TriggerConfig, ...] = ()
    from_level: float
    to_level: float
    off_level: float | None = None
    min_brightness: int = Field(MIN_BRIGHTNESS, ge=0, le=100)
    max_brightness: int = Field(MAX_BRIGHTNESS, ge=0, le=100)
    off_transition: float = Field(OFF_TRANSITION, ge=0)


class LightFadeApp(hass.Hass):
    Settings: ClassVar[type[LightFadeSettings]] = LightFadeSettings

    def initialize(self):
        args = {k: v for k, v in self.args.items() if k not in APPDAEMON_KEYS}
        s = self.Settings.model_validate(args)
        self.fade = LightFade(
            detector=s.detector.build(self),
            light=HassLight(self, s.light),
            from_level=s.from_level,
            to_level=s.to_level,
            off_level=s.off_level,
            min_brightness=s.min_brightness,
            max_brightness=s.max_brightness,
            off_transition=s.off_transition,
            triggered=bool(s.start),
        )
        triggers: list[Trigger] = [*s.start, Event(event=self.event)]
        for trigger in triggers:
            trigger.listen(self, self._start)
        self.fade.detector.listen(self.fade.update)
        self.log(f"{self.name} loaded: {s.light}, {s.from_level} to {s.to_level}, start {s.start or 'always'}, test event {self.event}")

    @property
    def event(self) -> str:
        """Event that runs a start check for this app instance."""
        return self.name + EVENT_SUFFIX

    def _start(self):
        if not self.fade.start():
            self.log(f"{self.name}: outside fade, nothing to do")
