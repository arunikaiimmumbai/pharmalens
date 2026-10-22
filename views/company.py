"""Company Deep-Dive: profile, brands, footprint, cost drivers and news impact for one company, with comparisons."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import industry as IND
from core import insights as I
from core import notes as N
from core import theme as T
from views.common import (IND_COLOR, IND_LABEL, bullets, color, compare_bar, focus_picker, impact_html, kpi_help, news_html,
                          note_box, value)

COST_LINES = [("Material", "material_pct"), ("Employee", "employee_pct"), ("Other / SG&A", "other_cost_pct"),
              ("Manufacturing", "manufacturing_pct"), ("Depreciation", "dep_pct"), ("Interest", "interest_pct")]


def _donut(d: dict, title: str):
    labels, vals = list(d.keys()), list(d.values())
    shades = ["#0A2A66", "#1D4ED8", "#3B82F6", "#06B6D4", "#93B8FF", "#C9DCFF", "#5B8FF5", "#173E9E"]
    fig = go.Figure(go.Pie(labels=labels, values=vals, hole=0.62, marker=dict(colors=shades[:len(vals)], line=dict(color="#fff", width=2)),
                           textinfo="percent", textfont=dict(color="#fff", size=12), sort=False,
                           hovertemplate="%{label}: %{value}%<extra></extra>"))
    fig.update_layout(title=title, showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5), hovermode="closest")
    return T.style_fig(fig, 320)


def _cmp_line(metric: str, names: list[str], year: str = "FY26") -> str:
    parts = []
    for n in names:
        v = value(n, metric, year)
        if v is not None and not pd.isna(v):
            parts.append(f"{'Industry' if n == IND_LABEL else n} {D.fmt(metric, v)}")
    return " · ".join(parts)


def render():
    top = st.container()
    cid = focus_picker("company_pick")
    if cid is None:
        with top:
            T.hero("Company Deep-Dive", "Everything about one company on one page: profile, brands, geography, plants, R&D, cost drivers, news and insights.",
                   ["6 companies", "Brands", "Footprint", "Cost drivers", "News impact"])
        T.footer(D.meta())
        return
    c = D.company(cid)
    df = D.financial_frame(cid)
    k = D.kpi_table().loc[c["short"]]
    p, m, fp, rg = c["profile"], c["market"], c["footprint"], c["regulatory"]
    with top:
        T.hero(c["name"], c["tagline"], [f"NSE: {c['ticker'].replace('.NS', '')}", f"HQ: {p['hq']}", f"Founded {p['founded']}",
                                         f"M-cap ₹{m['mcap_cr']:,.0f} Cr", f"P/E {m['pe']}x"])
    cmp = compare_bar("company", exclude=c["short"])
    others = [x for x in cmp["companies"]] + ([IND_LABEL] if cmp["industry"] else [])

    yoy = df["sales_growth"].iloc[-1]
    tiles = [
        ("FY26 revenue", f"₹{df['sales'].iloc[-1]/1000:,.1f}k Cr", f"{yoy:+.1f}% YoY", "up" if yoy > 0 else "down", "sales_growth"),
        ("EBITDA margin", f"{df['ebitda_margin'].iloc[-1]:.1f}%", f"{df['ebitda_margin'].iloc[-1]-df['ebitda_margin'].iloc[0]:+.1f} pts vs FY22",
         "up" if df['ebitda_margin'].iloc[-1] >= df['ebitda_margin'].iloc[0] else "down", "ebitda_margin"),
        ("ROCE", f"{df['roce'].iloc[-1]:.0f}%", f"ROIC {df['roic'].iloc[-1]:.1f}%", "flat", "roce"),
        ("Revenue CAGR FY22 to FY26", f"{k['sales_cagr']:.1f}%", f"PAT CAGR {k['pat_cagr']:.1f}%", "up", "sales_cagr"),
        ("Cash cycle", f"{df['ccc'].iloc[-1]:.0f} d", f"Inventory {df['inventory_days'].iloc[-1]:.0f} d", "down" if df['ccc'].iloc[-1] > 200 else "flat", "ccc"),
        ("Net debt / EBITDA", f"{df['net_debt_ebitda'].iloc[-1]:.2f}x", f"Borrowings ₹{df['borrowings'].iloc[-1]:,.0f} Cr", "flat", "net_debt_ebitda"),
    ]
    cols = st.columns(len(tiles))
    for col, (lab, val, dlt, dirn, met) in zip(cols, tiles):
        col.markdown(f'<div title="{kpi_help(met)}">' + T.kpi_card(lab, val, dlt, dirn, _cmp_line(met, others)) + "</div>", unsafe_allow_html=True)
    if cmp["industry"]:
        st.caption("Industry = average of the 20 Nifty Pharma companies (source A, Screener.in). Hover a tile for its meaning and formula.")
    note_box(f"{c['short']}: headline numbers", company=cid, theme="growth", metric="sales_cagr",
             facts=f"FY26 revenue ₹{df['sales'].iloc[-1]:,.0f} Cr ({yoy:+.1f}% YoY), EBITDA margin {df['ebitda_margin'].iloc[-1]:.1f}%, ROCE {df['roce'].iloc[-1]:.0f}%, "
                   f"revenue CAGR {k['sales_cagr']:.1f}%, cash cycle {df['ccc'].iloc[-1]:.0f} days. Industry revenue CAGR {IND.industry_value('sales_cagr')['avg']:.1f}%.")

    tabs = st.tabs(["🏛️ Profile", "💊 Brands & therapies", "🌍 Market & geography", "🏭 Manufacturing & R&D", "💰 Cost drivers",
                    "📰 News impact", "💡 Insights"])

    with tabs[0]:
        a, b = st.columns([1.4, 1])
        with a:
            st.markdown(f"""<div class="card"><h4>Company overview</h4><p style="font-size:.95rem">{p['description']}</p>
            <p><b>Business model:</b> {p['business_model']}</p><p><b>Leadership:</b> {p['leadership']}</p>
            <p class="muted">{p['employees_note']}</p></div>""", unsafe_allow_html=True)
        with b:
            sh = m["shareholding"]
            fig = go.Figure(go.Bar(x=list(sh.values()), y=list(sh.keys()), orientation="h", marker_color=["#0A2A66", "#1D4ED8", "#3B82F6", "#93B8FF"],
                                   marker_cornerradius=6, text=[f"{v:.1f}%" for v in sh.values()], textposition="outside",
                                   hovertemplate="%{y}: %{x:.2f}%<extra></extra>"))
            fig.update_layout(title="Shareholding (latest quarter)", xaxis_ticksuffix="%", hovermode="closest", yaxis=dict(autorange="reversed"),
                              xaxis_range=[0, max(sh.values()) * 1.18])
            st.plotly_chart(T.style_fig(fig, 260), use_container_width=True)
            st.markdown(f"""<div class="card"><h4>Guidance</h4><div style="font-size:.88rem">{c['guidance']}</div>
            <div class="muted" style="margin-top:6px">Consensus: {c['consensus']['broker']} · {c['consensus']['rating']}
            {('· TP ₹' + format(c['consensus']['target'], ',')) if c['consensus'].get('target') else ''}</div></div>""", unsafe_allow_html=True)

    with tabs[1]:
        br = c["brands"]
        st.markdown(f'<div class="card"><b>In one line:</b> {br["summary"]}</div>', unsafe_allow_html=True)
        a, b = st.columns([1, 1.15])
        with a:
            th = pd.DataFrame(br["therapies"])
            rank_basis = "rank" in br["therapy_basis"].lower() and "share" not in br["therapy_basis"].lower()
            th = th.sort_values("value", ascending=rank_basis)
            th["bar"] = (th["value"].max() + 1 - th["value"]) if rank_basis else th["value"]
            fig = go.Figure(go.Bar(y=th["therapy"], x=th["bar"], orientation="h", marker_color=c["color"], marker_cornerradius=6,
                                   text=th["detail"], textposition="outside", hovertemplate="%{y}: %{text}<extra></extra>"))
            fig.update_layout(title=("Therapy rank in India (longer bar = better rank)" if rank_basis else "Therapy areas, biggest first"),
                              yaxis=dict(autorange="reversed"), hovermode="closest",
                              xaxis=dict(range=[0, th["bar"].max() * 1.6], showticklabels=False))
            st.plotly_chart(T.style_fig(fig, 60 + 46 * len(th)), use_container_width=True)
            st.caption(f"Basis: {br['therapy_basis']}.")
        with b:
            bt = pd.DataFrame(br["brands"])
            bt.insert(0, "#", range(1, len(bt) + 1))
            st.markdown("**Top brands, strongest first**")
            st.dataframe(bt.rename(columns={"name": "Brand", "therapy": "Therapy", "evidence": "Evidence", "basis": "Basis"}),
                         hide_index=True, use_container_width=True, height=min(420, 38 + 35 * len(bt)))
            st.caption(f"Basis: {br['brand_basis']}. Exact brand market shares are IQVIA paid data, so this ranking is indicative and built from public evidence.")
        note_box(f"{c['short']}: brands and therapies", company=cid, theme="brands",
                 facts=br["summary"] + " Therapies: " + "; ".join(f"{t['therapy']} {t['detail']}" for t in br["therapies"]))

    with tabs[2]:
        a, b = st.columns([1, 1])
        with a:
            st.plotly_chart(_donut(fp["geography"], f"Revenue mix · {fp['geography_basis']}"), use_container_width=True)
            note_box(f"{c['short']}: revenue by geography", company=cid, theme="geo",
                     facts="; ".join(f"{g} {v}%" for g, v in fp["geography"].items()))
        with b:
            st.markdown(f"""<div class="card"><h4>Market footprint</h4><div style="font-size:.92rem">{fp['market']}</div></div>""", unsafe_allow_html=True)
            q = c["quarterly"]
            fig = go.Figure(go.Bar(x=D.meta()["quarters"], y=q["sales"], marker_color=c["color"], marker_cornerradius=6,
                                   text=[f"₹{v:,}" for v in q["sales"]], textposition="outside", hovertemplate="%{x}: ₹%{y:,} Cr<extra></extra>"))
            fig.update_layout(title="Quarterly revenue (₹ Cr) · operating margin: " + " → ".join(f"{v}%" for v in q["opm"]), hovermode="closest")
            st.plotly_chart(T.style_fig(fig, 280), use_container_width=True)
            note_box(f"{c['short']}: quarterly revenue", company=cid, theme="quarter",
                     facts="; ".join(f"{qq}: ₹{s:,} Cr ({o}%)" for qq, s, o in zip(D.meta()["quarters"], q["sales"], q["opm"])))

    with tabs[3]:
        a, b = st.columns(2)
        a.markdown(f"""<div class="card"><h4>🏭 Manufacturing footprint</h4>
            <div style="font-size:2rem;font-weight:800;color:#0A2A66;font-family:JetBrains Mono">{fp.get('plants') or 'n/a'} <span style="font-size:.9rem;color:#7A8AA6">sites</span></div>
            <div style="font-size:.9rem">{fp['manufacturing']}</div></div>""", unsafe_allow_html=True)
        b.markdown(f"""<div class="card"><h4>🔬 R&D footprint</h4>
            <div style="font-size:2rem;font-weight:800;color:#0A2A66;font-family:JetBrains Mono">{fp['rnd_pct']:.1f}% <span style="font-size:.9rem;color:#7A8AA6">of sales</span></div>
            <div style="font-size:.9rem">{fp['rnd']}</div></div>""", unsafe_allow_html=True)
        if cmp["companies"]:
            rows = [c["short"]] + cmp["companies"]
            vals = [D.company(next(x["id"] for x in D.companies() if x["short"] == r))["footprint"]["rnd_pct"] for r in rows]
            fig = go.Figure(go.Bar(x=rows, y=vals, marker_color=[color(r) for r in rows], text=[f"{v:.1f}%" for v in vals], textposition="outside"))
            fig.update_layout(title="R&D as % of sales", yaxis_ticksuffix="%", hovermode="closest")
            st.plotly_chart(T.style_fig(fig, 260), use_container_width=True)
            st.caption("No industry average for R&D: Nifty Pharma companies don't report it consistently.")
        st.markdown(f"""<div class="card" style="margin-top:10px"><h4>🧪 Regulatory snapshot ({rg['as_of']})</h4>
            {T.pill(f"ANDAs filed: {rg['anda_filed'] or 'not published'}")}{T.pill(f"Approved: {rg['anda_approved'] or 'not published'}", 'good')}
            {T.pill(f"Pending: {rg['anda_pending'] or 'not published'}", 'warn')}{T.pill(f"US products: {rg['us_products_commercialised'] or 'not published'}")}
            {T.pill(f"US DMFs: {rg['dmf_us'] or 'not published'}")}
            <div style="font-size:.9rem;margin-top:8px">{rg['status']}</div></div>""", unsafe_allow_html=True)
        note_box(f"{c['short']}: plants, R&D and regulatory", company=cid, theme="rnd",
                 facts=f"{fp.get('plants')} sites; R&D {fp['rnd_pct']:.1f}% of sales; {rg['status']}")

    with tabs[4]:
        T.section("Cost drivers, biggest first", "FY26, each cost as % of sales")
        r = df.iloc[-1]
        rows = []
        for lab, key in COST_LINES:
            v = r[key] if key in df.columns else None
            iv = IND.industry_value(key)["avg"]
            rows.append({"Cost line": lab, "% of sales": v, "₹ Cr": v / 100 * r["sales"] if v is not None else None,
                         "Industry %": iv, "Gap vs industry (pts)": (v - iv) if (v is not None and iv is not None) else None, "_k": key})
        ct = pd.DataFrame(rows).sort_values("% of sales", ascending=False).reset_index(drop=True)
        ct.insert(0, "Rank", range(1, len(ct) + 1))
        names = [c["short"]] + cmp["companies"] + ([IND_LABEL] if cmp["industry"] else [])
        fig = go.Figure()
        for n in names:
            vals = [value(n, key) for key in ct["_k"]]
            fig.add_trace(go.Bar(y=ct["Cost line"], x=vals, name=n if n != IND_LABEL else "Industry avg", orientation="h",
                                 marker_color=color(n), marker_pattern_shape="/" if n == IND_LABEL else "",
                                 text=[f"{v:.1f}%" if v is not None and not pd.isna(v) else "" for v in vals], textposition="outside",
                                 hovertemplate=f"{n}: %{{x:.1f}}% of sales<extra></extra>"))
        fig.update_layout(barmode="group", yaxis=dict(autorange="reversed"), xaxis_ticksuffix="%", hovermode="closest",
                          title=f"{c['short']} cost lines as % of sales" + (" vs comparison" if len(names) > 1 else ""))
        st.plotly_chart(T.style_fig(fig, 120 + 50 * len(ct) + 18 * len(names)), use_container_width=True)
        st.dataframe(ct.drop(columns="_k").style.format({"% of sales": "{:.1f}%", "₹ Cr": "{:,.0f}", "Industry %": "{:.1f}%",
                                                          "Gap vs industry (pts)": "{:+.1f}"}, na_rep="–"),
                     hide_index=True, use_container_width=True)
        st.caption(IND.note("employee_pct") + " Positive gap = this company spends more of each ₹100 of sales on that cost than the industry.")
        note_box(f"{c['short']}: cost drivers ranked", company=cid, theme="cost", metric="employee_pct",
                 facts="; ".join(f"{x['Cost line']} {x['% of sales']:.1f}% of sales" + (f" (industry {x['Industry %']:.1f}%)" if x['Industry %'] else "")
                                 for x in ct.to_dict("records") if x["% of sales"] is not None))

    with tabs[5]:
        st.caption("Each news item: what it does to the P&L, balance sheet and cash flow, what management is already doing, and what more it could do.")
        for n_ in sorted(c["news"], key=lambda x: x["date"], reverse=True):
            st.markdown(news_html(n_) + impact_html(n_.get("statement_impact")), unsafe_allow_html=True)

    with tabs[6]:
        ins = I.company_insights(cid)
        a, b, cc = st.columns(3)
        a.markdown(f'<div class="card"><h4>📈 Growth</h4>{bullets(ins["growth"], "list-good")}</div>', unsafe_allow_html=True)
        b.markdown(f'<div class="card"><h4>🎯 Opportunity</h4>{bullets(ins["opportunity"] or ["None flagged"])}</div>', unsafe_allow_html=True)
        cc.markdown(f'<div class="card"><h4>⚠️ Risk</h4>{bullets(ins["risk"] or ["None flagged"], "list-bad")}</div>', unsafe_allow_html=True)
        if c.get("data_notes"):
            st.info("Data notes: " + " ".join(c["data_notes"]))
        st.markdown(f'<div class="note">Sources: {N.sources_md([N.screener(cid)])}</div>', unsafe_allow_html=True)

    T.footer(D.meta())
