import pytest

from ha_automations.detectors import SunDetector, make_detector


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
    assert SunDetector(app).read() == (-3.0, True)


def test_sun_listen_calls_back_on_elevation_change():
    app = FakeApp()
    calls = []
    SunDetector(app).listen(lambda: calls.append(1))
    callback, entity_id, attribute = app.listeners[0]
    assert (entity_id, attribute) == ("sun.sun", "elevation")
    callback("sun.sun", "elevation", 1.0, 2.0)
    assert calls == [1]


def test_make_detector_default_is_sun():
    assert isinstance(make_detector(FakeApp()), SunDetector)


def test_make_detector_unknown():
    with pytest.raises(ValueError, match="unknown detector"):
        make_detector(FakeApp(), "nope")
