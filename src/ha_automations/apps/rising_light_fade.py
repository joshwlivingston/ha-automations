"""Turn a light on dim before dawn and brighten it as the light level rises.

Usage
-----
bedroom_rising_light:
    module: rising_light_fade
    class: RisingLightFade
    light: light.bedroom_lamp

Settings
--------
setting          default     meaning
light                        light entity to control
detector         sun         light level source, a key of detectors.DETECTORS
on_time          05:45:00    when to check if it is dark
dark_level       -6          level below which it is dark
full_level       0           level where max_brightness is reached
off_level        4           level where the light turns off
min_brightness   5           starting brightness, percent
max_brightness   50          brightness at full_level, percent
off_transition   300         fade-out length, seconds

Levels are in the detector's units. Defaults are sun elevation in degrees.

Testing
-------
Settings > Tools > Events, Event type `lamp_rising_light_on` > Fire event
"""
import appdaemon.plugins.hass.hassapi as hass

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.detectors import DEFAULT_DETECTOR, make_detector
from ha_automations.lights import brighten_only

DARK_LEVEL = -6        # below this counts as dark (civil dawn)
FULL_LEVEL = 0         # MAX_BRIGHTNESS reached (sunrise)
OFF_LEVEL = 4          # lamp turns off
MIN_BRIGHTNESS = 5     # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50
OFF_TRANSITION = 300   # seconds, fade-out duration
ON_TIME = "05:45:00"


class RisingLightFade(hass.Hass):
    def initialize(self):
        self.lamp = self.args["light"]
        a = self.args
        self.detector = make_detector(self, a.get("detector", DEFAULT_DETECTOR))
        self.dark_level = a.get("dark_level", DARK_LEVEL)
        self.full_level = a.get("full_level", FULL_LEVEL)
        self.off_level = a.get("off_level", OFF_LEVEL)
        self.min_brightness = a.get("min_brightness", MIN_BRIGHTNESS)
        self.max_brightness = a.get("max_brightness", MAX_BRIGHTNESS)
        self.off_transition = a.get("off_transition", OFF_TRANSITION)
        self.on_time = str(a.get("on_time", ON_TIME))
        # Level at self.on_time when we switched the lamp on; None = not running this morning.
        self._start_level = None
        self.run_daily(self._on_time, self.on_time)
        self.detector.listen(self.lamp_rising_light_ramp)
        self.listen_event(self._on_event, "lamp_rising_light_on")
        self.log(f"rising_light_fade loaded: {self.lamp}, on at {self.on_time} if < {self.dark_level}, off at {self.off_level}")

    def _on_time(self, **kwargs):
        self.lamp_rising_light_on()

    def _on_event(self, event_type, data, **kwargs):
        self.lamp_rising_light_on()

    def lamp_rising_light_on(self):
        """Switch the lamp on dimly if it's still dark."""
        level, rising = self.detector.read()
        if level is None or rising is False or level >= self.dark_level:
            self.log(f"rising_light_fade: already light enough ({level}), skipping")
            self._start_level = None
            return
        self._start_level = level
        brighten_only(self, self.lamp, self.min_brightness, transition=5)

    def lamp_rising_light_ramp(self):
        """Brighten as the level rises, then turn off once it's daylight."""
        if self._start_level is None:
            return
        level, rising = self.detector.read()
        if level is None:
            return
        if level >= self.off_level or rising is False:
            self._start_level = None
            self.call_service("light/turn_off", entity_id=self.lamp, transition=self.off_transition)
            return
        p = progress(level, self._start_level, self.full_level)
        brighten_only(self, self.lamp, round(lerp(self.min_brightness, self.max_brightness, ease_in(p))))
