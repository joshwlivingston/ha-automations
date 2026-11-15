"""Brighten a light as the sun sets and turn it off at night.

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

from pydantic import Field

from ha_automations.apps.light_fade import LightFadeApp, LightFadeSettings
from ha_automations.detectors import Sun


class SunsetSettings(LightFadeSettings):
    detector: Sun = Field(Sun(), description="Uses the sun's elevation")
    from_level: float = Field(6, description="A little above the horizon. The light turns on")
    to_level: float = Field(-6, description="Civil dusk. The light reaches full brightness")
    off_time: str | None = Field("23:00:00", description="Time the light turns off")


class SunsetFade(LightFadeApp):
    Settings: ClassVar[type[LightFadeSettings]] = SunsetSettings
