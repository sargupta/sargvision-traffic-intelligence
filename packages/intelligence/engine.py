"""Run every detector, keep only what survives, and connect what remains.

    detectors  →  FDR gate  →  prioritiser  →  evidence graph  →  feed

The gate is the part that matters. Detectors are allowed to be greedy: they
propose anything that looks interesting. Nothing they propose reaches a user
until it has survived Benjamini-Hochberg across the whole run, so the feed's
error rate is a property of the system rather than of how many questions we
happened to ask.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from packages.intelligence import discovery as det
from packages.intelligence.finding import Finding, Kind


@dataclass
class Run:
    findings: list[Finding]
    proposed: int
    rejected_fdr: int
    fdr_q: float
    edges: list[dict]

    @property
    def surfaced(self) -> int:
        return len(self.findings)


def _relate(findings: list[Finding]) -> list[dict]:
    """Edges of the intelligence graph.

    Two findings are related when they touch the same movement, the same zone
    or the same hour. This is what turns a list into something explorable:
    an evening-variability finding and a recurring-anomaly finding on the same
    movement are the same story told by two detectors, and the interface should
    be able to say so.
    """
    edges: list[dict] = []
    for i, a in enumerate(findings):
        for b in findings[i + 1 :]:
            shared_movements = set(a.movements) & set(b.movements)
            shared_zones = set(a.zones) & set(b.zones)
            if shared_movements:
                edges.append(
                    {
                        "source": a.id,
                        "target": b.id,
                        "via": "movement",
                        "shared": sorted(shared_movements),
                    }
                )
            elif shared_zones:
                edges.append(
                    {
                        "source": a.id,
                        "target": b.id,
                        "via": "zone",
                        "shared": sorted(shared_zones),
                    }
                )
    return edges


def discover(
    obs: pl.DataFrame,
    movements: pl.DataFrame,
    reliability: pl.DataFrame,
    baselines: pl.DataFrame,
    anomalies: pl.DataFrame,
    zones: pl.DataFrame,
    scored_total: int,
    fdr_q: float = det.FDR_Q,
) -> Run:
    candidates: list[dict] = []
    candidates += det.detect_unreliable(reliability, obs)
    candidates += det.detect_divergence(reliability)
    candidates += det.detect_asymmetry(obs, movements)
    candidates += det.detect_period(obs, movements)
    candidates += det.detect_day_type(obs, movements)
    candidates += det.detect_recurrence(anomalies, scored_total, obs)
    candidates += det.detect_evidence_gaps(baselines, movements, zones)

    # Only candidates that ran a hypothesis test enter the correction. Findings
    # that are descriptive by nature — a coverage gap, a rank comparison — carry
    # no p-value and are not smuggled through the gate as if they had one; they
    # are marked, and their confidence is capped elsewhere.
    tested = [c for c in candidates if c["p"] is not None]
    survive = det.benjamini_hochberg([c["p"] for c in tested], fdr_q)
    keep_ids = {id(c) for c, ok in zip(tested, survive, strict=True) if ok}

    kept = [c for c in candidates if c["p"] is None or id(c) in keep_ids]
    findings = [c["build"]() for c in kept]
    findings.sort(key=lambda f: f.priority, reverse=True)

    return Run(
        findings=findings,
        proposed=len(candidates),
        rejected_fdr=len(tested) - sum(survive),
        fdr_q=fdr_q,
        edges=_relate(findings),
    )


def feed_summary(run: Run) -> str:
    """The line the application opens with. Generated, never written."""
    if not run.findings:
        return "No pattern in this data cleared the evidence threshold."

    strong = [f for f in run.findings if f.confidence.value == "HIGH"]
    kinds = {f.kind for f in run.findings if f.kind is not Kind.EVIDENCE_GAP}
    noun = "pattern" if len(run.findings) == 1 else "patterns"
    lead = f"{len(run.findings)} {noun} cleared the evidence threshold"
    if strong:
        lead += f", {len(strong)} of them at high confidence"
    if kinds:
        lead += f", across {len(kinds)} kinds of behaviour"
    return lead + "."
