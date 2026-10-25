"""Deterministic insight engine: always-on analyst layer (works with or without an LLM key).

Generates Growth / Opportunity / Risk statements from the numbers, benchmarked to the peer median,
and a composite financial score. The LLM agent uses these as grounded facts.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core import data as D

PILLARS = {
    "Growth": (["sales_cagr", "ebitda_cagr", "pat_cagr"], 0.25),
    "Profitability": (["ebitda_margin", "gross_margin", "pat_margin"], 0.25),
    "Returns": (["roce", "roe"], 0.20),
    "Cash & working capital": (["cfo_pat", "ccc", "inventory_days"], 0.15),
    "Balance sheet": (["de_ratio", "interest_cover"], 0.15),
}


def pillar_scores() -> pd.DataFrame:
    k = D.kpi_table()
    out = pd.DataFrame(index=k.index)
    for p, (metrics, _) in PILLARS.items():
        out[p] = D.score_matrix(k, metrics).mean(axis=1)
    out["Financial score"] = sum(out[p] * w for p, (_, w) in PILLARS.items())
    return out.round(0)


def _q_yoy(c: dict) -> float:
    q = c["quarterly"]["sales"]
    return (q[-1] / q[0] - 1) * 100


def _pts(a, b) -> float:
    return float(b) - float(a)


def company_insights(cid: str) -> dict:
    c = D.company(cid)
    df = D.financial_frame(cid)
    k = D.kpi_table()
    me = k.loc[c["short"]]
    med = k.median(numeric_only=True)
    g, o, r = [], [], []

    # ── Growth ────────────────────────────────────────────────
    cagr = me["sales_cagr"]
    rel = "above" if cagr > med["sales_cagr"] else "below"
    g.append(f"Revenue compounded {cagr:.1f}% p.a. FY22–26 ({rel} peer median {med['sales_cagr']:.1f}%); "
             f"EBITDA CAGR {me['ebitda_cagr']:.1f}%.")
    qy = _q_yoy(c)
    g.append(f"Q1 FY27 revenue {('+' if qy >= 0 else '')}{qy:.0f}% YoY, "
             + ("faster than its 5-year trend." if qy > cagr + 2 else "in line with its 5-year trend." if abs(qy - cagr) <= 2 else "slower than its 5-year trend."))
    geo = c["footprint"]["geography"]
    top_seg = max(geo, key=geo.get)
    g.append(f"Largest source of revenue: {top_seg}, {geo[top_seg]}% of the total ({c['footprint']['geography_basis'].replace(' (%)', '')}).")

    # ── Margin / cost structure ──────────────────────────────
    em = df["ebitda_margin"]
    d_em = _pts(em.iloc[0], em.iloc[-1])
    d_emp = _pts(df["employee_pct"].iloc[0], df["employee_pct"].iloc[-1])
    d_mat = _pts(df["material_pct"].iloc[0], df["material_pct"].iloc[-1])
    d_ind = _pts(df["indirect_pct"].iloc[0], df["indirect_pct"].iloc[-1])
    if d_mat < -3:
        o.append(f"Cheaper materials helped: material cost fell {abs(d_mat):.1f} points of sales FY22–26. Protecting this as raw material "
                 f"prices rise again (for example by having two API suppliers) is the opportunity.")
    if d_emp > 2:
        r.append(f"Rising people cost: employee cost up {d_emp:.1f} points of sales FY22–26 ({df['employee_pct'].iloc[0]:.1f}% to "
                 f"{df['employee_pct'].iloc[-1]:.1f}%). Sales-team productivity and organisation structure are worth reviewing.")
    if d_ind > 2:
        r.append(f"Overheads (manufacturing plus selling and admin) up {d_ind:.1f} points of sales. Worth a line-by-line cost review.")
    if me["ebitda_margin"] < med["ebitda_margin"] - 3:
        o.append(f"Margin gap: EBITDA margin {me['ebitda_margin']:.1f}% vs peer median {med['ebitda_margin']:.1f}%. "
                 f"Each 1 point of margin is worth about ₹{me['sales'] / 100:,.0f} Cr of EBITDA.")
    elif me["ebitda_margin"] > med["ebitda_margin"] + 3:
        g.append(f"Margin leader: EBITDA margin {me['ebitda_margin']:.1f}% vs median {med['ebitda_margin']:.1f}% "
                 f"({'+' if d_em >= 0 else ''}{d_em:.1f} pts since FY22).")

    # ── Returns ──────────────────────────────────────────────
    if me["roce"] < med["roce"] - 3:
        o.append(f"Low return on capital: ROCE {me['roce']:.0f}% vs median {med['roce']:.0f}%, and every ₹1 of plant earns ₹"
                 f"{me['fixed_asset_turnover']:.2f} of sales. Filling existing plants or outsourcing low-margin products would help.")
    elif me["roce"] > med["roce"] + 5:
        g.append(f"Superior returns: ROCE {me['roce']:.0f}% (median {med['roce']:.0f}%).")
    roce_trend = _pts(df["roce"].iloc[0], df["roce"].iloc[-1])
    if roce_trend <= -8:
        r.append(f"ROCE fell {abs(roce_trend):.0f} pts since FY22 ({df['roce'].iloc[0]:.0f}% to {df['roce'].iloc[-1]:.0f}%). "
                 f"Recent acquisitions or new plants are not yet paying back.")

    # ── Cash & working capital ───────────────────────────────
    cfo_pat = me["cfo_pat"]
    if cfo_pat < 0.7:
        r.append(f"Weak cash conversion: CFO/PAT {cfo_pat:.2f}x in FY26 (debtor days {me['debtor_days']:.0f}).")
    elif cfo_pat > 1.2:
        g.append(f"Strong cash conversion: CFO/PAT {cfo_pat:.2f}x.")
    if me["inventory_days"] > 300:
        inv_30 = df["material_cost"].iloc[-1] / 365 * 30
        o.append(f"Inventory {me['inventory_days']:.0f} days (median {med['inventory_days']:.0f}) . Every 30 days of stock cut frees about ₹{inv_30:,.0f} Cr of cash.")
    if me["ccc"] > med["ccc"] + 60:
        r.append(f"Cash conversion cycle {me['ccc']:.0f} days vs median {med['ccc']:.0f}. Too much cash is tied up in stock and unpaid bills.")

    # ── Balance sheet ────────────────────────────────────────
    if me["debt_ebitda"] > 1.5:
        r.append(f"Leverage {me['debt_ebitda']:.1f}x debt/EBITDA; interest ₹{df['interest'].iloc[-1]:,.0f} Cr in FY26.")
    b_growth = df["borrowings"].iloc[-1] / max(df["borrowings"].iloc[0], 1)
    if b_growth > 1.8 and df["borrowings"].iloc[-1] > 250:
        r.append(f"Borrowings up {b_growth:.1f}x since FY22 (₹{df['borrowings'].iloc[0]:,.0f} → ₹{df['borrowings'].iloc[-1]:,.0f} Cr).")
    if me["de_ratio"] < 0.1:
        o.append(f"Balance-sheet headroom (D/E {me['de_ratio']:.2f}x) to fund bolt-on M&A / in-licensing.")

    # ── Valuation vs fundamentals ────────────────────────────
    peg = me["pe"] / max(me["pat_cagr"], 1) if me["pat_cagr"] and me["pat_cagr"] > 0 else np.nan
    if me["pe"] > med["pe"] + 5:
        r.append(f"Valuation premium: P/E {me['pe']:.1f}x vs median {med['pe']:.1f}x. The company has to keep delivering to justify it"
                 + (f" (PE/PAT-growth {peg:.1f})." if not np.isnan(peg) else "."))
    elif me["pe"] < med["pe"] - 5:
        o.append(f"Valuation discount: P/E {me['pe']:.1f}x vs median {med['pe']:.1f}x. The share price could rise if the problems below are fixed.")

    # ── Regulatory & news ────────────────────────────────────
    st_txt = c["regulatory"]["status"].lower()
    if c["regulatory"].get("fda_open", "oai" in st_txt or ("warning letter" in st_txt and "close" not in st_txt)):
        r.append("Open USFDA compliance issue (OAI or warning letter): US supply and new approvals are at risk.")
    news = pd.DataFrame(c.get("news", []))
    if not news.empty:
        bal = news["sentiment"].sum()
        tone = "net positive" if bal > 0 else "net negative" if bal < 0 else "mixed"
        g.append(f"News flow last 6 months is {tone} ({(news['sentiment'] > 0).sum()} positive / {(news['sentiment'] < 0).sum()} negative events).")

    if any("licensing" in n for n in c.get("data_notes", [])):
        caveat = " ⚑ FY26 includes one-off licensing income, so use the company's guided normal margin instead."
        g = [x + caveat if ("Margin leader" in x or "Superior returns" in x) else x for x in g]
    return {"growth": g, "opportunity": o, "risk": r}


def cross_company_signals() -> list[str]:
    """Portfolio-level key insights across the six companies."""
    k = D.kpi_table()
    s = []
    one_off = [c["short"] for c in D.companies() if any("licensing" in n.lower() or "one-off" in n.lower() for n in c.get("data_notes", []))]
    core = k.drop(index=one_off, errors="ignore")  # one-off income inflates FY26 returns
    best_roce, worst_roce = core["roce"].idxmax(), k["roce"].idxmin()
    fb = D.financial_frame(k.loc[best_roce, "id"]).loc["FY26"]
    fw = D.financial_frame(k.loc[worst_roce, "id"]).loc["FY26"]
    m_b, m_w = (fb["ebitda"] - fb["depreciation"]) / fb["sales"] * 100, (fw["ebitda"] - fw["depreciation"]) / fw["sales"] * 100
    t_b, t_w = fb["sales"] / fb["capital_employed"], fw["sales"] / fw["capital_employed"]
    s.append(f"Return dispersion is wide: {best_roce} earns {k.loc[best_roce, 'roce']:.0f}% ROCE vs {worst_roce} at "
             f"{k.loc[worst_roce, 'roce']:.0f}%. Decomposed, it is mostly margin (EBIT margin {m_b:.0f}% vs {m_w:.0f}%) rather than capital turnover "
             f"({t_b:.2f}x vs {t_w:.2f}x)."
             + (f" {', '.join(one_off)} {'is' if len(one_off) == 1 else 'are'} left out of the best-ROCE pick because FY26 includes one-off income." if one_off else ""))

    def _strength(r):
        a = abs(r)
        return "strong" if a >= 0.6 else "moderate" if a >= 0.3 else "weak"

    _, r_inv = D.pooled_correlation("inventory_days", "roce")
    s.append(f"Across 30 company-years, inventory days vs ROCE, link strength {r_inv:+.2f} ({_strength(r_inv)}). "
             + ("high-inventory models systematically earn lower returns." if r_inv <= -0.3 else
                "Inventory alone doesn't explain returns; it matters most where it is extreme ("
                + ", ".join(f"{n} {v:.0f} d" for n, v in k["inventory_days"].sort_values(ascending=False).head(2).items()) + ")."))
    _, r_cc = D.pooled_correlation("ccc", "roce")
    s.append(f"Cash cycle vs ROCE, link strength {r_cc:+.2f} ({_strength(r_cc)}). Employee cost % changed across the six FY22–26 "
             f"(+{(D.panel('employee_pct').iloc[-1] - D.panel('employee_pct').iloc[0]).mean():.1f} points on average). The key FY27 question is whether revenue can grow faster than costs.")
    us_heavy = k[k["us_share"] >= 25].index.tolist()
    dom_heavy = k[k["india_share"] >= 50].index.tolist()
    s.append(f"US-heavy names ({', '.join(us_heavy) or 'none'}) carry the generics-tariff risk (Jul-2026 proposal); "
             f"India-heavy names ({', '.join(dom_heavy) or 'none'}) carry Indian price and volume risk instead.")
    mat = D.panel("material_pct")
    drop = (mat.iloc[0] - mat.iloc[-1]).sort_values(ascending=False)
    n_fell = int((drop > 0).sum())
    s.append(f"Material cost/sales fell at {n_fell} of {len(drop)} companies FY22–26 (largest: {drop.index[0]} −{drop.iloc[0]:.1f} points). "
             f"The FY27 risk is that this reverses, as API and solvent prices rise (flagged on Q1 calls).")
    return s
