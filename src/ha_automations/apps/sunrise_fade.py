"""Living room lamp – dim-on at 5:45 when it's dark, brighten with the dawn.

At 05:45, if the sun is still below DARK_ELEVATION (pitch black), the lamp
comes on at MIN_BRIGHTNESS. As the sun rises it ramps (ease-in) to
MAX_BRIGHTNESS at FULL_ELEVATION, then fades off at OFF_ELEVATION once
daylight takes over. If it's already light at 05:45 (summer), nothing happens.
Never dims during the ramp, so manual brightening is respected.

Manual trigger: fire the `lamp_sunrise_on` event (Developer Tools → Events).
"""
import appdaemon.plugins.hass.hassapi as hass

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.lights import brighten_only
from ha_automations.solar import sun_state

LAMP = "light.your_lamp"
DARK_ELEVATION = -6    # degrees – below civil dawn counts as "pitch black"
FULL_ELEVATION = 0     # degrees – MAX reached at sunrise
OFF_ELEVATION = 4      # degrees – daylight, lamp no longer needed
MIN_BRIGHTNESS = 5     # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50
OFF_TRANSITION = 300   # seconds – slow fade out
ON_TIME = "05:45:00"


class SunriseFade(hass.Hass):
    def initialize(self):
        # Elevation at ON_TIME when we switched the lamp on; None = not running this morning.
        self._start_elevation = None
        self.run_daily(self._on_time, ON_TIME)
        self.listen_state(self._on_elevation, "sun.sun", attribute="elevation")
        self.listen_event(self._on_event, "lamp_sunrise_on")
        self.log(f"sunrise_fade loaded – {LAMP}, on at {ON_TIME} if < {DARK_ELEVATION}°, off at {OFF_ELEVATION}°")

    def _on_time(self, **kwargs):
        self.lamp_sunrise_on()

    def _on_event(self, event_type, data, **kwargs):
        self.lamp_sunrise_on()

    def _on_elevation(self, entity, attribute, old, new, **kwargs):
        self.lamp_sunrise_ramp()

    def lamp_sunrise_on(self):
        """Switch the lamp on dimly if it's still dark."""
        elevation, rising = sun_state(self)
        if elevation is None or not rising or elevation >= DARK_ELEVATION:
            self.log(f"sunrise_fade: already light enough ({elevation}°), skipping")
            self._start_elevation = None
            return
        self._start_elevation = elevation
        brighten_only(self, LAMP, MIN_BRIGHTNESS, transition=5)

    def lamp_sunrise_ramp(self):
        """Brighten with the rising sun, then turn off once it's daylight."""
        if self._start_elevation is None:
            return
        elevation, rising = sun_state(self)
        if elevation is None:
            return
        if elevation >= OFF_ELEVATION or not rising:
            self._start_elevation = None
            self.call_service("light/turn_off", entity_id=LAMP, transition=OFF_TRANSITION)
            return
        p = progress(elevation, self._start_elevation, FULL_ELEVATION)
        brighten_only(self, LAMP, round(lerp(MIN_BRIGHTNESS, MAX_BRIGHTNESS, ease_in(p))))
