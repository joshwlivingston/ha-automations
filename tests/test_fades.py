import pytest

from ha_automations.detectors import Reading
from ha_automations.fades import (
    ON_TRANSITION,
    RESTORE_MAX_AGE,
    LightFade,
    brighten_only,
    brightness_at,
    dimmed_at,
)

# Fixed range so tests do not depend on the default brightness range.
LO, HI = 5, 50
RANGE = {"min_brightness": LO, "max_brightness": HI}


class FakeDetector:
    label = "sun"
    unit = "deg"

    def __init__(self, level=None, rising=None):
        self.level = level
        self.rising = rising

    def read(self):
        return Reading(self.level, self.rising)

    def listen(self, callback):
        pass


class FakeLight:
    def __init__(self, pct=0):
        self.pct = pct
        self.calls = []

    def __str__(self):
        return "light.x"

    def brightness_pct(self):
        return self.pct

    def turn_on(self, pct, transition):
        self.pct = pct
        self.calls.append(("on", pct, transition))

    def turn_off(self, transition):
        self.pct = 0
        self.calls.append(("off", transition))


def falling(det, light):
    return LightFade(det, light, from_level=6, to_level=-6, min_brightness=LO, max_brightness=HI)


def rising(det, light):
    return LightFade(det, light, from_level=-6, to_level=0, off_level=4, triggered=True, min_brightness=LO, max_brightness=HI)


def test_brighten_only_raises():
    light = FakeLight(20)
    brighten_only(light, 30, transition=7)
    assert light.calls == [("on", 30, 7)]


def test_brighten_only_never_dims():
    light = FakeLight(50)
    brighten_only(light, 30)
    brighten_only(light, 50)
    assert light.calls == []


def test_equal_levels_rejected():
    with pytest.raises(ValueError):
        LightFade(FakeDetector(), FakeLight(), from_level=1, to_level=1)


def test_falling_brightens_through_window():
    det, light = FakeDetector(6, False), FakeLight()
    fade = falling(det, light)
    assert fade.update()
    assert light.pct == LO
    det.level = -6
    assert fade.update()
    assert light.pct == HI


def test_falling_ignores_wrong_direction_and_out_of_range():
    light = FakeLight()
    assert not falling(FakeDetector(0, True), light).update()
    assert not falling(FakeDetector(10, False), light).update()
    assert not falling(FakeDetector(-20, False), light).update()
    assert not falling(FakeDetector(None, False), light).update()
    assert light.calls == []


def test_falling_acts_within_end_margin():
    light = FakeLight()
    assert falling(FakeDetector(-6.5, False), light).update()
    assert light.pct == HI


def test_untriggered_start_is_update():
    light = FakeLight()
    assert falling(FakeDetector(0, False), light).start()
    assert light.pct > LO


def test_triggered_does_nothing_until_started():
    light = FakeLight()
    assert not rising(FakeDetector(-10, True), light).update()
    assert light.calls == []


def test_triggered_skips_when_already_light():
    light = FakeLight()
    fade = rising(FakeDetector(-2, True), light)
    assert not fade.start()
    assert not fade.update()
    assert light.calls == []


def test_triggered_full_cycle():
    det, light = FakeDetector(-10, True), FakeLight()
    fade = rising(det, light)
    assert fade.start()
    assert light.calls == [("on", LO, ON_TRANSITION)]
    det.level = 0
    fade.update()
    assert light.pct == HI
    det.level = 4
    fade.update()
    assert light.calls[-1] == ("off", fade.off_transition)
    assert fade.ramp_from is None
    det.level = 5
    assert not fade.update()


def test_dimmed_at_decays_smoothly():
    assert dimmed_at(0, 100) == 100
    assert dimmed_at(0.5, 100) == 77
    assert dimmed_at(1, 100) == 0


def test_decay_ramp_mirrors_dim():
    for p in (0, 0.25, 0.5, 0.75, 1):
        assert brightness_at(p, 0, 100, "decay") == dimmed_at(1 - p, 100)


def dimming(det, light):
    return LightFade(det, light, from_level=-6, to_level=0, off_level=12, dim=True, max_brightness=100)


def test_dim_lowers_then_turns_off():
    det, light = FakeDetector(0, True), FakeLight()
    fade = dimming(det, light)
    fade.update()
    assert light.pct == 100
    det.level = 6
    fade.update()
    assert light.pct == 77
    det.level = 11.9
    fade.update()
    assert light.pct == 1
    det.level = 12
    fade.update()
    assert light.calls[-1] == ("off", fade.off_transition)


def test_dim_leaves_light_off_or_raised_by_hand():
    det, light = FakeDetector(0, True), FakeLight()
    fade = dimming(det, light)
    fade.update()
    det.level = 6
    fade.update()
    light.pct = 90
    det.level = 9
    fade.update()
    assert light.pct == 90
    light.pct = 0
    det.level = 11
    fade.update()
    assert light.pct == 0


def test_dim_by_clock_from_to_level_to_dim_end():
    det, light = FakeDetector(1, False), FakeLight()
    clock = [1000.0]
    fade = LightFade(
        det, light, from_level=12, to_level=0, dim=True, max_brightness=100,
        ramp_curve="decay", dim_end=lambda t: t + 3600, now=lambda: clock[0],
    )
    fade.update()
    assert light.pct == 100
    det.level = -1
    fade.update()
    assert light.pct == 100
    clock[0] += 1800
    fade.update()
    assert light.pct == 77
    det.level = -10
    clock[0] += 1800
    fade.update()
    assert light.pct == 1


def test_dim_needs_off_level():
    with pytest.raises(ValueError, match="dim needs off_level"):
        LightFade(FakeDetector(), FakeLight(), from_level=-6, to_level=0, dim=True)


def test_untriggered_off_level_turns_off_once():
    det, light = FakeDetector(5, True), FakeLight(40)
    fade = LightFade(det, light, from_level=-6, to_level=0, off_level=4)
    fade.update()
    fade.update()
    assert light.calls == [("off", fade.off_transition)]


def test_stop_turns_off_and_ends():
    det, light = FakeDetector(-10, True), FakeLight()
    fade = rising(det, light)
    fade.start()
    assert fade.stop("reached off_time")
    assert light.calls[-1] == ("off", fade.off_transition)
    assert fade.ramp_from is None
    det.level = -4
    assert not fade.update()
    assert light.pct == 0


def test_stop_when_off_does_nothing():
    light = FakeLight()
    fade = falling(FakeDetector(-20, False), light)
    assert not fade.stop("reached off_time")
    assert light.calls == []
    assert fade.ramp_from == fade.from_level


class FakeStore:
    def __init__(self, record=None):
        self.record = record

    def __str__(self):
        return "store"

    def load(self):
        return self.record

    def save(self, record):
        self.record = record


NOW = 1000.0


def started(ramp_from, age=0):
    return {"ramp_from": ramp_from, "started_at": NOW - age}


def stored(fade, store):
    fade.store, fade.now = store, lambda: NOW
    return fade


def test_store_follows_start():
    det, light, store = FakeDetector(-10, True), FakeLight(), FakeStore()
    fade = stored(rising(det, light), store)
    fade.start()
    assert store.record == started(-10)
    det.level = 4
    fade.update()
    assert store.record is None


def test_restore_resumes_ramp():
    det, light = FakeDetector(-3, True), FakeLight()
    fade = stored(rising(det, light), FakeStore(started(-10, age=RESTORE_MAX_AGE)))
    assert fade.restore()
    assert fade.ramp_from == -10
    assert LO < light.pct < HI


def test_restore_past_off_level_turns_off():
    det, light, store = FakeDetector(6, True), FakeLight(40), FakeStore(started(-10))
    fade = stored(rising(det, light), store)
    fade.restore()
    assert light.calls == [("off", fade.off_transition)]
    assert store.record is None


@pytest.mark.parametrize(
    "record",
    [None, started(-10, age=RESTORE_MAX_AGE + 1), started(-10, age=-1), {"ramp_from": -10}, {"ramp_from": "x", "started_at": NOW}],
)
def test_restore_ignores_missing_old_or_bad_record(record):
    light, store = FakeLight(), FakeStore(record)
    fade = stored(rising(FakeDetector(-3, True), light), store)
    assert not fade.restore()
    assert fade.ramp_from is None
    assert store.record is None
    assert light.calls == []


def test_restore_untriggered_updates():
    light = FakeLight()
    assert falling(FakeDetector(0, False), light).restore()
    assert light.pct > LO


def test_brighten_only_reports_change():
    assert brighten_only(FakeLight(20), 30)
    assert not brighten_only(FakeLight(50), 30)


class Script:
    """Drives a fade step by step and records a transcript for snapshots.

    Each step writes a `>` line naming the call, then the log lines it caused,
    indented and tagged INFO or DEBUG.
    """

    def __init__(self, level, rising, **fade_args):
        self.det, self.light, self.lines = FakeDetector(level, rising), FakeLight(), []
        self.fade = LightFade(
            self.det,
            self.light,
            log=lambda m: self.lines.append(f"  INFO  {m}"),
            debug=lambda m: self.lines.append(f"  DEBUG {m}"),
            **fade_args,
        )

    def start(self):
        self.lines.append("> start()")
        self.fade.start()

    def sun(self, level, rising=None):
        """Move the sun and run the update its state listener would."""
        self.det.level = level
        if rising is not None:
            self.det.rising = rising
        self.lines.append(f"> sun({level}{'' if rising is None else f', rising={rising}'})")
        self.fade.update()

    def stop(self):
        self.lines.append("> stop()")
        self.fade.stop("reached off_time")

    def manual(self, pct):
        """Set the light by hand; logs nothing."""
        self.light.pct = pct
        self.lines.append(f"> manual({pct})")

    def __str__(self):
        return "\n".join(self.lines)


SUNRISE = {"from_level": -6, "to_level": 0, "off_level": 4, "triggered": True, **RANGE}
SUNSET = {"from_level": 6, "to_level": -6, **RANGE}


def test_sunrise_morning_log(snapshot):
    s = Script(-12, True, **SUNRISE)
    s.sun(-12)
    s.start()
    s.sun(-8)
    s.sun(-4)
    s.manual(80)
    for level in (-3.9, -2, 0, 0.5, 1.5, 2, 4.2, 6):
        s.sun(level)
    assert str(s) == snapshot


def test_sunrise_dim_log(snapshot):
    s = Script(-8, True, from_level=-6, to_level=0, off_level=12, dim=True, triggered=True, **RANGE)
    s.start()
    for level in (0, 3, 6):
        s.sun(level)
    s.manual(45)
    for level in (9, 12.1):
        s.sun(level)
    assert str(s) == snapshot


def test_sunrise_start_skip_log(snapshot):
    lines = []
    for level, rising in [(-2, True), (-10, False), (None, None)]:
        s = Script(level, rising, **SUNRISE)
        s.lines.append(f"# sun at {level}, rising={rising}")
        s.start()
        lines += s.lines
    assert "\n".join(lines) == snapshot


def test_sunset_evening_log(snapshot):
    s = Script(12, True, **SUNSET)
    s.start()
    s.sun(12, rising=False)
    for level in (6, 0, -6, -6.5, -8):
        s.sun(level)
    assert str(s) == snapshot


def test_restore_log(snapshot):
    s = Script(-3, True, store=FakeStore(started(-10)), now=lambda: NOW, **SUNRISE)
    s.lines.append("> restore()")
    s.fade.restore()
    s.sun(4.2)
    old = Script(-3, True, store=FakeStore(started(-10, age=RESTORE_MAX_AGE + 1)), now=lambda: NOW, **SUNRISE)
    old.lines.append("> restore() # started too long ago")
    old.fade.restore()
    none = Script(4.2, True, store=FakeStore(None), now=lambda: NOW, **SUNRISE)
    none.lines.append("> restore() # nothing saved")
    none.fade.restore()
    assert f"{s}\n{old}\n{none}" == snapshot


def test_off_time_log(snapshot):
    sunset = Script(-8, False, **SUNSET)
    sunset.lines.append("# sunset, light on after the fade")
    sunset.manual(50)
    sunset.stop()
    sunset.stop()
    sunrise = Script(-10, True, **SUNRISE)
    sunrise.lines.append("# sunrise, started")
    sunrise.start()
    sunrise.stop()
    sunrise.sun(-4)
    assert f"{sunset}\n{sunrise}" == snapshot
