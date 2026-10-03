"""Validate agent-collected CSVs and canonicalize them into data/ledger.csv.

Nothing reaches the engine unvalidated. Partial dates are imputed to the midpoint of the
period they name and flagged, so date precision can be tested as a sensitivity.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from engine.model import DATA

ACTIONS = {"ratify", "reject", "rescind", "ratify_late"}
LEDGER_COLUMNS = ["amendment", "state", "action", "date", "source_url"]


def parse_partial(value: str) -> tuple[date | None, str]:
    """Return (imputed date, precision). Midpoint imputation keeps the error symmetric."""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None, "missing"
    parts = text.split("-")
    try:
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2])), "day"
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 15), "month"
        if len(parts) == 1 and len(text) == 4:
            return date(int(text), 7, 1), "year"
    except ValueError:
        return None, "unparseable"
    return None, "unparseable"


def validate_ledger(data_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    problems: list[str] = []
    frames = []
    for path in sorted(data_dir.glob("ratifications*.csv")):
        if path.name == "ledger.csv":
            continue
        frame = pd.read_csv(path, dtype=str)
        missing = [c for c in LEDGER_COLUMNS if c not in frame.columns]
        if missing:
            problems.append(f"{path.name}: missing columns {missing}")
            continue
        frame["source_file"] = path.name
        frames.append(frame)
    if not frames:
        return pd.DataFrame(), ["no ratifications*.csv found"]

    led = pd.concat(frames, ignore_index=True)
    led["amendment"] = led["amendment"].str.strip()
    led["state"] = led["state"].str.strip()
    led["action"] = led["action"].str.strip()

    bad_actions = sorted(set(led["action"]) - ACTIONS)
    if bad_actions:
        problems.append(f"unknown actions: {bad_actions}")

    parsed = led["date"].map(parse_partial)
    led["date_parsed"] = [p[0] for p in parsed]
    led["date_precision"] = [p[1] for p in parsed]
    for _, row in led[led["date_precision"].isin(["missing", "unparseable"])].iterrows():
        problems.append(
            f"{row['source_file']}: unusable date {row['date']!r} "
            f"for amendment {row['amendment']} / {row['state']}"
        )

    states_path = data_dir / "states.csv"
    if states_path.exists():
        known = set(pd.read_csv(states_path)["state"].str.strip())
        unknown = sorted(set(led["state"]) - known)
        if unknown:
            problems.append(f"states not in states.csv: {unknown}")
    else:
        problems.append("states.csv absent; state names unchecked")

    dupes = led.duplicated(subset=["amendment", "state", "action", "date"], keep=False)
    if dupes.any():
        for _, row in led[dupes].iterrows():
            problems.append(
                f"duplicate row: {row['amendment']} / {row['state']} / "
                f"{row['action']} / {row['date']}"
            )

    missing_src = led["source_url"].isna() | (led["source_url"].str.strip() == "")
    if missing_src.any():
        problems.append(f"{int(missing_src.sum())} rows without a source_url")

    return led, problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--strict", action="store_true", help="exit nonzero on any problem")
    args = ap.parse_args()

    led, problems = validate_ledger(args.data)
    if led.empty:
        print("no ledger built")
        sys.exit(1)

    out = led.dropna(subset=["date_parsed"]).copy()
    out["date"] = out["date_parsed"]
    out = out[
        ["amendment", "state", "action", "date", "date_precision", "source_url", "source_file"]
    ]
    out.to_csv(args.data / "ledger.csv", index=False)

    print(f"ledger.csv: {len(out)} rows, {out['amendment'].nunique()} amendments")
    print(out["date_precision"].value_counts().to_string())
    if problems:
        print(f"\n{len(problems)} problems:")
        for p in problems:
            print(f"  - {p}")
        if args.strict:
            sys.exit(2)


if __name__ == "__main__":
    main()
