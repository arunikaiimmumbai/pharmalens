"""Ranking & scenarios engine.

Scorecard (user framework): Revenue growth 20, Profitability 25, Cash generation 20, Capital efficiency 15,
Balance sheet 10, Operating efficiency 10. Each metric is scored 1 to 5 by where the company sits in the
industry distribution (the 20 Nifty Pharma companies), so a 5 means top of the industry, not just top of six.

Three lenses: Current strength (40%), Momentum (30%: is it getting better?), Quality (30%: is it sustainable?).
Robustness: the ranking is re-run thousands of times with random but reasonable weights.
What-if: simple driver model FY27 to FY29 with consultant levers, low / likely / high outcomes and a tornado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core import data as D
from core import industry as IND

DIMENSIONS = {
    "Revenue growth": {"weight": 20, "metrics": [("sales_cagr", 10, True), ("sales_growth", 5, True), ("q1_growth", 5, True)]},
    "Profitability": {"weight": 25, "metrics": [("ebitda_margin", 10, True), ("margin_change_3y", 5, True), ("ebit_margin", 5, True), ("pat_margin", 5, True)]},
    "Cash generation": {"weight": 20, "metrics": [("fcf_margin", 10, True), ("cfo_ebitda", 5, True), ("cfo_pat", 5, True)]},
    "Capital efficiency": {"weight": 15, "metrics": [("roic", 5, True), ("roce", 5, True), ("roe", 5, True)]},
    "Balance sheet": {"weight": 10, "metrics": [("net_debt_ebitda", 5, False), ("interest_cover", 5, True)]},
    "Operating efficiency": {"weight": 10, "metrics": [("ccc", 5, False), ("asset_turnover", 5, True)]},
}
LENSES = {"Current strength": 40, "Momentum": 30, "Quality": 30}
LABELS = {"sales_cagr": "Revenue CAGR FY22–26", "sales_growth": "Revenue growth FY26", "q1_growth": "Revenue growth Q1 FY27",
          "ebitda_margin": "EBITDA margin", "margin_change_3y": "EBITDA margin change FY23→26 (pts)", "ebit_margin": "EBIT margin",
          "pat_margin": "PAT margin", "fcf_margin": "Free cash flow / sales", "cfo_ebitda": "CFO / EBITDA", "cfo_pat": "CFO / PAT",
          "roic": "ROIC", "roce": "ROCE", "roe": "ROE", "net_debt_ebitda": "Net debt / EBITDA", "interest_cover": "Interest cover",
          "ccc": "Cash conversion cycle", "asset_turnover": "Asset turnover"}
COST_OF_CAPITAL = 12.0  # % (assumed; typical for Indian pharma)
ONE_OFF = {"glenmark": "FY26 includes one-off AbbVie licensing income"}
ACQUIRED = {"mankind": "Revenue includes Bharat Serums (BSV) from Oct 2024", "ipca": "Revenue includes Unichem from FY24",
            "zydus": "Revenue includes acquisitions (Amplitude Surgical, Assertio, consumer brands)",
            "drreddy": "Europe includes acquired nicotine-replacement (NRT) brands"}
OPEN_FDA = {"alkem": "Daman plant classified OAI by the US FDA (Aug 2026)",
            "sun": "Halol plant OAI and under US import alert",
            "cipla": "Pithampur plant under US FDA warning letter (7 new observations, Aug 2026)",
            "lupin": "Pithampur Unit II classified OAI by the US FDA",
            "aurobindo": "Eugia Unit-I US FDA warning letter (Aug 2026)"}


# ── raw metric values ────────────────────────────────────────────────────────
ADJUST = {"on": True}  # strip one-off licensing income from Glenmark FY26 (switch on the page)


def _glenmark_adjust(m: dict, df: pd.DataFrame) -> dict:
    """Remove the one-off AbbVie licensing income X from FY26 so the margin equals the guided normal 21.5%:
    (EBITDA - X) / (Sales - X) = 21.5%. X comes out at about ₹1,170 Cr. Q1 FY27 growth uses the core 18%."""
    r = df.iloc[-1]
    nm = NORMAL_MARGIN["glenmark"] / 100
    x = (r["ebitda"] - nm * r["sales"]) / (1 - nm)
    s1, e1, ebit1 = r["sales"] - x, r["ebitda"] - x, r["ebit"] - x
    k = ebit1 / r["ebit"]
    m.update({"sales_growth": (s1 / df["sales"].iloc[-2] - 1) * 100,
              "sales_cagr": D._cagr(df["sales"].iloc[0], s1, 4) * 100,
              "q1_growth": 18.0, "ebitda_margin": e1 / s1 * 100, "ebit_margin": ebit1 / s1 * 100,
              "margin_change_3y": e1 / s1 * 100 - df["ebitda_margin"].iloc[1],
              "roce": r["roce"] * k, "roic": r["roic"] * k, "fcf_margin": (r["fcf"] - x) / s1 * 100,
              "cfo_ebitda": (r["cfo"] - x) / e1, "cfo_pat": (r["cfo"] - x) / r["pat"],
              "net_debt_ebitda": r["net_debt"] / e1, "interest_cover": ebit1 / r["interest"]})
    return m


def company_metrics(cid: str, df: pd.DataFrame | None = None) -> dict:
    c = D.company(cid)
    df = D.financial_frame(cid) if df is None else df
    r = df.iloc[-1]
    q = c["quarterly"]["sales"]
    m = {
        "sales_cagr": D._cagr(df["sales"].iloc[0], df["sales"].iloc[-1], 4) * 100,
        "sales_growth": r["sales_growth"], "q1_growth": (q[-1] / q[0] - 1) * 100,
        "ebitda_margin": r["ebitda_margin"], "margin_change_3y": df["ebitda_margin"].iloc[-1] - df["ebitda_margin"].iloc[1],
        "ebit_margin": r["ebit_margin"], "pat_margin": r["pat_margin"], "fcf_margin": r["fcf_margin"],
        "cfo_ebitda": r["cfo_ebitda"], "cfo_pat": r["cfo_pat"], "roic": r["roic"], "roce": r["roce"], "roe": r["roe"],
        "net_debt_ebitda": r["net_debt_ebitda"], "interest_cover": r["interest_cover"], "ccc": r["ccc"], "asset_turnover": r["asset_turnover"],
    }
    if cid == "glenmark" and ADJUST["on"]:
        m = _glenmark_adjust(m, df)
    return m


def _industry_dist(metric: str) -> np.ndarray:
    if metric == "margin_change_3y":
        vals = [f["ebitda_margin"].iloc[-1] - f["ebitda_margin"].iloc[1] for _, (_, f, _) in IND.frames().items()]
    elif metric == "q1_growth":
        return np.array([])
    else:
        vals = IND.member_values(metric).values
    v = np.array(vals, dtype=float)
    return v[np.isfinite(v)]


def _score(v: float, dist: np.ndarray, hib: bool) -> float:
    """1 to 5 by percentile within the distribution (higher = better)."""
    if v is None or not np.isfinite(v) or dist.size < 3:
        return np.nan
    pct = ((dist < v).sum() + 0.5 * (dist == v).sum()) / dist.size
    return 1 + 4 * (pct if hib else 1 - pct)


def metric_scores(metrics_by_company: dict[str, dict]) -> pd.DataFrame:
    """Rows = companies, columns = metrics, values = 1 to 5."""
    out = {}
    for m, _, hib in [x for d in DIMENSIONS.values() for x in d["metrics"]]:
        dist = _industry_dist(m)
        if dist.size < 3:  # no industry data: score within the six
            dist = np.array([mb[m] for mb in metrics_by_company.values() if np.isfinite(mb[m])])
        out[m] = {cid: _score(mb[m], dist, hib) for cid, mb in metrics_by_company.items()}
    return pd.DataFrame(out)


def dimension_scores(ms: pd.DataFrame) -> pd.DataFrame:
    out = {}
    for dim, cfg in DIMENSIONS.items():
        w = np.array([x[1] for x in cfg["metrics"]], dtype=float)
        cols = [x[0] for x in cfg["metrics"]]
        vals = ms[cols].values
        mask = np.isfinite(vals)
        out[dim] = (np.where(mask, vals, 0) * w).sum(axis=1) / (mask * w).sum(axis=1)
    return pd.DataFrame(out, index=ms.index)


def strength(dims: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    w = pd.Series(weights, dtype=float)
    return (dims[w.index] * w).sum(axis=1) / w.sum()


def momentum(cid: str, m: dict | None = None) -> dict:
    df = D.financial_frame(cid)
    m = m or company_metrics(cid)
    return {"margin_change_3y": m["margin_change_3y"],
            "roce_change_3y": m["roce"] - df["roce"].iloc[1],
            "ccc_change_3y": m["ccc"] - df["ccc"].iloc[1],
            "q1_growth": m["q1_growth"],
            "netdebt_change_3y": m["net_debt_ebitda"] - df["net_debt_ebitda"].iloc[1]}


MOMENTUM_DIR = {"margin_change_3y": True, "roce_change_3y": True, "ccc_change_3y": False, "q1_growth": True, "netdebt_change_3y": False}
MOMENTUM_LABELS = {"margin_change_3y": "EBITDA margin change FY23→26", "roce_change_3y": "ROCE change FY23→26",
                   "ccc_change_3y": "Cash cycle change FY23→26 (days)", "q1_growth": "Latest quarter growth (Q1 FY27)",
                   "netdebt_change_3y": "Net debt/EBITDA change FY23→26"}


def quality(cid: str, m: dict | None = None) -> dict:
    df = D.financial_frame(cid)
    m = m or company_metrics(cid)
    cc = df["cfo_pat"].clip(-1, 3).copy()
    margins = df["ebitda_margin"].copy()
    if cid == "glenmark" and ADJUST["on"]:
        cc.iloc[-1] = min(m["cfo_pat"], 3)
        margins.iloc[-1] = m["ebitda_margin"]
    return {"cash_conversion_5y": cc.mean(),
            "margin_stability": -margins.std(),
            "roic_spread": m["roic"] - COST_OF_CAPITAL,
            "organic": 0.0 if cid in ACQUIRED else 1.0,
            "clean_earnings": 0.0 if cid in ONE_OFF else 1.0,
            "clean_fda": 0.0 if cid in OPEN_FDA else 1.0}


QUALITY_LABELS = {"cash_conversion_5y": "Cash conversion, 5-yr average (CFO/PAT)", "margin_stability": "Margin stability (lower swings = better)",
                  "roic_spread": f"ROIC minus cost of capital ({COST_OF_CAPITAL:.0f}%)", "organic": "Growth is organic (no large acquisition)",
                  "clean_earnings": "No one-off income in FY26", "clean_fda": "No open US FDA issue"}


def _rank_within(d: dict[str, dict], directions: dict[str, bool]) -> pd.DataFrame:
    df = pd.DataFrame(d).T
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        v = df[col].astype(float)
        if v.nunique() <= 1:
            out[col] = 3.0
            continue
        lo, hi = v.min(), v.max()
        s = (v - lo) / (hi - lo)
        out[col] = 1 + 4 * (s if directions.get(col, True) else 1 - s)
    return out


def scorecard(dim_weights: dict[str, float] | None = None, lens_weights: dict[str, float] | None = None,
              overrides: dict[str, dict] | None = None) -> dict:
    """Full ranking. overrides = {cid: {metric: value}} for what-if runs."""
    dim_weights = dim_weights or {k: v["weight"] for k, v in DIMENSIONS.items()}
    lens_weights = lens_weights or LENSES
    ids = [c["id"] for c in D.companies()]
    mets = {cid: company_metrics(cid) for cid in ids}
    for cid, ov in (overrides or {}).items():
        mets[cid].update(ov)
    ms = metric_scores(mets)
    dims = dimension_scores(ms)
    cur = strength(dims, dim_weights)
    mom = _rank_within({cid: momentum(cid, mets[cid]) for cid in ids}, MOMENTUM_DIR)
    qual = _rank_within({cid: quality(cid, mets[cid]) for cid in ids}, {k: True for k in QUALITY_LABELS})
    lens = pd.DataFrame({"Current strength": cur, "Momentum": mom.mean(axis=1), "Quality": qual.mean(axis=1)})
    lw = pd.Series(lens_weights, dtype=float)
    overall = (lens[lw.index] * lw).sum(axis=1) / lw.sum()
    to100 = lambda s: (s - 1) / 4 * 100  # noqa: E731
    names = D.names()
    table = pd.DataFrame({"Company": [names[i] for i in ids], "Overall": to100(overall).values,
                          **{k: to100(lens[k]).values for k in lens.columns},
                          **{k: to100(dims[k]).values for k in dims.columns}}, index=ids)
    table = table.sort_values("Overall", ascending=False)
    table.insert(0, "Rank", range(1, len(table) + 1))
    return {"table": table, "metrics": mets, "metric_scores": ms, "dims": dims, "momentum": mom, "quality": qual}


def robustness(n: int = 3000, seed: int = 7, spread: float = 0.5) -> pd.DataFrame:
    """Re-rank n times with every weight drawn between (1 - spread) and (1 + spread) of its base value."""
    rng = np.random.default_rng(seed)
    base = scorecard()
    dims, mom, qual = base["dims"], base["momentum"].mean(axis=1), base["quality"].mean(axis=1)
    dw = np.array([v["weight"] for v in DIMENSIONS.values()], dtype=float)
    lw = np.array(list(LENSES.values()), dtype=float)
    ids = list(dims.index)
    ranks = np.zeros((n, len(ids)), dtype=int)
    D_ = dims.values
    for i in range(n):
        w = dw * rng.uniform(1 - spread, 1 + spread, size=dw.size)
        l_ = lw * rng.uniform(1 - spread, 1 + spread, size=lw.size)
        cur = D_ @ w / w.sum()
        ov = (cur * l_[0] + mom.values * l_[1] + qual.values * l_[2]) / l_.sum()
        ranks[i] = (-ov).argsort().argsort() + 1
    names = D.names()
    out = pd.DataFrame({"Company": [names[i] for i in ids],
                        "Chance of #1": (ranks == 1).mean(axis=0) * 100,
                        "Chance of top 3": (ranks <= 3).mean(axis=0) * 100,
                        "Median rank": np.median(ranks, axis=0),
                        "Best rank": ranks.min(axis=0), "Worst rank": ranks.max(axis=0)}, index=ids)
    return out.sort_values(["Median rank", "Chance of #1"], ascending=[True, False])


# ── What-if projection (FY27 to FY29) ────────────────────────────────────────
LEVERS = {
    "price": ("Price growth change (pts/yr)", -3.0, 3.0, 0.0, 0.5, 1.0),
    "volume": ("Volume growth change (pts/yr)", -5.0, 5.0, 0.0, 0.5, 2.0),
    "rnd": ("R&D spend change (pts of sales)", -2.0, 4.0, 0.0, 0.5, 1.0),
    "rnd_success": ("Chance the extra R&D pays off (%)", 10.0, 90.0, 50.0, 5.0, None),
    "employee": ("Employee cost change (pts of sales)", -3.0, 2.0, 0.0, 0.25, -1.0),
    "sga": ("Other / SG&A cost change (pts of sales)", -3.0, 2.0, 0.0, 0.25, -1.0),
    "inventory": ("Inventory days change", -150.0, 30.0, 0.0, 5.0, -30.0),
    "debtor": ("Debtor days change", -60.0, 30.0, 0.0, 5.0, -15.0),
    "capex": ("Extra capex per year (₹ Cr)", 0.0, 2000.0, 0.0, 50.0, 500.0),
    "debt": ("Debt change (% of borrowings)", -100.0, 100.0, 0.0, 5.0, -25.0),
}
NORMAL_MARGIN = {"glenmark": 21.5}  # guided normal margin, excluding licensing income


def base_growth(cid: str) -> float:
    c = D.company(cid)
    df = D.financial_frame(cid)
    cons = c.get("consensus", {})
    if cons.get("fy27_sales"):
        return (cons["fy27_sales"] / df["sales"].iloc[-1] - 1) * 100
    return D._cagr(df["sales"].iloc[1], df["sales"].iloc[-1], 3) * 100


def project(cid: str, lv: dict | None = None, realisation: float = 1.0, rnd_pays: float | None = None, shock: dict | None = None) -> dict:
    """Project FY27 to FY29. realisation = share of lever benefits achieved; rnd_pays = 0..1 (None = expected value)."""
    lv = {k: 0.0 for k in LEVERS} | {"rnd_success": 50.0} | (lv or {})
    shock = shock or {}
    df = D.financial_frame(cid)
    r = df.iloc[-1]
    g = base_growth(cid) / 100 + shock.get("growth", 0) / 100
    margin0 = NORMAL_MARGIN.get(cid, r["ebitda_margin"]) + shock.get("margin", 0)
    tax = float(np.clip(r["tax_pct"], 15, 30)) / 100
    pays = (lv["rnd_success"] / 100) if rnd_pays is None else rnd_pays
    sales, ce = r["sales"], r["capital_employed"]
    da0 = r["depreciation"] / r["sales"]
    mat_day = r["material_cost"] / 365
    sales_day = r["sales"] / 365
    debt = r["borrowings"] * (1 + lv["debt"] / 100 * realisation)
    interest = r["interest"] + (debt - r["borrowings"]) * 0.09
    fat = r["sales"] / (r["fixed_assets"] + r["cwip"])
    wc_int = float(np.clip(r["wc_days"], 0, 365)) / 365
    cum_capex = 0.0
    out = []
    for t in (1, 2, 3):
        growth = g + (lv["price"] + lv["volume"]) / 100 * realisation
        rnd_uplift = (0.03 * lv["rnd"] * pays) if (t == 3 and lv["rnd"] > 0) else 0.0
        capex_uplift = (cum_capex * fat * 0.5 / sales) if t > 1 else 0.0
        prev = sales
        sales = sales * (1 + growth + rnd_uplift + capex_uplift)
        margin = margin0 - lv["rnd"] - (lv["employee"] + lv["sga"]) * realisation + (lv["price"] * 0.6 * realisation)
        ebitda = sales * margin / 100
        cum_capex += lv["capex"]
        da = sales * da0 + 0.1 * cum_capex
        ebit = ebitda - da
        pat = (ebit - interest) * (1 - tax)
        wc_release = ((-lv["inventory"]) * mat_day + (-lv["debtor"]) * sales_day) * realisation if t == 1 else 0.0
        ce = ce * (1 + growth * 0.5) + lv["capex"] - wc_release + (debt - r["borrowings"] if t == 1 else 0)
        # FCF = EBITDA - tax - maintenance capex (~D&A) - extra capex + working-capital release - working capital for growth
        fcf = ebitda - max(ebit - interest, 0) * tax - sales * da0 - lv["capex"] + wc_release - (sales - prev) * wc_int
        out.append({"Year": f"FY{26 + t}", "Revenue": sales, "EBITDA": ebitda, "EBITDA margin %": margin, "EBIT": ebit, "PAT": pat,
                    "ROCE %": ebit / ce * 100, "ROIC %": ebit * (1 - tax) / ce * 100, "Free cash flow": fcf,
                    "Net debt / EBITDA": (debt - r["investments"] - r.get("cash", 0)) / ebitda, "Capital employed": ce})
    return {"years": pd.DataFrame(out).set_index("Year"), "wc_release": ((-lv["inventory"]) * mat_day + (-lv["debtor"]) * sales_day) * realisation}


def scenario_overrides(cid: str, lv: dict, realisation: float = 1.0, rnd_pays: float | None = None) -> dict:
    """Translate a what-if into changes to today's metrics (FY29 scenario minus FY29 base), for re-ranking."""
    base = project(cid)["years"].iloc[-1]
    scen = project(cid, lv, realisation, rnd_pays)["years"].iloc[-1]
    m = company_metrics(cid)
    d_margin = scen["EBITDA margin %"] - base["EBITDA margin %"]
    return {"ebitda_margin": m["ebitda_margin"] + d_margin, "ebit_margin": m["ebit_margin"] + d_margin,
            "pat_margin": m["pat_margin"] + d_margin * 0.75, "margin_change_3y": m["margin_change_3y"] + d_margin,
            "roce": m["roce"] + (scen["ROCE %"] - base["ROCE %"]), "roic": m["roic"] + (scen["ROIC %"] - base["ROIC %"]),
            "roe": m["roe"] + (scen["ROCE %"] - base["ROCE %"]) * 0.8,
            "sales_cagr": m["sales_cagr"] + ((scen["Revenue"] / base["Revenue"]) ** (1 / 3) - 1) * 100,
            "sales_growth": m["sales_growth"] + ((scen["Revenue"] / base["Revenue"]) ** (1 / 3) - 1) * 100,
            "ccc": m["ccc"] + lv.get("inventory", 0) * realisation + lv.get("debtor", 0) * realisation,
            "fcf_margin": m["fcf_margin"] + (scen["Free cash flow"] / scen["Revenue"] - base["Free cash flow"] / base["Revenue"]) * 100,
            "net_debt_ebitda": m["net_debt_ebitda"] + (scen["Net debt / EBITDA"] - base["Net debt / EBITDA"])}


def tornado(cid: str) -> pd.DataFrame:
    """Change in FY29 ROCE and in overall score from one standard step on each lever."""
    base_p = project(cid)["years"].iloc[-1]
    base_score = scorecard()["table"].loc[cid, "Overall"]
    rows = []
    for k, (label, lo, hi, default, step, std) in LEVERS.items():
        if std is None:
            continue
        lv = {k: std}
        p = project(cid, lv)["years"].iloc[-1]
        sc = scorecard(overrides={cid: scenario_overrides(cid, lv)})["table"].loc[cid, "Overall"]
        rows.append({"Lever": f"{label}: {std:+g}", "Δ ROCE FY29 (pts)": p["ROCE %"] - base_p["ROCE %"],
                     "Δ EBITDA FY29 (₹ Cr)": p["EBITDA"] - base_p["EBITDA"], "Δ overall score": sc - base_score})
    return pd.DataFrame(rows).sort_values("Δ overall score", key=abs, ascending=True)


SCENARIOS = {
    "Base": {"desc": "Company guidance and recent trends continue.", "shock": lambda c, us, ind: {}},
    "Upside": {"desc": "India market grows ~12% (2 pts faster); US price erosion eases; costs stable.",
               "shock": lambda c, us, ind: {"growth": 2.0 * ind / 100 + 1.5 * us / 100, "margin": 1.0}},
    "Downside": {"desc": "US generics tariff starts after the 2-year grace period, input costs rise 1.5 pts, and any open US FDA plant issue drags on.",
                 "shock": lambda c, us, ind: {"growth": -0.15 * us - (5.0 if c in OPEN_FDA else 0.0), "margin": -1.5 - 0.06 * us}},
}


def scenario_ranking() -> pd.DataFrame:
    k = D.kpi_table()
    rows = {}
    for sname, sc in SCENARIOS.items():
        ov = {}
        for c in D.companies():
            cid = c["id"]
            us, ind = k.loc[c["short"], "us_share"], k.loc[c["short"], "india_share"]
            shock = sc["shock"](cid, us, ind)
            if not shock:
                continue
            base = project(cid)["years"].iloc[-1]
            scen = project(cid, shock=shock)["years"].iloc[-1]
            m = company_metrics(cid)
            dm = scen["EBITDA margin %"] - base["EBITDA margin %"]
            dg = ((scen["Revenue"] / base["Revenue"]) ** (1 / 3) - 1) * 100
            ov[cid] = {"ebitda_margin": m["ebitda_margin"] + dm, "ebit_margin": m["ebit_margin"] + dm, "pat_margin": m["pat_margin"] + dm * 0.75,
                       "sales_cagr": m["sales_cagr"] + dg, "sales_growth": m["sales_growth"] + dg, "q1_growth": m["q1_growth"] + dg,
                       "roce": m["roce"] + (scen["ROCE %"] - base["ROCE %"]), "roic": m["roic"] + (scen["ROIC %"] - base["ROIC %"])}
        t = scorecard(overrides=ov)["table"]
        rows[sname] = t.set_index("Company")[["Rank", "Overall"]]
    out = pd.concat(rows, axis=1)
    out.columns = [f"{a} {b.lower()}" for a, b in out.columns]
    return out.sort_values("Base rank")
