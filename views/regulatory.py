"""Regulatory & Pipeline: ANDA/DMF engine correlated with US revenue, R&D and plant status."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T


def render():
    T.hero("Regulatory & Pipeline", "US drug filings (ANDAs and DMFs), FDA plant status, and how they link to US revenue, R&D spend and margins.",
           ["ANDA filed · approved · pending", "USFDA status", "R&D productivity", "Correlations"])
    k = D.kpi_table()
    rows = []
    for c in D.companies():
        rg = c["regulatory"]
        st_txt = rg["status"].lower()
        risk = "Open issue" if "oai" in st_txt else "Clean / remediated"
        rows.append({"Company": c["short"], "ANDA filed": rg["anda_filed"], "ANDA approved": rg["anda_approved"],
                     "Tentative": rg["anda_tentative"], "Pending": rg["anda_pending"],
                     "US products": rg["us_products_commercialised"], "US DMFs": rg["dmf_us"],
                     "US share %": k.loc[c["short"], "us_share"], "R&D %": c["footprint"]["rnd_pct"],
                     "EBITDA %": k.loc[c["short"], "ebitda_margin"], "FDA status": risk, "Detail": rg["status"], "As of": rg["as_of"]})
    rdf = pd.DataFrame(rows)

    T.section("USFDA site status", "latest disclosed")
    cols = st.columns(6)
    for col, (_, r) in zip(cols, rdf.iterrows()):
        kind = "bad" if r["FDA status"] == "Open issue" else "good"
        col.markdown(f"""<div class="card" style="border-top:4px solid {D.colors()[r['Company']]}"><h4>{r['Company']}</h4>
            {T.pill(r['FDA status'], kind)}<div style="font-size:.78rem;margin-top:6px;color:#42526E">{r['Detail']}</div></div>""",
                     unsafe_allow_html=True)

    a, b = st.columns([1.1, 1])
    with a:
        T.section("ANDA engine", "cumulative, where disclosed")
        sub = rdf.dropna(subset=["ANDA filed", "Pending", "US products"], how="all")
        fig = go.Figure()
        for lab, col, colr in [("Filed", "ANDA filed", "#C9DCFF"), ("Approved", "ANDA approved", "#1D4ED8"),
                               ("Pending", "Pending", "#06B6D4"), ("US products marketed", "US products", "#0A2A66")]:
            fig.add_trace(go.Bar(x=sub["Company"], y=sub[col], name=lab, marker_color=colr, marker_cornerradius=4,
                                 text=sub[col].map(lambda v: "" if pd.isna(v) else f"{v:.0f}"), textposition="outside",
                                 hovertemplate=f"{lab}: %{{y}}<extra></extra>"))
        fig.update_layout(barmode="group", title="ANDA filed / approved / pending & US products")
        st.plotly_chart(T.style_fig(fig, 400), use_container_width=True)
        st.caption("n.d. = not disclosed by the company in a comparable form (Ipca, Mankind report launches/filings rather than cumulative ANDAs).")
    with b:
        T.section("R&D intensity vs EBITDA margin", "does higher R&D spend mean higher margin?")
        cmap = D.colors()
        fig = go.Figure()
        for _, r in rdf.iterrows():
            fig.add_trace(go.Scatter(x=[r["R&D %"]], y=[r["EBITDA %"]], mode="markers+text", text=[r["Company"]], textposition="top center",
                                     marker=dict(size=10 + r["US share %"] * 0.9, color=cmap[r["Company"]], line=dict(color="#fff", width=2)),
                                     name=r["Company"], hovertemplate=f"{r['Company']}<br>R&D %{{x:.1f}}%<br>EBITDA %{{y:.1f}}%<br>US share {r['US share %']:.0f}%<extra></extra>"))
        rr = rdf["R&D %"].corr(rdf["EBITDA %"])
        fig.update_layout(title=f"Bubble = US revenue share · r = {rr:+.2f}", xaxis_title="R&D % of sales", yaxis_title="EBITDA margin FY26 %",
                          showlegend=False, hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 400), use_container_width=True)

    T.section("What the regulatory data says", "what the filings and news tell us")
    st.markdown(f"""<div class="card"><ul style="margin:0;padding-left:18px;font-size:.92rem">
    <li><b>Approvals ≠ revenue.</b> Alembic has the deepest book (244 approvals, 185 marketed) → ~₹3,100 Cr annualised US revenue (Q1 FY27 ×4); Ajanta earns ~₹1,950 Cr annualised
    from ~51 products, about 2.3x more revenue per product. Picking products with few competitors beats filing more of them.</li>
    <li><b>R&D intensity is inversely related to margin today</b> (r = {rr:+.2f}): Alembic (9% R&D) and Glenmark (6–7%) carry the heaviest pipelines;
    the payoff is visible in US growth (Alembic US +49%, Glenmark NA +41% in Q1 FY27) but not yet in margin.</li>
    <li><b>Compliance is a revenue variable.</b> Alkem's Daman OAI (Aug-2026) covers ~45% of its US sales and coincided with a US guidance cut and a 52-week low;
    Glenmark's Goa warning-letter closeout (Sep-2026) and Monroe VAI remove overhangs ahead of 2–3 respiratory approvals.</li>
    <li><b>Tariff lens.</b> Generics are outside the Sep-2026 Section 232 tariff, but the Jul-2026 proposal (0% → 100% → 200%) makes US-share a
    strategic-risk KPI: Alembic 36%, Ajanta 30%, Glenmark 27%, Alkem 20%.</li></ul></div>""", unsafe_allow_html=True)

    T.section("Regulatory data table")
    st.dataframe(rdf.drop(columns=["Detail"]), hide_index=True, use_container_width=True,
                 column_config={"US share %": st.column_config.ProgressColumn(min_value=0, max_value=50, format="%.0f%%"),
                                "R&D %": st.column_config.NumberColumn(format="%.1f%%"),
                                "EBITDA %": st.column_config.NumberColumn(format="%.1f%%")})
    T.footer(D.meta())
