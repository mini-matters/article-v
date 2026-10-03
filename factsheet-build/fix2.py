import json, itertools, statistics as s
from datetime import date
from engine.model import *

P = "factsheet-build/facts.json"
r = json.load(open(P))
e = Engine.load()
p = e.panel
t = p.original_thirteen()
w = p.weights(t, date(1788, 6, 21), Spec())
rat = e.ratifiers_by("CONST", date(1788, 6, 21), False)
act = float(w.reindex(rat).sum() / w.sum())
combos = [float(w.reindex(list(c)).sum() / w.sum()) for c in itertools.combinations(t, 9)]
r["founding"] = dict(
    ratifiers=rat,
    actual=act,
    combos=combos,
    pct_below=sum(c < act - 1e-12 for c in combos) / len(combos),
    n=len(combos),
    floor=min(combos),
    max=max(combos),
    median=s.median(combos),
)
print(act, r["founding"]["pct_below"], min(combos), max(combos), s.median(combos))
ev = [
    x for x in r["amendments"] if x["amendment"] not in [str(i) for i in range(2, 11)] + ["U-ERA"]
]
m = dict(
    n=len(ev),
    threshold=s.mean(x["threshold"] for x in ev),
    floor=s.mean(x["floor"] for x in ev),
    final=s.mean(x["final"] for x in ev),
    gained=sum(x["final"] > x["threshold"] + 1e-9 for x in ev),
    below_median=sum(x["threshold"] < x["same_size_median"] for x in ev),
    mean_excess=s.mean(x["threshold"] - x["same_size_median"] for x in ev),
    min_gap=min((x["threshold"] - x["floor"], x["amendment"]) for x in ev),
)
r["event_means"] = m
print(m)
json.dump(r, open(P, "w"), default=str)
