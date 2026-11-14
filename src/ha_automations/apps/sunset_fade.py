"""Living room lamp – gentle fade-in at sunset.

Ramps the lamp from MIN to MAX brightness as the sun drops from
START_ELEVATION (pre-dusk, ~30 min before sunset) to END_ELEVATION
(civil dusk). Ease-in curve; never dims.

Manual trigger: fire the `lamp_sunset_fade_in` event (Developer Tools → Events).
"""
import appdaemon.plugins.hass.hassapi as hass

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.lights import brighten_only
from ha_automations.solar import sun_state

LAMP = "light.your_lamp"
START_ELEVATION = 6    # degrees – fade begins
END_ELEVATION = -6     # degrees – full target reached
MIN_BRIGHTNESS = 5     # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50


class SunsetFade(hass.Hass):
    def initialize(self):
        self.listen_state(self._on_elevation, "sun.sun", attribute="elevation")
        self.listen_event(self._on_event, "lamp_sunset_fade_in")
        self.log(f"sunset_fade loaded – {LAMP}, {START_ELEVATION}° → {END_ELEVATION}°")

    def _on_elevation(self, entity, attribute, old, new, **kwargs):
        self.lamp_sunset_fade_in()

    def _on_event(self, event_type, data, **kwargs):
        self.lamp_sunset_fade_in()

    def evening_fade_progress(self):
        """0.0 → 1.0 while the sun is setting through the window, else None."""
        elevation, rising = sun_state(self)
        if elevation is None or rising:
            return None
        if not END_ELEVATION - 1 <= elevation <= START_ELEVATION:
            return None
        return progress(elevation, START_ELEVATION, END_ELEVATION)

    def lamp_sunset_fade_in(self):
        """Fade the lamp toward the current sunset target (no-op outside the window)."""
        p = self.evening_fade_progress()
        if p is None:
            self.log("sunset_fade: outside fade window, nothing to do", level="DEBUG")
            return
        target = round(lerp(MIN_BRIGHTNESS, MAX_BRIGHTNESS, ease_in(p)))
        brighten_only(self, LAMP, target)
