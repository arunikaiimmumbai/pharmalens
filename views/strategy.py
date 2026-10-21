"""Strategy Room: salient features, top-5 problem statements, consulting opportunities, digital journey."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T
from views.common import bullets, focus_picker

SERVICE_LINES = ["Strategy & portfolio", "Commercial excellence", "Operations & supply chain", "Quality & compliance",
                 "Finance & working capital", "Transactions & PMI", "Tax & trade", "Digital, data & AI"]

KEYWORDS = {
    "Strategy & portfolio": ["strategy", "portfolio", "capital allocation", "r&d", "corporate"],
    "Commercial excellence": ["commercial", "sfe", "launch", "omnichannel", "consumer", "rgm"],
    "Operations & supply chain": ["operations", "supply", "network", "manufacturing", "cost", "procurement"],
    "Quality & compliance": ["quality", "compliance", "risk"],
    "Finance & working capital": ["finance", "working capital", "o2c", "treasury"],
    "Transactions & PMI": ["transactions", "integration", "pmi", "m&a", "value creation", "due diligence", "corporate development"],
    "Tax & trade": ["tax", "trade"],
}

JOURNEY = [
    ("1 · Foundation", "Single ERP (S/4HANA), master-data governance, cloud data lake, e-QMS baseline", "0–6 mo"),
    ("2 · Connected", "Omnichannel HCP engagement, MES/LIMS & electronic batch records, integrated S&OP, CRM-SFA analytics", "6–18 mo"),
    ("3 · Intelligent", "AI demand sensing, predictive quality & deviation analytics, GenAI regulatory dossier drafting, next-best-action for MRs", "18–30 mo"),
    ("4 · Autonomous", "Self-optimising plants (digital twins), AI-led molecule & ANDA selection, autonomous control-tower supply chain", "30 mo+"),
]

DIGITAL_USE_CASES = {
    "Commercial & omnichannel": "Next-best-action for MRs, e-detailing, Rx analytics (IQVIA/AWACS) & digital CME",
    "Supply chain & S&OP": "AI demand sensing (US 852/EDI, India secondary), inventory optimisation, control tower",
    "Manufacturing 4.0 & quality": "e-BMR, MES, predictive maintenance, data-integrity monitoring, CAPA analytics",
    "R&D & regulatory": "GenAI for ANDA/DMF dossier authoring, BE study analytics, AI molecule selection",
    "Finance & ERP": "Continuous close, O2C automation, gross-to-net (US chargebacks/rebates) analytics",
    "Data & AI": "Enterprise data platform, AI CoE, LLM agents (like this one) over internal + market data",
}


SWOT_STYLE = {
    "strengths": ("S", "Strengths", "#0F9D58", "#F1FAF5"),
    "weaknesses": ("W", "Weaknesses", "#C62828", "#FDF3F3"),
    "opportunities": ("O", "Opportunities", "#1D4ED8", "#F2F6FF"),
    "threats": ("T", "Threats", "#B45309", "#FFF8EE"),
}


def _swot_box(key: str, items: list[str], compact: bool = False) -> str:
    letter, title, edge, tint = SWOT_STYLE[key]
    size = ".8rem" if compact else ".9rem"
    lis = "".join(f"<li style='margin:3px 0'>{i}</li>" for i in items)
    return (f'<div style="background:{tint};border:1px solid #DCE6F5;border-left:5px solid {edge};border-radius:12px;'
            f'padding:10px 12px;height:100%;color:#0F1B33">'
            f'<div style="font-weight:800;color:{edge};font-size:{"0.85rem" if compact else "1rem"}">{letter} · {title}</div>'
            f'<ul style="margin:4px 0 0 0;padding-left:18px;font-size:{size};color:#0F1B33">{lis}</ul></div>')


def swot_grid(c: dict, compact: bool = False) -> str:
    sw = c["swot"]
    cells = "".join(_swot_box(k, sw[k], compact) for k in ("strengths", "weaknesses", "opportunities", "threats"))
    return f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">{cells}</div>'


def _service_matrix() -> pd.DataFrame:
    rows = {}
    for c in D.companies():
        counts = {s: 0 for s in SERVICE_LINES}
        for p in c["problems"]:
            txt = (p["service"] + " " + p["title"]).lower()
            for s, kws in KEYWORDS.items():
                if any(kw in txt for kw in kws):
                    counts[s] += 1
        avg_digital = sum(c["digital"].values()) / len(c["digital"])
        counts["Digital, data & AI"] = round(5 - avg_digital, 1)
        rows[c["short"]] = counts
    return pd.DataFrame(rows).T


def render():
    T.hero("Strategy Room", "What is working, what is not, a SWOT for each company, the five problems a consultant could solve, and the digital roadmap.",
           ["Salient features", "SWOT", "Top-5 problem statements", "Consulting opportunity map", "Digitisation roadmap"])
    cid = focus_picker("strat_pick")
    c = D.company(cid)

    T.section(f"{c['short']} · salient features")
    a, b = st.columns(2)
    a.markdown(f'<div class="card" style="border-top:4px solid {T.GOOD}"><h4>✅ What is working</h4>{bullets(c["working"], "list-good")}</div>', unsafe_allow_html=True)
    b.markdown(f'<div class="card" style="border-top:4px solid {T.BAD}"><h4>⛔ What is not working</h4>{bullets(c["not_working"], "list-bad")}</div>', unsafe_allow_html=True)

    T.section(f"{c['short']} · SWOT analysis", "internal strengths & weaknesses · external opportunities & threats")
    st.markdown(swot_grid(c), unsafe_allow_html=True)
    with st.expander("Compare SWOT across all six companies"):
        cols = st.columns(2)
        for i, cc in enumerate(D.companies()):
            cols[i % 2].markdown(
                f'<div style="background:#FFFFFF;border:1px solid #DCE6F5;border-top:4px solid {cc["color"]};border-radius:14px;'
                f'padding:12px;margin-bottom:12px"><div style="font-weight:800;color:#0A2A66;margin-bottom:8px">{cc["short"]}</div>'
                f'{swot_grid(cc, compact=True)}</div>', unsafe_allow_html=True)
        st.caption("Strengths and weaknesses are internal (financials, operations); opportunities and threats are external "
                   "(markets, regulators, policy). Every point traces to the KPI tables, filings or news on the other pages.")

    T.section("Top-5 problem statements", "the evidence, the likely fix, and what to check next")
    for i, p in enumerate(c["problems"], 1):
        with st.container():
            st.markdown(f"""<div class="problem"><div class="n">{i}</div><h5>{p['title']}</h5>
            <div class="row"><b>Evidence:</b> {p['evidence']}</div>
            <div class="row"><b>Answer / insight:</b> {p['answer']}</div>
            <div class="row"><b>Investigate further:</b> {p['investigate']}</div>
            <div class="row">{T.pill(p['service'])}</div></div>""", unsafe_allow_html=True)

    T.section("Consulting opportunity map", "where each company most needs help, by type of consulting work")
    m = _service_matrix()
    fig = go.Figure(go.Heatmap(z=m.values, x=m.columns, y=m.index, colorscale=[[0, "#F5F8FF"], [0.5, "#5B8FF5"], [1, "#0A2A66"]],
                               xgap=3, ygap=3, text=m.values, texttemplate="%{text}", showscale=False,
                               hovertemplate="%{y} · %{x}: %{z}<extra></extra>"))
    fig.update_layout(xaxis=dict(side="top", tickangle=-20), yaxis=dict(autorange="reversed"), hovermode="closest")
    st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    st.caption("Cells = number of top-5 problems mapped to that service line; Digital column = maturity gap (5 − average maturity score).")
    cols = st.columns(6)
    for col, cc in zip(cols, D.companies()):
        col.markdown(f'<div class="card" style="border-top:4px solid {cc["color"]}"><h4>{cc["short"]}</h4>'
                     + "".join(T.pill(x) for x in cc["consulting"]) + "</div>", unsafe_allow_html=True)

    T.section("Journey of digitisation", "estimated from public information (1 = early, 5 = leading); to be checked in interviews")
    a, b = st.columns([1, 1.2])
    with a:
        dims = list(c["digital"].keys())
        fig = go.Figure()
        for cc in D.companies():
            v = [cc["digital"][d] for d in dims]
            sel = cc["id"] == cid
            fig.add_trace(go.Scatterpolar(r=v + v[:1], theta=dims + dims[:1], name=cc["short"],
                                          line=dict(color=cc["color"], width=3.5 if sel else 1.2),
                                          opacity=1 if sel else 0.35, fill="toself" if sel else None))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5], tickvals=[1, 2, 3, 4, 5], gridcolor="#DCE6F5"),
                                     angularaxis=dict(tickfont=dict(size=11))), hovermode="closest", title=f"{c['short']} highlighted vs peers")
        st.plotly_chart(T.style_fig(fig, 430), use_container_width=True)
    with b:
        html = '<div class="card"><h4>🚀 Four-wave roadmap</h4>'
        for stage, desc, t in JOURNEY:
            html += (f'<div style="display:flex;gap:12px;margin:10px 0"><div style="min-width:118px;font-weight:800;color:#1D4ED8">{stage}'
                     f'<div class="muted">{t}</div></div><div style="font-size:.88rem">{desc}</div></div>')
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        weakest = sorted(c["digital"].items(), key=lambda x: x[1])[:3]
        st.markdown('<div class="card"><h4>Priority use-cases for ' + c["short"] + "</h4>"
                    + bullets([f"<b>{d}</b> (maturity {s}/5): {DIGITAL_USE_CASES[d]}" for d, s in weakest]) + "</div>", unsafe_allow_html=True)
    T.footer(D.meta())
