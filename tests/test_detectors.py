from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from astral import SunDirection
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


class FakeLocation:
    """Sun reaches each elevation at a fixed offset from midnight UTC; never reaches 80deg."""

    def __init__(self, today):
        self._today = today
        self.calls = []

    def today(self, local=True):
        return self._today

    def time_at_elevation(self, elevation, date, direction):
        self.calls.append((elevation, date, direction))
        if elevation >= 80:
            raise ValueError("never reached")
        return datetime(date.year, date.month, date.day, tzinfo=UTC) + timedelta(hours=12 - elevation)


def sun_with(location):
    app = FakeApp()
    app.AD = SimpleNamespace(sched=SimpleNamespace(location=location))  # pyright: ignore[reportAttributeAccessIssue]
    return SunDetector(app)


def test_sun_passed_at_today_if_past():
    loc = FakeLocation(date(2000, 1, 1))
    t = sun_with(loc).passed_at(0, False)
    assert t == datetime(2000, 1, 1, 12, tzinfo=UTC).timestamp()
    assert loc.calls == [(0, date(2000, 1, 1), SunDirection.SETTING)]


def test_sun_passed_at_yesterday_if_today_is_ahead():
    today = datetime.now(UTC).date() + timedelta(days=1)
    loc = FakeLocation(today)
    t = sun_with(loc).passed_at(12, True)
    assert t == datetime(today.year, today.month, today.day, tzinfo=UTC).timestamp() - 86400
    assert [c[2] for c in loc.calls] == [SunDirection.RISING] * 2


def test_sun_passed_at_none_if_never_reached():
    assert sun_with(FakeLocation(date(2000, 1, 1))).passed_at(85, False) is None
