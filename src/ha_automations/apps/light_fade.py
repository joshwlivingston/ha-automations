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
Each field of LightFadeSettings has a docstring. The docs site renders
them as the settings table and the API reference. Unknown settings are an error.

Restarts
--------
A triggered fade saves its start level to a file in STATE_DIR under
AppDaemon's config directory and restores it on load. Every fade checks the
level once on load.

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
    RAMP_TRANSITION,
    LightFade,
    RampCurve,
    line,
)
from ha_automations.lights import HassLight
from ha_automations.store import JsonFile
from ha_automations.triggers import Daily, Event, Trigger, TriggerConfig

# Keys AppDaemon itself puts in app args.
APPDAEMON_KEYS = frozenset(f.alias or name for name, f in AppConfig.model_fields.items())
EVENT_SUFFIX = "_start"
STATE_DIR = "ha_automations_state"  # in AppDaemon's config directory, outside apps/, which deploys replace


class LightFadeSettings(Config):
    """Settings for LightFadeApp, read from apps.yaml."""

    light: str
    """Light to control, e.g. `light.bedroom_lamp`."""
    detector: DetectorConfig
    """What sets the level. Only `kind: sun`, sun elevation in degrees."""
    start: tuple[TriggerConfig, ...] = ()
    """Triggers that start the fade. Empty means it runs whenever the level is between from_level and to_level."""
    from_level: float
    """Level where the light turns on."""
    to_level: float
    """Level where the light reaches max_brightness."""
    off_level: float | None = None
    """Level where the light turns off. Unset means it stays on."""
    off_time: str | None = None
    """Time of day the light turns off, e.g. `"23:00:00"`. Unset means no set time."""
    min_brightness: int = Field(MIN_BRIGHTNESS, ge=0, le=100)
    """Brightness when the light turns on, percent."""
    max_brightness: int = Field(MAX_BRIGHTNESS, ge=0, le=100)
    """Brightness at to_level, percent."""
    off_transition: float = Field(OFF_TRANSITION, ge=0)
    """How long the light takes to fade off, seconds."""
    ramp_curve: RampCurve = "decay"
    """How the light brightens. `decay` is the dim curve reversed; `ease_in` starts slowly."""
    dim: bool = False
    """Dim from max_brightness at to_level to off on the `decay` curve: to off_level if set, else by clock to off_time. Ignored without either."""


class LightFadeApp(hass.Hass):
    """AppDaemon app that runs a LightFade with settings from apps.yaml."""

    Settings: ClassVar[type[LightFadeSettings]] = LightFadeSettings
    """Settings model the app reads from apps.yaml."""

    def initialize(self):
        """Read the settings, start listening and restore a saved fade. AppDaemon calls this on load."""
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
            ramp_curve=s.ramp_curve,
            dim=s.dim,
            dim_end=self._dim_end(s),
            triggered=bool(s.start),
            store=JsonFile(self.config_dir / STATE_DIR / f"{self.name}.json"),
            log=self.log,
            debug=lambda msg: self.log(msg, level="DEBUG"),
        )
        triggers: list[Trigger] = [*s.start, Event(event=self.event)]
        for trigger in triggers:
            trigger.listen(self, lambda t=trigger: self._start(t))
        if s.off_time is not None:
            Daily(daily=s.off_time).listen(self, lambda: self.fade.stop("reached off_time"))
        self.fade.detector.listen(self.fade.update)
        if self.fade.dim_end is not None:
            self.run_every(lambda **kwargs: self.fade.update(), "now", RAMP_TRANSITION)
        self.log(self._summary(s))
        self.fade.restore()

    def _dim_end(self, s: LightFadeSettings):
        """For a dim by clock, a function giving the next off_time after a time. Else None."""
        if not s.dim or s.off_level is not None or s.off_time is None:
            return None
        off_time = s.off_time

        def next_off(t: float) -> float:
            end = self.parse_datetime(off_time, aware=True, today=True).timestamp()
            return end if end > t else end + 24 * 3600

        return next_off

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
        if s.ramp_curve != "decay":
            fields.append(f"ramp_curve={s.ramp_curve}")
        if self.fade.dim:
            fields.append("dim=on")
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
