# ruff: noqa: E501
"""Render print figures for the Google Doc from facts.json. Run from docs/paper-article-v/."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "out"
R = json.loads((HERE.parent / "facts.json").read_text())

INK, MUTED, GRID, CONTEXT = "#1a1a1a", "#555555", "#e2e2e2", "#9a9a9a"
BLUE = ORANGE = INK
BAR, BAR_ALT = "#7a7a7a", "#cfcfcf"
W = 6.5

plt.rcParams.update(
    {
        "font.family": "Times New Roman",
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    }
)

EVENTS = [a for a in R["amendments"] if a["amendment"] not in [str(i) for i in range(2, 11)]]
ADOPTED = [a for a in EVENTS if a["amendment"] != "U-ERA"]


def label(a):
    return {"1": "1–10", "U-ERA": "ERA"}.get(a["amendment"], a["amendment"])


def pct(ax, axis="y"):
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)


def admission_years():
    ann = R["annual"]
    return [ann[i]["year"] for i in range(1, len(ann)) if ann[i]["n"] > ann[i - 1]["n"]]


def annual_line(key, name, ylim, ylabel):
    ann = R["annual"]
    x = [r["year"] for r in ann]
    y = [100 * r[key] for r in ann]
    fig, ax = plt.subplots(figsize=(W, 2.6))
    ax.plot(x, y, color=BLUE, lw=1.6)
    for yr in admission_years():
        ax.plot([yr, yr], [ylim[0], ylim[0] + (ylim[1] - ylim[0]) * 0.04], color=MUTED, lw=0.6)
    ax.set_ylim(*ylim)
    ax.set_xlim(1788, 2028)
    ax.set_ylabel(ylabel)
    pct(ax)
    ax.annotate(
        f"{y[-1]:.1f}%", (x[-1], y[-1]), xytext=(-30, 6), textcoords="offset points", color=INK
    )
    save(fig, name)


def fig_k():
    ann = R["annual"]
    x = [r["year"] for r in ann]
    fig, ax = plt.subplots(figsize=(W, 2.4))
    ax.step(x, [r["n"] for r in ann], where="post", color=CONTEXT, lw=1.4)
    ax.step(x, [r["k"] for r in ann], where="post", color=BLUE, lw=1.6)
    ax.text(2027, 50, "States in the union", ha="right", va="bottom", color=MUTED)
    ax.text(2027, 37, "States required", ha="right", va="top", color=BLUE)
    ax.set_ylim(0, 55)
    ax.set_xlim(1788, 2028)
    ax.set_ylabel("States")
    save(fig, "fig03_states_required")


def fig_dist():
    d = R["dist_today"]
    sh = np.array(d["shares"]) * 100
    ct = np.array(d["counts"], dtype=float)
    bins = np.arange(40, 97, 0.5)
    h, _ = np.histogram(sh, bins=bins, weights=ct)
    cum = np.cumsum(ct)
    med = sh[np.searchsorted(cum, cum[-1] * 0.5)]
    fig, ax = plt.subplots(figsize=(W, 2.6))
    ax.bar(bins[:-1], h / ct.sum() * 100, width=0.45, align="edge", color=BAR)
    top = ax.get_ylim()[1]
    for v, t, f, ha in [
        (sh.min(), "Smallest", 0.97, "left"),
        (med, "Median", 1.04, "center"),
        (sh.max(), "Largest", 0.97, "right"),
    ]:
        ax.axvline(v, color=INK, lw=0.7, ls=(0, (2, 2)))
        ax.text(
            v, top * f, f" {t} {v + 1e-9:.1f}% ", va="top" if f < 1 else "bottom", ha=ha, color=INK
        )
    ax.set_xlabel("Population share of a group of 38 states (2020 census)")
    ax.set_ylabel("Share of all groups")
    pct(ax, "x")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    save(fig, "fig04_distribution_38")


GRIDPOS = dict(
    AK=(0, 0),
    ME=(11, 0),
    VT=(10, 1),
    NH=(11, 1),
    WA=(1, 2),
    ID=(2, 2),
    MT=(3, 2),
    ND=(4, 2),
    MN=(5, 2),
    IL=(6, 2),
    WI=(7, 2),
    MI=(8, 2),
    NY=(9, 2),
    RI=(10, 2),
    MA=(11, 2),
    OR=(1, 3),
    NV=(2, 3),
    WY=(3, 3),
    SD=(4, 3),
    IA=(5, 3),
    IN=(6, 3),
    OH=(7, 3),
    PA=(8, 3),
    NJ=(9, 3),
    CT=(10, 3),
    CA=(1, 4),
    UT=(2, 4),
    CO=(3, 4),
    NE=(4, 4),
    MO=(5, 4),
    KY=(6, 4),
    WV=(7, 4),
    VA=(8, 4),
    MD=(9, 4),
    DE=(10, 4),
    AZ=(2, 5),
    NM=(3, 5),
    KS=(4, 5),
    AR=(5, 5),
    TN=(6, 5),
    NC=(7, 5),
    SC=(8, 5),
    OK=(4, 6),
    LA=(5, 6),
    MS=(6, 6),
    AL=(7, 6),
    GA=(8, 6),
    HI=(0, 7),
    TX=(4, 7),
    FL=(9, 7),
)


def fig_maps():
    m = R["maps"]
    post = m["postal"]
    panels = [
        ("The 38 least populous states", m["smallest38"], m["shares"]["s38"], BLUE),
        ("The 13 least populous states", m["smallest13"], m["shares"]["s13"], BLUE),
        ("13 least populous Republican-voting", m["rep13"], m["shares"]["rep"], ORANGE),
        ("13 least populous Democratic-voting", m["dem13"], m["shares"]["dem"], BLUE),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(W, 4.6))
    for ax, (title, sel, share, col) in zip(axes.flat, panels, strict=True):
        sel = {post[s] for s in sel}
        for p, (cx, cy) in GRIDPOS.items():
            on = p in sel
            ax.add_patch(plt.Rectangle((cx, -cy), 0.9, 0.9, color=col if on else "#eeeeee", lw=0))
            ax.text(
                cx + 0.45,
                -cy + 0.45,
                p,
                ha="center",
                va="center",
                fontsize=6,
                color="white" if on else MUTED,
            )
        ax.set_xlim(-0.2, 12)
        ax.set_ylim(-7.3, 1.1)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{title}\n{100 * share:.1f}% of the population", fontsize=9, color=INK)
    fig.tight_layout()
    save(fig, "fig05_blocking_sets")


def fig_statehood(floors):
    fig, ax = plt.subplots(figsize=(W, 1.5))
    ax.grid(False)
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    for i, (lab, v) in enumerate(floors):
        ax.plot(v, 0, "o", ms=8, color=BLUE, mec="white", mew=1.5)
        ax.annotate(
            f"{lab}\n{v:.2f}%",
            (v, 0),
            xytext=(0, 10 if i != 1 else -26),
            textcoords="offset points",
            ha="center",
            color=INK,
            fontsize=9,
        )
    ax.set_xlim(38.4, 41)
    ax.set_ylim(-1, 1)
    ax.set_xlabel("Ratification floor, 2020 census")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    save(fig, "fig06_statehood")


def fig_founding():
    f = R["founding"]
    c = np.array(f["combos"]) * 100
    fig, ax = plt.subplots(figsize=(W, 2.4))
    bins = np.arange(np.floor(c.min()), np.ceil(c.max()) + 1, 1)
    ax.hist(c, bins=bins, color=BAR_ALT, rwidth=0.85)
    ax.axvline(f["actual"] * 100, color=BLUE, lw=1.6)
    ax.text(
        f["actual"] * 100,
        ax.get_ylim()[1] * 1.02,
        f"The nine that ratified: {f['actual'] * 100:.1f}%",
        color=BLUE,
        va="bottom",
        ha="center",
    )
    ax.set_xlabel("Population share of a group of nine of the thirteen states (1790 census)")
    ax.set_ylabel("Number of groups")
    pct(ax, "x")
    save(fig, "fig08_founding")


def fig_dumbbell():
    ev = EVENTS
    xs = [i + (0.6 if a["amendment"] == "U-ERA" else 0) for i, a in enumerate(ev)]
    fig, ax = plt.subplots(figsize=(W, 3.2))
    for x, a in zip(xs, ev, strict=True):
        ax.plot([x, x], [a["floor"] * 100, a["final"] * 100], color=GRID, lw=2, zorder=1)
        ax.plot(x, a["floor"] * 100, "_", ms=9, mew=1.4, color=MUTED, zorder=2)
        ax.plot(x, a["threshold"] * 100, "o", ms=4.5, color=BLUE, mec="white", mew=0.8, zorder=4)
        ax.plot(x, a["final"] * 100, "o", ms=6, color="white", mec=BLUE, mew=1.3, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([label(a) for a in ev], fontsize=8)
    ax.axvline(xs[-1] - 0.8, color=MUTED, lw=0.5)
    ax.set_xlim(-0.7, xs[-1] + 0.7)
    ax.set_ylim(30, 102)
    pct(ax)
    ax.set_ylabel("Share of the population")
    ax.set_xlabel("Ratification event, in order of adoption; ERA at right")
    h = [
        plt.Line2D(
            [], [], marker="_", ls="", color=MUTED, ms=9, mew=1.4, label="Ratification floor"
        ),
        plt.Line2D([], [], marker="o", ls="", color=BLUE, mec="white", label="Threshold share"),
        plt.Line2D([], [], marker="o", ls="", color="white", mec=BLUE, label="Final share"),
    ]
    ax.legend(handles=h, loc="lower left", frameon=False, ncol=3, bbox_to_anchor=(0, 1.0))
    save(fig, "fig09_threshold_final")


def fig_percentile():
    fig, ax = plt.subplots(figsize=(W, 1.9))
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    ax.axvline(50, color=MUTED, lw=0.6, ls=(0, (2, 2)))
    ax.text(50, 1.05, "median group", ha="center", color=MUTED, fontsize=8)
    xs = [a["pct_below"] * 100 for a in ADOPTED]
    order = np.argsort(xs)
    ys = np.empty(len(xs))
    ys[order] = np.tile([-0.45, -0.15, 0.15, 0.45], 5)[: len(xs)]
    ax.scatter(xs, ys, s=40, color=BLUE, edgecolor="white", lw=1, zorder=3)
    for a, x, y in zip(ADOPTED, xs, ys, strict=True):
        if x < 10:
            ax.annotate(
                label(a), (x, y), xytext=(5, -3), textcoords="offset points", fontsize=8, color=INK
            )
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.8, 1.2)
    pct(ax, "x")
    ax.set_xlabel("Share of same-size groups holding fewer people than the ratifying states")
    save(fig, "fig11_percentile")


def fig_time():
    ev = EVENTS
    fig, ax = plt.subplots(figsize=(W, 4.4))
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ys = list(range(len(ev), 0, -1))
    ax.barh(
        ys,
        [a["years_to_adopt"] for a in ev],
        color=[BAR_ALT if a["amendment"] == "U-ERA" else BAR for a in ev],
        height=0.6,
    )
    ax.set_xscale("log")
    ax.set_xlim(0.2, 300)
    ax.set_yticks(ys)
    ax.set_yticklabels([label(a) for a in ev])
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.axvline(4, color=MUTED, lw=0.6, ls=(0, (2, 2)))
    for y, a in zip(ys, ev, strict=True):
        ax.text(
            a["years_to_adopt"] * 1.08,
            y,
            f"{a['years_to_adopt']:.1f}",
            va="center",
            fontsize=8,
            color=INK,
        )
    ax.set_xlabel(
        "Years from proposal to three-quarters (log scale); ERA: to its 38th ratification"
    )
    save(fig, "fig12_time")


def fig_rej():
    ev = EVENTS
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 4.2), sharey=True)
    ys = list(range(len(ev), 0, -1))
    for ax, key, title in [(a1, "rejections", "Rejections"), (a2, "rescissions", "Rescissions")]:
        vals = [a[key] for a in ev]
        ax.barh(
            ys, vals, color=[BAR_ALT if a["amendment"] == "U-ERA" else BAR for a in ev], height=0.6
        )
        ax.grid(axis="x", color=GRID)
        ax.grid(axis="y", visible=False)
        ax.set_title(title, fontsize=10, color=INK)
        ax.set_xlim(0, 10)
        for y, v in zip(ys, vals, strict=True):
            if v:
                ax.text(v + 0.15, y, str(v), va="center", fontsize=8, color=INK)
    a1.set_yticks(ys)
    a1.set_yticklabels([label(a) for a in ev])
    fig.supxlabel("State actions recorded in the ledger", fontsize=10)
    fig.tight_layout()
    save(fig, "fig13_rejections")


def fig_21():
    rows = [r for r in R["c21"] if r["yes"] is not None]
    rows.sort(key=lambda r: r["yes"])
    fig, ax = plt.subplots(figsize=(W, 5.6))
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ys = range(len(rows), 0, -1)
    mx = max(r["pop1930"] for r in rows)
    for y, r in zip(ys, rows, strict=True):
        s = 12 + 150 * r["pop1930"] / mx
        if r["ratified"]:
            ax.scatter(r["yes"] * 100, y, s=s, color=BLUE, edgecolor="white", lw=0.8, zorder=3)
        else:
            ax.scatter(r["yes"] * 100, y, s=s, color="white", edgecolor=ORANGE, lw=1.3, zorder=3)
    ax.axvline(200 / 3, color=MUTED, lw=0.6, ls=(0, (2, 2)))
    ax.axvline(50, color=MUTED, lw=0.6)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r["state"] for r in rows], fontsize=7)
    ax.set_xlim(25, 100)
    pct(ax, "x")
    ax.set_xlabel("Share of the statewide vote for repeal, 1933")
    h = [
        plt.Line2D(
            [], [], marker="o", ls="", color=BLUE, mec="white", ms=7, label="Convention ratified"
        ),
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            color="white",
            mec=ORANGE,
            mew=1.3,
            ms=7,
            label="Did not ratify",
        ),
        plt.Line2D([], [], color=MUTED, lw=0.6, ls=(0, (2, 2)), label="Two-thirds"),
    ]
    ax.legend(handles=h, loc="lower left", frameon=False)
    save(fig, "fig14_21st")


def fig_range():
    rng = {x["amendment"]: x for x in R["spec_ranges"]}
    ev = ADOPTED
    fig, ax = plt.subplots(figsize=(W, 4.4))
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ys = list(range(len(ev), 0, -1))
    for y, a in zip(ys, ev, strict=True):
        r = rng[a["amendment"]]
        ax.plot(
            [r["lo"] * 100, r["hi"] * 100],
            [y, y],
            color=BLUE,
            lw=5,
            solid_capstyle="round",
            alpha=0.35,
        )
        ax.plot(r["default"] * 100, y, "o", ms=5, color=BLUE, mec="white", mew=1)
        if r["hi"] - r["lo"] > 0.05:
            ax.text(
                r["hi"] * 100 + 0.6,
                y,
                f"{r['lo'] * 100:.1f}–{r['hi'] * 100:.1f}%",
                va="center",
                fontsize=8,
                color=INK,
            )
    ax.set_yticks(ys)
    ax.set_yticklabels([label(a) for a in ev])
    ax.set_xlim(60, 97)
    pct(ax, "x")
    ax.set_xlabel("Threshold share across 24 specifications (bar) and default specification (dot)")
    save(fig, "fig15_sensitivity")


def fig_records():
    recs = {x["amendment"]: x for x in R["records_tday"]}
    ev = ADOPTED
    code = {"tally": 2, "no_tally": 1, "not_collected": 0}
    names = {2: "Tally located", 1: "Action recorded, no tally located", 0: "Not collected"}
    fig, ax = plt.subplots(figsize=(W, 1.9))
    ax.grid(False)
    for i, a in enumerate(ev):
        c = code[recs[a["amendment"]]["status"]]
        style = (
            dict(color=BLUE)
            if c == 2
            else dict(color="white", mec=BLUE, mew=1.3)
            if c == 1
            else dict(color="white", mec=CONTEXT, mew=1.0)
        )
        ax.plot(i, c, "o", ms=9, **style)
    ax.set_xticks(range(len(ev)))
    ax.set_xticklabels([label(a) for a in ev], fontsize=8)
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels([names[k] for k in (0, 1, 2)], fontsize=8)
    ax.set_ylim(-0.6, 2.6)
    ax.set_xlabel("Ratification event")
    save(fig, "fig16_records")


def ratify_tallies():
    return [m for m in R["margins"] if m["action"].startswith("ratify")]


def fig_margins():
    ms = np.array([m["margin"] * 100 for m in ratify_tallies()])
    fig, ax = plt.subplots(figsize=(W, 2.4))
    ax.hist(ms, bins=np.arange(0, 105, 5), color=BAR, rwidth=0.85)
    med = float(np.median(ms))
    ax.axvline(med, color=INK, lw=0.7, ls=(0, (2, 2)))
    ax.text(
        med, ax.get_ylim()[1] * 0.97, f"Median {med:.0f} points ", va="top", ha="right", color=INK
    )
    ax.set_xlabel("Margin, (yeas − nays) ÷ (yeas + nays), in percentage points")
    ax.set_ylabel("Chamber tallies")
    save(fig, "fig17_margins")


def fig_suber():
    s = R["suber"]
    x = [r["year"] for r in s]
    fig, ax = plt.subplots(figsize=(W, 2.4))
    ax.axhspan(-0.1, 0.1, color="#eeeeee", lw=0)
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.plot(
        x,
        [r["L_ours"] - r["L_suber"] for r in s],
        "o-",
        color=BLUE,
        ms=4,
        lw=1,
        label="Ratification floor (L)",
    )
    ax.plot(
        x,
        [r["V_ours"] - r["V_suber"] for r in s],
        "s--",
        color=INK,
        mfc="white",
        ms=4,
        lw=1,
        label="Blocking floor (V)",
    )
    ax.set_ylabel("This work − Suber (points)")
    ax.set_ylim(-0.5, 1.7)
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig18_suber")


GREY = "#9a9a9a"
S_DOT, S_RING = 22, 16


def _frac_year(d):
    return int(d[:4]) + (int(d[5:7]) - 0.5) / 12


def _median(shares, counts):
    sh = np.asarray(shares)
    cum = np.cumsum(np.asarray(counts, dtype=float))
    return float(sh[np.searchsorted(cum, cum[-1] * 0.5)])


def fig_overview(unit):
    """Figure 0.1 (unit='share') and 0.2 (unit='people'): one timeline of Figures 1-4 and 8."""
    ann = R["annual"]
    yrs = np.array([r["year"] for r in ann], dtype=float)
    tot = np.array([r["total"] for r in ann])
    fl = np.array([r["floor"] for r in ann])
    bl = np.array([r["block"] for r in ann])
    ev_x = [_frac_year(a["adopted"]) for a in ADOPTED]
    ev_tot = np.interp(ev_x, yrs, tot)
    era = [(_frac_year(p["date"]), p) for p in R["era_points"]]
    t20 = next(r["total"] for r in ann if r["year"] == 2020)
    d38, d13 = R["dist_today"], R["dist13_today"]
    med38, med13 = _median(d38["shares"], d38["counts"]), _median(d13["shares"], d13["counts"])
    max38, max13 = max(d38["shares"]), max(d13["shares"])
    people = unit == "people"

    def y(share, total=None):
        v = np.asarray(share, dtype=float)
        return v * (tot if total is None else total) / 1e6 if people else 100 * v

    def yv(share, total):
        return share * total / 1e6 if people else 100 * share

    with plt.rc_context({"font.size": 8, "xtick.labelsize": 8, "ytick.labelsize": 8}):
        fig = plt.figure(figsize=(W, 6.0))
        gs = fig.add_gridspec(
            2, 2, width_ratios=[5.0, 1.5], height_ratios=[4.2, 0.6], wspace=0.04, hspace=0.16
        )
        ax = fig.add_subplot(gs[0, 0])
        col = fig.add_subplot(gs[0, 1], sharey=ax)
        lab = fig.add_subplot(gs[1, 0], sharex=ax)
        legax = fig.add_subplot(gs[1, 1])

        if people:
            ax.plot(yrs, tot / 1e6, color=MUTED, lw=1.0)
        ax.plot(yrs, y(fl), color=INK, lw=1.5)
        ax.plot(yrs, y(bl), color=INK, lw=1.5, ls=(0, (4, 2)))
        th = [yv(a["threshold"], t) for a, t in zip(ADOPTED, ev_tot, strict=True)]
        fn = [yv(a["final"], t) for a, t in zip(ADOPTED, ev_tot, strict=True)]
        for x, lo, hi in zip(ev_x, th, fn, strict=True):
            ax.plot([x, x], [lo, hi], color=GREY, lw=0.8, zorder=2)
        ax.scatter(
            ev_x, fn, s=S_RING, facecolor="white", edgecolor=INK, lw=0.9, zorder=3, clip_on=False
        )
        ax.scatter(ev_x, th, s=S_DOT, color=INK, edgecolor="white", lw=0.8, zorder=4)
        for x, pt in era:
            t = float(np.interp(x, yrs, tot))
            hi, lo = yv(pt["share_ignored"], t), yv(pt["share_counted"], t)
            ax.plot([x, x], [lo, hi], color=GREY, lw=2.2, solid_capstyle="butt", zorder=2)
            ax.scatter(
                [x], [hi], marker="D", s=S_RING, facecolor="white", edgecolor=GREY, lw=1.1, zorder=3
            )
        ax.set_xlim(1786, 2028)
        if people:
            ax.set_yscale("log")
            ax.set_ylim(0.25, 520)
            ax.set_yticks([0.3, 1, 3, 10, 30, 100, 300])
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
            ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
            ax.set_ylabel("People, millions (log scale)")
            ax.text(
                2027,
                tot[-1] / 1e6 * 1.12,
                "All states",
                ha="right",
                va="bottom",
                fontsize=7,
                color=MUTED,
            )
        else:
            ax.set_ylim(0, 104)
            ax.set_yticks([0, 20, 40, 60, 80, 100])
            pct(ax)
            ax.set_ylabel("Share of the population")
        ax.set_xticks([1800, 1850, 1900, 1950, 2000, 2026])
        ax.tick_params(axis="x", length=3)
        base = ax.get_ylim()[0]
        tick_top = base * 1.25 if people else 1.6
        for x in ev_x + [x for x, _ in era]:
            ax.plot([x, x], [base, tick_top], color=MUTED, lw=0.6)

        # right column: a new amendment today
        col.grid(False)
        for sp in ("left", "bottom", "right", "top"):
            col.spines[sp].set_visible(False)
        col.tick_params(left=False, labelleft=False, bottom=False, labelbottom=False)
        for d, shade in ((d38, "#bdbdbd"), (d13, "#d9d9d9")):
            vals = np.array(d["shares"]) * (t20 / 1e6 if people else 100)
            bins = np.geomspace(0.25, 520, 120) if people else np.arange(0, 100.5, 1.0)
            h, edges = np.histogram(vals, bins=bins, weights=np.array(d["counts"], dtype=float))
            col.barh(
                edges[:-1],
                h / h.max() * 0.5,
                height=np.diff(edges) * 0.92,
                align="edge",
                color=shade,
                lw=0,
            )
        unit_fmt = (
            (lambda v: f"{v:.0f}M" if v >= 10 else f"{v:.1f}M")
            if people
            else (lambda v: f"{v + 1e-9:.1f}%")
        )
        marks = [
            (yv(med38, t20), "typical 38", MUTED, "-", 0.8),
            (yv(fl[-1], t20), "smallest 38: can ratify", INK, "-", 1.4),
            (yv(med13, t20), "typical 13", MUTED, "-", 0.8),
            (yv(bl[-1], t20), "smallest 13: can block", INK, (0, (4, 2)), 1.4),
        ]
        if people:
            marks.insert(0, (t20 / 1e6, "everyone", MUTED, "-", 0.8))
        for v, name, c, ls, lw in marks:
            col.plot([0, 0.56], [v, v], color=c, lw=lw, ls=ls)
            col.text(0.6, v, f"{unit_fmt(v)}  {name}", va="center", fontsize=7, color=c)
        col.set_xlim(0, 2.3)
        col.set_title("A new amendment today\n(2020 census)", fontsize=8)

        # rows under the year axis
        lab.set_ylim(0, 1)
        lab.axis("off")
        items = sorted(
            [(x, label(a), INK) for x, a in zip(ev_x, ADOPTED, strict=True)]
            + [(x, "ERA", GREY) for x, _ in era]
        )
        gap = {"1–10": 14.0, "ERA": 13.0}
        pos = [x for x, _, _ in items]
        for _ in range(300):
            moved = False
            for k in range(1, len(pos)):
                need = (gap.get(items[k - 1][1], 8.6) + gap.get(items[k][1], 8.6)) / 2
                if pos[k] - pos[k - 1] < need:
                    dlt = (need - (pos[k] - pos[k - 1])) / 2
                    pos[k - 1] -= dlt
                    pos[k] += dlt
                    moved = True
            pos[0] = max(pos[0], 1792.0)
            if not moved:
                break
        for (x, t, c), px in zip(items, pos, strict=True):
            lab.plot([x, px], [1.0, 0.86], color=GREY, lw=0.5, clip_on=False)
            lab.text(px, 0.84, t, ha="center", va="top", fontsize=7, color=c)
        lab.text(1782, 0.84, "Amendment", ha="right", va="top", fontsize=7, color=MUTED)
        seen = None
        for r in ann:
            if r["k"] != seen and r["year"] in (1790, 1803, 1821, 1846, 1867, 1890, 1912, 1960):
                lab.text(
                    r["year"], 0.5, str(r["k"]), ha="center", va="top", fontsize=7, color=MUTED
                )
            seen = r["k"] if r["year"] in (1790, 1803, 1821, 1846, 1867, 1890, 1912, 1960) else seen
        lab.text(1782, 0.5, "States required", ha="right", va="top", fontsize=7, color=MUTED)

        L = R["legislators"]
        legax.axis("off")
        legax.set_xlim(0, 1)
        legax.set_ylim(0, 1)
        legax.text(0.02, 0.98, "State legislators needed", fontsize=7, va="top", color=INK)
        legax.text(
            0.02, 0.74, f"To ratify: {L['ratify_min']:,}–{L['ratify_max']:,}", fontsize=7, va="top"
        )
        legax.text(
            0.02, 0.52, f"To block: {L['block_min']:,}–{L['block_max']:,}", fontsize=7, va="top"
        )
        legax.text(
            0.02,
            0.30,
            f"of {L['seated']:,} seated ({L['year']})",
            fontsize=7,
            va="top",
            color=MUTED,
        )

        dl, rc = R["era_points"]
        entries = [
            ("line", "Ratification floor: smallest group of states that can ratify"),
            ("dash", "Blocking floor: smallest group of states that can block"),
            ("dot", "Threshold share: states that had ratified when three-quarters was reached"),
            ("ring", "Final share: every state that ever ratified"),
            (
                "diamond",
                f"ERA, not adopted. 1982 deadline: {dl['n_ignored']} of 38 states. 2020: {rc['n_ignored']} recorded, 3 after the deadline. Bar: if rescissions count ({rc['n_counted']})",
            ),
            (
                "bars",
                "Right column: every possible group of 38 states (dark; largest "
                + unit_fmt(yv(max38, t20))
                + ") and of 13 states (light; largest "
                + unit_fmt(yv(max13, t20))
                + ")",
            ),
            (
                "none",
                "Legislators: a majority of all seats in each chamber (one chamber suffices to block); a model, not each state's own rule",
            ),
        ]
        if people:
            entries.insert(
                0, ("grey", "All states: resident population of the states in the union")
            )
        kax = fig.add_axes(
            [0.07, -0.07 - 0.024 * (len(entries) - 7), 0.9, 0.17 + 0.024 * (len(entries) - 7)]
        )
        kax.axis("off")
        kax.set_xlim(0, 1)
        kax.set_ylim(0, len(entries))
        for i, (kind, text) in enumerate(entries):
            yy = len(entries) - i - 0.5
            if kind in ("line", "dash", "grey"):
                kax.plot(
                    [0, 0.04],
                    [yy, yy],
                    color=MUTED if kind == "grey" else INK,
                    lw=1.0 if kind == "grey" else 1.5,
                    ls=(0, (4, 2)) if kind == "dash" else "-",
                )
            elif kind == "dot":
                kax.scatter([0.02], [yy], s=S_DOT, color=INK)
            elif kind == "ring":
                kax.scatter([0.02], [yy], s=S_RING, facecolor="white", edgecolor=INK, lw=0.9)
            elif kind == "diamond":
                kax.scatter(
                    [0.02], [yy], marker="D", s=S_RING, facecolor="white", edgecolor=GREY, lw=1.1
                )
            elif kind == "bars":
                kax.add_patch(plt.Rectangle((0.005, yy - 0.22), 0.03, 0.44, color="#bdbdbd", lw=0))
            kax.text(0.06, yy, text, va="center", fontsize=7, color=INK)
        save(fig, "fig00_1_overview_share" if not people else "fig00_2_overview_people")


def _amend_row(lab, y=0.84):
    ev_x = [_frac_year(a["adopted"]) for a in ADOPTED]
    era_x = [_frac_year(pt["date"]) for pt in R["era_points"]]
    items = sorted(
        [(x, label(a), INK) for x, a in zip(ev_x, ADOPTED, strict=True)]
        + [(x, "ERA", GREY) for x in era_x]
    )
    gap = {"1–10": 14.0, "ERA": 13.0}
    pos = [x for x, _, _ in items]
    for _ in range(300):
        moved = False
        for k in range(1, len(pos)):
            need = (gap.get(items[k - 1][1], 8.6) + gap.get(items[k][1], 8.6)) / 2
            if pos[k] - pos[k - 1] < need:
                dlt = (need - (pos[k] - pos[k - 1])) / 2
                pos[k - 1] -= dlt
                pos[k] += dlt
                moved = True
        pos[0] = max(pos[0], 1792.0)
        if not moved:
            break
    for (x, t, c), px in zip(items, pos, strict=True):
        lab.plot([x, px], [1.0, y + 0.02], color=GREY, lw=0.5, clip_on=False)
        lab.text(px, y, t, ha="center", va="top", fontsize=7, color=c)
    lab.text(1782, y, "Amendment", ha="right", va="top", fontsize=7, color=MUTED)
    return ev_x + era_x


def _column(c, marks, title=None):
    c.grid(False)
    for sp in ("left", "bottom", "right", "top"):
        c.spines[sp].set_visible(False)
    c.tick_params(left=False, labelleft=False, bottom=False, labelbottom=False)
    for v, text, color, lw, ls in marks:
        c.plot([0, 0.35], [v, v], color=color, lw=lw, ls=ls)
        c.text(0.4, v, text, va="center", fontsize=7, color=color)
    c.set_xlim(0, 2.3)
    if title:
        c.set_title(title, fontsize=8)


def _key(fig, entries, bottom):
    kax = fig.add_axes([0.07, bottom, 0.9, 0.024 * len(entries)])
    kax.axis("off")
    kax.set_xlim(0, 1)
    kax.set_ylim(0, len(entries))
    styles = {
        "grey": dict(color=MUTED, lw=1.0),
        "line": dict(color=INK, lw=1.5),
        "thin": dict(color=INK, lw=0.8),
        "dash": dict(color=INK, lw=1.5, ls=(0, (4, 2))),
        "thindash": dict(color=INK, lw=0.8, ls=(0, (4, 2))),
        "ring": dict(color=INK, lw=0.9, marker="o", ms=3, mfc="white", markevery=[1]),
        "dashring": dict(
            color=INK, lw=0.9, ls=(0, (4, 2)), marker="o", ms=3, mfc="white", markevery=[1]
        ),
    }
    for i, (kind, text) in enumerate(entries):
        yy = len(entries) - i - 0.5
        if kind in styles:
            kax.plot([0, 0.02, 0.04], [yy, yy, yy], **styles[kind])
        elif kind == "band":
            kax.add_patch(plt.Rectangle((0.005, yy - 0.22), 0.03, 0.44, color="#d9d9d9", lw=0))
        kax.text(0.06, yy, text, va="center", fontsize=7, color=INK)


def _legislator_axes(ax, ticks_at):
    ax.set_xlim(1786, 2028)
    ax.set_xticks([1800, 1850, 1900, 1950, 2000, 2026])
    ax.axvspan(1786, 1829, color="#f5f5f5", lw=0, zorder=0)
    lo = ax.get_ylim()[0]
    for x in ticks_at:
        ax.plot([x, x], [lo, lo * 1.2], color=MUTED, lw=0.6)


def _fill_note():
    f = R["leg_filled"]
    return "; ".join(
        f"{d['snapshot']}: {d['state']} {d['chamber']} not in the source, filled with {d['seats']} seats from {d['from_year']}"
        for d in f
    )


def fig_legislators():
    """Figure 0.3: state legislators needed to ratify and to block."""
    df = R["leg_series"]
    x = [d["year"] for d in df]
    g = lambda k: [d[k] for d in df]  # noqa: E731
    with plt.rc_context({"font.size": 8, "xtick.labelsize": 8, "ytick.labelsize": 8}):
        fig = plt.figure(figsize=(W, 5.2))
        gs = fig.add_gridspec(
            2, 2, width_ratios=[5.0, 1.5], height_ratios=[4.2, 0.6], wspace=0.04, hspace=0.16
        )
        ax = fig.add_subplot(gs[0, 0])
        col = fig.add_subplot(gs[0, 1], sharey=ax)
        lab = fig.add_subplot(gs[1, 0], sharex=ax)
        ax.plot(x, g("seated"), color=MUTED, lw=1.0, marker="o", ms=2.5)
        ax.fill_between(x, g("ratify_min"), g("ratify_max"), color="#d9d9d9", lw=0)
        ax.plot(x, g("ratify_min"), color=INK, lw=1.5, marker="o", ms=3)
        ax.plot(x, g("ratify_max"), color=INK, lw=0.8, marker="o", ms=2.5, mfc="white")
        ax.fill_between(x, g("block_min"), g("block_max"), color="#ececec", lw=0)
        ax.plot(x, g("block_min"), color=INK, lw=1.5, ls=(0, (4, 2)), marker="o", ms=3)
        ax.plot(
            x, g("block_max"), color=INK, lw=0.8, ls=(0, (4, 2)), marker="o", ms=2.5, mfc="white"
        )
        ax.set_yscale("log")
        ax.set_ylim(30, 12000)
        ax.set_yticks([30, 100, 300, 1000, 3000, 10000])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax.set_ylabel("State legislators (log scale)")
        lab.set_ylim(0, 1)
        lab.axis("off")
        _legislator_axes(ax, _amend_row(lab))
        ax.text(1807, 60, "no complete\nrecord", ha="center", fontsize=7, color=MUTED)
        for d in df:
            if d["year"] in (1830, 1870, 1900, 1940, 1960, 2026):
                lab.text(
                    d["year"],
                    0.5,
                    f"{d['k']} / {d['n'] - d['k'] + 1}",
                    ha="center",
                    va="top",
                    fontsize=7,
                    color=MUTED,
                )
        lab.text(
            1782, 0.5, "States to ratify / block", ha="right", va="top", fontsize=7, color=MUTED
        )
        last = df[-1]
        _column(
            col,
            [
                (last["seated"], f"{last['seated']:,}  seated", MUTED, 0.8, "-"),
                (last["ratify_max"], f"{last['ratify_max']:,}  most to ratify", INK, 0.8, "-"),
                (last["ratify_min"], f"{last['ratify_min']:,}  fewest to ratify", INK, 1.5, "-"),
                (last["block_max"], f"{last['block_max']:,}  most to block", INK, 0.8, (0, (4, 2))),
                (
                    last["block_min"],
                    f"{last['block_min']:,}  fewest to block",
                    INK,
                    1.5,
                    (0, (4, 2)),
                ),
            ],
            f"A new amendment today\n({last['year']} seats)",
        )
        entries = [
            ("grey", "All state legislators seated"),
            (
                "line",
                "Fewest legislators who can ratify: a majority of both chambers in the 38 states with the smallest legislatures",
            ),
            (
                "thin",
                "Most legislators a ratification can require: the same for the 38 largest legislatures (shaded between)",
            ),
            (
                "dash",
                "Fewest who can block: a majority of one chamber (the smaller) in the 13 states where that is smallest",
            ),
            (
                "thindash",
                "Most a block can require: the same in the 13 states where it is largest (shaded between)",
            ),
            (
                "none",
                "Snapshots where every state's chamber sizes are recorded; 19th-century sizes carry up to 3% error. "
                + _fill_note(),
            ),
            (
                "none",
                "A model (a majority of all seats in each chamber), not each state's own vote rule",
            ),
        ]
        _key(fig, entries, -0.12)
        save(fig, "fig00_3_legislators")


def fig_represented():
    """Figure 0.4: the population those legislators represent."""
    df = R["leg_series"]
    x = [d["year"] for d in df]
    g = lambda k: np.array([d[k] for d in df], dtype=float)  # noqa: E731
    ann = R["annual"]
    yrs = [r["year"] for r in ann]
    fl = [100 * r["floor"] for r in ann]
    bl = [100 * r["block"] for r in ann]
    with plt.rc_context({"font.size": 8, "xtick.labelsize": 8, "ytick.labelsize": 8}):
        fig = plt.figure(figsize=(W, 6.4))
        gs = fig.add_gridspec(
            3, 2, width_ratios=[5.0, 1.5], height_ratios=[2.9, 1.9, 0.6], wspace=0.04, hspace=0.14
        )
        ax = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[1, 0], sharex=ax)
        col = fig.add_subplot(gs[0, 1], sharey=ax)
        col2 = fig.add_subplot(gs[1, 1], sharey=ax2)
        lab = fig.add_subplot(gs[2, 0], sharex=ax)
        ax.plot(yrs, fl, color=INK, lw=1.5)
        ax.plot(x, 100 * g("ratify_min_share"), color=INK, lw=0.9, marker="o", ms=3, mfc="white")
        ax.plot(yrs, bl, color=INK, lw=1.5, ls=(0, (4, 2)))
        ax.plot(
            x,
            100 * g("block_min_share"),
            color=INK,
            lw=0.9,
            ls=(0, (4, 2)),
            marker="o",
            ms=3,
            mfc="white",
        )
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 20, 40, 60, 80, 100])
        pct(ax)
        ax.set_ylabel("Share of the population")
        ax.tick_params(axis="x", labelbottom=False)
        ax.axvspan(1786, 1829, color="#f5f5f5", lw=0, zorder=0)
        ax.text(
            1807,
            88,
            "no complete\nlegislature\nrecord",
            ha="center",
            va="top",
            fontsize=7,
            color=MUTED,
        )
        ax2.fill_between(x, g("constituency_min"), g("constituency_max"), color="#e3e3e3", lw=0)
        ax2.plot(x, g("constituency_max"), color=INK, lw=0.8, marker="o", ms=2.5, mfc="white")
        ax2.plot(x, g("constituency_min"), color=INK, lw=0.8, marker="o", ms=2.5, mfc="white")
        ax2.plot(x, g("people_per_legislator"), color=INK, lw=1.5, marker="o", ms=3)
        ax2.set_yscale("log")
        ax2.set_ylim(300, 1_000_000)
        ax2.set_yticks([1_000, 10_000, 100_000, 1_000_000])
        ax2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax2.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
        ax2.set_ylabel("People per legislator\n(log scale)")
        lab.set_ylim(0, 1)
        lab.axis("off")
        _legislator_axes(ax2, _amend_row(lab))
        last = df[-1]
        _column(
            col,
            [
                (
                    100 * last["ratify_min_share"],
                    f"{100 * last['ratify_min_share'] + 1e-9:.1f}%  fewest-legislator ratifiers",
                    INK,
                    0.9,
                    "-",
                ),
                (fl[-1], f"{fl[-1] + 1e-9:.1f}%  fewest-people ratifiers", INK, 1.5, "-"),
                (
                    100 * last["block_min_share"],
                    f"{100 * last['block_min_share'] + 1e-9:.1f}%  fewest-legislator blockers",
                    INK,
                    0.9,
                    (0, (4, 2)),
                ),
                (bl[-1], f"{bl[-1] + 1e-9:.1f}%  fewest-people blockers", INK, 1.5, (0, (4, 2))),
            ],
            "A new amendment today",
        )
        _column(
            col2,
            [
                (
                    last["constituency_max"],
                    f"{last['constituency_max']:,.0f}  {last['constituency_max_state']}",
                    INK,
                    0.8,
                    "-",
                ),
                (
                    last["people_per_legislator"],
                    f"{last['people_per_legislator']:,.0f}  national average",
                    INK,
                    1.5,
                    "-",
                ),
                (
                    last["constituency_min"],
                    f"{last['constituency_min']:,.0f}  {last['constituency_min_state']}",
                    INK,
                    0.8,
                    "-",
                ),
            ],
        )
        entries = [
            ("line", "Fewest people who can ratify: the ratification floor (Figure 0.1)"),
            (
                "ring",
                "Population of the 38 states whose legislatures need the fewest yes votes to ratify (Figure 0.3)",
            ),
            ("dash", "Fewest people who can block: the blocking floor"),
            ("dashring", "Population of the 13 states where the fewest legislators can block"),
            ("line", "People per state legislator, all states (lower panel)"),
            (
                "band",
                "Range across states: people per seat in each state's lower (or only) chamber",
            ),
            ("none", _fill_note() + ". Legislator counts are a model (a majority of all seats)"),
        ]
        _key(fig, entries, -0.08)
        save(fig, "fig00_4_represented")


def render(floors):
    fig_overview("share")
    fig_overview("people")
    fig_legislators()
    fig_represented()
    annual_line("floor", "fig01_ratification_floor", (35, 60), "Ratification floor")
    annual_line("block", "fig02_blocking_floor", (0, 14), "Blocking floor")
    fig_k()
    fig_dist()
    fig_maps()
    fig_statehood(floors)
    fig_founding()
    fig_dumbbell()
    fig_percentile()
    fig_time()
    fig_rej()
    fig_21()
    fig_range()
    fig_records()
    fig_margins()
    fig_suber()
    return sorted(p.name for p in OUT.glob("*.png"))


if __name__ == "__main__":
    print(render([("50 states", 40.38), ("+ DC", 40.51), ("+ DC and PR", 38.79)]))
