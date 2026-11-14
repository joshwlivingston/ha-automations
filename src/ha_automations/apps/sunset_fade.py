"""Brighten a light as the light level falls in the evening.

Usage
-----
living_room_sunset:
    module: sunset_fade
    class: SunsetFade
    light: light.living_room_lamp

Settings
--------
setting          default     meaning
light                        light entity to control
detector         sun         light level source, a key of detectors.DETECTORS
start_level      6           level where brightening starts
end_level        -6          level where max_brightness is reached
min_brightness   5           starting brightness, percent
max_brightness   50          brightness at end_level, percent

Levels are in the detector's units. Defaults are sun elevation in degrees.

Testing
-------
Settings > Tools > Events, Event type `lamp_sunset_fade_in` > Fire event
"""
import appdaemon.plugins.hass.hassapi as hass

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.detectors import DEFAULT_DETECTOR, make_detector
from ha_automations.lights import brighten_only

START_LEVEL = 6        # ramp starts
END_LEVEL = -6         # ramp ends at MAX_BRIGHTNESS
END_MARGIN = 1         # keep acting this far past END_LEVEL to catch a missed final update
MIN_BRIGHTNESS = 5     # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50


class SunsetFade(hass.Hass):
    def initialize(self):
        self.lamp = self.args["light"]
        a = self.args
        self.detector = make_detector(self, a.get("detector", DEFAULT_DETECTOR))
        self.start_level = a.get("start_level", START_LEVEL)
        self.end_level = a.get("end_level", END_LEVEL)
        self.min_brightness = a.get("min_brightness", MIN_BRIGHTNESS)
        self.max_brightness = a.get("max_brightness", MAX_BRIGHTNESS)
        self.detector.listen(self.lamp_sunset_fade_in)
        self.listen_event(self._on_event, "lamp_sunset_fade_in")
        self.log(f"sunset_fade loaded: {self.lamp}, {self.start_level} to {self.end_level}")

    def _on_event(self, event_type, data, **kwargs):
        self.lamp_sunset_fade_in()

    def evening_fade_progress(self):
        """Ramp progress 0.0-1.0 while the level is in range, else None."""
        level, rising = self.detector.read()
        if level is None or rising is True:
            return None
        if not self.end_level - END_MARGIN <= level <= self.start_level:
            return None
        return progress(level, self.start_level, self.end_level)

    def lamp_sunset_fade_in(self):
        """Fade the lamp toward the current sunset target (no-op outside the window)."""
        p = self.evening_fade_progress()
        if p is None:
            self.log("sunset_fade: outside fade window, nothing to do", level="DEBUG")
            return
        target = round(lerp(self.min_brightness, self.max_brightness, ease_in(p)))
        brighten_only(self, self.lamp, target)
