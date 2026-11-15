"""Fades that set a Light from a Detector's level. No Home Assistant imports.

Levels are in the detector's units.
"""
from collections.abc import Callable
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


def brighten_only(light: Light, pct: int, transition: float = RAMP_TRANSITION) -> bool:
    """Raise `light` to `pct`, never lower it, so manual increases stick. True if raised."""
    if pct > light.brightness_pct():
        light.turn_on(pct, transition)
        return True
    return False


def _quiet(msg: str) -> None:
    pass


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

    `log` gets one line per change to the light or arming; `debug` gets
    updates that did nothing.
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
    log: Callable[[str], None] = _quiet
    debug: Callable[[str], None] = _quiet
    # Level the ramp starts from; None while a triggered fade is not armed.
    ramp_from: float | None = field(default=None, init=False)
    # True while a brighter manual level is being kept, so it is logged once.
    _kept: bool = field(default=False, init=False, repr=False)
    # True while the level is inside the ramp, so leaving it is logged once.
    _in_ramp: bool = field(default=False, init=False, repr=False)

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

    def _at(self, level: float) -> str:
        """`level` with the detector's label and unit, e.g. sun at -4.3°."""
        return f"{self.detector.label} at {level:.1f}{self.detector.unit}"

    def _skip(self, level: float | None, rising: bool | None) -> str | None:
        """Why a reading is unusable, or None if it is usable."""
        if level is None:
            return f"no {self.detector.label} reading"
        if not self._with_fade(rising):
            return f"{self.detector.label} is {'rising' if rising else 'falling'}"
        return None

    def start(self) -> bool:
        """Arm a triggered fade if the level is short of from_level, then update.

        False if nothing was done.
        """
        if not self.triggered:
            return self.update(explain=True)
        level, rising = self.detector.read()
        self.ramp_from = None
        if reason := self._skip(level, rising):
            self.log(f"Not armed: {reason}.")
            return False
        assert level is not None
        if not self._ahead(self.from_level, level):
            self.log(f"Not armed: {self._at(level)}, already past {self.from_level:g}.")
            return False
        self.ramp_from = level
        self._kept = False
        self.log(f"Armed at {level:.1f}{self.detector.unit}. Ramp runs to {self.to_level:g}.")
        return self.update(ON_TRANSITION, explain=True)

    def update(self, transition: float = RAMP_TRANSITION, explain: bool = False) -> bool:
        """Set the light for the current level. False if outside the fade.

        Lines for updates that do nothing go to `debug`, or to `log` if `explain`.
        """
        noop = self.log if explain else self.debug
        level, rising = self.detector.read()
        if self.ramp_from is None:
            noop("Ignored: not armed.")
            return False
        if reason := self._skip(level, rising):
            noop(f"Ignored: {reason}.")
            return False
        assert level is not None
        if self.off_level is not None and not self._ahead(self.off_level, level):
            self._in_ramp = False
            if self.light.brightness_pct() > 0:
                self.light.turn_off(self.off_transition)
                self.log(f"{self.light} off over {self.off_transition:g} s; {self._at(level)}.")
            else:
                noop(f"{self.light} already off; {self._at(level)}.")
            if self.triggered:
                self.ramp_from = None
                self.log("Disarmed until the next start.")
            return True
        end = self.to_level + (END_MARGIN if self.rising else -END_MARGIN)
        if self._ahead(self.ramp_from, level) or self._ahead(level, end):
            if not self._ahead(level, end):
                noop(f"Ignored: {self._at(level)}, short of {self.ramp_from:g}.")
            elif self._in_ramp:
                self.log(f"Ramp done; {self._at(level)}.")
            else:
                noop(f"Ignored: {self._at(level)}, past {self.to_level:g}.")
            self._in_ramp = False
            return False
        self._in_ramp = True
        p = progress(level, self.ramp_from, self.to_level)
        pct = brightness_at(p, self.min_brightness, self.max_brightness)
        if brighten_only(self.light, pct, transition):
            self._kept = False
            self.log(f"{self.light} to {pct}%, {self._at(level)}, {p:.0%} of the way.")
        elif not self._kept and (now := self.light.brightness_pct()) > pct:
            self._kept = True
            self.log(f"Kept {self.light} at {now}%; fade wanted {pct}%. Fades never dim.")
        else:
            noop(f"Left {self.light} alone; fade wants {pct}%.")
        return True
