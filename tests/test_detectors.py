import pytest
from pydantic import ValidationError

from ha_automations.detectors import Reading, Sun, SunDetector


class FakeApp:
    def __init__(self, attrs=None):
        self.attrs = attrs or {}
        self.listeners = []

    def get_state(self, entity_id, attribute=None):
        return {"attributes": self.attrs}

    def listen_state(self, callback, entity_id, attribute=None):
        self.listeners.append((callback, entity_id, attribute))


def test_sun_read():
    app = FakeApp({"elevation": -3.0, "rising": True})
    assert SunDetector(app).read() == Reading(-3.0, True)


def test_sun_listen_calls_back_on_elevation_change():
    app = FakeApp()
    calls = []
    SunDetector(app).listen(lambda: calls.append(1))
    callback, entity_id, attribute = app.listeners[0]
    assert (entity_id, attribute) == ("sun.sun", "elevation")
    callback("sun.sun", "elevation", 1.0, 2.0)
    assert calls == [1]


def test_sun_spec_builds_sun_detector():
    assert isinstance(Sun.model_validate({"kind": "sun"}).build(FakeApp()), SunDetector)


def test_unknown_detector_kind():
    with pytest.raises(ValidationError):
        Sun.model_validate({"kind": "nope"})
