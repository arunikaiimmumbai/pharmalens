"""P&L Lab: where revenue goes, which costs drive margin, and which numbers move together."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import industry as IND
from core import theme as T
from views.common import IND_LABEL, color, compare_bar, comparison_block, focus_picker, note_box, value

LINES = [("Material", "material_pct", "material_cost"), ("Employee", "employee_pct", "employee_cost"),
         ("Manufacturing", "manufacturing_pct", "manufacturing_cost"), ("Other / SG&A", "other_cost_pct", "other_cost")]


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
             ("Other op. items (net)", "recon_pct", "#CBD5E1"), ("EBITDA", "ebitda_margin", "#06B6D4")]
    fig = go.Figure()
    for lab, col, colr in parts:
        fig.add_trace(go.Bar(x=df.index, y=df[col], name=lab, marker_color=colr, marker_line=dict(color="#fff", width=2),
                             texttemplate="%{y:.0f}%", textposition="inside", insidetextfont=dict(color="#fff"),
                             hovertemplate=f"{lab}: %{{y:.1f}}% of sales<extra></extra>"))
    fig.update_layout(barmode="relative", title=f"{name} · each cost as % of revenue", yaxis_ticksuffix="%")
    return T.style_fig(fig, 420)


def render():
    T.hero("P&L Lab", "Where every rupee of revenue goes, which costs drive the margin, and which numbers move together.",
           ["P&L bridge", "Cost drivers ranked", "Cost growth check", "Test any two numbers"])
    cid = focus_picker("pnl_pick")
    if cid is None:
        T.footer(D.meta())
        return
    c = D.company(cid)
    df = D.financial_frame(cid)
    name = c["short"]
    cmp = compare_bar("pnl", exclude=name,
                      help_text="Pick companies and/or Industry to open a side-by-side comparison; the cost charts below also add them.")
    comparison_block("pnl", name, cmp, ["ebitda_margin", "gross_margin", "pat_margin", "employee_pct", "material_pct", "indirect_pct",
                                        "ebitda_cagr", "pat_cagr"], title="P&L side by side")
    names = [name] + cmp["companies"] + ([IND_LABEL] if cmp["industry"] else [])

    a, b = st.columns([1.1, 1])
    with a:
        yr = st.select_slider("Year", options=D.years(), value="FY26", key="pnl_year")
        st.plotly_chart(_waterfall(df, yr, name), use_container_width=True)
    with b:
        st.plotly_chart(_common_size(df, name), use_container_width=True)
        st.caption("'Other op. items (net)' is a small balancing figure so the costs add up to the company's reported total.")
    r = df.loc[yr]
    note_box(f"{name}: P&L bridge and cost mix", company=cid, theme="margin", metric="ebitda_margin",
             facts=f"{yr}: revenue ₹{r['sales']:,.0f} Cr, EBITDA ₹{r['ebitda']:,.0f} Cr ({r['ebitda_margin']:.1f}%), PAT ₹{r['pat']:,.0f} Cr; "
                   f"material {r['material_pct']:.1f}%, employee {r['employee_pct']:.1f}%, other {r['other_cost_pct']:.1f}% of sales. "
                   f"Industry EBITDA margin {IND.industry_value('ebitda_margin', yr)['avg']:.1f}%.")

    # ── Cost drivers ─────────────────────────────────────────────────────────
    T.section("Cost drivers ranked", "which costs moved the margin most, and which matter most today")
    a, b = st.columns(2)
    with a:
        rows = []
        for lab, pct, _ in LINES:
            rows.append({"line": lab, "pct": pct, name: df[pct].iloc[-1] - df[pct].iloc[0]})
        imp = pd.DataFrame(rows).sort_values(name, ascending=False)
        fig = go.Figure()
        for n in names:
            vals = []
            for pct in imp["pct"]:
                if n == IND_LABEL:
                    s = IND.industry_series(pct)["Average"]
                    vals.append(s.iloc[-1] - s.iloc[0])
                else:
                    f = D.financial_frame(next(x["id"] for x in D.companies() if x["short"] == n))
                    vals.append(f[pct].iloc[-1] - f[pct].iloc[0])
            fig.add_trace(go.Bar(y=imp["line"], x=vals, orientation="h", name="Industry avg" if n == IND_LABEL else n, marker_color=color(n),
                                 marker_pattern_shape="/" if n == IND_LABEL else "", text=[f"{v:+.1f}" for v in vals], textposition="outside",
                                 hovertemplate=f"{n}: %{{x:+.1f}} pts of sales<extra></extra>"))
        fig.add_vline(x=0, line_color=T.NAVY, line_width=1)
        fig.update_layout(barmode="group", yaxis=dict(autorange="reversed"), hovermode="closest",
                          title="Margin impact FY22 → FY26 (points of sales; + = cost rose, margin fell)")
        st.plotly_chart(T.style_fig(fig, 300 + 14 * len(names)), use_container_width=True)
    with b:
        r26 = df.iloc[-1]
        sens = []
        for lab, pct, cost in LINES:
            cost_v = r26[cost]
            sens.append({"Cost line": lab, "Cost ₹ Cr": cost_v, "1% saving adds to EBITDA ₹ Cr": cost_v * 0.01,
                         "= % of EBITDA": cost_v * 0.01 / r26["ebitda"] * 100, "Margin gain (bps)": cost_v * 0.01 / r26["sales"] * 10000})
        sens = pd.DataFrame(sens).sort_values("Cost ₹ Cr", ascending=False).reset_index(drop=True)
        sens.insert(0, "Rank", range(1, len(sens) + 1))
        fig = go.Figure(go.Bar(y=sens["Cost line"], x=sens["1% saving adds to EBITDA ₹ Cr"], orientation="h", marker_color=c["color"],
                               text=[f"₹{v:,.0f} Cr" for v in sens["1% saving adds to EBITDA ₹ Cr"]], textposition="outside",
                               hovertemplate="%{y}: ₹%{x:,.1f} Cr<extra></extra>"))
        fig.update_layout(title="Sensitivity: EBITDA gained from a 1% saving on each cost (FY26)", yaxis=dict(autorange="reversed"), hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 300), use_container_width=True)
    st.dataframe(sens.style.format({"Cost ₹ Cr": "{:,.0f}", "1% saving adds to EBITDA ₹ Cr": "{:,.1f}", "= % of EBITDA": "{:.2f}%",
                                    "Margin gain (bps)": "{:.0f}"}), hide_index=True, use_container_width=True)
    if cmp["industry"]:
        st.caption(IND.note("employee_pct"))
    el = D.cost_elasticity(cid)
    with st.expander("Cost growth check: how fast each cost grew compared with revenue (1.0 = same pace)"):
        st.dataframe(el.style.format({"Extra cost since FY22 (₹ Cr)": "{:,.0f}", "Extra cost per ₹100 of extra revenue": "{:.1f}",
                                      "Cost growth per year %": "{:.1f}%", "Cost growth vs revenue growth": "{:.2f}x"}, na_rep="n/a")
                     .background_gradient(subset=["Cost growth vs revenue growth"], cmap="Reds", vmin=0.5, vmax=2.5),
                     hide_index=True, use_container_width=True)
        st.caption("Above 1.0x = the cost grows faster than revenue, so it eats margin. Interest often shows a big number because it starts from a tiny base.")
    top = imp.iloc[0]
    note_box(f"{name}: cost drivers", company=cid, theme="cost", metric="employee_pct",
             facts=f"Biggest margin hit FY22–26: {top['line']} ({top[name]:+.1f} pts of sales). Biggest cost today: {sens.iloc[0]['Cost line']} "
                   f"(₹{sens.iloc[0]['Cost ₹ Cr']:,.0f} Cr; a 1% saving adds ₹{sens.iloc[0]['1% saving adds to EBITDA ₹ Cr']:,.0f} Cr EBITDA). "
                   f"Employee cost {df['employee_pct'].iloc[0]:.1f}% → {df['employee_pct'].iloc[-1]:.1f}% of sales; industry {IND.industry_value('employee_pct')['avg']:.1f}%.")

    # ── Growth per year by line ──────────────────────────────────────────────
    T.section("Growth per year by line", "FY22 → FY26 (CAGR)")
    keys = [("Revenue", "sales"), ("EBITDA", "ebitda"), ("PAT", "pat"), ("Employee cost", "employee_cost"), ("Material cost", "material_cost"),
            ("Indirect (mfg + other)", "indirect_cost"), ("Depreciation", "depreciation"), ("Interest", "interest")]
    tbl = pd.DataFrame({"Line": [k_ for k_, _ in keys], "FY22 ₹ Cr": [df[x].iloc[0] for _, x in keys], "FY26 ₹ Cr": [df[x].iloc[-1] for _, x in keys]})
    tbl[f"{name} CAGR %"] = [D._cagr(df[x].iloc[0], df[x].iloc[-1], 4) * 100 for _, x in keys]
    for n in cmp["companies"]:
        f = D.financial_frame(next(x["id"] for x in D.companies() if x["short"] == n))
        tbl[f"{n} CAGR %"] = [D._cagr(f[x].iloc[0], f[x].iloc[-1], 4) * 100 for _, x in keys]
    if cmp["industry"]:
        tbl["Industry CAGR %"] = [IND.industry_value(m_)["avg"] if m_ else None for m_ in ("sales_cagr", "ebitda_cagr", "pat_cagr", None, None, None, None, None)]
    st.dataframe(tbl.style.format({c_: "{:.1f}%" for c_ in tbl.columns if "CAGR" in c_} | {"FY22 ₹ Cr": "{:,.0f}", "FY26 ₹ Cr": "{:,.0f}"}, na_rep="–")
                 .background_gradient(subset=[f"{name} CAGR %"], cmap="Blues"), hide_index=True, use_container_width=True)
    note_box(f"{name}: growth by P&L line", company=cid, theme="growth", metric="sales_cagr",
             facts="; ".join(f"{l_} {v:.1f}%/yr" for l_, v in zip(tbl["Line"], tbl[f"{name} CAGR %"]) if not pd.isna(v)))

    # ── Test any two numbers ─────────────────────────────────────────────────
    T.section("Test any two numbers", "does one number move with another? each dot = one company in one year")
    opts = {"Employee cost %": "employee_pct", "Material cost %": "material_pct", "Inventory days": "inventory_days",
            "Cash conversion cycle": "ccc", "EBITDA margin": "ebitda_margin", "ROCE": "roce", "ROIC": "roic", "ROE": "roe",
            "Revenue growth %": "sales_growth", "Asset turnover": "asset_turnover", "Debt/equity": "de_ratio", "Free cash flow / sales": "fcf_margin"}
    c1, c2, c3 = st.columns([1, 1, 1.2])
    x = c1.selectbox("X axis", list(opts), index=2, key="px")
    y = c2.selectbox("Y axis", list(opts), index=5, key="py")
    wide = c3.toggle("Include all 20 Nifty Pharma companies", value=False, key="pwide",
                     help="Off: the six companies (30 dots). On: the 20 industry companies (about 100 dots) for a sturdier test.")
    xm, ym = opts[x], opts[y]
    rows = []
    if wide:
        for sym, (nm, f, _) in IND.frames().items():
            for yy in f.index:
                if xm in f.columns and ym in f.columns:
                    rows.append({"Company": nm, "Year": yy, xm: f.loc[yy, xm], ym: f.loc[yy, ym]})
    else:
        for co in D.companies():
            f = D.financial_frame(co["id"])
            for yy in f.index:
                rows.append({"Company": co["short"], "Year": yy, xm: f.loc[yy, xm], ym: f.loc[yy, ym]})
    pdf = pd.DataFrame(rows).replace([np.inf, -np.inf], np.nan).dropna()
    rr = pdf[xm].corr(pdf[ym]) if len(pdf) > 2 else np.nan
    cmap = D.colors()
    fig = go.Figure()
    for comp, g in pdf.groupby("Company"):
        fig.add_trace(go.Scatter(x=g[xm], y=g[ym], mode="markers", name=comp, text=g["Year"],
                                 marker=dict(size=11 if comp in cmap else 8, color=cmap.get(comp, "#CBD5E1"), line=dict(color="#fff", width=1.5)),
                                 hovertemplate=f"{comp} %{{text}}<br>{x}: %{{x:.1f}}<br>{y}: %{{y:.1f}}<extra></extra>"))
    if len(pdf) > 2:
        mm, b0 = np.polyfit(pdf[xm], pdf[ym], 1)
        xs = np.linspace(pdf[xm].min(), pdf[xm].max(), 20)
        fig.add_trace(go.Scatter(x=xs, y=mm * xs + b0, mode="lines", name="trend", line=dict(color=T.MUTED, dash="dot", width=2), hoverinfo="skip"))
    strength = "strong" if abs(rr) >= 0.6 else "moderate" if abs(rr) >= 0.3 else "weak"
    fig.update_layout(title=f"Link strength {rr:+.2f} ({strength}; +1 = move together, 0 = no link, −1 = opposite) · {len(pdf)} dots",
                      xaxis_title=x, yaxis_title=y, hovermode="closest", showlegend=not wide)
    st.plotly_chart(T.style_fig(fig, 420), use_container_width=True)
    if wide:
        st.caption("Grey dots = the other Nifty Pharma companies; coloured = the six in this study.")
    note_box("Test any two numbers", peer="pl_scatter", facts=f"{x} vs {y}: link strength {rr:+.2f} ({strength}) across {len(pdf)} company-years.")
    T.footer(D.meta())
