from ha_automations.calibrations import Linear
from ha_automations.lights import HassLight


class FakeApp:
    def __init__(self, state="off", brightness=None):
        self.state = state
        self.brightness = brightness
        self.calls = []

    def get_state(self, entity_id, attribute=None):
        return self.brightness if attribute == "brightness" else self.state

    def call_service(self, service, **kwargs):
        self.calls.append((service, kwargs))


def test_brightness_pct_off_is_zero():
    assert HassLight(FakeApp("off", 255), "light.x").brightness_pct() == 0


def test_brightness_pct_on():
    assert HassLight(FakeApp("on", 255), "light.x").brightness_pct() == 100
    assert HassLight(FakeApp("on", None), "light.x").brightness_pct() == 0


def test_turn_on():
    app = FakeApp()
    HassLight(app, "light.x").turn_on(5, 5)
    assert app.calls == [
        ("light/turn_on", {"entity_id": "light.x", "brightness": 13, "transition": 5})
    ]


def test_turn_off():
    app = FakeApp("on", 255)
    HassLight(app, "light.x").turn_off(300)
    assert app.calls == [("light/turn_off", {"entity_id": "light.x", "transition": 300})]



def test_calibrated_light():
    app = FakeApp("on", 205)
    light = HassLight(app, "light.x", Linear(low=27, high=205))
    assert light.brightness_pct() == 100
    light.turn_on(1, 5)
    assert app.calls == [("light/turn_on", {"entity_id": "light.x", "brightness": 27, "transition": 5})]


def test_light_uses_registered_calibration():
    from ha_automations.calibrations import register, unregister

    app = FakeApp()
    light = HassLight(app, "light.reg")
    register("light.reg", Linear(low=27, high=205))
    try:
        light.turn_on(100, 0)
    finally:
        unregister("light.reg")
    light.turn_on(100, 0)
    assert [c[1]["brightness"] for c in app.calls] == [205, 255]
