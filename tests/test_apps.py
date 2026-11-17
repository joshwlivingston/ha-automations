import json
import tempfile
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from ha_automations.apps.light_fade import STATE_DIR, LightFadeApp
from ha_automations.apps.sunrise_fade import SunriseFade
from ha_automations.apps.sunset_fade import SunsetFade


def build(cls, args, app_name="test", config_dir=None, states=None):
    """Run `cls.initialize` against stubbed AppDaemon calls, skipping Hass.__init__.

    `states` maps entity IDs to get_state(attribute="all") results.
    """
    states = states or {}
    root = Path(config_dir or tempfile.mkdtemp())

    class Stub(cls):
        name = app_name  # pyright: ignore[reportAssignmentType]
        config_dir = root  # pyright: ignore[reportAssignmentType]

        def get_state(self, entity_id, attribute=None):
            entity = states.get(entity_id)
            if attribute == "all" or entity is None:
                return entity
            return entity["attributes"].get(attribute) if attribute else entity["state"]

        def call_service(self, service, **kwargs):
            self.services.append((service, kwargs))

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
    app.daily, app.events, app.logs, app.services = [], [], [], []
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


def sun(elevation, rising=True):
    return {"sun.sun": {"state": "", "attributes": {"elevation": elevation, "rising": rising}}}


def test_sunrise_restores_after_restart(tmp_path):
    path = tmp_path / STATE_DIR / "bedroom_sunrise.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"value": -10, "saved_at": time.time()}))
    app = build(SunriseFade, {"light": "light.x"}, "bedroom_sunrise", tmp_path, sun(-3))
    assert app.fade.ramp_from == -10
    assert app.services[0][0] == "light/turn_on"


def test_sunrise_saves_when_armed(tmp_path):
    app = build(SunriseFade, {"light": "light.x"}, "bedroom_sunrise", tmp_path, sun(-10))
    app.fade.start()
    path = tmp_path / STATE_DIR / "bedroom_sunrise.json"
    assert json.loads(path.read_text())["value"] == -10
    app.fade.stop("reached off_time")
    assert not path.exists()


def test_sunset_checks_on_load():
    app = build(SunsetFade, {"light": "light.y"}, states=sun(0, rising=False))
    assert app.services[0][0] == "light/turn_on"
