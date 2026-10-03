"""Core model for normalized Article V ratification thresholds.

No framing decision is baked in. Every contested analytic choice is a field on `Spec`,
so the paper's argument can be selected after the specification curve is run, not before.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

Unit = Literal[
    "persons", "free_persons", "apportionment_persons", "electorate", "votes", "land", "income"
]
ThresholdRule = Literal[
    "three_quarters_states", "two_thirds_states", "two_thirds_congress", "article_vii"
]
Denominator = Literal["all_union", "ex_confederate", "ex_unrepresented", "ratification_eligible"]
CoalitionStat = Literal[
    "actual", "eventual", "min", "max", "median", "blocking_min", "distribution"
]
DateBasis = Literal["adoption", "final", "proposal"]
Interpolation = Literal["linear", "nearest_census", "step"]
NAsOf = Literal["adoption", "proposal"]
Boundaries = Literal["contemporaneous", "modern"]
Extrapolate = Literal["bounded", "hold", "none"]

# Virginia and Tennessee seceded but were never without members in Congress. The Restored
# Government's senators Willey and Carlile were seated 1861-07-13 and five Virginia
# representatives sat in the 37th Congress; Andrew Johnson held his Tennessee seat to
# 1862-03-04. Any rule that drops them is dropping states with loyal members in both chambers.
RETAINED_REPRESENTATION = ("Virginia", "Tennessee")


class MissingUnitData(Exception):
    """Raised when a Spec asks for a unit whose source data has not been built yet."""


@dataclass(frozen=True)
class Spec:
    """One analytic specification. The grid over these is the paper's robustness surface."""

    unit: Unit = "persons"
    threshold_rule: ThresholdRule = "three_quarters_states"
    denominator: Denominator = "all_union"
    coalition_stat: CoalitionStat = "min"
    date_basis: DateBasis = "adoption"
    interpolation: Interpolation = "linear"
    n_asof: NAsOf = "adoption"
    count_rescissions: bool = False
    boundaries: Boundaries = "contemporaneous"
    extrapolate: Extrapolate = "bounded"
    income_series: str = "BEA_SAINC1"

    def label(self) -> str:
        return "|".join(
            [
                self.unit,
                self.threshold_rule,
                self.denominator,
                self.coalition_stat,
                self.date_basis,
                self.interpolation,
                self.n_asof,
                f"rescind={int(self.count_rescissions)}",
                self.boundaries,
                f"extrap={self.extrapolate}",
            ]
        )


@dataclass(frozen=True)
class Result:
    amendment: str
    on: date | None
    n_states: int
    k_required: int
    n_ratifiers: int
    value: float
    total_weight: float
    note: str = ""


def required_states(n: int, rule: ThresholdRule) -> int:
    """States needed under a threshold rule. Article V fractions round up."""
    if rule == "article_vii":
        return 9
    if rule == "three_quarters_states":
        return math.ceil(n * 3 / 4)
    if rule == "two_thirds_states":
        return math.ceil(n * 2 / 3)
    raise ValueError(f"{rule} is not a state-counting rule")


class Panel:
    """Time-varying state panel: who is in the union, and what each state weighs."""

    def __init__(self, data_dir: Path = DATA) -> None:
        self.dir = data_dir
        self.states = pd.read_csv(data_dir / "states.csv", parse_dates=["admission_date"])
        self.pop = pd.read_csv(data_dir / "population.csv")
        self.land = self._maybe("land_area.csv")
        self.electorate = self._maybe("electorate.csv")
        self.income = self._maybe("income.csv")
        self.votes = self._maybe("votes_cast.csv")
        self.boundaries = self._maybe("boundaries.csv")
        self.secession = self._maybe("secession.csv")
        self._pop_wide: dict[str, pd.DataFrame] = {}

    def _maybe(self, name: str) -> pd.DataFrame | None:
        path = self.dir / name
        return pd.read_csv(path) if path.exists() else None

    def union_members(self, on: date, denominator: Denominator = "all_union") -> list[str]:
        adm = self.states.dropna(subset=["admission_date"])
        members = adm.loc[adm["admission_date"].dt.date <= on, "state"].tolist()
        out = self.out_of_union(on, denominator)
        return sorted(s for s in members if s not in out)

    def out_of_union(self, on: date, denominator: Denominator) -> set[str]:
        """States excluded from the denominator on a date, per-state rather than by blanket window.

        "ex_confederate" runs from each state's own secession ordinance to its own readmission
        act. "ex_unrepresented" instead runs from the departure of its delegation, and never
        excludes Virginia or Tennessee, which kept members seated throughout. The two differ by
        up to two months per state and by two states entirely, which is a measurable sensitivity
        on exactly the amendments where it matters most.
        """
        if denominator not in ("ex_confederate", "ex_unrepresented") or self.secession is None:
            return set()
        start_col = (
            "secession_date" if denominator == "ex_confederate" else "representation_lost_date"
        )
        out: set[str] = set()
        for _, row in self.secession.iterrows():
            if denominator == "ex_unrepresented" and row["state"] in RETAINED_REPRESENTATION:
                continue
            start = pd.to_datetime(row[start_col]).date()
            end = pd.to_datetime(row["readmission_date"]).date()
            if start <= on < end:
                out.add(row["state"])
        return out

    def original_thirteen(self) -> list[str]:
        """Under Article VII the ratifying states were the union, so admission cannot be the
        denominator. The thirteen confederation states are."""
        order = pd.to_numeric(self.states["order"], errors="coerce")
        return sorted(self.states.loc[order <= 13, "state"])

    def _wide(self, column: str) -> pd.DataFrame:
        if column not in self._pop_wide:
            frame = self.pop.pivot_table(index="state", columns="year", values=column)
            self._pop_wide[column] = frame.sort_index(axis=1)
        return self._pop_wide[column]

    def parent_map(self, on: date) -> dict[str, str]:
        """Territories that legally belonged to a state on a date, from boundaries.csv.

        The census sources report every state on modern boundaries, so Maine sits outside
        Massachusetts before 1820 and West Virginia outside Virginia before 1863 unless
        they are folded back. Rows with no parent are documented non-merges.
        """
        if self.boundaries is None:
            return {}
        frame = self.boundaries.dropna(subset=["parent"])
        cutoff = pd.to_datetime(frame["until_date"]).dt.date
        live = frame[cutoff > on]
        return dict(zip(live["child"], live["parent"], strict=True))

    def weights(self, states: list[str], on: date, spec: Spec) -> pd.Series:
        """Weight per state under the spec's unit, at a date, after boundary reconciliation."""
        if spec.boundaries == "modern":
            return self._raw_weights(states, on, spec)

        parents = {c: p for c, p in self.parent_map(on).items() if p in states}
        if not parents:
            return self._raw_weights(states, on, spec)

        raw = self._raw_weights(states + sorted(parents), on, spec)
        folded = raw.reindex(states).copy()
        for child, parent in parents.items():
            addition = raw.get(child, float("nan"))
            if pd.notna(addition):
                folded[parent] = folded.get(parent, 0.0) + addition
        return folded

    def _raw_weights(self, states: list[str], on: date, spec: Spec) -> pd.Series:
        if spec.unit in ("persons", "free_persons", "apportionment_persons"):
            return self._population_weights(states, on, spec)
        if spec.unit == "land":
            if self.land is None:
                raise MissingUnitData("land_area.csv not built")
            frame = self.land.set_index("state")["land_sq_mi"]
            return frame.reindex(states).astype(float)
        if spec.unit == "electorate":
            if self.electorate is None:
                raise MissingUnitData("electorate.csv not built")
            wide = self.electorate.pivot_table(index="state", columns="year", values="eligible")
            return self._interp(wide, states, on, spec.interpolation, spec.extrapolate)
        if spec.unit == "votes":
            if self.votes is None:
                raise MissingUnitData("votes_cast.csv not built")
            wide = self.votes.pivot_table(index="state", columns="year", values="total_votes_cast")
            return self._interp(wide, states, on, spec.interpolation, spec.extrapolate)
        if spec.unit == "income":
            if self.income is None:
                raise MissingUnitData("income.csv not built")
            frame = self.income[self.income["series"] == spec.income_series]
            if frame.empty:
                raise MissingUnitData(f"income series {spec.income_series!r} absent")
            wide = frame.pivot_table(index="state", columns="year", values="total_income")
            return self._interp(wide, states, on, spec.interpolation, spec.extrapolate)
        raise ValueError(spec.unit)

    def _population_weights(self, states: list[str], on: date, spec: Spec) -> pd.Series:
        how, ex = spec.interpolation, spec.extrapolate
        total = self._interp(self._wide("total_pop"), states, on, how, ex)
        if spec.unit == "persons":
            return total
        free = self._interp(self._wide("free_pop"), states, on, how, ex)
        enslaved = self._interp(
            self._wide("slave_pop"), states, on, spec.interpolation, spec.extrapolate
        )
        if spec.unit == "free_persons":
            return free.fillna(total)
        apportioned = free.fillna(total) + 0.6 * enslaved.fillna(0.0)
        return apportioned

    @staticmethod
    def _interp(
        wide: pd.DataFrame,
        states: list[str],
        on: date,
        how: Interpolation,
        extrapolate: Extrapolate = "bounded",
    ) -> pd.Series:
        """Interpolate a wide state-by-year frame to a date.

        "bounded" (the default) extends the series by at most one of its own sampling
        intervals -- six years past the 2020 census is a forward hold, a century before the
        first vote-count series is not. "none" refuses any extrapolation, "hold" clamps.
        Unbounded clamping silently invented votes-cast figures for pre-1824 amendments and
        spliced 1840 commodity income into 1929 BEA personal income before this guard existed.
        """
        years = np.array([c for c in wide.columns], dtype=float)
        t = on.year + (on.timetuple().tm_yday - 1) / 365.25
        frame = wide.reindex(states)
        if extrapolate != "hold":
            gap = max(years.min() - t, t - years.max(), 0.0)
            budget = float(np.median(np.diff(years))) if len(years) > 1 else 0.0
            if gap > (budget if extrapolate == "bounded" else 0.0):
                return pd.Series(float("nan"), index=states)

        if how == "nearest_census":
            col = wide.columns[int(np.argmin(np.abs(years - t)))]
            return frame[col].astype(float)
        if how == "step":
            prior = [c for c, y in zip(wide.columns, years, strict=True) if y <= t]
            col = prior[-1] if prior else wide.columns[0]
            return frame[col].astype(float)

        lo_idx = int(np.searchsorted(years, t, side="right") - 1)
        lo_idx = min(max(lo_idx, 0), len(years) - 1)
        hi_idx = min(lo_idx + 1, len(years) - 1)
        lo_col, hi_col = wide.columns[lo_idx], wide.columns[hi_idx]
        if lo_idx == hi_idx or years[hi_idx] == years[lo_idx]:
            return frame[lo_col].astype(float)
        w = (t - years[lo_idx]) / (years[hi_idx] - years[lo_idx])
        w = float(np.clip(w, 0.0, 1.0))
        lo, hi = frame[lo_col].astype(float), frame[hi_col].astype(float)
        return lo.fillna(hi) * (1 - w) + hi.fillna(lo) * w


def min_share(weights: pd.Series, k: int) -> float:
    """Smallest share of total weight any k-state coalition can hold."""
    w = weights.dropna().sort_values().to_numpy(dtype=float)
    return float(w[:k].sum() / w.sum()) if len(w) >= k else float("nan")


def max_share(weights: pd.Series, k: int) -> float:
    w = weights.dropna().sort_values().to_numpy(dtype=float)
    return float(w[-k:].sum() / w.sum()) if len(w) >= k else float("nan")


def blocking_min_share(weights: pd.Series, n: int, k: int) -> float:
    """Smallest share of total weight that can defeat the threshold."""
    return min_share(weights, n - k + 1)


def coalition_distribution(
    weights: pd.Series, k: int, buckets: int = 20_000
) -> tuple[np.ndarray, np.ndarray]:
    """Exact count of k-state coalitions by bucketed weight share.

    Dynamic program over (states, coalition size, bucketed weight). Counts are exact
    integers; bucketing introduces at most n/2 buckets of rounding error in the share axis.
    """
    w = weights.dropna().to_numpy(dtype=float)
    n = len(w)
    if n < k:
        return np.array([]), np.array([])
    unit = w.sum() / buckets
    idx = np.rint(w / unit).astype(np.int64)
    width = int(idx.sum()) + 1
    dp = np.zeros((k + 1, width), dtype=np.int64)
    dp[0, 0] = 1
    for i in range(n):
        step = idx[i]
        upper = min(k, i + 1)
        for j in range(upper, 0, -1):
            src = dp[j - 1, : width - step]
            dp[j, step:] += src
    counts = dp[k]
    shares = np.arange(width, dtype=float) * unit / w.sum()
    keep = counts > 0
    return shares[keep], counts[keep]


def quantile_from_distribution(shares: np.ndarray, counts: np.ndarray, q: float) -> float:
    cum = np.cumsum(counts)
    target = cum[-1] * q
    return float(shares[int(np.searchsorted(cum, target))])


class Engine:
    def __init__(self, panel: Panel, ledger: pd.DataFrame, meta: pd.DataFrame) -> None:
        self.panel = panel
        self.ledger = ledger
        self.meta = meta.set_index("amendment")

    @classmethod
    def load(cls, data_dir: Path = DATA) -> Engine:
        canonical = data_dir / "ledger.csv"
        if canonical.exists():
            frames = [pd.read_csv(canonical)]
        else:
            frames = [pd.read_csv(p) for p in sorted(data_dir.glob("ratifications*.csv"))]
        if not frames:
            raise FileNotFoundError(f"no ledger.csv or ratifications*.csv in {data_dir}")
        ledger = pd.concat(frames, ignore_index=True)
        ledger["amendment"] = ledger["amendment"].astype(str)
        ledger["date"] = pd.to_datetime(ledger["date"], errors="coerce")
        meta_path = data_dir / "amendments_meta.csv"
        if meta_path.exists():
            meta = pd.read_csv(meta_path, parse_dates=["proposed_date", "adopted_date"])
            meta["amendment"] = meta["amendment"].astype(str)
        else:
            meta = pd.DataFrame(
                {"amendment": sorted(ledger["amendment"].unique())},
            ).assign(proposed_date=pd.NaT, adopted_date=pd.NaT)
        return cls(Panel(data_dir), ledger, meta)

    def event_date(self, amendment: str, basis: DateBasis) -> date | None:
        rows = self.ledger[self.ledger["amendment"] == amendment]
        meta = self.meta.loc[amendment] if amendment in self.meta.index else None
        if basis == "proposal" and meta is not None and pd.notna(meta.get("proposed_date")):
            return meta["proposed_date"].date()
        if basis == "final":
            valid = rows[rows["action"].isin(["ratify", "ratify_late"])]["date"].dropna()
            return valid.max().date() if len(valid) else None
        if meta is not None and pd.notna(meta.get("adopted_date")):
            return meta["adopted_date"].date()
        return self._threshold_date(amendment)

    @staticmethod
    def rule_for(amendment: str, spec_rule: ThresholdRule) -> ThresholdRule:
        """Article VII fixed nine states for the Constitution itself; Article V is a fraction."""
        return "article_vii" if amendment == "CONST" else spec_rule

    def _threshold_date(self, amendment: str) -> date | None:
        """Date the k-of-n threshold was first met, computed from the ledger itself."""
        rows = (
            self.ledger[
                (self.ledger["amendment"] == amendment) & (self.ledger["action"] == "ratify")
            ]
            .dropna(subset=["date"])
            .sort_values("date")
        )
        for i, (_, row) in enumerate(rows.iterrows(), start=1):
            on = row["date"].date()
            n = len(self.panel.union_members(on))
            if i >= required_states(n, self.rule_for(amendment, "three_quarters_states")):
                return on
        return None

    def decisive_states(self, amendment: str) -> tuple[list[str], bool]:
        """States that ratified on the threshold-crossing date, and whether that is ambiguous.

        For 6 of 29 amendments more than one state acted that day -- five ratified the 18th on
        1919-01-16 -- so "the 36th state" has no determinate answer. Callers get the set and
        the flag rather than a silent alphabetical tiebreak.
        """
        on = self.event_date(amendment, "adoption")
        if on is None:
            return [], False
        rows = self.ledger[
            (self.ledger["amendment"] == amendment) & (self.ledger["action"] == "ratify")
        ].dropna(subset=["date"])
        same_day = sorted(rows.loc[rows["date"].dt.date == on, "state"])
        return same_day, len(same_day) > 1

    def ratifiers_ever(self, amendment: str, count_rescissions: bool) -> list[str]:
        """Every state that ever ratified, including after the threshold was already met.

        27 of 28 amendments kept collecting states after adoption. Support at the threshold
        is what the legal machinery certified; this is what the country came to accept.
        """
        rows = self.ledger[self.ledger["amendment"] == amendment]
        yes = set(rows[rows["action"].isin(["ratify", "ratify_late"])]["state"])
        if count_rescissions:
            yes -= set(rows[rows["action"] == "rescind"]["state"])
        return sorted(yes)

    def ratifiers_by(self, amendment: str, on: date, count_rescissions: bool) -> list[str]:
        rows = self.ledger[(self.ledger["amendment"] == amendment)].dropna(subset=["date"])
        rows = rows[rows["date"].dt.date <= on]
        yes = set(rows[rows["action"].isin(["ratify", "ratify_late"])]["state"])
        if count_rescissions:
            yes -= set(rows[rows["action"] == "rescind"]["state"])
        return sorted(yes)

    def evaluate(self, amendment: str, spec: Spec) -> Result:
        on = self.event_date(amendment, spec.date_basis)
        if on is None:
            return Result(amendment, None, 0, 0, 0, float("nan"), float("nan"), "no event date")

        n_date = on
        if spec.n_asof == "proposal":
            proposed = self.event_date(amendment, "proposal")
            n_date = proposed or on
        members = self.panel.union_members(n_date, spec.denominator)
        if amendment == "CONST":
            members = self.panel.original_thirteen()
        n = len(members)
        k = required_states(n, self.rule_for(amendment, spec.threshold_rule))

        weights = self.panel.weights(members, on, spec)
        total = float(weights.dropna().sum())
        if not total or weights.isna().all():
            return Result(amendment, on, n, k, 0, float("nan"), total, "unit data absent at date")
        ratifiers = self.ratifiers_by(amendment, on, spec.count_rescissions)
        in_union = [s for s in ratifiers if s in members]

        if spec.coalition_stat == "actual":
            value = float(weights.reindex(in_union).dropna().sum() / total)
        elif spec.coalition_stat == "eventual":
            every = self.ratifiers_ever(amendment, spec.count_rescissions)
            ever = [s for s in every if s in members]
            value = float(weights.reindex(ever).dropna().sum() / total)
        elif spec.coalition_stat == "min":
            value = min_share(weights, k)
        elif spec.coalition_stat == "max":
            value = max_share(weights, k)
        elif spec.coalition_stat == "blocking_min":
            value = blocking_min_share(weights, n, k)
        elif spec.coalition_stat == "median":
            shares, counts = coalition_distribution(weights, k)
            value = quantile_from_distribution(shares, counts, 0.5)
        else:
            raise ValueError(spec.coalition_stat)

        return Result(amendment, on, n, k, len(in_union), value, total)

    def series(self, spec: Spec, amendments: list[str] | None = None) -> pd.DataFrame:
        ids = amendments or sorted(
            self.meta.index.tolist(), key=lambda a: (not a.isdigit(), int(a) if a.isdigit() else a)
        )
        rows = []
        for a in ids:
            try:
                r = self.evaluate(a, spec)
            except MissingUnitData as exc:
                rows.append({"amendment": a, "value": float("nan"), "note": str(exc)})
                continue
            rows.append(
                {
                    "amendment": r.amendment,
                    "date": r.on,
                    "n_states": r.n_states,
                    "k_required": r.k_required,
                    "n_ratifiers": r.n_ratifiers,
                    "value": r.value,
                    "total_weight": r.total_weight,
                    "note": r.note,
                }
            )
        out = pd.DataFrame(rows)
        out["spec"] = spec.label()
        return out


def gap_series(engine: Engine, base: Spec) -> pd.DataFrame:
    """Q2: distance between what ratification actually commanded and what the text required."""
    actual = engine.series(replace(base, coalition_stat="actual")).set_index("amendment")
    floor = engine.series(replace(base, coalition_stat="min")).set_index("amendment")
    out = pd.DataFrame(
        {
            "date": actual["date"],
            "n_states": actual["n_states"],
            "k_required": actual["k_required"],
            "n_ratifiers": actual["n_ratifiers"],
            "actual": actual["value"],
            "floor": floor["value"],
        }
    )
    out["gap"] = out["actual"] - out["floor"]
    return out.reset_index()
