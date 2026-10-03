"""Answer the pre-registered questions Q1-Q7 from the built data. Writes out/findings.md."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from engine.model import (
    DATA,
    Engine,
    MissingUnitData,
    Panel,
    Spec,
    blocking_min_share,
    coalition_distribution,
    gap_series,
    max_share,
    min_share,
    quantile_from_distribution,
    required_states,
)


def annual_floor(panel: Panel, spec: Spec, years: range) -> pd.DataFrame:
    """Q1: the minimum-population coalition permitted by the rule, every year."""
    rows = []
    for year in years:
        on = date(year, 7, 1)
        members = panel.union_members(on, spec.denominator)
        if len(members) < 4:
            continue
        k = required_states(len(members), spec.threshold_rule)
        try:
            w = panel.weights(members, on, spec)
        except MissingUnitData:
            return pd.DataFrame()
        rows.append(
            {
                "year": year,
                "n_states": len(members),
                "k_required": k,
                "floor": min_share(w, k),
                "ceiling": max_share(w, k),
                "blocking_floor": blocking_min_share(w, len(members), k),
            }
        )
    return pd.DataFrame(rows)


def contestation_table(engine: Engine, spec: Spec) -> pd.DataFrame:
    """Q3: normalized support at adoption against contestation measured from the ledger.

    Every contestation measure here is derived from recorded state actions, not coded by
    judgment: rejections on the record before adoption, rescission attempts, days from
    proposal to adoption, and ratifications arriving after the threshold was already met.
    """
    gap = gap_series(engine, spec).set_index("amendment")
    led = engine.ledger.copy()
    led["amendment"] = led["amendment"].astype(str)

    rows = []
    for amendment, group in led.groupby("amendment"):
        if amendment not in gap.index:
            continue
        adopted = gap.loc[amendment, "date"]
        proposed = engine.event_date(amendment, "proposal")
        dated = group.dropna(subset=["date"])
        before = dated[dated["date"].dt.date <= adopted] if pd.notna(adopted) else dated
        rows.append(
            {
                "amendment": amendment,
                "rejections_before_adoption": int((before["action"] == "reject").sum()),
                "rescission_attempts": int((group["action"] == "rescind").sum()),
                "late_ratifications": int((group["action"] == "ratify_late").sum()),
                "days_to_adopt": (
                    (adopted - proposed).days
                    if pd.notna(adopted) and proposed is not None
                    else float("nan")
                ),
            }
        )
    measured = pd.DataFrame(rows).set_index("amendment")
    return gap.join(measured).reset_index()


def axis_agreement(engine: Engine, base: Spec, units: list[str]) -> pd.DataFrame:
    """Q4: do the candidate denominators move together?"""
    series = {}
    for unit in units:
        try:
            frame = engine.series(replace(base, unit=unit)).set_index("amendment")["value"]
        except MissingUnitData:
            continue
        series[unit] = frame
    return pd.DataFrame(series).corr() if series else pd.DataFrame()


def min_states_to_reach(weights: pd.Series, target: float) -> int:
    """Fewest states whose combined weight reaches a target share."""
    w = weights.dropna().sort_values(ascending=False).to_numpy(dtype=float)
    cum = np.cumsum(w) / w.sum()
    hit = np.searchsorted(cum, target) + 1
    return int(min(hit, len(w)))


def equivalence_map(panel: Panel, spec: Spec, on: date, target: float) -> dict[str, float]:
    """Q7: what it takes today to reproduce a historical ratio."""
    members = panel.union_members(on, spec.denominator)
    w = panel.weights(members, on, spec)
    n = len(members)
    k = required_states(n, spec.threshold_rule)
    shares, counts = coalition_distribution(w, k)
    total = counts.sum()
    at_or_above = counts[shares >= target].sum() if len(shares) else 0
    median = quantile_from_distribution(shares, counts, 0.5) if len(shares) else float("nan")
    above_frac = float(at_or_above / total) if total else float("nan")
    return {
        "n_states": n,
        "k_required": k,
        "target_share": target,
        "floor": min_share(w, k),
        "median_coalition": median,
        "ceiling": max_share(w, k),
        "min_states_to_reach_target": min_states_to_reach(w, target),
        "share_of_coalitions_at_or_above_target": above_frac,
        "total_coalitions": float(total),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=DATA.parent / "out")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    engine = Engine.load(args.data)
    base = Spec()

    floor = annual_floor(engine.panel, base, range(1790, 2027))
    floor.to_csv(args.out / "q1_annual_floor.csv", index=False)

    gap = gap_series(engine, base)
    gap.to_csv(args.out / "q2_gap.csv", index=False)

    dur = contestation_table(engine, base)
    if not dur.empty:
        dur.to_csv(args.out / "q3_contestation.csv", index=False)

    axes = axis_agreement(engine, base, ["persons", "apportionment_persons", "land", "income"])
    if not axes.empty:
        axes.to_csv(args.out / "q4_axis_agreement.csv")

    lines = ["# Findings (generated)", ""]
    if not floor.empty:
        first, last = floor.iloc[0], floor.iloc[-1]
        lines += [
            "## Q1 Shape of the floor",
            f"- {int(first['year'])}: {first['n_states']} states, k={int(first['k_required'])}, "
            f"floor={first['floor']:.1%}, blocking floor={first['blocking_floor']:.1%}",
            f"- {int(last['year'])}: {last['n_states']} states, k={int(last['k_required'])}, "
            f"floor={last['floor']:.1%}, blocking floor={last['blocking_floor']:.1%}",
            f"- monotonically declining: {bool((floor['floor'].diff().dropna() <= 1e-9).all())}",
            "",
        ]
    if not gap.empty:
        lines += [
            "## Q2 Practice against the textual floor",
            f"- mean actual share: {gap['actual'].mean():.1%}",
            f"- mean floor: {gap['floor'].mean():.1%}",
            f"- mean gap: {gap['gap'].mean():.1%}",
            "",
        ]
        thin = gap.nsmallest(5, "gap")[["amendment", "date", "actual", "floor", "gap"]]
        lines += ["Thinnest ratifications:", "", thin.to_markdown(index=False), ""]
    if not axes.empty:
        lines += ["## Q4 Axis agreement", "", axes.round(3).to_markdown(), ""]

    today = date.today()
    try:
        eq = equivalence_map(engine.panel, base, today, target=0.60)
        lines += [
            "## Q7 Equivalence today",
            *[f"- {k}: {v:,.4g}" for k, v in eq.items()],
            "",
        ]
    except MissingUnitData:
        pass

    (args.out / "findings.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
