"""AI response contract — structurally enforced, not prompted.

Each section is a separate field the assembler fills. The model writes prose into
slots; it cannot skip LIMITATION, because an AnswerContract without one will not
construct.

    OBSERVATION → COMPARISON → INTERPRETATION → LIMITATION → NEXT STEP

Principle 3: the system distinguishes observation from interpretation from hypothesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.contracts.metric import Metric


@dataclass(frozen=True)
class AnswerContract:
    observation: str  # what the data shows — fact
    comparison: str  # how it compares to baseline — fact
    interpretation: str  # why it is operationally relevant — inference, labelled
    limitation: str  # what the data does NOT establish — mandatory
    next_step: str  # what an officer should investigate
    evidence: list[Metric] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len((self.limitation or "").strip()) < 10:
            raise ValueError(
                "AnswerContract requires a limitation. An answer that does not state "
                "what the data fails to establish must not reach an officer."
            )
        if not self.evidence and not self.tools_called:
            raise ValueError(
                "AnswerContract requires evidence or a tool trace. The AI explains "
                "intelligence; it does not manufacture it."
            )

    def render(self) -> str:
        return (
            f"**Observation** — {self.observation}\n\n"
            f"**Comparison** — {self.comparison}\n\n"
            f"**Interpretation** — {self.interpretation}\n\n"
            f"**Limitation** — {self.limitation}\n\n"
            f"**Suggested next step** — {self.next_step}"
        )

    def as_dict(self) -> dict:
        return {
            "observation": self.observation,
            "comparison": self.comparison,
            "interpretation": self.interpretation,
            "limitation": self.limitation,
            "next_step": self.next_step,
            "evidence": [m.as_dict() for m in self.evidence],
            "tools_called": self.tools_called,
        }
