"""Triggers that start fades.

A trigger calls back when something happens. Triggers are configured as specs,
one-key dicts mapping a TRIGGERS key to that trigger's argument, for example
`{"daily": "05:45:00"}` or `{"event": "bedroom_alarm"}`.
"""
from collections.abc import Callable
from typing import Any, Protocol


class Trigger(Protocol):
    def listen(self, callback: Callable[[], object]) -> None:
        """Call `callback` each time the trigger fires."""
        ...


class DailyTrigger:
    """Fires once a day at `time`, any time string `run_daily` accepts."""

    def __init__(self, app, time: str):
        self.app = app
        self.time = str(time)

    def listen(self, callback: Callable[[], object]) -> None:
        def on_time(**kwargs):
            callback()

        self.app.run_daily(on_time, self.time)


class EventTrigger:
    """Fires when the Home Assistant event `event` is fired."""

    def __init__(self, app, event: str):
        self.app = app
        self.event = event

    def listen(self, callback: Callable[[], object]) -> None:
        def on_event(event_type, data, **kwargs):
            callback()

        self.app.listen_event(on_event, self.event)


TRIGGERS: dict[str, Callable[[Any, Any], Trigger]] = {"daily": DailyTrigger, "event": EventTrigger}


def make_trigger(app, spec: dict[str, Any]) -> Trigger:
    """Build the trigger for a one-key spec."""
    if not isinstance(spec, dict) or len(spec) != 1:
        raise ValueError(f"trigger spec must be a one-key dict, got {spec!r}")
    [(name, arg)] = spec.items()
    try:
        factory = TRIGGERS[name]
    except KeyError:
        raise ValueError(f"unknown trigger {name!r}, expected one of {sorted(TRIGGERS)}") from None
    return factory(app, arg)


def make_triggers(app, specs: list[dict[str, Any]]) -> list[Trigger]:
    return [make_trigger(app, spec) for spec in specs]
