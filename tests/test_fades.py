import pytest

from ha_automations.detectors import Reading
from ha_automations.fades import (
    MAX_BRIGHTNESS,
    MIN_BRIGHTNESS,
    ON_TRANSITION,
    LightFade,
    brighten_only,
)


class FakeDetector:
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

    def brightness_pct(self):
        return self.pct

    def turn_on(self, pct, transition):
        self.pct = pct
        self.calls.append(("on", pct, transition))

    def turn_off(self, transition):
        self.pct = 0
        self.calls.append(("off", transition))


def falling(det, light):
    return LightFade(det, light, from_level=6, to_level=-6)


def rising(det, light):
    return LightFade(det, light, from_level=-6, to_level=0, off_level=4, triggered=True)


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
    assert light.pct == MIN_BRIGHTNESS
    det.level = -6
    assert fade.update()
    assert light.pct == MAX_BRIGHTNESS


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
    assert light.pct == MAX_BRIGHTNESS


def test_untriggered_start_is_update():
    light = FakeLight()
    assert falling(FakeDetector(0, False), light).start()
    assert light.pct > MIN_BRIGHTNESS


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
    assert light.calls == [("on", MIN_BRIGHTNESS, ON_TRANSITION)]
    det.level = 0
    fade.update()
    assert light.pct == MAX_BRIGHTNESS
    det.level = 4
    fade.update()
    assert light.calls[-1] == ("off", fade.off_transition)
    assert fade.ramp_from is None
    det.level = 5
    assert not fade.update()


def test_untriggered_off_level_turns_off_once():
    det, light = FakeDetector(5, True), FakeLight(40)
    fade = LightFade(det, light, from_level=-6, to_level=0, off_level=4)
    fade.update()
    fade.update()
    assert light.calls == [("off", fade.off_transition)]
