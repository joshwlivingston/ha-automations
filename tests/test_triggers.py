import pytest

from ha_automations.triggers import (
    DailyTrigger,
    EventTrigger,
    make_trigger,
    make_triggers,
)


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
    DailyTrigger(app, "05:45:00").listen(lambda: calls.append(1))
    callback, time = app.daily[0]
    assert time == "05:45:00"
    callback()
    assert calls == [1]


def test_event_trigger():
    app, calls = FakeApp(), []
    EventTrigger(app, "alarm").listen(lambda: calls.append(1))
    callback, event = app.events[0]
    assert event == "alarm"
    callback("alarm", {})
    assert calls == [1]


def test_make_triggers():
    triggers = make_triggers(FakeApp(), [{"daily": "06:00:00"}, {"event": "alarm"}])
    assert isinstance(triggers[0], DailyTrigger) and triggers[0].time == "06:00:00"
    assert isinstance(triggers[1], EventTrigger) and triggers[1].event == "alarm"


def test_make_trigger_unknown():
    with pytest.raises(ValueError, match="unknown trigger"):
        make_trigger(FakeApp(), {"nope": 1})


def test_make_trigger_bad_spec():
    with pytest.raises(ValueError, match="one-key dict"):
        make_trigger(FakeApp(), {"daily": "06:00:00", "event": "alarm"})
