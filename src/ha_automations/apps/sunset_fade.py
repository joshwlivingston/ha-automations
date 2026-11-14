"""Brighten the lamp as the sun sets.

Ramps from MIN_BRIGHTNESS to MAX_BRIGHTNESS as sun elevation drops from
START_ELEVATION to END_ELEVATION. Never lowers brightness.

Args: `light` (required). Constants below can be overridden with lowercase
args, e.g. `max_brightness: 80`.

Fire the `lamp_sunset_fade_in` event to trigger manually.
"""
import appdaemon.plugins.hass.hassapi as hass

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.lights import brighten_only
from ha_automations.solar import sun_state

START_ELEVATION = 6    # degrees, ramp starts
END_ELEVATION = -6     # degrees, ramp ends at MAX_BRIGHTNESS
MIN_BRIGHTNESS = 5     # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50


class SunsetFade(hass.Hass):
    def initialize(self):
        self.lamp = self.args["light"]
        a = self.args
        self.start_elevation = a.get("start_elevation", START_ELEVATION)
        self.end_elevation = a.get("end_elevation", END_ELEVATION)
        self.min_brightness = a.get("min_brightness", MIN_BRIGHTNESS)
        self.max_brightness = a.get("max_brightness", MAX_BRIGHTNESS)
        self.listen_state(self._on_elevation, "sun.sun", attribute="elevation")
        self.listen_event(self._on_event, "lamp_sunset_fade_in")
        self.log(f"sunset_fade loaded: {self.lamp}, {self.start_elevation}° → {self.end_elevation}°")

    def _on_elevation(self, entity, attribute, old, new, **kwargs):
        self.lamp_sunset_fade_in()

    def _on_event(self, event_type, data, **kwargs):
        self.lamp_sunset_fade_in()

    def evening_fade_progress(self):
        """Ramp progress 0.0-1.0 while elevation is in range, else None."""
        elevation, rising = sun_state(self)
        if elevation is None or rising:
            return None
        if not self.end_elevation - 1 <= elevation <= self.start_elevation:
            return None
        return progress(elevation, self.start_elevation, self.end_elevation)

    def lamp_sunset_fade_in(self):
        """Fade the lamp toward the current sunset target (no-op outside the window)."""
        p = self.evening_fade_progress()
        if p is None:
            self.log("sunset_fade: outside fade window, nothing to do", level="DEBUG")
            return
        target = round(lerp(self.min_brightness, self.max_brightness, ease_in(p)))
        brighten_only(self, self.lamp, target)
