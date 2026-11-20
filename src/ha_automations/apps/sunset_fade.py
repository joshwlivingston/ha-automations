"""Brighten a light as the sun sets, then dim it off by off_time.

Usage
-----
living_room_sunset:
    module: sunset_fade
    class: SunsetFade
    light: light.living_room_lamp

Settings
--------
Same as light_fade.py, with the defaults in SunsetSettings. The detector is
always the sun, so levels are sun elevation in degrees.

Testing
-------
Developer tools > Events, Event type `<app name>_start`, e.g. `living_room_sunset_start` > Fire event
"""
from typing import ClassVar

from ha_automations.apps.light_fade import LightFadeApp, LightFadeSettings
from ha_automations.detectors import Sun
from ha_automations.fades import RampCurve


class SunsetSettings(LightFadeSettings):
    """Settings for SunsetFade. Same as LightFadeSettings, with sunset defaults."""

    detector: Sun = Sun()
    """Uses the sun's elevation."""
    from_level: float = 12
    """Well above the horizon. The light turns on."""
    to_level: float = 0
    """Sunset. The light reaches full brightness."""
    ramp_curve: RampCurve = "decay"
    """The Sunrise Fade dim curve reversed."""
    off_time: str | None = "23:00:00"
    """Time the light turns off."""
    dim: bool = True
    """Dims from full brightness at to_level to off at off_time, by clock time."""


class SunsetFade(LightFadeApp):
    """LightFadeApp with SunsetSettings."""

    Settings: ClassVar[type[LightFadeSettings]] = SunsetSettings
    """Settings model the app reads from apps.yaml."""
