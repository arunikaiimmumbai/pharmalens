"""Data layer: loads curated company data and derives every ratio / KPI used across the app."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "companies.json"


@st.cache_data(show_spinner=False)
def load_raw() -> dict:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def meta() -> dict:
    return load_raw()["meta"]


def companies() -> list[dict]:
    return load_raw()["companies"]


def company(cid: str) -> dict:
    return next(c for c in companies() if c["id"] == cid)


def names() -> dict[str, str]:
    return {c["id"]: c["short"] for c in companies()}


def colors() -> dict[str, str]:
    """Colour follows the entity (keyed by short name) — never by rank."""
    return {c["short"]: c["color"] for c in companies()}


def years() -> list[str]:
    return meta()["years"]


def _cagr(first: float, last: float, n: int) -> float:
    if first is None or last is None or first <= 0 or last <= 0 or n <= 0:
        return np.nan
    return (last / first) ** (1 / n) - 1


def _safe_div(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(b == 0, np.nan, a / b)
    return out


@st.cache_data(show_spinner=False)
def financial_frame(cid: str) -> pd.DataFrame:
    """Year-indexed frame of raw lines + derived ratios for one company."""
    c = company(cid)
    f = c["financials"]
    df = pd.DataFrame(f, index=years())
    s = df["sales"]
    df["net_worth"] = df["equity_capital"] + df["reserves"]
    df["capital_employed"] = df["net_worth"] + df["borrowings"]
    df["ebitda_margin"] = df["ebitda"] / s * 100
    df["pat_margin"] = df["pat"] / s * 100
    df["pbt_margin"] = df["pbt"] / s * 100
    df["gross_margin"] = 100 - df["material_pct"]
    df["material_cost"] = df["material_pct"] / 100 * s
    df["employee_cost"] = df["employee_pct"] / 100 * s
    df["manufacturing_cost"] = df["manufacturing_pct"] / 100 * s
    df["other_cost"] = df["other_cost_pct"] / 100 * s
    df["recon_cost"] = df["expenses"] - (df["material_cost"] + df["employee_cost"] + df["manufacturing_cost"] + df["other_cost"])
    df["recon_pct"] = df["recon_cost"] / s * 100
    df["indirect_cost"] = df["manufacturing_cost"] + df["other_cost"]
    df["indirect_pct"] = df["manufacturing_pct"] + df["other_cost_pct"]
    avg_nw = (df["net_worth"] + df["net_worth"].shift(1)) / 2
    avg_nw = avg_nw.fillna(df["net_worth"])
    df["roe"] = df["pat"] / avg_nw * 100
    df["roa"] = df["pat"] / df["total_assets"] * 100
    df["de_ratio"] = df["borrowings"] / df["net_worth"]
    df["debt_ebitda"] = df["borrowings"] / df["ebitda"]
    df["interest_cover"] = _safe_div(df["ebitda"] - df["depreciation"], df["interest"])
    df["asset_turnover"] = s / df["total_assets"]
    df["fixed_asset_turnover"] = s / (df["fixed_assets"] + df["cwip"])
    df["cfo_ebitda"] = df["cfo"] / df["ebitda"]
    df["cfo_pat"] = _safe_div(df["cfo"], df["pat"])
    df["fcf_proxy"] = df["cfo"] + df["cfi"]
    df["sales_growth"] = s.pct_change() * 100
    df["ebitda_growth"] = df["ebitda"].pct_change() * 100
    df["pat_growth"] = df["pat"].pct_change() * 100
    df["employee_growth"] = df["employee_cost"].pct_change() * 100
    df["indirect_growth"] = df["indirect_cost"].pct_change() * 100
    df["material_growth"] = df["material_cost"].pct_change() * 100
    df["inventory_value"] = df["inventory_days"] / 365 * df["material_cost"]
    df["receivables_value"] = df["debtor_days"] / 365 * s
    df["dep_pct"] = df["depreciation"] / s * 100
    df["interest_pct"] = df["interest"] / s * 100
    df["tax_pct_clean"] = df["tax_pct"].clip(lower=-50, upper=60)
    return df


KPI_DEFS = {
    # key: (label, unit, higher_is_better, fmt)
    "sales": ("Revenue (₹ Cr)", "₹ Cr", True, "{:,.0f}"),
    "sales_cagr": ("Revenue CAGR FY22–26", "%", True, "{:.1f}%"),
    "ebitda_cagr": ("EBITDA CAGR FY22–26", "%", True, "{:.1f}%"),
    "pat_cagr": ("PAT CAGR FY22–26", "%", True, "{:.1f}%"),
    "ebitda_margin": ("EBITDA margin", "%", True, "{:.1f}%"),
    "gross_margin": ("Gross margin", "%", True, "{:.1f}%"),
    "pat_margin": ("PAT margin", "%", True, "{:.1f}%"),
    "roce": ("ROCE", "%", True, "{:.0f}%"),
    "roe": ("ROE", "%", True, "{:.1f}%"),
    "roa": ("ROA", "%", True, "{:.1f}%"),
    "employee_pct": ("Employee cost / sales", "%", False, "{:.1f}%"),
    "material_pct": ("Material cost / sales", "%", False, "{:.1f}%"),
    "indirect_pct": ("Indirect cost / sales (mfg + other)", "%", False, "{:.1f}%"),
    "inventory_days": ("Inventory days", "days", False, "{:.0f}"),
    "debtor_days": ("Debtor days", "days", False, "{:.0f}"),
    "payable_days": ("Payable days", "days", None, "{:.0f}"),
    "ccc": ("Cash conversion cycle", "days", False, "{:.0f}"),
    "wc_days": ("Working-capital days", "days", False, "{:.0f}"),
    "de_ratio": ("Debt / equity", "x", False, "{:.2f}x"),
    "debt_ebitda": ("Debt / EBITDA", "x", False, "{:.2f}x"),
    "interest_cover": ("Interest cover (EBIT/int)", "x", True, "{:.1f}x"),
    "asset_turnover": ("Asset turnover", "x", True, "{:.2f}x"),
    "fixed_asset_turnover": ("Fixed-asset turnover", "x", True, "{:.2f}x"),
    "cfo_pat": ("CFO / PAT", "x", True, "{:.2f}x"),
    "cfo_ebitda": ("CFO / EBITDA", "x", True, "{:.2f}x"),
    "rnd_pct": ("R&D / sales (latest)", "%", None, "{:.1f}%"),
    "pe": ("P/E (TTM)", "x", None, "{:.1f}x"),
    "pb": ("P/B", "x", None, "{:.1f}x"),
    "ev_ebitda": ("EV / EBITDA (TTM, approx.)", "x", None, "{:.1f}x"),
    "mcap_cr": ("Market cap (₹ Cr)", "₹ Cr", None, "{:,.0f}"),
    "us_share": ("US revenue share", "%", None, "{:.0f}%"),
    "india_share": ("India revenue share", "%", None, "{:.0f}%"),
    "div_payout": ("Dividend payout", "%", None, "{:.0f}%"),
}

US_KEYS = ("US formulations", "US generics", "US", "North America")
INDIA_KEYS = ("India branded", "India", "Domestic formulations", "Domestic Rx (ex-CH)", "Consumer healthcare")


@st.cache_data(show_spinner=False)
def kpi_table(year: str = "FY26") -> pd.DataFrame:
    """One row per company, one column per KPI (latest year unless stated)."""
    rows = []
    yrs = years()
    n = len(yrs) - 1
    for c in companies():
        df = financial_frame(c["id"])
        r = df.loc[year]
        geo = c["footprint"]["geography"]
        mkt = c["market"]
        ttm = c.get("ttm", {})
        ev = mkt["mcap_cr"] + r["borrowings"] - r["investments"]
        row = {
            "id": c["id"],
            "Company": c["short"],
            "sales": r["sales"],
            "sales_cagr": _cagr(df["sales"].iloc[0], df["sales"].iloc[-1], n) * 100,
            "ebitda_cagr": _cagr(df["ebitda"].iloc[0], df["ebitda"].iloc[-1], n) * 100,
            "pat_cagr": _cagr(df["pat"].iloc[0], df["pat"].iloc[-1], n) * 100,
            "rnd_pct": c["footprint"].get("rnd_pct"),
            "pe": mkt.get("pe"),
            "pb": mkt.get("pb"),
            "mcap_cr": mkt.get("mcap_cr"),
            "ev_ebitda": ev / ttm["ebitda"] if ttm.get("ebitda") else np.nan,
            "us_share": sum(v for k, v in geo.items() if k in US_KEYS),
            "india_share": sum(v for k, v in geo.items() if k in INDIA_KEYS),
        }
        for k in KPI_DEFS:
            if k not in row and k in df.columns:
                row[k] = r[k]
        rows.append(row)
    return pd.DataFrame(rows).set_index("Company")


@st.cache_data(show_spinner=False)
def panel(metric: str) -> pd.DataFrame:
    """Years × companies for a single metric (time-series comparisons)."""
    out = {}
    for c in companies():
        df = financial_frame(c["id"])
        if metric in df.columns:
            out[c["short"]] = df[metric]
    return pd.DataFrame(out)


def peer_rank(kpis: pd.DataFrame, metric: str) -> pd.Series:
    hib = KPI_DEFS[metric][2]
    if hib is None:
        return kpis[metric].rank(ascending=False)
    return kpis[metric].rank(ascending=not hib)


def score_matrix(kpis: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """0–100 normalised score per KPI (100 = best in peer set) for heatmaps/radars."""
    out = pd.DataFrame(index=kpis.index)
    for m in metrics:
        v = kpis[m].astype(float)
        hib = KPI_DEFS[m][2]
        lo, hi = v.min(), v.max()
        if hi == lo or np.isnan(lo):
            out[m] = 50.0
            continue
        sc = (v - lo) / (hi - lo) * 100
        out[m] = sc if hib in (True, None) else 100 - sc
    return out


def cost_elasticity(cid: str) -> pd.DataFrame:
    """Incremental cost per incremental ₹ of revenue FY22→FY26 (operating leverage lens)."""
    df = financial_frame(cid)
    d_sales = df["sales"].iloc[-1] - df["sales"].iloc[0]
    rows = []
    for col, lab in [("material_cost", "Material"), ("employee_cost", "Employee"),
                     ("manufacturing_cost", "Manufacturing"), ("other_cost", "Other / SG&A"),
                     ("depreciation", "Depreciation"), ("interest", "Interest")]:
        d = df[col].iloc[-1] - df[col].iloc[0]
        g_cost = _cagr(df[col].iloc[0], df[col].iloc[-1], len(df) - 1)
        g_sales = _cagr(df["sales"].iloc[0], df["sales"].iloc[-1], len(df) - 1)
        rows.append({
            "Cost line": lab,
            "Δ cost (₹ Cr)": d,
            "Δ cost per ₹100 Δ revenue": d / d_sales * 100 if d_sales else np.nan,
            "Cost CAGR %": g_cost * 100,
            "Elasticity vs revenue": (g_cost / g_sales) if g_sales else np.nan,
        })
    return pd.DataFrame(rows)


def correlation_matrix(cid: str, cols: list[str]) -> pd.DataFrame:
    df = financial_frame(cid)[cols]
    return df.corr()


def pooled_correlation(x: str, y: str) -> tuple[pd.DataFrame, float]:
    """Pooled company-year observations (30 points) for cross-company relationships."""
    rows = []
    for c in companies():
        df = financial_frame(c["id"])
        for yr in df.index:
            rows.append({"Company": c["short"], "Year": yr, x: df.loc[yr, x], y: df.loc[yr, y]})
    pdf = pd.DataFrame(rows).dropna()
    r = pdf[x].corr(pdf[y]) if len(pdf) > 2 else np.nan
    return pdf, r


def all_news() -> pd.DataFrame:
    rows = []
    for c in companies():
        for n in c.get("news", []):
            rows.append({**n, "Company": c["short"], "id": c["id"]})
    for n in meta().get("sector_news", []):
        rows.append({**n, "Company": "Sector", "id": "sector"})
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date", ascending=False)


def fmt(metric: str, v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return KPI_DEFS.get(metric, ("", "", None, "{:,.1f}"))[3].format(v)
