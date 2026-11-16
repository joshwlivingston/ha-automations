"""Lights that fades write to.

A light reports its brightness in percent and can be turned on at a brightness
or turned off, each over a transition in seconds. str() of a light names it in logs.
"""
from typing import Protocol

from ha_automations.calibrations import Calibration, calibration_for


class Light(Protocol):
    def brightness_pct(self) -> int:
        """Current brightness in percent (0 if off)."""
        ...

    def turn_on(self, pct: int, transition: float) -> None: ...

    def turn_off(self, transition: float) -> None: ...


class HassLight:
    """A Home Assistant `light` entity, controlled through an AppDaemon app.

    Percents are converted to raw brightness by the calibration registered for
    the entity, looked up on each call. A calibration passed in is used instead.
    """

    def __init__(self, app, entity_id: str, calibration: Calibration | None = None):
        self.app = app
        self.entity_id = entity_id
        self._calibration = calibration

    @property
    def calibration(self) -> Calibration:
        return self._calibration or calibration_for(self.entity_id)

    def __str__(self) -> str:
        return self.entity_id

    def brightness_pct(self) -> int:
        if self.app.get_state(self.entity_id) != "on":
            return 0
        raw = self.app.get_state(self.entity_id, attribute="brightness") or 0
        return self.calibration.to_pct(raw) if raw else 0

    def turn_on(self, pct: int, transition: float) -> None:
        self.app.call_service(
            "light/turn_on",
            entity_id=self.entity_id,
            brightness=self.calibration.to_raw(pct),
            transition=transition,
        )

    def turn_off(self, transition: float) -> None:
        self.app.call_service("light/turn_off", entity_id=self.entity_id, transition=transition)
