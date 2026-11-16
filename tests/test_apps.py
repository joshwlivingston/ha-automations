import pytest
from pydantic import ValidationError

from ha_automations.apps.light_calibration import LightCalibrationApp
from ha_automations.apps.light_fade import LightFadeApp
from ha_automations.apps.sunrise_fade import SunriseFade
from ha_automations.apps.sunset_fade import SunsetFade


def build(cls, args, app_name="test"):
    """Run `cls.initialize` against stubbed AppDaemon calls, skipping Hass.__init__."""

    class Stub(cls):
        name = app_name  # pyright: ignore[reportAssignmentType]

        def log(self, msg, level="INFO"):
            self.logs.append(msg)

        def run_daily(self, callback, time):
            self.daily.append(time)

        def listen_event(self, callback, event):
            self.events.append(event)

        def listen_state(self, *a, **k):
            pass

    app = Stub.__new__(Stub)
    app.args = args
    app.daily, app.events, app.logs = [], [], []
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
    assert app.daily == ["23:00:00"]


def test_off_time_null_schedules_nothing():
    app = build(SunsetFade, {"light": "light.x", "off_time": None})
    assert app.daily == []


def test_ignores_appdaemon_keys():
    app = build(
        SunsetFade,
        {
            "name": "test",
            "module": "sunset_fade",
            "class": "SunsetFade",
            "light": "light.x",
        },
    )
    assert app.fade.from_level == 6


def test_rejects_unknown_setting():
    with pytest.raises(ValidationError, match="form_level"):
        build(SunsetFade, {"light": "light.x", "form_level": 3})


def test_generic_requires_levels():
    with pytest.raises(ValidationError, match="from_level"):
        build(LightFadeApp, {"light": "light.x"})


def test_generic_from_settings():
    args = {
        "light": "light.x",
        "detector": {"kind": "sun"},
        "from_level": 10,
        "to_level": 200,
        "start": [{"event": "alarm"}],
    }
    app = build(LightFadeApp, args, app_name="desk")
    assert (app.fade.from_level, app.fade.to_level, app.fade.triggered) == (
        10,
        200,
        True,
    )
    assert app.events == ["alarm", "desk_start"]


@pytest.mark.parametrize("app", [LightFadeApp, SunriseFade, SunsetFade])
def test_settings_have_descriptions(app):
    missing = [
        name for name, f in app.Settings.model_fields.items() if not f.description
    ]
    assert missing == []


def test_summary_lines(snapshot):
    cases = [
        (SunriseFade, {"light": "light.x"}, "bedroom_sunrise"),
        (SunsetFade, {"light": "light.y"}, "living"),
        (SunsetFade, {"light": "light.y", "off_time": None}, "living"),
        (
            LightFadeApp,
            {
                "light": "light.z",
                "detector": {"kind": "sun"},
                "from_level": 10,
                "to_level": 20,
                "start": [{"event": "alarm"}, {"daily": "06:00:00"}],
            },
            "desk",
        ),
    ]
    lines = []
    for cls, args, name in cases:
        lines.append(f"> {cls.__name__} {name}: {args}")
        lines += [f"  {m}" for m in build(cls, args, app_name=name).logs]
    assert "\n".join(lines) == snapshot


def test_light_calibration_app_registers():
    from ha_automations.calibrations import Linear, calibration_for

    app = build(
        LightCalibrationApp,
        {"light": "light.cal", "calibration": {"kind": "linear", "low": 27, "high": 205}},
    )
    assert calibration_for("light.cal") == Linear(low=27, high=205)
    assert app.logs == ["load: init; light=light.cal calibration=linear 27..205"]
    app.terminate()
    assert calibration_for("light.cal").label == "full_range"


class SliderHass:
    """States and service calls for slider tests."""

    def __init__(self, light_state="off", brightness=None, slider="0.0"):
        self.states = {"light.cal": light_state, "brightness": brightness, "input_number.cal": slider}
        self.calls = []


def build_slider(hass_state, cls):
    class Stub(cls):
        name = "cal"

        def log(self, msg, level="INFO"):
            pass

        def listen_state(self, *a, **k):
            pass

        def get_state(self, entity_id, attribute=None):
            return hass_state.states["brightness" if attribute == "brightness" else entity_id]

        def call_service(self, service, **kwargs):
            hass_state.calls.append((service, kwargs))

    app = Stub.__new__(Stub)
    app.args = {
        "light": "light.cal",
        "slider": "input_number.cal",
        "calibration": {"kind": "linear", "low": 27, "high": 205},
    }
    app.initialize()
    app.terminate()
    return app


def test_slider_follows_light_on_start():
    h = SliderHass("on", 205, "0.0")
    build_slider(h, LightCalibrationApp)
    assert h.calls == [("input_number/set_value", {"entity_id": "input_number.cal", "value": 100})]


def test_slider_sets_calibrated_brightness():
    h = SliderHass()
    app = build_slider(h, LightCalibrationApp)
    h.states["input_number.cal"] = "1.0"
    app._on_slider()
    assert h.calls == [("light/turn_on", {"entity_id": "light.cal", "brightness": 27, "transition": 0})]


def test_slider_zero_turns_off():
    h = SliderHass("on", 205, "100.0")
    app = build_slider(h, LightCalibrationApp)
    h.states["input_number.cal"] = "0.0"
    app._on_slider()
    assert h.calls == [("light/turn_off", {"entity_id": "light.cal", "transition": 0})]


def test_slider_echo_does_not_set_light():
    h = SliderHass("on", 116, "0.0")
    app = build_slider(h, LightCalibrationApp)
    h.calls.clear()
    h.states["input_number.cal"] = f"{app._pushed}.0"
    h.states["brightness"] = 150  # light moved again mid transition
    app._on_slider()
    assert h.calls == []
