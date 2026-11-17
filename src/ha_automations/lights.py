"""Lights that fades write to.

A light reports its brightness in percent and can be turned on at a brightness
or turned off, each over a transition in seconds. str() of a light names it in logs.
"""
from typing import Protocol


class Light(Protocol):
    """A light a fade can set."""

    def brightness_pct(self) -> int:
        """Current brightness in percent (0 if off)."""
        ...

    def turn_on(self, pct: int, transition: float) -> None:
        """Turn on at `pct` percent over `transition` seconds."""
        ...

    def turn_off(self, transition: float) -> None:
        """Turn off over `transition` seconds."""
        ...


class HassLight:
    """A Home Assistant `light` entity, controlled through an AppDaemon app."""

    def __init__(self, app, entity_id: str):
        self.app = app
        """AppDaemon app that makes the calls."""
        self.entity_id = entity_id
        """Entity ID, e.g. `light.bedroom_lamp`."""

    def __str__(self) -> str:
        return self.entity_id

    def brightness_pct(self) -> int:
        """Current brightness in percent (0 if off)."""
        if self.app.get_state(self.entity_id) != "on":
            return 0
        return round((self.app.get_state(self.entity_id, attribute="brightness") or 0) / 2.55)

    def turn_on(self, pct: int, transition: float) -> None:
        """Call `light/turn_on` at `pct` percent over `transition` seconds."""
        self.app.call_service(
            "light/turn_on", entity_id=self.entity_id, brightness_pct=pct, transition=transition
        )

    def turn_off(self, transition: float) -> None:
        """Call `light/turn_off` over `transition` seconds."""
        self.app.call_service("light/turn_off", entity_id=self.entity_id, transition=transition)
