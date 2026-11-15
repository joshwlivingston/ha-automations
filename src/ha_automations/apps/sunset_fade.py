"""Brighten a light as the sun sets.

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
Settings > Tools > Events, Event type `<app name>_start`, e.g. `living_room_sunset_start` > Fire event
"""
from typing import ClassVar

from pydantic import Field

from ha_automations.apps.light_fade import LightFadeApp, LightFadeSettings
from ha_automations.detectors import Sun


class SunsetSettings(LightFadeSettings):
    detector: Sun = Field(Sun(), description="always the sun")
    from_level: float = Field(6, description="a little above the horizon, brightening starts")
    to_level: float = Field(-6, description="civil dusk, max brightness")


class SunsetFade(LightFadeApp):
    Settings: ClassVar[type[LightFadeSettings]] = SunsetSettings
