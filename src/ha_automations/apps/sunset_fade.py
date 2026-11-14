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
from typing import Any, ClassVar

from ha_automations.apps.light_fade import LightFadeApp


class SunsetFade(LightFadeApp):
    DETECTOR = "sun"
    DEFAULTS: ClassVar[dict[str, Any]] = {"from_level": 6, "to_level": -6}
