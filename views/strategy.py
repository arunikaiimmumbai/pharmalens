"""Strategy Room: salient features, top-5 problem statements, consulting opportunities, digital journey."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T
from core import notes as N
from views.common import bullets, compare_bar, focus_picker, note_box, register

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
    if cid is None:
        T.footer(D.meta())
        return
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
        st.caption("Strengths and weaknesses are about the company itself (its numbers and operations). Opportunities and threats "
                   "come from outside (markets, regulators, government policy). Every point is backed by a number or news item on the other pages.")

    T.section("Top-5 problem statements", "the evidence, the likely fix, and what to check next")
    for i, p in enumerate(c["problems"], 1):
        with st.container():
            st.markdown(f"""<div class="problem"><div class="n">{i}</div><h5>{p['title']}</h5>
            <div class="row"><b>Evidence:</b> {p['evidence']}</div>
            <div class="row"><b>Answer / insight:</b> {p['answer']}</div>
            <div class="row"><b>Investigate further:</b> {p['investigate']}</div>
            <div class="row">{T.pill(p['service'])}</div></div>""", unsafe_allow_html=True)

    register(f"{c['short']}: top-5 problem statements", company=cid, kind="text", theme="returns",
             facts=" | ".join(f"{p['title']}: {p['evidence']}" for p in c["problems"]))

    T.section("Consulting opportunity map", "where each company most needs help, by type of consulting work")
    m = _service_matrix()
    fig = go.Figure(go.Heatmap(z=m.values, x=m.columns, y=m.index, colorscale=[[0, "#F5F8FF"], [0.5, "#5B8FF5"], [1, "#0A2A66"]],
                               xgap=3, ygap=3, text=m.values, texttemplate="%{text}", showscale=False,
                               hovertemplate="%{y} · %{x}: %{z}<extra></extra>"))
    fig.update_layout(xaxis=dict(side="top", tickangle=-20), yaxis=dict(autorange="reversed"), hovermode="closest")
    st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    note_box("Consulting opportunity map", peer="st_map",
             facts="; ".join(f"{r_}: " + ", ".join(f"{col} {v:g}" for col, v in m.loc[r_].items() if v) for r_ in m.index))

    T.section(f"{c['short']} · digitisation roadmap", "what it is doing today, where it is weak, and where a consultant comes in")
    cmp = compare_bar("strategy", exclude=c["short"], help_text="Pick companies to compare digital maturity scores side by side.")
    STATUS = {"Doing well": ("#E8F7EF", "#0F9D58"), "In progress": ("#EAF2FF", "#1D4ED8"),
              "Weak": ("#FDECEC", "#C62828"), "No public evidence": ("#FFF4E5", "#B45309")}
    rows_html = ""
    for r in c["digital_roadmap"]:
        bg, fg = STATUS[r["status"]]
        dots = "".join(f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:3px;background:{"#1D4ED8" if i < r["score"] else "#DCE6F5"}"></span>' for i in range(5))
        src = N.sources_md(r["sources"])
        flag = r["status"] in ("Weak", "No public evidence")
        rows_html += (f'<tr style="background:{"#FFFBF7" if flag else "#fff"}">'
                      f'<td style="font-weight:700;color:#0A2A66">{r["area"]}</td><td style="white-space:nowrap">{dots}<div class="muted" style="font-size:.72rem">{r["score"]}/5</div></td>'
                      f'<td><span class="status" style="background:{bg};color:{fg}">{r["status"]}</span></td>'
                      f'<td>{r["doing"]}' + (f'<div class="muted" style="font-size:.72rem;margin-top:3px">Source: {src}</div>' if src else "") + '</td>'
                      f'<td>{r["gap"]}</td><td style="color:#0A2A66;font-weight:600">{"🎯 " if flag else ""}{r["consultant"]}</td><td>{r["wave"]}</td></tr>')
    st.markdown(f"""<div class="card" style="padding:6px 8px"><table style="width:100%;font-size:.84rem;border-collapse:collapse">
        <tr style="text-align:left;color:#42526E;font-size:.74rem;text-transform:uppercase"><th>Area</th><th>Maturity</th><th>Status</th>
        <th>What it is doing today</th><th>Gap</th><th>Consultant entry point</th><th>When</th></tr>{rows_html}</table></div>""", unsafe_allow_html=True)
    st.caption("Status: Doing well / In progress = public evidence of a programme. Weak or No public evidence (highlighted, 🎯) = "
               "nothing disclosed, which is where a consultant comes in. Scores are outside-in estimates; check them in management interviews.")
    waves = {"0–6 mo": [], "6–18 mo": [], "18–30 mo": []}
    for r in c["digital_roadmap"]:
        waves.setdefault(r["wave"], []).append(f'<b>{r["area"]}</b>: {r["consultant"]}')
    wcols = st.columns(3)
    for col, (w, items) in zip(wcols, waves.items()):
        col.markdown(f'<div class="card"><h4>{w}</h4>{bullets(items) if items else "<span class=muted>Nothing scheduled</span>"}</div>', unsafe_allow_html=True)
    if cmp["companies"]:
        tbl = pd.DataFrame({cc["short"]: cc["digital"] for cc in D.companies() if cc["short"] in [c["short"]] + cmp["companies"]})
        st.markdown("**Digital maturity, side by side (1 = early, 5 = leading)**")
        st.dataframe(tbl.style.background_gradient(cmap="Blues", vmin=1, vmax=5), use_container_width=True)
    register(f"{c['short']}: digitisation roadmap", company=cid, kind="text", theme="rnd",
             facts=" | ".join(f"{r['area']} {r['score']}/5 ({r['status']}): doing {r['doing']}; gap {r['gap']}; consultant {r['consultant']}" for r in c["digital_roadmap"]),
             note={"text": "Outside-in digital maturity from annual reports, investor presentations and news.",
                   "sources": [s_ for r in c["digital_roadmap"] for s_ in r["sources"]]})
    T.footer(D.meta())
