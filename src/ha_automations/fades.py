"""Fades that set a Light from a Detector's level. No Home Assistant imports.

Levels are in the detector's units.
"""
from dataclasses import dataclass, field

from ha_automations.curves import ease_in, lerp, progress
from ha_automations.detectors import Detector
from ha_automations.lights import Light

MIN_BRIGHTNESS = 5        # lowest level the bulb visibly glows at
MAX_BRIGHTNESS = 50
RAMP_TRANSITION = 60      # seconds, per brightness step
ON_TRANSITION = 5         # seconds, first step after start() arms the fade
OFF_TRANSITION = 300      # seconds, fade-out at off_level
END_MARGIN = 1            # keep acting this far past to_level to catch a missed final update


def brightness_at(p: float, lo: int, hi: int) -> int:
    """Eased brightness between `lo` and `hi` at progress `p`."""
    return round(lerp(lo, hi, ease_in(p)))


def brighten_only(light: Light, pct: int, transition: float = RAMP_TRANSITION) -> None:
    """Raise `light` to `pct`, never lower it, so manual increases stick."""
    if pct > light.brightness_pct():
        light.turn_on(pct, transition)


@dataclass
class LightFade:
    """Brighten a light as the level moves from from_level to to_level.

    The fade runs in whichever direction from_level to to_level points, and
    ignores readings while the detector reports the opposite direction.
    Brightness goes from min_brightness to max_brightness, never lowered.
    Once the level reaches off_level, if set, the light turns off.

    Untriggered fades act whenever the level is between from_level and
    to_level. Triggered fades do nothing until start() finds the level short of
    from_level, then ramp from that level until off_level.
    """

    detector: Detector
    light: Light
    from_level: float
    to_level: float
    off_level: float | None = None
    min_brightness: int = MIN_BRIGHTNESS
    max_brightness: int = MAX_BRIGHTNESS
    off_transition: float = OFF_TRANSITION
    triggered: bool = False
    # Level the ramp starts from; None while a triggered fade is not armed.
    ramp_from: float | None = field(default=None, init=False)

    def __post_init__(self):
        if self.from_level == self.to_level:
            raise ValueError("from_level and to_level must differ")
        if not self.triggered:
            self.ramp_from = self.from_level

    @property
    def rising(self) -> bool:
        return self.to_level > self.from_level

    def _ahead(self, a: float, b: float) -> bool:
        """True if level `a` is further along the fade than level `b`."""
        return a > b if self.rising else a < b

    def _with_fade(self, rising: bool | None) -> bool:
        return rising is None or rising == self.rising

    def start(self) -> bool:
        """Arm a triggered fade if the level is short of from_level, then update.

        False if nothing was done.
        """
        if not self.triggered:
            return self.update()
        level, rising = self.detector.read()
        if level is None or not self._with_fade(rising) or not self._ahead(self.from_level, level):
            self.ramp_from = None
            return False
        self.ramp_from = level
        return self.update(ON_TRANSITION)

    def update(self, transition: float = RAMP_TRANSITION) -> bool:
        """Set the light for the current level. False if outside the fade."""
        level, rising = self.detector.read()
        if level is None or self.ramp_from is None or not self._with_fade(rising):
            return False
        if self.off_level is not None and not self._ahead(self.off_level, level):
            if self.triggered:
                self.ramp_from = None
            if self.light.brightness_pct() > 0:
                self.light.turn_off(self.off_transition)
            return True
        end = self.to_level + (END_MARGIN if self.rising else -END_MARGIN)
        if self._ahead(self.ramp_from, level) or self._ahead(level, end):
            return False
        p = progress(level, self.ramp_from, self.to_level)
        brighten_only(self.light, brightness_at(p, self.min_brightness, self.max_brightness), transition)
        return True
