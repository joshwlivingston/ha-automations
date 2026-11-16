"""Calibrations that map a light's percent brightness onto the raw range its bulb uses.

Configured as CalibrationConfig models discriminated on `kind`, for example
`{"kind": "linear", "low": 27, "high": 205}`. Calibrations are registered per light
entity id; lights without one use FullRange.
"""
from typing import Annotated

from pydantic import Field

from ha_automations.calibrations.base import MAX_RAW, Calibration
from ha_automations.calibrations.full_range import FullRange
from ha_automations.calibrations.linear import Linear
from ha_automations.calibrations.registry import calibration_for, register, unregister

CalibrationConfig = Annotated[FullRange | Linear, Field(discriminator="kind")]

__all__ = [
    "MAX_RAW",
    "Calibration",
    "CalibrationConfig",
    "FullRange",
    "Linear",
    "calibration_for",
    "register",
    "unregister",
]
