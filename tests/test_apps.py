import pytest

from ha_automations.apps.light_fade import LightFadeApp
from ha_automations.apps.sunrise_fade import SunriseFade
from ha_automations.apps.sunset_fade import SunsetFade


def build(cls, args, app_name="test"):
    """Run `cls.initialize` against stubbed AppDaemon calls, skipping Hass.__init__."""

    class Stub(cls):
        name = app_name  # pyright: ignore[reportAssignmentType]

        def log(self, *a, **k):
            pass

        def run_daily(self, callback, time):
            self.daily.append(time)

        def listen_event(self, callback, event):
            self.events.append(event)

        def listen_state(self, *a, **k):
            pass

    app = Stub.__new__(Stub)
    app.args = args
    app.daily, app.events = [], []
    app.initialize()
    return app


def test_sunrise_defaults():
    app = build(SunriseFade, {"light": "light.x"}, app_name="bedroom_sunrise")
    f = app.fade
    assert (f.from_level, f.to_level, f.off_level, f.triggered) == (-6, 0, 4, True)
    assert app.daily == ["05:45:00"]
    assert app.events == ["bedroom_sunrise_start"]


def test_sunset_defaults():
    app = build(SunsetFade, {"light": "light.x", "to_level": -8})
    f = app.fade
    assert (f.from_level, f.to_level, f.off_level, f.triggered) == (6, -8, None, False)
    assert app.daily == []


def test_sun_fades_reject_detector():
    with pytest.raises(ValueError, match="fixed"):
        build(SunsetFade, {"light": "light.x", "detector": "sun"})


def test_generic_requires_levels():
    with pytest.raises(ValueError, match="missing settings"):
        build(LightFadeApp, {"light": "light.x"})


def test_generic_from_settings():
    args = {"light": "light.x", "from_level": 10, "to_level": 200, "start": [{"event": "alarm"}]}
    app = build(LightFadeApp, args, app_name="desk")
    assert (app.fade.from_level, app.fade.to_level, app.fade.triggered) == (10, 200, True)
    assert app.events == ["alarm", "desk_start"]
