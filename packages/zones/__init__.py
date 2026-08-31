"""Siliguri zone model — the spatial abstraction the whole product rests on."""

from packages.zones.gazetteer import LANDMARKS, Landmark
from packages.zones.model import ZoneModel, assign, build_zones

__all__ = ["LANDMARKS", "Landmark", "ZoneModel", "assign", "build_zones"]
