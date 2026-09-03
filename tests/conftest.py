"""Shared markers.

Some tests exercise the historical analytics against the 2019 dataset, which is
a 4 MB extract from a 1.6 GB academic archive and is not committed. Those tests
are correct and worth keeping — they cannot run on a fresh clone.

They are skipped with a reason rather than deleted or silently passed, and the
run summary reports the count, so it stays visible that a slice of the suite
did not execute. Regenerate the extract with scripts/fetch_data.py and
scripts/prepare_data.py to run them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

OBSERVATIONS = Path("data/processed/siliguri_observations.parquet")

needs_dataset = pytest.mark.skipif(
    not OBSERVATIONS.exists(),
    reason=(
        f"{OBSERVATIONS} is absent. It is a 4 MB extract from a 1.6 GB archive and is "
        "not committed. Run scripts/fetch_data.py then scripts/prepare_data.py."
    ),
)


def pytest_report_header(config) -> str:
    state = "present" if OBSERVATIONS.exists() else "ABSENT — dataset tests will skip"
    return f"2019 observations: {state}"


@pytest.fixture(autouse=True)
def _reset_rate_limit_counters():
    """Each test gets a fresh rate-limit window.

    The limiter keeps per-IP counters in process, which is correct for a service
    pinned to one instance — and means every test using TestClient shares one
    bucket. Without this the suite's own POSTs exhaust the write budget and
    later tests fail with 429s that say nothing about the code under test.
    """
    try:
        from apps.api import main
    except Exception:  # the analytics tests do not import the API at all
        yield
        return
    main._hits.clear()
    yield
    main._hits.clear()
