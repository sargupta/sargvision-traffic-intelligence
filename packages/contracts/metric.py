"""Metric contract — every number carries its provenance.

    METRIC
      ├── definition   what it counts, precisely
      ├── source       where the underlying data came from
      ├── derivation   how it was computed
      └── limitation   what it does NOT tell you

Enforced at construction. A metric that cannot state all four raises ValueError and
therefore cannot reach a dashboard, a brief, or the Copilot.

Principle 4: every important insight is traceable to evidence.
Principle 5: every important claim states its limitation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

_MIN = 10


@dataclass(frozen=True)
class Metric:
    name: str
    value: float | int | str
    unit: str
    definition: str
    source: str
    derivation: str
    limitation: str

    def __post_init__(self) -> None:
        for field in ("definition", "source", "derivation", "limitation"):
            if len((getattr(self, field) or "").strip()) < _MIN:
                raise ValueError(
                    f"Metric {self.name!r} has no usable {field}. Every metric must state "
                    "its definition, source, derivation and limitation."
                )

    @property
    def headline(self) -> str:
        return f"{self.value} {self.unit}".strip()

    def as_dict(self) -> dict:
        return asdict(self)

    def for_copilot(self) -> str:
        """The form the LLM receives. It never sees a bare number."""
        return (
            f"{self.name}: {self.headline}\n"
            f"  definition: {self.definition}\n"
            f"  source: {self.source}\n"
            f"  derivation: {self.derivation}\n"
            f"  LIMITATION: {self.limitation}"
        )
