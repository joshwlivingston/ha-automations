"""Brighten a light as the sun sets.

Usage
-----
living_room_sunset:
    module: sunset_fade
    class: SunsetFade
    light: light.living_room_lamp

Settings
--------
See light_fade.py. The detector is always the sun.

Defaults
--------
setting      value     meaning
start        []        always armed
from_level   6         a little above the horizon, brightening starts
to_level     -6        civil dusk, max brightness
off_level    unset     light stays on

Levels are sun elevation in degrees.

Testing
-------
Settings > Tools > Events, Event type `<app name>_start`, e.g. `living_room_sunset_start` > Fire event
"""
from typing import ClassVar

from ha_automations.apps.light_fade import LightFadeApp, LightFadeSettings
from ha_automations.detectors import Sun


class SunsetSettings(LightFadeSettings):
    detector: Sun = Sun()
    from_level: float = 6
    to_level: float = -6


class SunsetFade(LightFadeApp):
    Settings: ClassVar[type[LightFadeSettings]] = SunsetSettings
