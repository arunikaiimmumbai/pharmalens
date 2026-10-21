"""Ratio Benchmark: every KPI, ranked, scored and trended."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T
from views.common import bar_peers, multi_line

GROUPS = {
    "Growth": ["sales", "sales_cagr", "ebitda_cagr", "pat_cagr"],
    "Profitability": ["gross_margin", "ebitda_margin", "pat_margin"],
    "Returns": ["roce", "roe", "roa"],
    "Cost structure": ["material_pct", "employee_pct", "indirect_pct", "rnd_pct"],
    "Working capital": ["inventory_days", "debtor_days", "payable_days", "ccc", "wc_days"],
    "Cash quality": ["cfo_pat", "cfo_ebitda"],
    "Leverage & efficiency": ["de_ratio", "debt_ebitda", "interest_cover", "asset_turnover", "fixed_asset_turnover"],
    "Valuation": ["mcap_cr", "pe", "pb", "ev_ebitda", "div_payout"],
    "Mix": ["us_share", "india_share"],
}


def render():
    T.hero("Ratio Benchmark", "Every ratio side by side, ranked against the other five companies and shown over five years.",
           ["33 KPIs", "Peer median & rank", "Radar comparison", "5-year trends"])
    year = st.radio("Financial year", D.years(), index=4, horizontal=True, key="ratio_year")
    k = D.kpi_table(year)

    T.section("KPI master table", f"{year} · green = best in peer set, red = weakest")
    rows = []
    for grp, metrics in GROUPS.items():
        for m in metrics:
            if m not in k.columns:
                continue
            lab, unit, hib, _ = D.KPI_DEFS[m]
            row = {"Group": grp, "KPI": lab}
            for comp in k.index:
                row[comp] = k.loc[comp, m]
            row["Median"] = k[m].median()
            row["_hib"] = hib
            row["_m"] = m
            rows.append(row)
    tbl = pd.DataFrame(rows)
    comps = list(k.index)

    def color_row(r):
        hib = r["_hib"]
        vals = pd.to_numeric(r[comps], errors="coerce")
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
        return styles

    def fmt_cell(v, m):
        return D.fmt(m, v)

    disp = tbl.copy()
    for comp in comps + ["Median"]:
        disp[comp] = [fmt_cell(v, m) for v, m in zip(tbl[comp], tbl["_m"])]
    styled = disp.style.apply(lambda r: color_row(tbl.loc[r.name]), axis=1)
    st.dataframe(styled, hide_index=True, use_container_width=True, height=560,
                 column_order=["Group", "KPI"] + comps + ["Median"])
    st.download_button("⬇️ Download KPI table (CSV)", tbl.drop(columns=["_hib", "_m"]).to_csv(index=False).encode(),
                       file_name=f"pharmalens_kpis_{year}.csv", mime="text/csv")

    a, b = st.columns([1, 1.15])
    with a:
        T.section("Radar comparison", "scored 0 to 100, where 100 is best of the six")
        sel = st.multiselect("Companies", comps, default=comps[:3], key="radar_sel")
        rm = ["sales_cagr", "ebitda_margin", "roce", "roe", "cfo_pat", "ccc", "inventory_days", "de_ratio", "employee_pct"]
        sc = D.score_matrix(k, rm)
        labels = [D.KPI_DEFS[m][0].split(" (")[0] for m in rm]
        fig = go.Figure()
        cmap = D.colors()
        for comp in sel:
            v = sc.loc[comp].tolist()
            fig.add_trace(go.Scatterpolar(r=v + v[:1], theta=labels + labels[:1], name=comp, fill="toself", opacity=0.75,
                                          line=dict(color=cmap[comp], width=2.5), fillcolor=cmap[comp].replace("#", "#") + "22"))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False, gridcolor="#DCE6F5"),
                                     angularaxis=dict(gridcolor="#DCE6F5", tickfont=dict(size=11))), hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 460), use_container_width=True)
    with b:
        T.section("KPI spotlight", "peer bar with median")
        choice = st.selectbox("KPI", [m for g in GROUPS.values() for m in g if m in k.columns],
                              format_func=lambda m: D.KPI_DEFS[m][0], index=7, key="spot")
        unit = D.KPI_DEFS[choice][1]
        suf = "%" if unit == "%" else "x" if unit == "x" else " d" if unit == "days" else ""
        st.plotly_chart(bar_peers(k[choice], D.KPI_DEFS[choice][0], suf, 420, sort_desc=D.KPI_DEFS[choice][2] is not False),
                        use_container_width=True)

    T.section("Five-year ratio trends", "pick any ratio")
    trend_opts = {"ROCE": ("roce", "%"), "ROE": ("roe", "%"), "EBITDA margin": ("ebitda_margin", "%"), "Inventory days": ("inventory_days", " d"),
                  "Debtor days": ("debtor_days", " d"), "Cash conversion cycle": ("ccc", " d"), "Debt / equity": ("de_ratio", "x"),
                  "CFO / PAT": ("cfo_pat", "x"), "Asset turnover": ("asset_turnover", "x"), "Interest cover": ("interest_cover", "x")}
    t = st.radio("Ratio", list(trend_opts), horizontal=True, key="trend_ratio")
    col, suf = trend_opts[t]
    st.plotly_chart(multi_line(D.panel(col), f"{t} · FY22–26", suf, 400), use_container_width=True)

    T.section("Why ROE differs (DuPont)", "return on equity = profit margin × asset use × borrowing")
    rows = []
    for comp in comps:
        df = D.financial_frame(D.company(next(c["id"] for c in D.companies() if c["short"] == comp))["id"]).loc[year]
        lev = df["total_assets"] / df["net_worth"]
        rows.append({"Company": comp, "PAT margin %": df["pat_margin"], "Asset turnover x": df["asset_turnover"],
                     "Equity multiplier x": lev, "ROE % (DuPont)": df["pat_margin"] * df["asset_turnover"] * lev})
    st.dataframe(pd.DataFrame(rows).style.format({"PAT margin %": "{:.1f}", "Asset turnover x": "{:.2f}", "Equity multiplier x": "{:.2f}",
                                                  "ROE % (DuPont)": "{:.1f}"}), hide_index=True, use_container_width=True)
    st.caption("This table uses shareholders' funds at year end, while the main table uses the average across the year, so the numbers differ slightly.")
    T.footer(D.meta())
