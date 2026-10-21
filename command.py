"""Command Center — portfolio-level view of the six companies."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import insights as I
from core import live as L
from core import theme as T
from views.common import bullets, news_html


def _live_strip():
    if not st.session_state.get("live_on", True):
        return None
    tickers = tuple(c["ticker"] for c in D.companies())
    px, err = L.fetch_prices(tickers, "6mo")
    return None if px.empty else px


def render():
    meta = D.meta()
    k = D.kpi_table()
    scores = I.pillar_scores()
    T.hero(
        "Indian Mid-cap Pharma · Command Center",
        "Six companies, five years, one lens. Live market & news signals correlated with consolidated financials, "
        "regulatory pipelines and strategy — built for a partner-level conversation.",
        [f'<span class="pulse"></span> Live feeds {"on" if st.session_state.get("live_on", True) else "off"}',
         "FY22 → FY26 + Q1 FY27", "Consolidated · ₹ Cr", f"As of {meta['as_of']}"],
    )

    tot_sales = k["sales"].sum()
    tot_mcap = k["mcap_cr"].sum()
    T.kpi_row([
        T.kpi_card("Combined FY26 revenue", f"₹{tot_sales/1000:,.1f}k Cr", f"{np.average(k['sales_cagr'], weights=k['sales']):.1f}% wtd CAGR", "up"),
        T.kpi_card("Combined market cap", f"₹{tot_mcap/100000:,.2f} L Cr", f"P/E median {k['pe'].median():.1f}x", "flat"),
        T.kpi_card("Median EBITDA margin", f"{k['ebitda_margin'].median():.1f}%", f"range {k['ebitda_margin'].min():.0f}–{k['ebitda_margin'].max():.0f}%", "flat"),
        T.kpi_card("Median ROCE", f"{k['roce'].median():.0f}%", f"{k['roce'].idxmax()} {k['roce'].max():.0f}% best", "up", ("*incl. one-off licensing income" if k['roce'].idxmax() == "Glenmark" else "")),
        T.kpi_card("Median cash cycle", f"{k['ccc'].median():.0f} d", f"{k['ccc'].idxmax()} worst at {k['ccc'].max():.0f} d", "down"),
    ])

    # ── Live ticker / momentum ──────────────────────────────────────────────
    px = _live_strip()
    T.section("Market pulse", "6-month total return vs Nifty Pharma" if px is not None else "curated snapshot (live feed unavailable)")
    cols = st.columns(6)
    for col, c in zip(cols, D.companies()):
        m = c["market"]
        delta, direction = "", "flat"
        if px is not None and c["ticker"] in px:
            s = px[c["ticker"]].dropna()
            if len(s) > 2:
                r = (s.iloc[-1] / s.iloc[0] - 1) * 100
                delta, direction = f"{r:+.1f}% 6M", "up" if r >= 0 else "down"
                price = s.iloc[-1]
            else:
                price = m["price"]
        else:
            price = m["price"]
            pos = (m["price"] - m["low_52w"]) / (m["high_52w"] - m["low_52w"]) * 100
            delta = f"{pos:.0f}% of 52W range"
        col.markdown(T.kpi_card(c["short"], f"₹{price:,.0f}", delta, direction, f"P/E {m['pe']}x · ₹{m['mcap_cr']/1000:,.1f}k Cr"),
                     unsafe_allow_html=True)

    # ── Positioning map + scorecard ─────────────────────────────────────────
    left, right = st.columns([1.25, 1])
    with left:
        T.section("Strategic positioning map", "growth × profitability · bubble = market cap")
        cmap = D.colors()
        fig = go.Figure()
        for name, r in k.iterrows():
            fig.add_trace(go.Scatter(
                x=[r["sales_cagr"]], y=[r["ebitda_margin"]], mode="markers+text", name=name, text=[name],
                textposition="top center", textfont=dict(color=T.INK, size=12),
                marker=dict(size=np.sqrt(r["mcap_cr"]) / 5.2, color=cmap[name], opacity=0.85, line=dict(color="#fff", width=2)),
                customdata=[[r["roce"], r["pe"], r["mcap_cr"]]],
                hovertemplate=f"<b>{name}</b><br>Revenue CAGR %{{x:.1f}}%<br>EBITDA margin %{{y:.1f}}%<br>ROCE %{{customdata[0]:.0f}}%<br>P/E %{{customdata[1]:.1f}}x<extra></extra>",
            ))
        fig.add_vline(x=k["sales_cagr"].median(), line_dash="dot", line_color=T.MUTED)
        fig.add_hline(y=k["ebitda_margin"].median(), line_dash="dot", line_color=T.MUTED)
        for txt, x, y in [("Compounders", 0.98, 0.98), ("Margin-rich, slower", 0.02, 0.98), ("Scale-up, margin-light", 0.98, 0.04), ("Fix-the-base", 0.02, 0.04)]:
            fig.add_annotation(text=txt, xref="paper", yref="paper", x=x, y=y, showarrow=False, font=dict(color=T.MUTED, size=11),
                               xanchor="right" if x > 0.5 else "left")
        fig.update_layout(xaxis_title="Revenue CAGR FY22–26 (%)", yaxis_title="EBITDA margin FY26 (%)", showlegend=False, hovermode="closest",
                          yaxis_range=[k["ebitda_margin"].min() - 4, k["ebitda_margin"].max() + 4],
                          xaxis_range=[k["sales_cagr"].min() - 2.5, k["sales_cagr"].max() + 2.5])
        st.plotly_chart(T.style_fig(fig, 430), use_container_width=True)
    with right:
        T.section("PharmaLens scorecard", "0–100 vs peers; weighted")
        sc = scores.sort_values("PharmaLens score", ascending=False)
        z = sc.drop(columns="PharmaLens score").rename(columns={"Cash & working capital": "Cash &<br>WC", "Balance sheet": "Balance<br>sheet", "Profitability": "Profit-<br>ability"})
        fig = go.Figure(go.Heatmap(
            z=z.values, x=z.columns, y=z.index, colorscale=[[0, "#EFF5FF"], [0.5, "#5B8FF5"], [1, "#0A2A66"]],
            text=z.values.astype(int), texttemplate="%{text}", textfont=dict(size=13), showscale=False, xgap=3, ygap=3,
            hovertemplate="%{y} · %{x}: %{z:.0f}/100<extra></extra>"))
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(side="top", tickangle=0, tickfont=dict(size=11)), margin=dict(t=70), hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 300), use_container_width=True)
        st.markdown(" ".join(T.pill(f"{n}: {int(v)}") for n, v in sc["PharmaLens score"].items()), unsafe_allow_html=True)
        st.caption("Pillars: Growth 25% · Profitability 25% · Returns 20% · Cash & WC 15% · Balance sheet 15%.")

    # ── Key insights ────────────────────────────────────────────────────
    T.section("Key insights", "auto-generated from the numbers")
    st.markdown(f'<div class="card">{bullets(I.cross_company_signals())}</div>', unsafe_allow_html=True)

    # ── Growth / opportunity / risk grid ────────────────────────────────────
    T.section("Growth · Opportunity · Risk radar", "headline signal per company")
    cols = st.columns(3)
    for i, c in enumerate(D.companies()):
        g = c["working"][0]
        o = c["problems"][0]["title"] + " — " + c["problems"][0]["evidence"]
        r = c["not_working"][0]
        cols[i % 3].markdown(
            f"""<div class="card" style="margin-bottom:12px;border-top:4px solid {c['color']}">
            <h4>{c['short']}</h4><div class="muted">{c['tagline']}</div>
            <div style="margin-top:8px;font-size:.86rem">{T.pill('Growth','good')} {g}</div>
            <div style="margin-top:6px;font-size:.86rem">{T.pill('Opportunity')} {o}</div>
            <div style="margin-top:6px;font-size:.86rem">{T.pill('Risk','bad')} {r}</div></div>""",
            unsafe_allow_html=True)

    # ── News pulse ──────────────────────────────────────────────────────────
    T.section("News pulse", "latest curated events · last 6 months")
    nd = D.all_news().head(8)
    c1, c2 = st.columns(2)
    for i, (_, row) in enumerate(nd.iterrows()):
        (c1 if i % 2 == 0 else c2).markdown(news_html(row.to_dict(), row["Company"]), unsafe_allow_html=True)

    T.footer(meta)
