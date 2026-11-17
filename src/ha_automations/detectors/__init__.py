"""Ambient light detectors that fades read from.

A detector reports a light level (higher is brighter, in the detector's own
units) and whether that level is rising. Fade thresholds are in the same units
as the detector they are used with. Detectors are configured as DetectorConfig
models, for example `{"kind": "sun"}`, and each config builds its detector.
"""
from ha_automations.detectors.base import Detector, Reading
from ha_automations.detectors.sun import Sun, SunDetector

# Make this a union discriminated on `kind` when a second detector is added.
DetectorConfig = Sun
"""Settings for a detector. Only Sun for now."""

__all__ = ["Detector", "DetectorConfig", "Reading", "Sun", "SunDetector"]
