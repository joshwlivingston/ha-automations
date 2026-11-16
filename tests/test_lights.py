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
        ("light/turn_on", {"entity_id": "light.x", "brightness_pct": 5, "transition": 5})
    ]


def test_turn_off():
    app = FakeApp("on", 255)
    HassLight(app, "light.x").turn_off(300)
    assert app.calls == [("light/turn_off", {"entity_id": "light.x", "transition": 300})]
