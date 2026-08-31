"""Fetch the Siliguri observations. CC BY 4.0, no login required."""

from __future__ import annotations

from pathlib import Path

SOURCE_HINT = """
The processed parquet (101,418 valid primary-route observations) is produced by the
derivation in docs/data-provenance.md from Zenodo 10.5281/zenodo.10499064.

If you have it locally, copy it to data/processed/siliguri_2019_observations.parquet.
Otherwise run the full derivation described in the provenance document.
"""

TARGET = Path("data/processed/siliguri_2019_observations.parquet")

if __name__ == "__main__":
    if TARGET.exists():
        print(f"already present: {TARGET}")
    else:
        print(SOURCE_HINT)
