"""Lights that fades write to.

A light reports its brightness in percent and can be turned on at a brightness
or turned off, each over a transition in seconds.
"""
from typing import Protocol


class Light(Protocol):
    def brightness_pct(self) -> int:
        """Current brightness in percent (0 if off)."""
        ...

    def turn_on(self, pct: int, transition: float) -> None: ...

    def turn_off(self, transition: float) -> None: ...


class HassLight:
    """A Home Assistant `light` entity, controlled through an AppDaemon app."""

    def __init__(self, app, entity_id: str):
        self.app = app
        self.entity_id = entity_id

    def brightness_pct(self) -> int:
        if self.app.get_state(self.entity_id) != "on":
            return 0
        return round((self.app.get_state(self.entity_id, attribute="brightness") or 0) / 2.55)

    def turn_on(self, pct: int, transition: float) -> None:
        self.app.call_service(
            "light/turn_on", entity_id=self.entity_id, brightness_pct=pct, transition=transition
        )

    def turn_off(self, transition: float) -> None:
        self.app.call_service("light/turn_off", entity_id=self.entity_id, transition=transition)
