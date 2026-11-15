"""Triggers that start fades.

A trigger calls back through an AppDaemon app when it fires. Triggers are
configured as TriggerConfig models, for example `{"daily": "05:45:00"}` or
`{"event": "bedroom_alarm"}`.
"""
from collections.abc import Callable
from typing import Protocol

from ha_automations.config import Config


class Trigger(Protocol):
    def listen(self, app, callback: Callable[[], object]) -> None:
        """Call `callback` through `app` each time the trigger fires."""
        ...


class Daily(Config):
    """Fires once a day at `daily`, any time string `run_daily` accepts."""

    daily: str

    def listen(self, app, callback: Callable[[], object]) -> None:
        def on_time(**kwargs):
            callback()

        app.run_daily(on_time, self.daily)


class Event(Config):
    """Fires when the Home Assistant event `event` is fired."""

    event: str

    def listen(self, app, callback: Callable[[], object]) -> None:
        def on_event(event_type, data, **kwargs):
            callback()

        app.listen_event(on_event, self.event)


TriggerConfig = Daily | Event
