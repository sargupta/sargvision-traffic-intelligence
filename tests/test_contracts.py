"""The contracts are the product's integrity guarantees. Test them first."""
import pytest

from packages.analytics.anomalies import SILIGURI
from packages.contracts.metric import Metric
from packages.contracts.response import AnswerContract
from packages.domain.models import CorridorImportance, Priority, Severity
from packages.intelligence.priority import score

GOOD = dict(
    definition="A sufficiently long definition of the metric.",
    source="A sufficiently long statement of the source.",
    derivation="A sufficiently long description of the derivation.",
    limitation="A sufficiently long statement of the limitation.",
)


def test_metric_requires_full_provenance():
    Metric(name="ok", value=1, unit="x", **GOOD)
    for missing in ("definition", "source", "derivation", "limitation"):
        with pytest.raises(ValueError):
            Metric(name="bad", value=1, unit="x", **{**GOOD, missing: ""})


def test_answer_requires_limitation_and_evidence():
    with pytest.raises(ValueError):
        AnswerContract("o", "c", "i", "", "n", tools_called=["t"])
    with pytest.raises(ValueError):
        AnswerContract("o", "c", "i", "a long enough limitation", "n")
    AnswerContract("o", "c", "i", "a long enough limitation", "n", tools_called=["t"])


def test_severity_bands():
    assert SILIGURI.classify(10) is Severity.EXPECTED
    assert SILIGURI.classify(35) is Severity.MODERATE
    assert SILIGURI.classify(50) is Severity.HIGH
    assert SILIGURI.classify(70) is Severity.CRITICAL


def test_priority_is_not_severity():
    """The case the split exists for: persistent+important beats severe+brief."""
    persistent, _ = score(35, 45, CorridorImportance.CRITICAL)
    brief, brief_band = score(70, 5, CorridorImportance.LOW)
    assert SILIGURI.classify(35) is Severity.MODERATE
    assert SILIGURI.classify(70) is Severity.CRITICAL
    assert persistent > brief
    assert brief_band is Priority.P4
