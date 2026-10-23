"""Company Overview: portfolio-level view of the six companies against the industry."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import industry as IND
from core import insights as I
from core import live as L
from core import theme as T
from views.common import IND_COLOR, IND_LABEL, bullets, compare_bar, comparison_block, kpi_help, note_box


def _live_strip():
    if not st.session_state.get("live_on", True):
        return None
    tickers = tuple(c["ticker"] for c in D.companies())
    px, err = L.fetch_prices(tickers, "6mo")
    return None if px.empty else px


def _tile(label, value, delta, direction, metric, note=""):
    tip = kpi_help(metric) if metric else ""
    return f'<div title="{tip}">' + T.kpi_card(label, value, delta, direction, note) + "</div>"


def render():
    k = D.kpi_table()
    T.hero(
        "Company Overview",
        "Six companies, five years, one lens. Live market and news signals, consolidated financials, regulatory pipelines "
        "and strategy, benchmarked against the Nifty Pharma industry average.",
        [f'<span class="pulse"></span> Live feeds {"on" if st.session_state.get("live_on", True) else "off"}',
         "FY22 → FY26 + Q1 FY27", "Consolidated · ₹ Cr", "Industry = 20 Nifty Pharma companies"],
    )
    cmp = compare_bar("command", help_text="Pick companies and/or Industry to open a side-by-side comparison below. "
                                           "Selected companies are also highlighted on the map; Industry adds a star.")
    cmp_view = {"industry": cmp["industry"], "companies": cmp["companies"] or (list(k.index) if cmp["industry"] else [])}
    comparison_block("overview", None, cmp_view,
                     ["sales_cagr", "ebitda_margin", "roce", "roic", "ccc", "cfo_pat", "net_debt_ebitda", "pe"])

    tot_sales = k["sales"].sum()
    tot_mcap = k["mcap_cr"].sum()
    w_growth = np.average(k["sales_cagr"], weights=k["sales"])
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    T.kpi_row([
        _tile("Combined FY26 revenue", f"₹{tot_sales/1000:,.1f}k Cr", f"growing {w_growth:.1f}% a year", "up", "sales_cagr"),
        _tile("Combined market cap", f"₹{tot_mcap/100000:,.2f} L Cr", f"P/E median {k['pe'].median():.1f}x", "flat", "pe"),
        _tile("Median EBITDA margin", f"{k['ebitda_margin'].median():.1f}%", f"range {k['ebitda_margin'].min():.0f}–{k['ebitda_margin'].max():.0f}%", "flat", "ebitda_margin"),
        _tile("Median ROCE", f"{k['roce'].median():.0f}%", f"{k['roce'].idxmax()} {k['roce'].max():.0f}% best", "up", "roce",
              "*incl. one-off licensing income" if k['roce'].idxmax() == "Glenmark" else ""),
        _tile("Median cash cycle", f"{k['ccc'].median():.0f} d", f"{k['ccc'].idxmax()} worst at {k['ccc'].max():.0f} d", "down", "ccc"),
    ])
    note_box("Headline tiles (six-company medians)", peer="cmd_tiles", metric="roce",
             facts=f"Median EBITDA margin {k['ebitda_margin'].median():.1f}%, median ROCE {k['roce'].median():.0f}%, median cash cycle {k['ccc'].median():.0f} days. "
                   f"Industry averages: EBITDA margin {IND.industry_value('ebitda_margin')['avg']:.1f}%, ROCE {IND.industry_value('roce')['avg']:.1f}%, "
                   f"cash cycle {IND.industry_value('ccc')['avg']:.0f} days.")

    m0 = IND.market()[0]
    m1 = IND.market()[1]
    st.markdown(
        f'<div class="card" style="margin-top:6px"><b>Indian pharma market</b> grew <b>{m0["value"]:.0f}%</b> in FY26 '
        f'({m0["detail"]}); chronic therapies grew ~{m1["value"]:.0f}% vs acute ~{m1["value2"]:.0f}% (Mar 2026). '
        f'<div class="muted" style="margin-top:4px">Industry = Indian pharma market growth (IQVIA). Source: '
        f'<a href="{m0["source"]["url"]}" target="_blank">{m0["source"]["title"]}</a></div></div>', unsafe_allow_html=True)

    # ── Market pulse ─────────────────────────────────────────────────────────
    px = _live_strip()
    T.section("Market pulse", "share price change over the last 6 months" if px is not None else "latest saved prices (live prices not available right now)")
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

    # ── Positioning map ──────────────────────────────────────────────────────
    T.section("Strategic positioning map", "growth vs margin · bigger bubble = bigger company")
    cmap = D.colors()
    hl = cmp["companies"]
    fig = go.Figure()
    for name, r in k.iterrows():
        dim = bool(hl) and name not in hl
        fig.add_trace(go.Scatter(
            x=[r["sales_cagr"]], y=[r["ebitda_margin"]], mode="markers+text", name=name, text=[name],
            textposition="top center", textfont=dict(color=T.INK, size=12),
            marker=dict(size=np.sqrt(r["mcap_cr"]) / 5.2, color=cmap[name], opacity=0.25 if dim else 0.85, line=dict(color="#fff", width=2)),
            customdata=[[r["roce"], r["pe"]]],
            hovertemplate=f"<b>{name}</b><br>Revenue CAGR %{{x:.1f}}%<br>EBITDA margin %{{y:.1f}}%<br>ROCE %{{customdata[0]:.0f}}%<br>P/E %{{customdata[1]:.1f}}x<extra></extra>",
        ))
    if cmp["industry"]:
        ix, iy = IND.industry_value("sales_cagr")["avg"], IND.industry_value("ebitda_margin")["avg"]
        fig.add_trace(go.Scatter(x=[ix], y=[iy], mode="markers+text", name=IND_LABEL, text=["Industry avg"], textposition="bottom center",
                                 marker=dict(size=18, symbol="star", color=IND_COLOR), textfont=dict(color=IND_COLOR, size=12),
                                 hovertemplate=f"<b>Industry average</b><br>Revenue CAGR {ix:.1f}%<br>EBITDA margin {iy:.1f}%<extra></extra>"))
    fig.add_vline(x=k["sales_cagr"].median(), line_dash="dot", line_color=T.MUTED)
    fig.add_hline(y=k["ebitda_margin"].median(), line_dash="dot", line_color=T.MUTED)
    for txt, x, y in [("Fast growth, high margin", 0.98, 0.98), ("High margin, slower growth", 0.02, 0.98), ("Fast growth, lower margin", 0.98, 0.04), ("Slower growth, lower margin", 0.02, 0.04)]:
        fig.add_annotation(text=txt, xref="paper", yref="paper", x=x, y=y, showarrow=False, font=dict(color=T.MUTED, size=11),
                           xanchor="right" if x > 0.5 else "left")
    fig.update_layout(xaxis_title="Revenue CAGR FY22–26 (%)", yaxis_title="EBITDA margin FY26 (%)", showlegend=False, hovermode="closest",
                      yaxis_range=[k["ebitda_margin"].min() - 4, k["ebitda_margin"].max() + 4],
                      xaxis_range=[k["sales_cagr"].min() - 2.5, k["sales_cagr"].max() + 2.5])
    st.plotly_chart(T.style_fig(fig, 440), use_container_width=True)
    st.caption("Dotted lines = middle of the six companies. Star = industry average (choose 'Industry' in Compare with).")
    note_box("Strategic positioning map", peer="cmd_map", metric="ebitda_margin",
             facts="; ".join(f"{n}: growth {r['sales_cagr']:.1f}%/yr, margin {r['ebitda_margin']:.1f}%" for n, r in k.iterrows()))

    # ── Key insights ─────────────────────────────────────────────────────────
    T.section("Key insights", "written automatically from the numbers")
    st.markdown(f'<div class="card">{bullets(I.cross_company_signals())}</div>', unsafe_allow_html=True)

    T.footer(D.meta())
