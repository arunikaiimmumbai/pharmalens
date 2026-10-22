"""Industry benchmark: the 20 Nifty Pharma constituents (source A) plus published market growth (source C).

Industry value = simple average of the constituents for that metric and year; the median is kept alongside
because one very large or loss-making company can pull an average around.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from core import data as D

IND_PATH = Path(__file__).resolve().parent.parent / "data" / "industry.json"

NOTE_A = "Industry = average of the 20 Nifty Pharma companies (median {med}). Source: Screener.in consolidated accounts."
NOTE_C = "Industry = Indian pharma market growth ({provider}). Source: {title}."

# Metrics that can be benchmarked against the industry (same definition for every company).
BENCHMARKABLE = [
    "sales", "sales_growth", "sales_cagr", "ebitda_cagr", "pat_cagr", "ebitda_margin", "ebit_margin", "pat_margin", "gross_margin",
    "roce", "roe", "roa", "roic", "employee_pct", "material_pct", "indirect_pct", "inventory_days", "debtor_days", "payable_days",
    "ccc", "wc_days", "de_ratio", "debt_ebitda", "net_debt_ebitda", "interest_cover", "asset_turnover", "fixed_asset_turnover",
    "cfo_pat", "cfo_ebitda", "fcf_margin", "pe", "manufacturing_pct", "other_cost_pct", "dep_pct", "interest_pct",
]


def _raw() -> dict:
    return _raw_cached(IND_PATH.stat().st_mtime)


@st.cache_data(show_spinner=False)
def _raw_cached(mtime: float) -> dict:
    with open(IND_PATH, encoding="utf-8") as f:
        return json.load(f)


def _member_frame(m: dict) -> pd.DataFrame:
    f = {k: v for k, v in m["financials"].items() if k != "cost_ok"}
    df = pd.DataFrame(f, index=D.years()).astype(float)
    s = df["sales"]
    nw = df["equity_capital"] + df["reserves"]
    df["net_worth"] = nw
    df["ebitda_margin"] = df["ebitda"] / s * 100
    df["pat_margin"] = df["pat"] / s * 100
    avg_nw = ((nw + nw.shift(1)) / 2).fillna(nw)
    df["roe"] = df["pat"] / avg_nw * 100
    df["roa"] = df["pat"] / df["total_assets"] * 100
    df["de_ratio"] = df["borrowings"] / nw
    df["debt_ebitda"] = D._safe_div(df["borrowings"], df["ebitda"])
    df["interest_cover"] = D._safe_div(df["ebitda"] - df["depreciation"], df["interest"])
    df["asset_turnover"] = s / df["total_assets"]
    df["fixed_asset_turnover"] = s / (df["fixed_assets"] + df["cwip"])
    df["cfo_ebitda"] = D._safe_div(df["cfo"], df["ebitda"])
    df["cfo_pat"] = D._safe_div(df["cfo"], df["pat"])
    df["sales_growth"] = s.pct_change() * 100
    df["dep_pct"] = df["depreciation"] / s * 100
    df["interest_pct"] = df["interest"] / s * 100
    if "material_pct" in df.columns:
        ok = pd.Series(m["financials"].get("cost_ok", [True] * len(df)), index=df.index)
        for col in ("material_pct", "employee_pct", "manufacturing_pct", "other_cost_pct"):
            df[col] = df[col].where(ok)
        df["gross_margin"] = 100 - df["material_pct"]
        df["indirect_pct"] = df["manufacturing_pct"] + df["other_cost_pct"]
    D.add_return_metrics(df)
    # Loss-making years make some ratios meaningless; blank them rather than distort the average.
    for col in ("cfo_pat",):
        df.loc[df["pat"] <= 0, col] = np.nan
    return df


@st.cache_data(show_spinner=False)
def _frames(mtime: float, dmtime: float) -> dict[str, tuple[str, pd.DataFrame, float | None]]:
    raw = _raw()
    out = {}
    for m in raw["members"]:
        out[m["symbol"]] = (m["name"], _member_frame(m), m.get("pe"))
    for sym, cid in raw["in_app_members"].items():
        c = D.company(cid)
        out[sym] = (c["short"], D.financial_frame(cid), c["market"].get("pe"))
    return out


def frames() -> dict[str, tuple[str, pd.DataFrame, float | None]]:
    return _frames(IND_PATH.stat().st_mtime, D.DATA_PATH.stat().st_mtime)


def member_values(metric: str, year: str = "FY26") -> pd.Series:
    """One value per industry member for a metric (year-based or CAGR / P/E)."""
    vals = {}
    yrs = D.years()
    for sym, (name, df, pe) in frames().items():
        if metric == "pe":
            v = pe
        elif metric.endswith("_cagr"):
            col = metric.replace("_cagr", "")
            col = "sales" if col == "sales" else col
            v = D._cagr(df[col].iloc[0], df[col].iloc[-1], len(yrs) - 1) * 100 if col in df.columns else np.nan
        elif metric in df.columns:
            v = df.loc[year, metric]
        else:
            v = np.nan
        vals[name] = v
    return pd.Series(vals, dtype=float)


def industry_value(metric: str, year: str = "FY26") -> dict:
    """{'avg', 'median', 'n'} for one metric. avg is None when the metric can't be benchmarked."""
    if metric not in BENCHMARKABLE:
        return {"avg": None, "median": None, "n": 0}
    v = member_values(metric, year).replace([np.inf, -np.inf], np.nan).dropna()
    if v.empty:
        return {"avg": None, "median": None, "n": 0}
    return {"avg": float(v.mean()), "median": float(v.median()), "n": int(v.size)}


def industry_series(metric: str) -> pd.DataFrame:
    """Years x [Average, Median, N] for a year-based metric."""
    rows = []
    for y in D.years():
        iv = industry_value(metric, y)
        rows.append({"Year": y, "Average": iv["avg"], "Median": iv["median"], "N": iv["n"]})
    return pd.DataFrame(rows).set_index("Year")


def note(metric: str, year: str = "FY26") -> str:
    """Grey note text saying which industry source (A) is used and the median."""
    iv = industry_value(metric, year)
    if iv["avg"] is None:
        return "No industry benchmark for this metric (not published consistently for all Nifty Pharma companies)."
    med = D.fmt(metric, iv["median"]) if metric in D.KPI_DEFS else f"{iv['median']:.1f}"
    return NOTE_A.format(med=med) + f" {iv['n']} companies with data."


def market() -> list[dict]:
    """Published market figures (source C)."""
    return _raw()["market"]


def market_note(i: int = 0) -> str:
    m = market()[i]
    return NOTE_C.format(provider=m["provider"], title=m["source"]["title"])


def members_table() -> pd.DataFrame:
    raw = _raw()
    rows = [{"Company": m["name"], "NSE symbol": m["symbol"], "Accounts": m["basis"], "Source": m["url"]} for m in raw["members"]]
    for sym, cid in raw["in_app_members"].items():
        rows.append({"Company": D.company(cid)["short"], "NSE symbol": sym, "Accounts": "consolidated",
                     "Source": f"https://www.screener.in/company/{sym}/consolidated/"})
    return pd.DataFrame(rows).sort_values("Company")


def meta() -> dict:
    raw = _raw()
    return {"index": raw["index"], "as_of": raw["as_of"], "method": raw["method"], "constituents_source": raw["constituents_source"]}
