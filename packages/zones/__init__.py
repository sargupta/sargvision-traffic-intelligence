"""Siliguri zone model — the spatial abstraction the whole product rests on."""

from packages.zones.gazetteer import LANDMARKS, Landmark
from packages.zones.model import ZoneModel, build_zones, assign

__all__ = ["LANDMARKS", "Landmark", "ZoneModel", "build_zones", "assign"]
