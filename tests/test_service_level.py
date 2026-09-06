"""The absolute metric: a jam reads as a jam, chronic is told from acute.

The regression this locks down is the one the officer reported — Darjeeling More
at ~11 km/h showing green because the relative index sat near 1.0. The absolute
grade must call that HEAVY, and the condition must call it CHRONIC (slow, but not
unusual for that road), never CLEAR.
"""

from __future__ import annotations

from packages.command.centre import SERVICE, ServiceLevel, condition_of


class TestServiceLevel:
    def test_grades_by_absolute_speed(self):
        assert SERVICE.grade(30) == "FREE"
        assert SERVICE.grade(20) == "MODERATE"
        assert SERVICE.grade(12) == "HEAVY"
        assert SERVICE.grade(6) == "STANDSTILL"
        assert SERVICE.grade(None) == "UNKNOWN"

    def test_slow_is_heavy_or_worse(self):
        assert ServiceLevel.is_slow("HEAVY")
        assert ServiceLevel.is_slow("STANDSTILL")
        assert not ServiceLevel.is_slow("MODERATE")
        assert not ServiceLevel.is_slow("FREE")


class TestCondition:
    def test_darjeeling_more_reads_chronic_not_clear(self):
        # 11 km/h (HEAVY) with a normal index — the reported bug. Must NOT be CLEAR.
        assert condition_of(SERVICE.grade(11.0), "NORMAL") == "CHRONIC"

    def test_slow_and_unusual_is_acute(self):
        assert condition_of("STANDSTILL", "HIGH") == "ACUTE"
        assert condition_of("HEAVY", "ELEVATED") == "ACUTE"

    def test_slow_but_normal_is_chronic(self):
        assert condition_of("HEAVY", "NORMAL") == "CHRONIC"
        assert condition_of("STANDSTILL", "NORMAL") == "CHRONIC"

    def test_moving_but_unusual_is_watch(self):
        assert condition_of("MODERATE", "ELEVATED") == "WATCH"
        assert condition_of("FREE", "HIGH") == "WATCH"

    def test_moving_and_normal_is_clear(self):
        assert condition_of("FREE", "NORMAL") == "CLEAR"
        assert condition_of("MODERATE", "NORMAL") == "CLEAR"

    def test_unobserved_stays_unknown(self):
        assert condition_of("UNKNOWN", "UNKNOWN") == "UNKNOWN"

    def test_the_taxonomy_separates_deploy_now_from_structural(self):
        # the whole point: a fresh jam and a standing one are different actions
        assert condition_of("STANDSTILL", "SEVERE") == "ACUTE"  # deploy now
        assert condition_of("STANDSTILL", "NORMAL") == "CHRONIC"  # structural
