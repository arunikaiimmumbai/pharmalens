"""Company Deep-Dive: profile and every footprint lens."""
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import insights as I
from core import theme as T
from views.common import bullets, focus_picker, news_html


def _donut(d: dict, title: str, color: str):
    labels, vals = list(d.keys()), list(d.values())
    shades = ["#0A2A66", "#1D4ED8", "#3B82F6", "#06B6D4", "#93B8FF", "#C9DCFF", "#5B8FF5", "#173E9E"]
    fig = go.Figure(go.Pie(labels=labels, values=vals, hole=0.62, marker=dict(colors=shades[:len(vals)], line=dict(color="#fff", width=2)),
                           textinfo="percent", textfont=dict(color="#fff", size=12), sort=False,
                           hovertemplate="%{label}: %{value}%<extra></extra>"))
    fig.update_layout(title=title, showlegend=True, legend=dict(orientation="v", x=1.0, y=0.5), hovermode="closest",
                      annotations=[dict(text="mix", showarrow=False, font=dict(size=13, color=T.MUTED))])
    return T.style_fig(fig, 320)


def _treemap(d: dict, title: str):
    fig = go.Figure(go.Treemap(labels=list(d.keys()), parents=[""] * len(d), values=list(d.values()),
                               marker=dict(colors=list(d.values()), colorscale=[[0, "#C9DCFF"], [1, "#0A2A66"]], line=dict(color="#fff", width=3)),
                               texttemplate="<b>%{label}</b><br>%{value}%", textfont=dict(size=13),
                               hovertemplate="%{label}: %{value}%<extra></extra>"))
    fig.update_layout(title=title, margin=dict(t=48, l=4, r=4, b=4))
    return T.style_fig(fig, 320)


def render():
    cid = focus_picker("company_pick")
    c = D.company(cid)
    df = D.financial_frame(cid)
    k = D.kpi_table().loc[c["short"]]
    p, m, fp, rg = c["profile"], c["market"], c["footprint"], c["regulatory"]

    T.hero(c["name"], c["tagline"], [f"NSE: {c['ticker'].replace('.NS', '')}", f"HQ: {p['hq']}", f"Founded {p['founded']}",
                                     f"M-cap ₹{m['mcap_cr']:,.0f} Cr", f"P/E {m['pe']}x"])
    yoy = df["sales_growth"].iloc[-1]
    T.kpi_row([
        T.kpi_card("FY26 revenue", f"₹{df['sales'].iloc[-1]/1000:,.1f}k Cr", f"{yoy:+.1f}% YoY", "up" if yoy > 0 else "down"),
        T.kpi_card("EBITDA margin", f"{df['ebitda_margin'].iloc[-1]:.1f}%", f"{df['ebitda_margin'].iloc[-1]-df['ebitda_margin'].iloc[0]:+.1f} pts vs FY22", "up" if df['ebitda_margin'].iloc[-1] >= df['ebitda_margin'].iloc[0] else "down"),
        T.kpi_card("ROCE", f"{df['roce'].iloc[-1]:.0f}%", f"ROE {df['roe'].iloc[-1]:.1f}%", "flat"),
        T.kpi_card("5-yr revenue CAGR", f"{k['sales_cagr']:.1f}%", f"PAT CAGR {k['pat_cagr']:.1f}%", "up"),
        T.kpi_card("Cash cycle", f"{df['ccc'].iloc[-1]:.0f} d", f"Inventory {df['inventory_days'].iloc[-1]:.0f} d", "down" if df['ccc'].iloc[-1] > 200 else "flat"),
        T.kpi_card("Debt / equity", f"{df['de_ratio'].iloc[-1]:.2f}x", f"Borrowings ₹{df['borrowings'].iloc[-1]:,.0f} Cr", "flat"),
    ])

    tabs = st.tabs(["🏛️ Profile", "🌍 Market & geography", "🏭 Manufacturing & R&D", "💊 Therapy footprint", "📰 News (6M)", "💡 Insights"])

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
        a, b = st.columns([1, 1])
        with a:
            st.plotly_chart(_donut(fp["geography"], f"Revenue mix · {fp['geography_basis']}", c["color"]), use_container_width=True)
        with b:
            st.markdown(f"""<div class="card"><h4>Market footprint</h4><div style="font-size:.92rem">{fp['market']}</div></div>""", unsafe_allow_html=True)
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            q = c["quarterly"]
            fig = go.Figure(go.Bar(x=D.meta()["quarters"], y=q["sales"], marker_color=c["color"], marker_cornerradius=6,
                                   text=[f"₹{v:,}" for v in q["sales"]], textposition="outside", hovertemplate="%{x}: ₹%{y:,} Cr<extra></extra>"))
            fig.update_layout(title="Quarterly revenue (₹ Cr)", hovermode="closest")
            st.plotly_chart(T.style_fig(fig, 260), use_container_width=True)

    with tabs[2]:
        a, b = st.columns(2)
        a.markdown(f"""<div class="card"><h4>🏭 Manufacturing footprint</h4>
            <div style="font-size:2rem;font-weight:800;color:#0A2A66;font-family:JetBrains Mono">{fp.get('plants') or 'n/a'} <span style="font-size:.9rem;color:#7A8AA6">sites</span></div>
            <div style="font-size:.9rem">{fp['manufacturing']}</div></div>""", unsafe_allow_html=True)
        b.markdown(f"""<div class="card"><h4>🔬 R&D footprint</h4>
            <div style="font-size:2rem;font-weight:800;color:#0A2A66;font-family:JetBrains Mono">{fp['rnd_pct']:.1f}% <span style="font-size:.9rem;color:#7A8AA6">of sales</span></div>
            <div style="font-size:.9rem">{fp['rnd']}</div></div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div class="card"><h4>🧪 Regulatory snapshot ({rg['as_of']})</h4>
            {T.pill(f"ANDAs filed: {rg['anda_filed'] or 'not published'}")}{T.pill(f"Approved: {rg['anda_approved'] or 'not published'}", 'good')}
            {T.pill(f"Pending: {rg['anda_pending'] or 'not published'}", 'warn')}{T.pill(f"US products: {rg['us_products_commercialised'] or 'not published'}")}
            {T.pill(f"US DMFs: {rg['dmf_us'] or 'not published'}")}
            <div style="font-size:.9rem;margin-top:8px">{rg['status']}</div></div>""", unsafe_allow_html=True)

    with tabs[3]:
        a, b = st.columns([1.3, 1])
        a.plotly_chart(_treemap(fp["therapies"], "Therapy footprint (indicative weights)"), use_container_width=True)
        b.markdown(f"""<div class="card"><h4>💊 How to read this</h4><div style="font-size:.88rem">{fp['therapies_basis']}.</div>
            <div class="muted" style="margin-top:8px">These shares are my estimates from public information, not company figures.
            They would need checking against IQVIA sales data before use with a client.</div></div>""", unsafe_allow_html=True)

    with tabs[4]:
        for n in sorted(c["news"], key=lambda x: x["date"], reverse=True):
            st.markdown(news_html(n), unsafe_allow_html=True)

    with tabs[5]:
        ins = I.company_insights(cid)
        a, b, cc = st.columns(3)
        a.markdown(f'<div class="card"><h4>📈 Growth</h4>{bullets(ins["growth"], "list-good")}</div>', unsafe_allow_html=True)
        b.markdown(f'<div class="card"><h4>🎯 Opportunity</h4>{bullets(ins["opportunity"] or ["None flagged"])}</div>', unsafe_allow_html=True)
        cc.markdown(f'<div class="card"><h4>⚠️ Risk</h4>{bullets(ins["risk"] or ["None flagged"], "list-bad")}</div>', unsafe_allow_html=True)
        if c.get("data_notes"):
            st.info("Data notes: " + " ".join(c["data_notes"]))

    T.footer(D.meta())
