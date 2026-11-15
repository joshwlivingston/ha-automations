import pytest
from pydantic import TypeAdapter, ValidationError

from ha_automations.triggers import Daily, Event, TriggerConfig

TRIGGERS = TypeAdapter(list[TriggerConfig])


class FakeApp:
    def __init__(self):
        self.daily = []
        self.events = []

    def run_daily(self, callback, time):
        self.daily.append((callback, time))

    def listen_event(self, callback, event):
        self.events.append((callback, event))


def test_daily_trigger():
    app, calls = FakeApp(), []
    Daily(daily="05:45:00").listen(app, lambda: calls.append(1))
    callback, time = app.daily[0]
    assert time == "05:45:00"
    callback()
    assert calls == [1]


def test_event_trigger():
    app, calls = FakeApp(), []
    Event(event="alarm").listen(app, lambda: calls.append(1))
    callback, event = app.events[0]
    assert event == "alarm"
    callback("alarm", {})
    assert calls == [1]


def test_parse_triggers():
    triggers = TRIGGERS.validate_python([{"daily": "06:00:00"}, {"event": "alarm"}])
    assert triggers == [Daily(daily="06:00:00"), Event(event="alarm")]


@pytest.mark.parametrize("spec", [{"nope": 1}, {"daily": "06:00:00", "event": "alarm"}])
def test_bad_trigger(spec):
    with pytest.raises(ValidationError):
        TRIGGERS.validate_python([spec])
