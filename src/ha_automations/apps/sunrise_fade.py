"""Turn a light on dim before dawn and brighten it as the sun rises.

Usage
-----
bedroom_sunrise:
    module: sunrise_fade
    class: SunriseFade
    light: light.bedroom_lamp

Settings
--------
setting          default     meaning
light                        light entity to control
on_time          05:45:00    when to check if it is dark
dark_elevation   -6          sun elevation (degrees) below which it is dark
full_elevation   0           elevation where max_brightness is reached
off_elevation    4           elevation where the light turns off
min_brightness   5           starting brightness, percent
max_brightness   50          brightness at full_elevation, percent
off_transition   300         fade-out length, seconds

Testing
-------
Settings > Tools > Events, Event type `lamp_sunrise_on` > Fire event
"""
import appdaemon.plugins.hass.hassapi as hass

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.lights import brighten_only
from ha_automations.solar import sun_state

DARK_ELEVATION = -6    # degrees, below this counts as dark (civil dawn)
FULL_ELEVATION = 0     # degrees, MAX_BRIGHTNESS reached (sunrise)
OFF_ELEVATION = 4      # degrees, lamp turns off
MIN_BRIGHTNESS = 5     # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50
OFF_TRANSITION = 300   # seconds, fade-out duration
ON_TIME = "05:45:00"


class SunriseFade(hass.Hass):
    def initialize(self):
        self.lamp = self.args["light"]
        a = self.args
        self.dark_elevation = a.get("dark_elevation", DARK_ELEVATION)
        self.full_elevation = a.get("full_elevation", FULL_ELEVATION)
        self.off_elevation = a.get("off_elevation", OFF_ELEVATION)
        self.min_brightness = a.get("min_brightness", MIN_BRIGHTNESS)
        self.max_brightness = a.get("max_brightness", MAX_BRIGHTNESS)
        self.off_transition = a.get("off_transition", OFF_TRANSITION)
        self.on_time = str(a.get("on_time", ON_TIME))
        # Elevation at self.on_time when we switched the lamp on; None = not running this morning.
        self._start_elevation = None
        self.run_daily(self._on_time, self.on_time)
        self.listen_state(self._on_elevation, "sun.sun", attribute="elevation")
        self.listen_event(self._on_event, "lamp_sunrise_on")
        self.log(f"sunrise_fade loaded: {self.lamp}, on at {self.on_time} if < {self.dark_elevation}°, off at {self.off_elevation}°")

    def _on_time(self, **kwargs):
        self.lamp_sunrise_on()

    def _on_event(self, event_type, data, **kwargs):
        self.lamp_sunrise_on()

    def _on_elevation(self, entity, attribute, old, new, **kwargs):
        self.lamp_sunrise_ramp()

    def lamp_sunrise_on(self):
        """Switch the lamp on dimly if it's still dark."""
        elevation, rising = sun_state(self)
        if elevation is None or not rising or elevation >= self.dark_elevation:
            self.log(f"sunrise_fade: already light enough ({elevation}°), skipping")
            self._start_elevation = None
            return
        self._start_elevation = elevation
        brighten_only(self, self.lamp, self.min_brightness, transition=5)

    def lamp_sunrise_ramp(self):
        """Brighten with the rising sun, then turn off once it's daylight."""
        if self._start_elevation is None:
            return
        elevation, rising = sun_state(self)
        if elevation is None:
            return
        if elevation >= self.off_elevation or not rising:
            self._start_elevation = None
            self.call_service("light/turn_off", entity_id=self.lamp, transition=self.off_transition)
            return
        p = progress(elevation, self._start_elevation, self.full_elevation)
        brighten_only(self, self.lamp, round(lerp(self.min_brightness, self.max_brightness, ease_in(p))))
