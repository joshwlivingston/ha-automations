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
Each field of LightFadeSettings has a description. The docs site renders
them as the settings table. Unknown settings are an error.

Testing
-------
Developer tools > Events, Event type `<app name>` plus EVENT_SUFFIX > Fire event.
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
    line,
)
from ha_automations.lights import HassLight
from ha_automations.triggers import Daily, Event, Trigger, TriggerConfig

# Keys AppDaemon itself puts in app args.
APPDAEMON_KEYS = frozenset(f.alias or name for name, f in AppConfig.model_fields.items())
EVENT_SUFFIX = "_start"


class LightFadeSettings(Config):
    light: str = Field(description="Light to control, e.g. `light.bedroom_lamp`")
    detector: DetectorConfig = Field(description="What sets the level. Only `kind: sun`, sun elevation in degrees")
    start: tuple[TriggerConfig, ...] = Field(
        (), description="Triggers that start the fade. Empty means it runs whenever the level is between from_level and to_level"
    )
    from_level: float = Field(description="Level where the light turns on")
    to_level: float = Field(description="Level where the light reaches max_brightness")
    off_level: float | None = Field(None, description="Level where the light turns off. Unset means it stays on")
    off_time: str | None = Field(
        None, description='Time of day the light turns off, e.g. `"23:00:00"`. Unset means no set time'
    )
    min_brightness: int = Field(MIN_BRIGHTNESS, ge=0, le=100, description="Brightness when the light turns on, percent")
    max_brightness: int = Field(MAX_BRIGHTNESS, ge=0, le=100, description="Brightness at to_level, percent")
    off_transition: float = Field(OFF_TRANSITION, ge=0, description="How long the light takes to fade off, seconds")


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
            log=self.log,
            debug=lambda msg: self.log(msg, level="DEBUG"),
        )
        triggers: list[Trigger] = [*s.start, Event(event=self.event)]
        for trigger in triggers:
            trigger.listen(self, lambda t=trigger: self._start(t))
        if s.off_time is not None:
            Daily(daily=s.off_time).listen(self, lambda: self.fade.stop("reached off_time"))
        self.fade.detector.listen(self.fade.update)
        self.log(self._summary(s))

    def _summary(self, s: LightFadeSettings) -> str:
        """One line saying what this app controls and when it starts."""
        u = self.fade.detector.unit
        fields = [
            f"light={s.light}",
            f"detector={self.fade.detector.label}",
            f"from_level={s.from_level:g}{u}",
            f"to_level={s.to_level:g}{u}",
        ]
        if s.off_level is not None:
            fields.append(f"off_level={s.off_level:g}{u}")
        if s.off_time is not None:
            fields.append(f'off_time="{s.off_time}"')
        fields += [
            f"brightness={s.min_brightness}%..{s.max_brightness}%",
            f'start="{", ".join(map(str, s.start))}"' if s.start else "start=none",
            f"test_event={self.event}",
        ]
        return line("load", "init", " ".join(fields))

    @property
    def event(self) -> str:
        """Event that runs a start check for this app instance."""
        return self.name + EVENT_SUFFIX

    def _start(self, trigger: Trigger):
        self.log(line("check", "start trigger", str(trigger)))
        self.fade.start()
