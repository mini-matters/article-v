"""Synthetic-fixture tests. The arithmetic is verified independent of the real data."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.model import (
    Engine,
    Panel,
    Spec,
    blocking_min_share,
    coalition_distribution,
    max_share,
    min_share,
    quantile_from_distribution,
    required_states,
)


@pytest.fixture
def toy(tmp_path: Path) -> Path:
    """Four-state union: A admitted 1800, B/C/D 1810. Populations double 1800 -> 1810."""
    pd.DataFrame(
        {
            "state": ["A", "B", "C", "D"],
            "postal": ["A", "B", "C", "D"],
            "admission_date": ["1800-01-01", "1810-01-01", "1810-01-01", "1810-01-01"],
            "order": [1, 2, 3, 4],
            "source_url": ["test"] * 4,
        }
    ).to_csv(tmp_path / "states.csv", index=False)

    rows = []
    for year, scale in ((1800, 1.0), (1810, 2.0)):
        for state, base, enslaved in (("A", 100, 0), ("B", 200, 50), ("C", 300, 0), ("D", 400, 0)):
            rows.append(
                {
                    "state": state,
                    "year": year,
                    "total_pop": base * scale,
                    "free_pop": (base - enslaved) * scale,
                    "slave_pop": enslaved * scale,
                    "source_url": "test",
                }
            )
    pd.DataFrame(rows).to_csv(tmp_path / "population.csv", index=False)

    pd.DataFrame(
        {
            "amendment": ["1"],
            "title": ["toy"],
            "proposed_date": ["1810-01-01"],
            "adopted_date": ["1810-07-01"],
            "deadline": [""],
            "ratification_mode": ["legislature"],
            "states_in_union_at_adoption": [4],
            "source_url": ["test"],
        }
    ).to_csv(tmp_path / "amendments_meta.csv", index=False)

    pd.DataFrame(
        {
            "amendment": ["1", "1", "1", "1"],
            "state": ["A", "B", "C", "D"],
            "action": ["ratify", "ratify", "ratify", "rescind"],
            "date": ["1810-02-01", "1810-03-01", "1810-07-01", "1810-08-01"],
            "source_url": ["test"] * 4,
        }
    ).to_csv(tmp_path / "ratifications_toy.csv", index=False)
    return tmp_path


def test_required_states_rounds_up():
    assert required_states(13, "three_quarters_states") == 10
    assert required_states(50, "three_quarters_states") == 38
    assert required_states(48, "three_quarters_states") == 36
    assert required_states(36, "three_quarters_states") == 27
    assert required_states(50, "two_thirds_states") == 34
    assert required_states(13, "two_thirds_states") == 9


def test_min_max_blocking_shares():
    w = pd.Series({"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0})
    assert min_share(w, 3) == pytest.approx(6 / 10)
    assert max_share(w, 3) == pytest.approx(9 / 10)
    # blocking a 3-of-4 rule needs 2 states; the two smallest hold 3/10
    assert blocking_min_share(w, 4, 3) == pytest.approx(3 / 10)


def test_min_share_is_floor_of_distribution():
    rng = np.random.default_rng(0)
    w = pd.Series(rng.integers(1, 500, size=12).astype(float))
    shares, counts = coalition_distribution(w, 9, buckets=5_000)
    assert counts.sum() == math.comb(12, 9)
    assert shares[0] == pytest.approx(min_share(w, 9), abs=2e-3)
    assert shares[-1] == pytest.approx(max_share(w, 9), abs=2e-3)


def test_distribution_median_between_floor_and_ceiling():
    w = pd.Series([1.0, 1.0, 1.0, 50.0, 60.0, 70.0])
    shares, counts = coalition_distribution(w, 4, buckets=5_000)
    med = quantile_from_distribution(shares, counts, 0.5)
    assert min_share(w, 4) < med < max_share(w, 4)


def test_union_membership_respects_admission(toy: Path):
    panel = Panel(toy)
    assert panel.union_members(date(1805, 1, 1)) == ["A"]
    assert panel.union_members(date(1815, 1, 1)) == ["A", "B", "C", "D"]


def test_linear_interpolation_midpoint(toy: Path):
    panel = Panel(toy)
    w = panel.weights(["A"], date(1805, 1, 1), Spec(interpolation="linear"))
    assert w["A"] == pytest.approx(150.0, abs=1.0)
    w_step = panel.weights(["A"], date(1805, 1, 1), Spec(interpolation="step"))
    assert w_step["A"] == pytest.approx(100.0)


def test_apportionment_unit_applies_three_fifths(toy: Path):
    panel = Panel(toy)
    persons = panel.weights(["B"], date(1810, 1, 1), Spec(unit="persons"))
    apportioned = panel.weights(["B"], date(1810, 1, 1), Spec(unit="apportionment_persons"))
    assert persons["B"] == pytest.approx(400.0)
    # 300 free + 0.6 * 100 enslaved
    assert apportioned["B"] == pytest.approx(360.0)


def test_engine_actual_vs_floor(toy: Path):
    eng = Engine.load(toy)
    # 4 states, 3/4 rule -> k=3. Ratifiers by adoption: A, B, C.
    floor = eng.evaluate("1", Spec(coalition_stat="min"))
    actual = eng.evaluate("1", Spec(coalition_stat="actual"))
    assert floor.n_states == 4
    assert floor.k_required == 3
    # 1810 populations: A 200, B 400, C 600, D 800; total 2000
    assert floor.value == pytest.approx((200 + 400 + 600) / 2000)
    assert actual.value == pytest.approx((200 + 400 + 600) / 2000)
    assert actual.n_ratifiers == 3


def test_rescission_switch_changes_actual(toy: Path):
    eng = Engine.load(toy)
    late = date(1810, 12, 1)
    assert "D" not in eng.ratifiers_by("1", late, count_rescissions=True)
    assert "D" not in eng.ratifiers_by("1", late, count_rescissions=False)


def test_threshold_date_computed_from_ledger(toy: Path):
    eng = Engine.load(toy)
    assert eng._threshold_date("1") == date(1810, 7, 1)


def test_contestation_measures_come_from_ledger(toy: Path):
    from engine.report import contestation_table

    eng = Engine.load(toy)
    table = contestation_table(eng, Spec()).set_index("amendment")
    assert table.loc["1", "rescission_attempts"] == 1
    assert table.loc["1", "rejections_before_adoption"] == 0
    # proposed 1810-01-01, adopted 1810-07-01
    assert table.loc["1", "days_to_adopt"] == 181


def test_income_series_is_selected_not_averaged(toy: Path):
    """Regression: pivot_table's default mean silently averaged personal income against GDP."""
    pd.DataFrame(
        {
            "state": ["A", "A", "B", "B"],
            "year": [1810, 1810, 1810, 1810],
            "total_income": [100.0, 900.0, 200.0, 1800.0],
            "per_capita": [1, 9, 2, 18],
            "units": ["current USD millions"] * 4,
            "series": ["BEA_SAINC1", "BEA_SAGDP1"] * 2,
            "source_url": ["test"] * 4,
        }
    ).to_csv(toy / "income.csv", index=False)
    panel = Panel(toy)
    w = panel.weights(["A", "B"], date(1810, 1, 1), Spec(unit="income", boundaries="modern"))
    assert w["A"] == pytest.approx(100.0)
    assert w["B"] == pytest.approx(200.0)
    gdp = panel.weights(
        ["A", "B"], date(1810, 1, 1), Spec(unit="income", income_series="BEA_SAGDP1",
                                          boundaries="modern")
    )
    assert gdp["A"] == pytest.approx(900.0)


def test_bounded_extrapolation_refuses_distant_dates(toy: Path):
    """Regression: clamping invented votes-cast figures for amendments predating the series."""
    pd.DataFrame(
        {
            "state": ["A", "A", "B", "B"],
            "year": [1900, 1904, 1900, 1904],
            "total_votes_cast": [10, 12, 20, 24],
            "source_url": ["test"] * 4,
        }
    ).to_csv(toy / "votes_cast.csv", index=False)
    panel = Panel(toy)
    far = panel.weights(["A", "B"], date(1800, 1, 1), Spec(unit="votes", boundaries="modern"))
    assert far.isna().all()
    near = panel.weights(["A", "B"], date(1906, 1, 1), Spec(unit="votes", boundaries="modern"))
    assert near["A"] == pytest.approx(12.0)
    held = panel.weights(
        ["A", "B"], date(1800, 1, 1), Spec(unit="votes", extrapolate="hold", boundaries="modern")
    )
    assert held["A"] == pytest.approx(10.0)


def test_eventual_counts_post_adoption_ratifiers(toy: Path):
    """27 of 28 real amendments gained states after adoption; the pair must be trackable."""
    led = pd.read_csv(toy / "ratifications_toy.csv")
    led.loc[led.state == "D", "action"] = "ratify_late"
    led.to_csv(toy / "ratifications_toy.csv", index=False)
    (toy / "ledger.csv").unlink(missing_ok=True)
    eng = Engine.load(toy)
    at = eng.evaluate("1", Spec(coalition_stat="actual"))
    ever = eng.evaluate("1", Spec(coalition_stat="eventual"))
    assert at.value == pytest.approx((200 + 400 + 600) / 2000)
    assert ever.value == pytest.approx(1.0)


def test_decisive_states_flags_same_day_ties(toy: Path):
    """6 of 29 real amendments have more than one state acting on the threshold date."""
    led = pd.read_csv(toy / "ratifications_toy.csv")
    led.loc[led.state == "B", "date"] = "1810-07-01"  # B and C now tie on the decisive day
    led.to_csv(toy / "ratifications_toy.csv", index=False)
    (toy / "ledger.csv").unlink(missing_ok=True)
    eng = Engine.load(toy)
    states, ambiguous = eng.decisive_states("1")
    assert ambiguous is True
    assert states == ["B", "C"]
