"""Regulatory & Pipeline: ANDA/DMF engine correlated with US revenue, R&D and plant status."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T
from views.common import note_box, register


def render():
    T.hero("Regulatory & Pipeline", "US drug filings (ANDAs and DMFs), FDA plant status, and how they link to US revenue, R&D spend and margins.",
           ["ANDA filed · approved · pending", "USFDA status", "R&D productivity", "Correlations"])
    k = D.kpi_table()
    rows = []
    for c in D.companies():
        rg = c["regulatory"]
        st_txt = rg["status"].lower()
        open_issue = rg["fda_open"] if "fda_open" in rg else ("oai" in st_txt)
        risk = "Open issue" if open_issue else "Clean / remediated"
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
    note_box("USFDA site status", peer="rg_fda", facts="; ".join(f"{r['Company']}: {r['FDA status']}" for _, r in rdf.iterrows()))

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
        nopub = [r["Company"] for _, r in rdf.iterrows() if pd.isna(r["ANDA filed"]) and pd.isna(r["Pending"]) and pd.isna(r["US products"])]
        if nopub:
            st.caption(f"{' and '.join(nopub)} {'does' if len(nopub) == 1 else 'do'} not publish total US filings, so no bars appear here. "
                       "That means 'not published', not zero.")
        note_box("ANDA engine (US filings)", peer="rg_anda",
                 facts="; ".join(f"{r['Company']}: filed {r['ANDA filed']}, approved {r['ANDA approved']}, pending {r['Pending']}, US products {r['US products']}" for _, r in rdf.iterrows()))
    with b:
        T.section("R&D intensity vs EBITDA margin", "does higher R&D spend mean higher margin?")
        cmap = D.colors()
        fig = go.Figure()
        for _, r in rdf.iterrows():
            fig.add_trace(go.Scatter(x=[r["R&D %"]], y=[r["EBITDA %"]], mode="markers+text", text=[r["Company"]], textposition="top center",
                                     marker=dict(size=10 + r["US share %"] * 0.9, color=cmap[r["Company"]], line=dict(color="#fff", width=2)),
                                     name=r["Company"], hovertemplate=f"{r['Company']}<br>R&D %{{x:.1f}}%<br>EBITDA %{{y:.1f}}%<br>US share {r['US share %']:.0f}%<extra></extra>"))
        rr = rdf["R&D %"].corr(rdf["EBITDA %"])
        fig.update_layout(title=f"Bigger bubble = more US revenue · link between R&D and margin: {rr:+.2f}", xaxis_title="R&D % of sales", yaxis_title="EBITDA margin FY26 %",
                          showlegend=False, hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 400), use_container_width=True)
        note_box("R&D intensity vs EBITDA margin", peer="rg_rnd", metric="rnd_pct",
                 facts=f"Link strength {rr:+.2f}. " + "; ".join(f"{r['Company']}: R&D {r['R&D %']:.1f}%, margin {r['EBITDA %']:.1f}%, US {r['US share %']:.0f}%" for _, r in rdf.iterrows()))

    T.section("What the regulatory data says", "what the filings and news tell us")
    pts = "".join(f"<li>{p.format(rr=f'{rr:+.2f}')}</li>" for p in D.meta().get("regulatory_takeaways", []))
    st.markdown(f'<div class="card"><ul style="margin:0;padding-left:18px;font-size:.92rem">{pts}</ul></div>', unsafe_allow_html=True)

    register("What the regulatory data says", kind="text", facts="Approvals are not revenue; R&D spenders have lower margins today; compliance moves revenue; US share is a tariff-risk number.")
    with st.expander("Regulatory data table (all numbers above in one table)"):
        st.dataframe(rdf.drop(columns=["Detail"]), hide_index=True, use_container_width=True,
                     column_config={"US share %": st.column_config.ProgressColumn(min_value=0, max_value=50, format="%.0f%%"),
                                    "R&D %": st.column_config.NumberColumn(format="%.1f%%"),
                                    "EBITDA %": st.column_config.NumberColumn(format="%.1f%%")})
        st.caption("No industry average here: Nifty Pharma companies don't report filings and R&D in a consistent way.")
    T.footer(D.meta())
