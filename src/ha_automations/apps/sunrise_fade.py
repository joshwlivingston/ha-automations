"""Turn a light on dim before dawn and brighten it as the sun rises.

Usage
-----
bedroom_sunrise:
    module: sunrise_fade
    class: SunriseFade
    light: light.bedroom_lamp

Settings
--------
See light_fade.py. The detector is always the sun.

Defaults
--------
setting      value                   meaning
start        - daily: "05:45:00"     when to check if it is dark
from_level   -6                      civil dawn, below which the light turns on
to_level     0                       sunrise, max brightness
off_level    4                       a little after sunrise, light turns off

Levels are sun elevation in degrees.

Testing
-------
Settings > Tools > Events, Event type `<app name>_start`, e.g. `bedroom_sunrise_start` > Fire event
"""
from typing import ClassVar

from ha_automations.apps.light_fade import LightFadeApp, LightFadeSettings
from ha_automations.detectors import Sun
from ha_automations.triggers import Daily, TriggerConfig


class SunriseSettings(LightFadeSettings):
    detector: Sun = Sun()
    start: tuple[TriggerConfig, ...] = (Daily(daily="05:45:00"),)
    from_level: float = -6
    to_level: float = 0
    off_level: float | None = 4


class SunriseFade(LightFadeApp):
    Settings: ClassVar[type[LightFadeSettings]] = SunriseSettings
