"""Persistence for deployments — one document each, like incidents.

A deployment is a police record of an action taken and what it achieved, so it
survives restarts. Only our own derived readings (speed, index, band) are kept,
never a raw Google response — the same Maps-terms boundary the other stores hold.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Protocol

from packages.verification.deployment import Deployment, DeploySample

COLLECTION = "deployments"


def _when(v: str | None) -> datetime | None:
    return datetime.fromisoformat(v) if v else None


def to_document(d: Deployment) -> dict:
    def samples(xs: list[DeploySample]) -> list[dict]:
        return [
            {"at": s.at.isoformat(), "speed_kmh": s.speed_kmh, "index": s.index, "band": s.band}
            for s in xs
        ]

    return {
        "deployment_id": d.deployment_id,
        "corridor_ids": d.corridor_ids,
        "primary_corridor_id": d.primary_corridor_id,
        "location_name": d.location_name,
        "by": d.by,
        "unit": d.unit,
        "purpose": d.purpose,
        "started_at": d.started_at.isoformat(),
        "ended_at": d.ended_at.isoformat() if d.ended_at else None,
        "incident_id": d.incident_id,
        "note": d.note,
        "before": samples(d.before),
        "during": samples(d.during),
    }


def from_document(doc: dict) -> Deployment:
    def samples(xs) -> list[DeploySample]:
        return [
            DeploySample(
                at=datetime.fromisoformat(s["at"]),
                speed_kmh=s.get("speed_kmh"),
                index=s.get("index"),
                band=s.get("band", "UNKNOWN"),
            )
            for s in (xs or [])
        ]

    return Deployment(
        deployment_id=doc["deployment_id"],
        corridor_ids=list(doc.get("corridor_ids") or []),
        primary_corridor_id=doc["primary_corridor_id"],
        location_name=doc.get("location_name", ""),
        by=doc.get("by", ""),
        unit=doc.get("unit", ""),
        purpose=doc.get("purpose", ""),
        started_at=datetime.fromisoformat(doc["started_at"]),
        before=samples(doc.get("before")),
        during=samples(doc.get("during")),
        ended_at=_when(doc.get("ended_at")),
        incident_id=doc.get("incident_id"),
        note=doc.get("note"),
    )


class DeploymentStore(Protocol):
    def load_recent(self) -> list[Deployment]: ...
    def save(self, deployment: Deployment) -> None: ...
    def describe(self) -> dict: ...


class MemoryDeploymentStore:
    durable = False

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    def load_recent(self) -> list[Deployment]:
        return [from_document(d) for d in self._docs.values()]

    def save(self, deployment: Deployment) -> None:
        self._docs[deployment.deployment_id] = to_document(deployment)

    def describe(self) -> dict:
        return {"backend": "memory", "durable": False, "note": "Deployments lost on exit."}


class FirestoreDeploymentStore:
    durable = True

    def __init__(self, project: str | None = None, collection: str = COLLECTION):
        from google.cloud import firestore

        self._db = firestore.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
        self._collection = collection

    def load_recent(self, limit: int = 200) -> list[Deployment]:
        docs = (
            self._db.collection(self._collection)
            .order_by("started_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )
        out: list[Deployment] = []
        for doc in docs:
            try:
                out.append(from_document(doc.to_dict()))
            except (KeyError, ValueError):
                continue
        return out

    def save(self, deployment: Deployment) -> None:
        self._db.collection(self._collection).document(deployment.deployment_id).set(
            to_document(deployment)
        )

    def describe(self) -> dict:
        return {
            "backend": "firestore",
            "durable": True,
            "collection": self._collection,
            "note": "Deployment records survive restarts; only derived readings are stored.",
        }


def build_deployment_store() -> DeploymentStore:
    backend = os.environ.get("DEPLOYMENT_STORE", os.environ.get("INCIDENT_STORE", "memory")).lower()
    if backend == "firestore":
        return FirestoreDeploymentStore()
    return MemoryDeploymentStore()
