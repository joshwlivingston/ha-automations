from ha_automations.lights import brighten_only, brightness_pct


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
    assert brightness_pct(FakeApp("off", 255), "light.x") == 0


def test_brightness_pct_on():
    assert brightness_pct(FakeApp("on", 255), "light.x") == 100
    assert brightness_pct(FakeApp("on", None), "light.x") == 0


def test_turns_on_from_off():
    app = FakeApp("off")
    brighten_only(app, "light.x", 5, transition=5)
    assert app.calls == [
        ("light/turn_on", {"entity_id": "light.x", "brightness_pct": 5, "transition": 5})
    ]


def test_brightens_when_target_higher():
    app = FakeApp("on", 51)  # 20%
    brighten_only(app, "light.x", 30)
    assert app.calls[0][1]["brightness_pct"] == 30


def test_never_dims():
    app = FakeApp("on", 128)  # ~50%
    brighten_only(app, "light.x", 30)
    brighten_only(app, "light.x", 50)
    assert app.calls == []
