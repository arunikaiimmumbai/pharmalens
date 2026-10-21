"""P&L Lab: five-year profitability, cost structure, CAGR and correlation analysis."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T
from views.common import focus_picker, multi_line


def _waterfall(df: pd.DataFrame, year: str, name: str):
    r = df.loc[year]
    items = [("Revenue", r["sales"], "absolute"), ("Material", -r["material_cost"], "relative"),
             ("Employee", -r["employee_cost"], "relative"), ("Manufacturing", -r["manufacturing_cost"], "relative"),
             ("Other / SG&A", -r["other_cost"], "relative"), ("Other op. items (net)", -r["recon_cost"], "relative"),
             ("EBITDA", r["ebitda"], "total"),
             ("D&A", -r["depreciation"], "relative"), ("Interest", -r["interest"], "relative"),
             ("Other income", r["other_income"], "relative"), ("PBT", r["pbt"], "total"),
             ("Tax", -(r["pbt"] - r["pat"]), "relative"), ("PAT", r["pat"], "total")]
    fig = go.Figure(go.Waterfall(
        x=[i[0] for i in items], y=[i[1] for i in items], measure=[i[2] for i in items],
        text=[f"{v:,.0f}" for _, v, _ in items], textposition="outside",
        increasing=dict(marker=dict(color="#06B6D4")), decreasing=dict(marker=dict(color="#93B8FF")),
        totals=dict(marker=dict(color="#1D4ED8")), connector=dict(line=dict(color="#DCE6F5", width=1)),
        hovertemplate="%{x}: ₹%{y:,.0f} Cr<extra></extra>"))
    fig.update_layout(title=f"{name} · {year} P&L bridge (₹ Cr)", hovermode="closest", showlegend=False)
    return T.style_fig(fig, 420)


def _common_size(df: pd.DataFrame, name: str):
    parts = [("Material", "material_pct", "#0A2A66"), ("Employee", "employee_pct", "#1D4ED8"),
             ("Manufacturing", "manufacturing_pct", "#3B82F6"), ("Other / SG&A", "other_cost_pct", "#93B8FF"),
             ("Other op. items (net)", "recon_pct", "#CBD5E1"),
             ("EBITDA", "ebitda_margin", "#06B6D4")]
    fig = go.Figure()
    for lab, col, colr in parts:
        fig.add_trace(go.Bar(x=df.index, y=df[col], name=lab, marker_color=colr, marker_line=dict(color="#fff", width=2),
                             text=[f"{v:.0f}%" for v in df[col]], textposition="inside", insidetextfont=dict(color="#fff"), texttemplate="%{y:.0f}%",
                             hovertemplate=f"{lab}: %{{y:.1f}}% of sales<extra></extra>"))
    fig.update_layout(barmode="relative", title=f"{name} · common-size P&L (% of revenue)", yaxis_ticksuffix="%")
    return T.style_fig(fig, 400)


def render():
    T.hero("P&L Lab", "Where every rupee of revenue goes over five years, which costs are growing too fast, "
           "and which cost lines move together.", ["Turnover · EBITDA · PAT", "Cost elasticity", "Correlation matrix", "CAGR league table"])
    cid = focus_picker("pnl_pick")
    c = D.company(cid)
    df = D.financial_frame(cid)
    name = c["short"]

    a, b = st.columns([1.1, 1])
    with a:
        yr = st.select_slider("Year", options=D.years(), value="FY26", key="pnl_year")
        st.plotly_chart(_waterfall(df, yr, name), use_container_width=True)
    with b:
        st.plotly_chart(_common_size(df, name), use_container_width=True)
        st.caption("'Other op. items (net)' reconciles reported total expenses to the cost schedules (inventory changes, "
                   "reclassifications; negative where one-off income, such as Glenmark's FY26 licensing income, sits in revenue).")

    T.section("Five-year trajectory", "revenue, EBITDA and PAT · ₹ Cr")
    fig = go.Figure()
    for col, lab, colr in [("sales", "Revenue", "#0A2A66"), ("ebitda", "EBITDA", "#1D4ED8"), ("pat", "PAT", "#06B6D4")]:
        fig.add_trace(go.Bar(x=df.index, y=df[col], name=lab, marker_color=colr, marker_cornerradius=4,
                             text=[f"{v:,.0f}" for v in df[col]], textposition="outside", hovertemplate=f"{lab}: ₹%{{y:,.0f}} Cr<extra></extra>"))
    fig.update_layout(barmode="group", title=f"{name} · revenue, EBITDA, PAT (₹ Cr)")
    c1, c2 = st.columns([1.3, 1])
    c1.plotly_chart(T.style_fig(fig, 380), use_container_width=True)
    with c2:
        tbl = pd.DataFrame({
            "Metric": ["Revenue", "EBITDA", "PAT", "Employee cost", "Material cost", "Indirect (mfg+other)", "Depreciation", "Interest"],
            "FY22": [df[x].iloc[0] for x in ["sales", "ebitda", "pat", "employee_cost", "material_cost", "indirect_cost", "depreciation", "interest"]],
            "FY26": [df[x].iloc[-1] for x in ["sales", "ebitda", "pat", "employee_cost", "material_cost", "indirect_cost", "depreciation", "interest"]],
        })
        tbl["CAGR %"] = ((tbl["FY26"] / tbl["FY22"]).clip(lower=0) ** 0.25 - 1) * 100
        tbl.loc[(tbl["FY22"] <= 0) | (tbl["FY26"] <= 0), "CAGR %"] = np.nan
        st.markdown("**4-year CAGR by line (FY22→FY26)**")
        st.dataframe(tbl.style.format({"FY22": "{:,.0f}", "FY26": "{:,.0f}", "CAGR %": "{:.1f}%"})
                     .background_gradient(subset=["CAGR %"], cmap="Blues"), hide_index=True, use_container_width=True)

    T.section("Cost elasticity", "cost growth ÷ revenue growth (above 1.0 means the cost is growing faster than sales)")
    el = D.cost_elasticity(cid)
    c1, c2 = st.columns([1, 1])
    with c1:
        e = el.dropna(subset=["Elasticity vs revenue"])
        colors = ["#C62828" if v > 1.05 else "#0F9D58" if v < 0.95 else "#7A8AA6" for v in e["Elasticity vs revenue"]]
        fig = go.Figure(go.Bar(y=e["Cost line"], x=e["Elasticity vs revenue"], orientation="h", marker_color=colors, marker_cornerradius=6,
                               text=[f"{v:.2f}x" for v in e["Elasticity vs revenue"]], textposition="outside",
                               hovertemplate="%{y}: %{x:.2f}x revenue growth<extra></extra>"))
        fig.add_vline(x=1, line_dash="dot", line_color=T.NAVY, annotation_text="grows with revenue", annotation_font_color=T.MUTED)
        fig.update_layout(title=f"{name} · cost CAGR ÷ revenue CAGR", hovermode="closest", yaxis=dict(autorange="reversed"))
        st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    with c2:
        st.dataframe(el.style.format({"Δ cost (₹ Cr)": "{:,.0f}", "Δ cost per ₹100 Δ revenue": "{:.1f}", "Cost CAGR %": "{:.1f}%",
                                      "Elasticity vs revenue": "{:.2f}x"}, na_rep="n/a"), hide_index=True, use_container_width=True)
        st.caption("Reads as: for every ₹100 of incremental revenue since FY22, how many rupees went to each cost line. "
                   "Red bars are costs growing faster than revenue. That is where margin is being lost.")

    T.section("Correlation matrix", "which numbers moved together, FY22–26 (blue = together, orange = opposite)")
    cols = ["sales", "employee_cost", "material_cost", "indirect_cost", "ebitda_margin", "employee_pct", "inventory_days", "roce", "borrowings"]
    labels = ["Revenue", "Employee ₹", "Material ₹", "Indirect ₹", "EBITDA %", "Employee %", "Inventory d", "ROCE", "Borrowings"]
    cm = D.correlation_matrix(cid, cols)
    fig = go.Figure(go.Heatmap(z=cm.values, x=labels, y=labels, zmin=-1, zmax=1, colorscale=T.DIVERGING, xgap=2, ygap=2,
                               text=np.round(cm.values, 2), texttemplate="%{text}", hovertemplate="%{y} × %{x}: r = %{z:.2f}<extra></extra>"))
    fig.update_layout(title=f"{name} · Pearson r (n = 5 years, directional)", yaxis=dict(autorange="reversed"), hovermode="closest")
    c1, c2 = st.columns([1.2, 1])
    c1.plotly_chart(T.style_fig(fig, 460), use_container_width=True)
    with c2:
        T.section("Pooled relationship explorer", "all six companies × five years = 30 data points")
        opts = {"Employee cost %": "employee_pct", "Material cost %": "material_pct", "Indirect cost %": "indirect_pct",
                "Inventory days": "inventory_days", "Cash conversion cycle": "ccc", "EBITDA margin": "ebitda_margin",
                "ROCE": "roce", "ROE": "roe", "Revenue growth %": "sales_growth", "Employee cost growth %": "employee_growth",
                "Asset turnover": "asset_turnover", "Debt/equity": "de_ratio"}
        x = st.selectbox("X", list(opts), index=3, key="px")
        y = st.selectbox("Y", list(opts), index=6, key="py")
        pdf, r = D.pooled_correlation(opts[x], opts[y])
        cmap = D.colors()
        fig = go.Figure()
        for comp, g in pdf.groupby("Company"):
            fig.add_trace(go.Scatter(x=g[opts[x]], y=g[opts[y]], mode="markers", name=comp, text=g["Year"],
                                     marker=dict(size=11, color=cmap[comp], line=dict(color="#fff", width=2)),
                                     hovertemplate=f"{comp} %{{text}}<br>{x}: %{{x:.1f}}<br>{y}: %{{y:.1f}}<extra></extra>"))
        if len(pdf) > 2:
            m, b0 = np.polyfit(pdf[opts[x]], pdf[opts[y]], 1)
            xs = np.linspace(pdf[opts[x]].min(), pdf[opts[x]].max(), 20)
            fig.add_trace(go.Scatter(x=xs, y=m * xs + b0, mode="lines", name="trend", line=dict(color=T.MUTED, dash="dot", width=2), hoverinfo="skip"))
        fig.update_layout(title=f"r = {r:+.2f}", xaxis_title=x, yaxis_title=y, hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 330), use_container_width=True)

    T.section("Peer trend comparison", "pick a metric")
    metric_opts = {"Revenue (₹ Cr)": ("sales", ""), "EBITDA margin": ("ebitda_margin", "%"), "PAT margin": ("pat_margin", "%"),
                   "Gross margin": ("gross_margin", "%"), "Employee cost / sales": ("employee_pct", "%"),
                   "Material cost / sales": ("material_pct", "%"), "Indirect cost / sales": ("indirect_pct", "%"),
                   "Revenue growth YoY": ("sales_growth", "%")}
    mlab = st.radio("Metric", list(metric_opts), horizontal=True, key="pnl_metric", index=1)
    mcol, suf = metric_opts[mlab]
    st.plotly_chart(multi_line(D.panel(mcol), f"{mlab} · FY22–26", suf, 400, highlight=name), use_container_width=True)

    T.section("Quarterly momentum", "Q1 FY26 → Q1 FY27")
    q = c["quarterly"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=D.meta()["quarters"], y=q["sales"], name="Revenue", marker_color="#C9DCFF", marker_cornerradius=4,
                         hovertemplate="Revenue ₹%{y:,} Cr<extra></extra>"))
    fig.add_trace(go.Bar(x=D.meta()["quarters"], y=q["ebitda"], name="EBITDA", marker_color="#1D4ED8", marker_cornerradius=4,
                         hovertemplate="EBITDA ₹%{y:,} Cr<extra></extra>"))
    fig.add_trace(go.Bar(x=D.meta()["quarters"], y=q["pat"], name="PAT", marker_color="#06B6D4", marker_cornerradius=4,
                         hovertemplate="PAT ₹%{y:,} Cr<extra></extra>"))
    fig.update_layout(barmode="group", title=f"{name} · quarterly P&L (₹ Cr) · OPM: " + " → ".join(f"{v}%" for v in q["opm"]))
    st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    if c.get("data_notes"):
        st.info("Data notes: " + " ".join(c["data_notes"]))
    T.footer(D.meta())
