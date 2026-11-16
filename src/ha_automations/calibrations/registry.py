"""Calibrations by light entity id, filled by LightCalibrationApp instances."""
from ha_automations.calibrations.base import Calibration
from ha_automations.calibrations.full_range import FullRange

_calibrations: dict[str, Calibration] = {}


def register(entity_id: str, calibration: Calibration) -> None:
    _calibrations[entity_id] = calibration


def unregister(entity_id: str) -> None:
    _calibrations.pop(entity_id, None)


def calibration_for(entity_id: str) -> Calibration:
    """The light's registered calibration, or FullRange if none."""
    return _calibrations.get(entity_id) or FullRange()
