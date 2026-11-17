"""Turn a light on dim before dawn and brighten it as the sun rises.

Usage
-----
bedroom_sunrise:
    module: sunrise_fade
    class: SunriseFade
    light: light.bedroom_lamp

Settings
--------
Same as light_fade.py, with the defaults in SunriseSettings. The detector is
always the sun, so levels are sun elevation in degrees.

Testing
-------
Developer tools > Events, Event type `<app name>_start`, e.g. `bedroom_sunrise_start` > Fire event
"""
from typing import ClassVar

from ha_automations.apps.light_fade import LightFadeApp, LightFadeSettings
from ha_automations.detectors import Sun
from ha_automations.triggers import Daily, TriggerConfig


class SunriseSettings(LightFadeSettings):
    """Settings for SunriseFade. Same as LightFadeSettings, with sunrise defaults."""

    detector: Sun = Sun()
    """Uses the sun's elevation."""
    start: tuple[TriggerConfig, ...] = (Daily(daily="05:45:00"),)
    """When to check if it is still dark."""
    from_level: float = -6
    """Civil dawn. The light turns on if the sun is below this at the start time."""
    to_level: float = 0
    """Sunrise. The light reaches full brightness."""
    off_level: float | None = 4
    """A little after sunrise. The light turns off."""


class SunriseFade(LightFadeApp):
    Settings: ClassVar[type[LightFadeSettings]] = SunriseSettings
