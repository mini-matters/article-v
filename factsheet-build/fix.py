import json, itertools
from dataclasses import replace
from engine.model import *

P = "factsheet-build/facts.json"
r = json.load(open(P))
e = Engine.load()
base = Spec()
c = e.evaluate("CONST", replace(base, coalition_stat="actual"))
print("CONST", c.on, c.value, c.n_states, c.k_required)
grid = dict(
    denominator=["all_union", "ex_confederate"],
    interpolation=["linear", "nearest_census", "step"],
    count_rescissions=[True, False],
    boundaries=["contemporaneous", "modern"],
)
out = []
for a in [x["amendment"] for x in r["amendments"]]:
    vals = [
        e.evaluate(a, replace(base, coalition_stat="actual", **dict(zip(grid, cmb)))).value
        for cmb in itertools.product(*grid.values())
    ]
    vals = [v for v in vals if v == v]
    d = next(x for x in r["amendments"] if x["amendment"] == a)
    out.append(dict(amendment=a, lo=min(vals), hi=max(vals), n=len(vals), default=d["threshold"]))
r["spec_ranges"] = out
ev = [x for x in r["amendments"] if x["amendment"] not in [str(i) for i in range(2, 11)]]
import statistics as s

print(
    "events",
    len(ev),
    "mean th",
    s.mean(x["threshold"] for x in ev),
    "mean floor",
    s.mean(x["floor"] for x in ev),
    "mean final",
    s.mean(x["final"] for x in ev),
)
r["event_means"] = dict(
    n=len(ev),
    threshold=s.mean(x["threshold"] for x in ev),
    floor=s.mean(x["floor"] for x in ev),
    final=s.mean(x["final"] for x in ev),
)
json.dump(r, open(P, "w"), default=str)
for x in out:
    print(x["amendment"], round(x["lo"] * 100, 1), round(x["hi"] * 100, 1), x["n"])
