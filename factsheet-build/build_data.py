import csv
import itertools
import json
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from engine.model import (
    Engine,
    Spec,
    blocking_min_share,
    coalition_distribution,
    min_share,
    quantile_from_distribution,
    required_states,
)

OUT = "factsheet-build/facts.json"
e = Engine.load()
p = e.panel
base = Spec()
res = {}

# A. annual floors
rows = []
for y in range(1790, 2027):
    on = date(y, 7, 1)
    m = p.union_members(on)
    k = required_states(len(m), "three_quarters_states")
    w = p.weights(m, on, base)
    rows.append(
        dict(
            year=y,
            n=len(m),
            k=k,
            floor=min_share(w, k),
            block=blocking_min_share(w, len(m), k),
            total=float(w.sum()),
        )
    )
res["annual"] = rows

# A1. overview extras: 13-state groups today, ERA milestones, modeled legislator counts
on = date(2020, 7, 1)
w20 = p.weights(p.union_members(on), on, base)
sh, ct = coalition_distribution(w20, 13, buckets=4000)
res["dist13_today"] = dict(shares=sh.tolist(), counts=[int(c) for c in ct])
era_pts = []
for label, d in (("deadline", date(1982, 6, 30)), ("recorded", date(2020, 1, 27))):
    mm = p.union_members(d)
    ww = p.weights(mm, d, base)
    pt = dict(label=label, date=str(d))
    for tag, resc in (("ignored", False), ("counted", True)):
        rat = [s for s in e.ratifiers_by("U-ERA", d, resc) if s in mm]
        pt[f"n_{tag}"] = len(rat)
        pt[f"share_{tag}"] = float(ww.reindex(rat).sum() / ww.sum())
    era_pts.append(pt)
res["era_points"] = era_pts
leg = pd.read_csv("data/legislature_sizes.csv")
leg = leg[leg.year == leg.year.max()].assign(maj=lambda d: d.seats.astype(int) // 2 + 1)
both = leg.groupby("state").maj.sum().sort_values()
one = leg.groupby("state").maj.min().sort_values()

# A1b. legislator snapshots (Figures 0.3, 0.4): each state's nearest record within three years;
# a chamber missing from that window is filled from the state's nearest record and listed in "filled"
LEG_ALL = pd.read_csv("data/legislature_sizes.csv").assign(
    maj=lambda d: d.seats.astype(int) // 2 + 1
)
leg_series, filled = [], []
for y in (1830, 1870, 1900, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2026):
    on = date(y, 7, 1)
    mm = p.union_members(on)
    ww = p.weights(mm, on, base)
    n_, k_ = len(mm), required_states(len(mm), "three_quarters_states")
    b_ = n_ - k_ + 1
    win = LEG_ALL[(LEG_ALL.year - y).abs() <= 3].assign(d=lambda d, y=y: (d.year - y).abs())
    best = win.sort_values(["d", "year"]).groupby(["state", "chamber"]).head(1)
    for st_, ch in best.groupby("state").chamber.apply(set).items():
        if ch == {"unicameral"}:
            continue
        for need in {"house", "senate"} - ch:
            cand = LEG_ALL[(LEG_ALL.state == st_) & (LEG_ALL.chamber == need)]
            fill = cand.assign(d=(cand.year - y).abs()).sort_values("d").head(1)
            filled.append(
                dict(
                    snapshot=y,
                    state=st_,
                    chamber=need,
                    from_year=int(fill.year.iloc[0]),
                    seats=int(fill.seats.iloc[0]),
                )
            )
            best = pd.concat([best, fill])
    s_both = best.groupby("state").maj.sum().reindex(ww.index)
    s_one = best.groupby("state").maj.min().reindex(ww.index)
    seats = best.groupby("state").seats.sum().reindex(ww.index)
    lower = (
        best[best.chamber.isin(["house", "unicameral"])]
        .groupby("state")
        .seats.sum()
        .reindex(ww.index)
    )
    assert s_both.notna().all() and lower.notna().all(), y
    cons = ww / lower
    rmin_states = s_both.sort_values().index[:k_]
    bmin_states = s_one.sort_values().index[:b_]
    leg_series.append(
        dict(
            year=y,
            n=n_,
            k=k_,
            ratify_min=int(s_both.sort_values().iloc[:k_].sum()),
            ratify_max=int(s_both.sort_values().iloc[-k_:].sum()),
            block_min=int(s_one.sort_values().iloc[:b_].sum()),
            block_max=int(s_one.sort_values().iloc[-b_:].sum()),
            seated=int(seats.sum()),
            ratify_min_share=float(ww[rmin_states].sum() / ww.sum()),
            block_min_share=float(ww[bmin_states].sum() / ww.sum()),
            people_per_legislator=float(ww.sum() / seats.sum()),
            constituency_min=float(cons.min()),
            constituency_min_state=cons.idxmin(),
            constituency_max=float(cons.max()),
            constituency_max_state=cons.idxmax(),
        )
    )
res["leg_series"] = leg_series
res["leg_filled"] = filled
res["legislators"] = dict(
    year=int(leg.year.max()),
    seated=int(leg.seats.astype(int).sum()),
    ratify_min=int(both.iloc[:38].sum()),
    ratify_max=int(both.iloc[-38:].sum()),
    block_min=int(one.iloc[:13].sum()),
    block_max=int(one.iloc[-13:].sum()),
)
_last = leg_series[-1]
assert all(
    res["legislators"][k] == _last[k]
    for k in ("ratify_min", "ratify_max", "block_min", "block_max")
), (
    res["legislators"],
    _last,
)

# A2. per-year spread of shares across all groups of the ratifying and blocking sizes
QS = [0.1, 0.25, 0.5, 0.75, 0.9]
fan = []
for y in range(1790, 2027):
    on = date(y, 7, 1)
    m = p.union_members(on)
    n, k = len(m), required_states(len(m), "three_quarters_states")
    w = p.weights(m, on, base)
    total = float(w.sum())
    row = dict(year=y)
    for tag, size in (("r", k), ("b", n - k + 1)):
        sh, ct = coalition_distribution(w, size, buckets=4000)
        srt = np.sort(w.to_numpy())
        row[f"{tag}_min"] = float(srt[:size].sum() / total)
        row[f"{tag}_max"] = float(srt[-size:].sum() / total)
        for q in QS:
            row[f"{tag}_q{int(q * 100)}"] = quantile_from_distribution(sh, ct, q)
    fan.append(row)
res["fan"] = fan
st = pd.read_csv("data/states.csv", parse_dates=["admission_date"])
res["admissions"] = [
    dict(state=r.state, year=r.admission_date.year)
    for r in st.itertuples()
    if r.admission_date.year >= 1791
]

# B. per amendment
meta = e.meta
AMS = [str(i) for i in range(1, 28)] + ["U-ERA"]
led = e.ledger
amend = []
for a in AMS:
    act = e.evaluate(a, replace(base, coalition_stat="actual"))
    fl = e.evaluate(a, replace(base, coalition_stat="min"))
    ev = e.evaluate(a, replace(base, coalition_stat="eventual"))
    on = act.on
    members = p.union_members(on)
    w = p.weights(members, on, base)
    ratifiers = [s for s in e.ratifiers_by(a, on, False) if s in members]
    sh, ct = coalition_distribution(w, len(ratifiers))
    pct_below = float(ct[sh < act.value - 1e-9].sum() / ct.sum())
    cum = np.cumsum(ct)
    median = float(sh[int(np.searchsorted(cum, cum[-1] * 0.5))])
    rowsA = led[led["amendment"] == a]
    prop = meta.loc[a, "proposed_date"]
    yrs = (pd.Timestamp(on) - pd.Timestamp(prop)).days / 365.25
    amend.append(
        dict(
            amendment=a,
            adopted=str(on),
            proposed=str(prop),
            years_to_adopt=round(yrs, 2),
            floor=fl.value,
            threshold=act.value,
            final=ev.value,
            n_ratifiers=len(ratifiers),
            n_states=len(members),
            k=act.k_required,
            pct_below=pct_below,
            same_size_median=median,
            rejections=int((rowsA["action"] == "reject").sum()),
            rescissions=int((rowsA["action"] == "rescind").sum()),
            decisive=e.decisive_states(a)[0],
        )
    )
res["amendments"] = amend

# C. distributions: today and founding
on = date(2020, 7, 1)
m = p.union_members(on)
w = p.weights(m, on, base)
sh, ct = coalition_distribution(w, 38, buckets=4000)
res["dist_today"] = dict(shares=sh.tolist(), counts=[int(c) for c in ct], total=int(ct.sum()))
thirteen = p.original_thirteen()
w13 = p.weights(thirteen, date(1790, 8, 2), base)
rat9 = e.ratifiers_by("CONST", date(1788, 6, 21), False)
actual9 = float(w13.reindex(rat9).sum() / w13.sum())
combos = [
    float(w13.reindex(list(c)).sum() / w13.sum()) for c in itertools.combinations(thirteen, 9)
]
res["founding"] = dict(
    ratifiers=rat9,
    actual=actual9,
    combos=combos,
    pct_below=sum(c < actual9 - 1e-12 for c in combos) / len(combos),
    n=len(combos),
    floor=min(combos),
)

# D. 21st amendment by state
pop = pd.read_csv("data/population.csv")
p1930 = pop[pop.year == 1930].set_index("state")["total_pop"]
c21 = []
for r in csv.DictReader(open("data/convention_votes_21st.csv")):
    wet, dry = r["wet_votes"], r["dry_votes"]
    yes = int(wet) / (int(wet) + int(dry)) if wet and dry else None
    c21.append(
        dict(
            state=r["state"],
            yes=yes,
            ratified=r["convention_ratified"] == "TRUE",
            pop1930=int(p1930.get(r["state"], 0)),
        )
    )
res["c21"] = c21

# E. map sets (2020 census, 50 states)
p2020 = pop[(pop.year == 2020) & (pop.state != "District of Columbia")].set_index("state")[
    "total_pop"
]
order = p2020.sort_values()
pol = pd.read_csv("data/state_politics.csv")
pw = pol[(pol.measure == "pres_plurality_winner_party") & (pol.year.isin([2016, 2020, 2024]))]
streak = pw.groupby("state")["value"].agg(
    lambda s: s.iloc[0] if s.nunique() == 1 and len(s) == 3 else None
)
rep = [s for s in order.index if streak.get(s) == "REPUBLICAN"][:13]
dem = [s for s in order.index if streak.get(s) == "DEMOCRAT"][:13]
res["maps"] = dict(
    pop2020={s: int(v) for s, v in p2020.items()},
    postal=dict(zip(st.state, st.postal)),
    smallest38=list(order.index[:38]),
    smallest13=list(order.index[:13]),
    rep13=rep,
    dem13=dem,
    party2024={s: pw[(pw.state == s) & (pw.year == 2024)]["value"].iloc[0] for s in p2020.index},
    shares=dict(
        s38=float(order.iloc[:38].sum() / order.sum()),
        s13=float(order.iloc[:13].sum() / order.sum()),
        rep=float(p2020[rep].sum() / order.sum()),
        dem=float(p2020[dem].sum() / order.sum()),
    ),
)

# F. decisive-state records
mar = pd.read_csv("data/ratification_margins.csv", dtype=str)
dec = mar[mar.is_decisive_state == "TRUE"]
recs = []
for a in AMS:
    d = dec[dec.amendment == a]
    tallied = d[d.yeas.notna() & (d.yeas != "")]
    recs.append(
        dict(
            amendment=a,
            states=sorted(d.state.unique().tolist()),
            rows=len(d),
            tallied_rows=len(tallied),
            chambers=[
                dict(
                    state=r.state,
                    chamber=r.chamber,
                    yeas=r.yeas,
                    nays=r.nays,
                    action=r.action,
                    note=(r.notes or "")[:160],
                )
                for r in d.itertuples()
            ],
        )
    )
res["records"] = recs
rat = mar[mar.action.fillna("").str.startswith("ratify")]
tday = []
for a in AMS:
    states, tie = e.decisive_states(a)
    per = []
    for s in states:
        r = rat[(rat.amendment == a) & (rat.state == s)]
        t = r[r.yeas.notna() & (r.yeas != "")]
        per.append(dict(state=s, rows=len(r), tallied=sorted(set(t.chamber))))
    if any(x["tallied"] for x in per):
        status = "tally"
    elif all(x["rows"] for x in per):
        status = "no_tally"
    else:
        status = "not_collected"
    tday.append(dict(amendment=a, tie=bool(tie), states=per, status=status))
res["records_tday"] = tday
allm = mar[mar.yeas.notna() & mar.nays.notna() & (mar.yeas != "") & (mar.nays != "")].copy()
allm["y"] = allm.yeas.astype(float)
allm["n"] = allm.nays.astype(float)
allm = allm[(allm.y + allm.n) > 0]
allm["margin"] = (allm.y - allm.n) / (allm.y + allm.n)
res["margins"] = [
    dict(
        amendment=r.amendment,
        state=r.state,
        chamber=r.chamber,
        yeas=int(r.y),
        nays=int(r.n),
        margin=float(r.margin),
        action=r.action,
        decisive=r.is_decisive_state == "TRUE",
    )
    for r in allm.itertuples()
]

# G. Suber replication: his convention = states in union on Jan 1 of the census year, modern boundaries, census value
SUBER_L = {
    1790: 56.74,
    1800: 50.86,
    1810: 52.29,
    1820: 49.60,
    1830: 46.84,
    1840: 50.19,
    1850: 49.26,
    1860: 48.40,
    1870: 46.09,
    1880: 49.64,
    1890: 48.08,
    1900: 43.68,
    1910: 46.95,
    1920: 43.88,
    1930: 41.80,
    1940: 41.97,
    1950: 41.21,
    1960: 40.43,
    1970: 39.87,
    1980: 41.12,
}
SUBER_V = {
    1790: 13.32,
    1800: 11.03,
    1810: 12.11,
    1820: 6.17,
    1830: 8.70,
    1840: 8.29,
    1850: 6.89,
    1860: 6.87,
    1870: 5.87,
    1880: 5.79,
    1890: 4.88,
    1900: 4.58,
    1910: 5.11,
    1920: 5.04,
    1930: 4.74,
    1940: 4.69,
    1950: 4.69,
    1960: 4.09,
    1970: 4.07,
    1980: 4.34,
}
sspec = replace(base, boundaries="modern", interpolation="nearest_census")
sub = []
for y in SUBER_L:
    mm = p.union_members(date(y, 1, 1))
    n = len(mm)
    k = required_states(n, "three_quarters_states")
    ww = p.weights(mm, date(y, 6, 1), sspec)
    sub.append(
        dict(
            year=y,
            n=n,
            k=k,
            L_ours=100 * min_share(ww, k),
            L_suber=SUBER_L[y],
            V_ours=100 * blocking_min_share(ww, n, k),
            V_suber=SUBER_V[y],
        )
    )
res["suber"] = sub

# H. specification ranges (persons unit only)
grid = dict(
    denominator=["all_union", "ex_confederate"],
    date_basis=["adoption", "final"],
    interpolation=["linear", "nearest_census", "step"],
    n_asof=["adoption", "proposal"],
    count_rescissions=[True, False],
    boundaries=["contemporaneous", "modern"],
)
keys = list(grid)
ranges = []
for a in AMS:
    vals = []
    for combo in itertools.product(*grid.values()):
        s = replace(base, coalition_stat="actual", **dict(zip(keys, combo)))
        try:
            v = e.evaluate(a, s).value
        except Exception:
            continue
        if v == v:
            vals.append(v)
    ranges.append(
        dict(
            amendment=a,
            lo=min(vals),
            hi=max(vals),
            n=len(vals),
            default=next(x["threshold"] for x in amend if x["amendment"] == a),
        )
    )
res["spec_ranges"] = ranges

json.dump(res, open(OUT, "w"), default=str)
print("ok")
