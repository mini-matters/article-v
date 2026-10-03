"""Run the full analytic grid and emit a specification curve.

Every framing choice that could have been made by argument is made by enumeration here.
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import fields
from pathlib import Path

import pandas as pd

from engine.model import DATA, Engine, MissingUnitData, Spec

GRID: dict[str, list] = {
    "unit": ["persons", "apportionment_persons", "votes", "land", "income"],
    "threshold_rule": ["three_quarters_states"],
    "denominator": ["all_union", "ex_confederate"],
    "coalition_stat": ["actual", "min", "max", "blocking_min"],
    "date_basis": ["adoption", "final"],
    "interpolation": ["linear", "nearest_census", "step"],
    "n_asof": ["adoption", "proposal"],
    "count_rescissions": [True, False],
    "boundaries": ["contemporaneous", "modern"],
}

QUICK: dict[str, list] = {
    "unit": ["persons"],
    "threshold_rule": ["three_quarters_states"],
    "denominator": ["all_union"],
    "coalition_stat": ["actual", "min", "blocking_min"],
    "date_basis": ["adoption"],
    "interpolation": ["linear"],
    "n_asof": ["adoption"],
    "count_rescissions": [False],
    "boundaries": ["contemporaneous"],
}


def specs(grid: dict[str, list]) -> list[Spec]:
    keys = [f.name for f in fields(Spec) if f.name in grid]
    return [Spec(**dict(zip(keys, combo, strict=True))) for combo in itertools.product(
        *(grid[k] for k in keys)
    )]


def run(engine: Engine, grid: dict[str, list]) -> pd.DataFrame:
    out = []
    for spec in specs(grid):
        try:
            frame = engine.series(spec)
        except MissingUnitData:
            continue
        for name in ("unit", "denominator", "coalition_stat", "date_basis", "interpolation",
                     "n_asof", "count_rescissions", "boundaries"):
            frame[name] = getattr(spec, name)
        out.append(frame)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=DATA.parent / "out" / "spec_curve.csv")
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    engine = Engine.load(args.data)
    frame = run(engine, QUICK if args.quick else GRID)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    print(f"{len(frame)} rows across {frame['spec'].nunique()} specifications -> {args.out}")


if __name__ == "__main__":
    main()
