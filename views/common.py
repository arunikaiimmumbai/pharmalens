"""Shared view helpers."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T


def focus_picker(key: str, label: str = "Company") -> str | None:
    """Company picker that follows the sidebar focus. Returns None while 'Select' is chosen."""
    ids = [None] + list(D.names().keys())
    focus = st.session_state.get("focus")
    seen = f"_{key}_seen_focus"
    if st.session_state.get(seen, "__unset__") != focus:  # sidebar focus changed: follow it
        st.session_state[key] = focus
        st.session_state[seen] = focus
    cid = st.selectbox(label, ids, format_func=lambda x: "Select" if x is None else D.names()[x], key=key, placeholder="Select")
    if cid is None:
        company_chooser(key)
    return cid


def _choose(key: str, cid: str) -> None:
    st.session_state[key] = cid    # open this page on the company
    st.session_state.focus = cid   # sidebar follows, so every company page opens on it


def company_chooser(key: str) -> None:
    """Shown when no company is selected: six clickable company cards."""
    k = D.kpi_table()
    st.markdown(
        '<div class="card" style="text-align:center;padding:22px 18px;margin:6px 0 18px 0">'
        '<div style="font-size:1.25rem;font-weight:800;color:#0A2A66">Choose a company to open this page</div>'
        '<div class="muted" style="margin-top:6px">Click a card below, use the drop-down above, '
        'or set the Focus company in the sidebar so every page opens on it.</div></div>',
        unsafe_allow_html=True)
    cols = st.columns(3)
    for i, c in enumerate(D.companies()):
        r = k.loc[c["short"]]
        star = "*" if any("licensing" in n for n in c.get("data_notes", [])) else ""
        with cols[i % 3]:
            st.markdown(
                f'<div class="card" style="border-top:5px solid {c["color"]};margin-bottom:8px;min-height:200px">'
                f'<div style="font-size:1.1rem;font-weight:800;color:#0A2A66">{c["short"]}</div>'
                f'<div class="muted" style="font-size:.84rem;min-height:40px">{c["tagline"]}</div>'
                f'<div style="display:flex;gap:16px;margin-top:10px">'
                f'<div><div class="muted" style="font-size:.72rem">FY26 revenue</div>'
                f'<div style="font-weight:700;color:#0A2A66">₹{r["sales"]/1000:,.1f}k Cr</div></div>'
                f'<div><div class="muted" style="font-size:.72rem">EBITDA margin</div>'
                f'<div style="font-weight:700;color:#0A2A66">{r["ebitda_margin"]:.1f}%</div></div>'
                f'<div><div class="muted" style="font-size:.72rem">ROCE</div>'
                f'<div style="font-weight:700;color:#0A2A66">{r["roce"]:.0f}%{star}</div></div></div>'
                + (f'<div class="muted" style="font-size:.72rem;margin-top:6px">*includes one-off licensing income</div>' if star else "")
                + '</div>',
                unsafe_allow_html=True)
            st.button(f"Open {c['short']}", key=f"choose_{key}_{c['id']}", on_click=_choose, args=(key, c["id"]),
                      use_container_width=True)


def multi_line(panel: pd.DataFrame, title: str, ysuffix: str = "", height: int = 360, highlight: str | None = None) -> go.Figure:
    cmap = D.colors()
    fig = go.Figure()
    for col in panel.columns:
        dim = highlight and col != highlight
        fig.add_trace(go.Scatter(
            x=panel.index, y=panel[col], name=col, mode="lines+markers",
            line=dict(color=cmap[col], width=3.5 if col == highlight else 2.2),
            marker=dict(size=9 if col == highlight else 7, line=dict(color="#fff", width=2)),
            opacity=0.35 if dim else 1.0,
            hovertemplate=f"{col}: %{{y:,.1f}}{ysuffix}<extra></extra>",
        ))
        fig.add_annotation(x=panel.index[-1], y=panel[col].iloc[-1], text=f" {col}", showarrow=False,
                           xanchor="left", font=dict(size=11, color=T.INK2), opacity=0.35 if dim else 1)
    fig.update_layout(title=title, yaxis_ticksuffix=ysuffix, showlegend=True, margin=dict(r=80))
    return T.style_fig(fig, height)


def bar_peers(series: pd.Series, title: str, suffix: str = "", height: int = 330, sort_desc: bool = True) -> go.Figure:
    s = series.dropna().sort_values(ascending=not sort_desc)
    cmap = D.colors()
    fig = go.Figure(go.Bar(
        x=s.index, y=s.values, marker_color=[cmap[i] for i in s.index], marker_cornerradius=6,
        text=[f"{v:,.1f}{suffix}" for v in s.values], textposition="outside", textfont=dict(color=T.INK2),
        hovertemplate="%{x}: %{y:,.1f}" + suffix + "<extra></extra>"))
    med = series.median()
    fig.add_hline(y=med, line_dash="dot", line_color=T.MUTED,
                  annotation_text=f"Peer median {med:,.1f}{suffix}", annotation_position="top left",
                  annotation_font_color=T.MUTED)
    fig.update_layout(title=title, yaxis_ticksuffix=suffix, hovermode="closest", showlegend=False)
    return T.style_fig(fig, height)


def news_html(row: dict, company: str | None = None) -> str:
    s = row.get("sentiment", 0)
    kind = "good" if s > 0 else "bad" if s < 0 else "warn"
    lab = "Positive" if s > 0 else "Negative" if s < 0 else "Neutral"
    date = row["date"].strftime("%d %b %Y") if hasattr(row["date"], "strftime") else row["date"]
    tags = "".join(T.pill(m) for m in (row.get("metrics") or []))
    comp = T.pill(company) if company else ""
    link = f' · <a href="{row["url"]}" target="_blank">source ↗</a>' if row.get("url") else ""
    border = {"good": T.GOOD, "bad": T.BAD, "warn": T.WARN}[kind]
    return (f'<div class="newsrow" style="border-left-color:{border}"><div class="d">{date} · {row.get("category", "")}{link}</div>'
            f'<div class="t">{row["title"]}</div><div class="i">{row.get("impact", "")}</div>'
            f'<div>{comp}{T.pill(lab, kind)}{tags}</div></div>')


def bullets(items: list[str], cls: str = "") -> str:
    return f'<ul class="{cls}" style="margin:0;padding-left:18px">' + "".join(f"<li style='margin:4px 0'>{i}</li>" for i in items) + "</ul>"
