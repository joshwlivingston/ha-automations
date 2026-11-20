"""Fades that set a Light from a Detector's level. No Home Assistant imports.

Levels are in the detector's units.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from ha_automations.curves import ease_in, ease_out_log, lerp, progress
from ha_automations.detectors import Detector
from ha_automations.lights import Light
from ha_automations.store import Store

MIN_BRIGHTNESS = 0
"""Default brightness when the light turns on, percent."""
MAX_BRIGHTNESS = 100
"""Default brightness at to_level, percent."""
RAMP_TRANSITION = 60
"""Seconds each brightness step takes."""
ON_TRANSITION = 5
"""Seconds the first step takes after start() starts the fade."""
OFF_TRANSITION = 300
"""Default seconds the light takes to fade off."""
END_MARGIN = 1
"""How far past to_level the fade keeps acting, to catch a missed final update."""
RESTORE_MAX_AGE = 12 * 3600  # seconds; a fade started longer ago is not restored, so it never resumes the next day


def brightness_at(p: float, lo: int, hi: int) -> int:
    """Eased brightness between `lo` and `hi` at progress `p`."""
    return round(lerp(lo, hi, ease_in(p)))


def dimmed_at(p: float, hi: int) -> int:
    """Brightness at progress `p` of a dim from `hi` to 0, on a -log curve."""
    return round(lerp(0, hi, ease_out_log(p)))


def brighten_only(light: Light, pct: int, transition: float = RAMP_TRANSITION) -> bool:
    """Raise `light` to `pct`, never lower it, so manual increases stick. True if raised."""
    if pct > light.brightness_pct():
        light.turn_on(pct, transition)
        return True
    return False


def _quiet(msg: str) -> None:
    pass


def line(action: str, reason: str, detail: str = "") -> str:
    """One log line: action, reason and optional detail."""
    return f"{action}: {reason}; {detail}" if detail else f"{action}: {reason}"


@dataclass
class LightFade:
    """Brighten a light as the level moves from from_level to to_level.

    The fade runs in whichever direction from_level to to_level points, and
    ignores readings while the detector reports the opposite direction.
    Brightness goes from min_brightness to max_brightness, never lowered.
    With `dim`, brightness then goes from max_brightness to 0 between
    to_level and off_level, never raised. Once the level reaches off_level,
    if set, the light turns off. stop() turns it off at any time.

    Untriggered fades act whenever the level is between from_level and
    to_level. Triggered fades do nothing until start() finds the level short of
    from_level, then ramp from that level until off_level.

    A triggered fade saves its start level in `store`, if set, and restore()
    resumes it from there after a restart.
    """

    detector: Detector
    """Source of the level."""
    light: Light
    """Light to set."""
    from_level: float
    """Level where the light turns on."""
    to_level: float
    """Level where the light reaches max_brightness."""
    off_level: float | None = None
    """Level where the light turns off. None means it stays on."""
    min_brightness: int = MIN_BRIGHTNESS
    """Brightness at from_level, percent."""
    max_brightness: int = MAX_BRIGHTNESS
    """Brightness at to_level, percent."""
    off_transition: float = OFF_TRANSITION
    """Seconds the light takes to fade off."""
    dim: bool = False
    """Dim from max_brightness at to_level to off at off_level. Needs off_level."""
    triggered: bool = False
    """Wait for start() before acting."""
    log: Callable[[str], None] = _quiet
    """Gets one line per change to the light or to whether the fade is started."""
    debug: Callable[[str], None] = _quiet
    """Gets one line per update that did nothing."""
    store: Store | None = None
    """Where a triggered fade saves its start level. None means it is not saved."""
    now: Callable[[], float] = time.time
    """Current time in seconds, saved with the start level."""
    ramp_from: float | None = field(default=None, init=False)
    """Level the ramp starts from. None while a triggered fade is not started."""
    # True while a brighter manual level is being kept, so it is logged once.
    _kept: bool = field(default=False, init=False, repr=False)
    # True while the level is inside the ramp, so leaving it is logged once.
    _in_ramp: bool = field(default=False, init=False, repr=False)
    # Brightness this fade last set, to tell a manual increase while dimming. None if unknown.
    _set_pct: int | None = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self.from_level == self.to_level:
            raise ValueError("from_level and to_level must differ")
        if self.dim and self.off_level is None:
            raise ValueError("dim needs off_level")
        if not self.triggered:
            self.ramp_from = self.from_level

    @property
    def rising(self) -> bool:
        """True if to_level is above from_level."""
        return self.to_level > self.from_level

    def _ahead(self, a: float, b: float) -> bool:
        """True if level `a` is further along the fade than level `b`."""
        return a > b if self.rising else a < b

    def _with_fade(self, rising: bool | None) -> bool:
        return rising is None or rising == self.rising

    def _at(self, level: float) -> str:
        """A reading as a log field, e.g. sun=-4.3deg."""
        return f"{self.detector.label}={level:.1f}{self.detector.unit}"

    def _u(self, name: str, level: float) -> str:
        """A configured level as a log field, e.g. from_level=-6deg."""
        return f"{name}={level:g}{self.detector.unit}"

    def _skip(self, level: float | None, rising: bool | None) -> str | None:
        """Why a reading is unusable, or None if it is usable."""
        if level is None:
            return f"no {self.detector.label} reading"
        if not self._with_fade(rising):
            return f"{self.detector.label} {'rising' if rising else 'falling'}"
        return None

    def start(self) -> bool:
        """Start a triggered fade if the level is short of from_level, then update.

        False if nothing was done.
        """
        if not self.triggered:
            return self.update(explain=True)
        level, rising = self.detector.read()
        self._set_start(None)
        if reason := self._skip(level, rising):
            self.log(line("skip start", reason, self._at(level) if level is not None else ""))
            return False
        assert level is not None
        if not self._ahead(self.from_level, level):
            detail = f"{self._at(level)} {self._u('from_level', self.from_level)}"
            self.log(line("skip start", "past from_level", detail))
            return False
        self._set_start(level)
        self._kept = False
        off = f" {self._u('off_level', self.off_level)}" if self.off_level is not None else ""
        detail = f"{self._at(level)} {self._u('to_level', self.to_level)}{off}"
        self.log(line("start", "short of from_level", detail))
        return self.update(ON_TRANSITION, explain=True)

    def restore(self) -> bool:
        """Resume a triggered fade from `store`, if started within RESTORE_MAX_AGE, then update.

        Run once on load. False if nothing was done.
        """
        if self.triggered and self.store is not None:
            ramp_from = self._restored_level(self.store)
            if ramp_from is not None:
                self.ramp_from = ramp_from
                self.log(line("resume", "started before restart", self._u("ramp_from", ramp_from)))
        return self.update(explain=True)

    def _restored_level(self, store: Store) -> float | None:
        """The start level in `store` if still usable, else None. Clears an unusable record."""
        record = store.load()
        if record is None:
            self.log(line("skip resume", "no saved fade"))
            return None
        try:
            ramp_from, started_at = float(record["ramp_from"]), float(record["started_at"])
        except (KeyError, TypeError, ValueError):
            reason, detail = "unreadable record", str(store)
        else:
            if 0 <= self.now() - started_at <= RESTORE_MAX_AGE:
                return ramp_from
            reason, detail = "started too long ago", self._u("ramp_from", ramp_from)
        self.log(line("skip resume", reason, detail))
        store.save(None)
        return None

    def _set_start(self, level: float | None) -> None:
        """Set the start level and save it with the time in `store` if it changed."""
        if level == self.ramp_from:
            return
        self.ramp_from = level
        if self.store is not None:
            self.store.save(None if level is None else {"ramp_from": level, "started_at": self.now()})

    def stop(self, reason: str) -> bool:
        """Turn the light off and end a triggered fade. False if already off."""
        return self._turn_off(reason, "", self.log)

    def _turn_off(self, reason: str, at: str, noop: Callable[[str], None]) -> bool:
        """Turn the light off if on, then end a triggered fade. False if already off."""
        self._in_ramp = False
        where = f"{self.light} {at}" if at else str(self.light)
        turned_off = self.light.brightness_pct() > 0
        if turned_off:
            self.light.turn_off(self.off_transition)
            self.log(line("off", reason, f"{where} transition={self.off_transition:g}s"))
        else:
            noop(line("skip", "already off", where))
        if self.triggered and self.ramp_from is not None:
            self._set_start(None)
            self.log(line("end", reason, "until next start trigger"))
        return turned_off

    def update(self, transition: float = RAMP_TRANSITION, explain: bool = False) -> bool:
        """Set the light for the current level. False if outside the fade.

        Lines for updates that do nothing go to `debug`, or to `log` if `explain`.
        """
        noop = self.log if explain else self.debug
        level, rising = self.detector.read()
        if self.ramp_from is None:
            noop(line("skip", "waiting for start trigger"))
            return False
        if reason := self._skip(level, rising):
            noop(line("skip", reason, self._at(level) if level is not None else ""))
            return False
        assert level is not None
        if self.off_level is not None and not self._ahead(self.off_level, level):
            at = f"{self._at(level)} {self._u('off_level', self.off_level)}"
            self._turn_off("reached off_level", at, noop)
            return True
        if self.dim and self._ahead(level, self.to_level):
            return self._dim(level, transition, noop)
        end = self.to_level + (END_MARGIN if self.rising else -END_MARGIN)
        if self._ahead(self.ramp_from, level) or self._ahead(level, end):
            if not self._ahead(level, end):
                detail = f"{self._at(level)} {self._u('ramp_from', self.ramp_from)}"
                noop(line("skip", "short of ramp_from", detail))
            elif self._in_ramp:
                detail = f"{self._at(level)} {self._u('to_level', self.to_level)}"
                self.log(line("ramp done", "past to_level", detail))
            else:
                detail = f"{self._at(level)} {self._u('to_level', self.to_level)}"
                noop(line("skip", "past to_level", detail))
            self._in_ramp = False
            return False
        self._in_ramp = True
        p = progress(level, self.ramp_from, self.to_level)
        pct = brightness_at(p, self.min_brightness, self.max_brightness)
        if brighten_only(self.light, pct, transition):
            self._kept = False
            self._set_pct = pct
            detail = f"{self.light} {pct}% {self._at(level)} transition={transition:g}s"
            self.log(line("set", f"ramp {p:.0%}", detail))
        elif not self._kept and (now := self.light.brightness_pct()) > pct:
            self._kept = True
            detail = f"{self.light} {now}% target={pct}% {self._at(level)}"
            self.log(line("keep", "above target", detail))
        else:
            detail = f"{self.light} {self.light.brightness_pct()}% target={pct}% {self._at(level)}"
            noop(line("skip", "at or above target", detail))
        return True

    def _dim(self, level: float, transition: float, noop: Callable[[str], None]) -> bool:
        """Lower the light toward its dim brightness at `level`. Leaves it off or raised by hand."""
        assert self.off_level is not None
        self._in_ramp = False
        p = progress(level, self.to_level, self.off_level)
        pct = max(1, dimmed_at(p, self.max_brightness))
        now = self.light.brightness_pct()
        raised = self._set_pct is not None and now > self._set_pct + 1
        if 0 < now and pct < now and not raised:
            self.light.turn_on(pct, transition)
            self._kept = False
            self._set_pct = pct
            detail = f"{self.light} {pct}% {self._at(level)} transition={transition:g}s"
            self.log(line("set", f"dim {p:.0%}", detail))
        elif raised and not self._kept:
            self._kept = True
            detail = f"{self.light} {now}% target={pct}% {self._at(level)}"
            self.log(line("keep", "raised by hand", detail))
        else:
            reason = "off" if now == 0 else "at or below target"
            noop(line("skip", reason, f"{self.light} {now}% target={pct}% {self._at(level)}"))
        return True
