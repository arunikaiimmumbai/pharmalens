"""Ratio Benchmark: every KPI side by side, against the industry, and over five years."""
import pandas as pd
import streamlit as st

from core import data as D
from core import glossary as G
from core import industry as IND
from core import theme as T
from views.common import IND_LABEL, compare_bar, multi_line, note_box

GROUPS = {
    "Growth": ["sales", "sales_cagr", "ebitda_cagr", "pat_cagr"],
    "Profitability": ["gross_margin", "ebitda_margin", "ebit_margin", "pat_margin"],
    "Returns": ["roce", "roic", "roe", "roa"],
    "Cost structure": ["material_pct", "employee_pct", "indirect_pct", "rnd_pct"],
    "Working capital": ["inventory_days", "debtor_days", "payable_days", "ccc", "wc_days"],
    "Cash quality": ["cfo_pat", "cfo_ebitda", "fcf_margin"],
    "Debt & efficiency": ["de_ratio", "net_debt_ebitda", "interest_cover", "asset_turnover", "fixed_asset_turnover"],
    "Valuation": ["mcap_cr", "pe", "pb", "ev_ebitda", "div_payout"],
    "Mix": ["us_share", "india_share"],
}

TRENDS = {"ROCE": ("roce", "%"), "ROIC": ("roic", "%"), "ROE": ("roe", "%"), "EBITDA margin": ("ebitda_margin", "%"),
          "Inventory days": ("inventory_days", " d"), "Debtor days": ("debtor_days", " d"), "Cash conversion cycle": ("ccc", " d"),
          "CFO / PAT": ("cfo_pat", "x"), "Free cash flow / sales": ("fcf_margin", "%"), "Debt / equity": ("de_ratio", "x"),
          "Asset turnover": ("asset_turnover", "x"), "Interest cover": ("interest_cover", "x")}


def render():
    T.hero("Ratio Benchmark", "Every ratio side by side, against the Nifty Pharma industry average, and over five years.",
           ["36 KPIs", "Industry benchmark", "Plain-English meaning", "5-year trends"])
    year = st.radio("Financial year", D.years(), index=4, horizontal=True, key="ratio_year")
    cmp = compare_bar("ratios", help_text="Pick companies to show only those columns (none = all six). "
                                          "Industry adds the Nifty Pharma average column.")
    k = D.kpi_table(year)
    comps = cmp["companies"] or list(k.index)

    T.section("KPI master table", f"{year} · green = best of the six, red = weakest")
    rows = []
    for grp, metrics in GROUPS.items():
        for m in metrics:
            if m not in k.columns:
                continue
            lab, unit, hib, _ = D.KPI_DEFS[m]
            row = {"Group": grp, "KPI": lab, "_hib": hib, "_m": m}
            for comp in k.index:
                row[comp] = k.loc[comp, m]
            row["Median of six"] = k[m].median()
            row[IND_LABEL] = IND.industry_value(m, year)["avg"]
            row["Meaning"] = G.meaning(m)
            rows.append(row)
    tbl = pd.DataFrame(rows)

    def color_row(r):
        hib = r["_hib"]
        vals = pd.to_numeric(r[list(k.index)], errors="coerce")
        styles = [""] * len(r)
        if hib is None or vals.isna().all():
            return styles
        best = vals.idxmax() if hib else vals.idxmin()
        worst = vals.idxmin() if hib else vals.idxmax()
        for i, col in enumerate(r.index):
            if col == best:
                styles[i] = "background-color:#E3F6EC;color:#0B7A43;font-weight:700"
            elif col == worst:
                styles[i] = "background-color:#FDECEC;color:#B71C1C;font-weight:700"
            elif col == IND_LABEL:
                styles[i] = "background-color:#F1F5F9;color:#0F1B33;font-style:italic"
        return styles

    disp = tbl.copy()
    for col in list(k.index) + ["Median of six", IND_LABEL]:
        disp[col] = [D.fmt(m, v) if v is not None and not (isinstance(v, float) and pd.isna(v)) else "–" for v, m in zip(tbl[col], tbl["_m"])]
    styled = disp.style.apply(lambda r: color_row(tbl.loc[r.name]), axis=1)
    order = ["Group", "KPI"] + comps + ["Median of six"] + ([IND_LABEL] if cmp["industry"] else []) + ["Meaning"]
    st.dataframe(styled, hide_index=True, use_container_width=True, height=600, column_order=order,
                 column_config={"Meaning": st.column_config.TextColumn(width="large")})
    st.caption(IND.meta()["method"] + " '–' = no consistent industry figure (e.g. R&D, US share, valuation multiples other than P/E).")
    note_box("KPI master table", peer="rt_table",
             facts=f"{year}: " + "; ".join(f"{c} ROCE {D.fmt('roce', k.loc[c, 'roce'])}, EBITDA margin {D.fmt('ebitda_margin', k.loc[c, 'ebitda_margin'])}" for c in k.index)
             + f". Industry ROCE {D.fmt('roce', IND.industry_value('roce', year)['avg'])}.")
    st.download_button("⬇️ Download KPI table (CSV)", tbl.drop(columns=["_hib", "_m"]).to_csv(index=False).encode(),
                       file_name=f"financial_kpis_{year}.csv", mime="text/csv")

    T.section("Five-year ratio trends", "pick any ratio · dashed line = industry average")
    t = st.radio("Ratio", list(TRENDS), horizontal=True, key="trend_ratio")
    col, suf = TRENDS[t]
    st.plotly_chart(multi_line(D.panel(col), f"{t} · FY22–26", suf, 420, highlight=cmp["companies"],
                               industry=cmp["industry"], metric=col), use_container_width=True)
    if cmp["industry"]:
        st.caption(IND.note(col))
    p = D.panel(col)
    note_box(f"{t} trend, FY22–26", peer=f"rt_trend_{col}", metric=col,
             facts="; ".join(f"{c}: {D.fmt(col, p[c].iloc[0])} → {D.fmt(col, p[c].iloc[-1])}" for c in p.columns)
             + f". Industry: {D.fmt(col, IND.industry_series(col)['Average'].iloc[0])} → {D.fmt(col, IND.industry_series(col)['Average'].iloc[-1])}.")

    T.section("Why ROE differs (DuPont)", "return on equity = profit margin × asset use × borrowing")
    rows = []
    for c in D.companies():
        if cmp["companies"] and c["short"] not in cmp["companies"]:
            continue
        df = D.financial_frame(c["id"]).loc[year]
        lev = df["total_assets"] / df["net_worth"]
        rows.append({"Company": c["short"], "PAT margin %": df["pat_margin"], "Asset turnover x": df["asset_turnover"],
                     "Equity multiplier x": lev, "ROE % (DuPont)": df["pat_margin"] * df["asset_turnover"] * lev})
    if cmp["industry"]:
        pm, at = IND.industry_value("pat_margin", year)["avg"], IND.industry_value("asset_turnover", year)["avg"]
        rows.append({"Company": IND_LABEL, "PAT margin %": pm, "Asset turnover x": at, "Equity multiplier x": None, "ROE % (DuPont)": IND.industry_value("roe", year)["avg"]})
    st.dataframe(pd.DataFrame(rows).style.format({"PAT margin %": "{:.1f}", "Asset turnover x": "{:.2f}", "Equity multiplier x": "{:.2f}",
                                                  "ROE % (DuPont)": "{:.1f}"}, na_rep="–"), hide_index=True, use_container_width=True)
    st.caption("This table uses shareholders' funds at year end, while the main table uses the average across the year, so the numbers differ slightly.")
    note_box("DuPont: why ROE differs", peer="rt_dupont", metric="roe",
             facts="; ".join(f"{r['Company']}: {r['PAT margin %']:.1f}% × {r['Asset turnover x']:.2f}" for r in rows if r["Company"] != IND_LABEL))
    T.footer(D.meta())
