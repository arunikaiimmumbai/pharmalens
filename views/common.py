"""Shared view helpers: company picker, compare bar, analyst notes, page-item registry for the analyst panel, charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import glossary as G
from core import industry as IND
from core import notes as N
from core import theme as T

IND_LABEL = "Industry (Nifty Pharma avg)"
IND_COLOR = "#0F1B33"
ALL_LABEL = "All six companies"


# ── Company picker ───────────────────────────────────────────────────────────
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
        '<div style="font-size:1.25rem;font-weight:800;color:#0A2A66">👈 Select a company from the Focus company menu on the left</div>'
        '<div class="muted" style="margin-top:6px">This page shows one company at a time. '
        'You can also click one of the cards below.</div></div>',
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
                + ('<div class="muted" style="font-size:.72rem;margin-top:6px">*includes one-off licensing income</div>' if star else "")
                + '</div>',
                unsafe_allow_html=True)
            st.button(f"Open {c['short']}", key=f"choose_{key}_{c['id']}", on_click=_choose, args=(key, c["id"]),
                      use_container_width=True)


# ── Compare bar ──────────────────────────────────────────────────────────────
def _store_compare(key: str) -> None:
    st.session_state["_compare_store"] = list(st.session_state.get(key) or [])


def compare_bar(key: str, exclude: str | None = None, help_text: str | None = None) -> dict:
    """'Compare with' selector shared across pages. Returns {'industry': bool, 'companies': [short names]}.
    'Industry' = average of the 20 Nifty Pharma companies; 'All six companies' selects every company."""
    shorts = [s for s in D.names().values() if s != exclude]
    opts = [IND_LABEL, ALL_LABEL] + shorts
    stored = [o for o in st.session_state.get("_compare_store", []) if o in opts]
    wkey = f"cmp_{key}"
    if wkey not in st.session_state:
        st.session_state[wkey] = stored
    sel = st.multiselect("Compare with", opts, key=wkey, placeholder="Please select", on_change=_store_compare, args=(wkey,),
                         help=help_text or "Industry = average of the 20 Nifty Pharma companies (Screener.in). "
                                           "Pick one or more companies, 'All six companies', or leave empty for none.")
    comps = shorts if ALL_LABEL in sel else [s for s in sel if s in shorts]
    return {"industry": IND_LABEL in sel, "companies": comps}


def entities(focus_short: str | None, cmp: dict) -> list[str]:
    """Ordered list of names to plot: focus company, compared companies, then industry."""
    out = [focus_short] if focus_short else []
    out += [c for c in cmp["companies"] if c != focus_short]
    if cmp["industry"]:
        out.append(IND_LABEL)
    return out


def series(name: str, metric: str) -> pd.Series:
    if name == IND_LABEL:
        return IND.industry_series(metric)["Average"]
    p = D.panel(metric)
    return p[name] if name in p.columns else pd.Series(dtype=float)


def value(name: str, metric: str, year: str = "FY26"):
    if name == IND_LABEL:
        return IND.industry_value(metric, year)["avg"]
    k = D.kpi_table(year)
    if name in k.index and metric in k.columns:
        return k.loc[name, metric]
    cid = next((c["id"] for c in D.companies() if c["short"] == name), None)
    if cid:
        df = D.financial_frame(cid)
        if metric in df.columns:
            return df.loc[year, metric]
    return None


def color(name: str) -> str:
    return IND_COLOR if name == IND_LABEL else D.colors().get(name, T.SKY)


def industry_caption(metric: str, year: str = "FY26") -> None:
    st.caption(IND.note(metric, year))


# ── Page-item registry (what the analyst panel can be asked about) ──────────
def register(title: str, *, company: str | None = None, metric: str | None = None, theme: str | None = None,
             note: dict | None = None, facts: str = "", kind: str = "chart") -> str:
    items = st.session_state.setdefault("_items", [])
    if not any(i["title"] == title for i in items):
        items.append({"title": title, "company": company, "metric": metric, "theme": theme, "note": note or {},
                      "facts": facts, "kind": kind, "page": st.session_state.get("_page", "")})
    return title


def _open_panel(title: str) -> None:
    st.session_state["panel_open"] = True
    st.session_state["panel_item"] = title


def ask_button(title: str) -> None:
    st.button("💬 Ask about this", key=f"ask_{title}", on_click=_open_panel, args=(title,), type="tertiary")


def note_box(title: str, *, company: str | None = None, theme: str | None = None, peer: str | None = None,
             metric: str | None = None, facts: str = "", extra: str = "") -> None:
    """Grey 'Analyst note' under a chart: why it looks this way, sources, and an 'Ask about this' link."""
    note = (N.company(company, theme) if company and theme else None) or (N.peer(peer) if peer else None) or {}
    register(title, company=company, metric=metric, theme=theme, note=note, facts=facts)
    text = note.get("text", "")
    if extra:
        text = f"{text} {extra}".strip()
    src = N.sources_md(note.get("sources", []))
    if text:
        st.markdown(
            f'<div class="note"><b>Analyst note</b> · {text}'
            + (f'<div class="src">Sources: {src}</div>' if src else "") + "</div>", unsafe_allow_html=True)
    st.button("💬 Ask about this", key=f"ask_{title}", on_click=_open_panel, args=(title,), type="tertiary")


def kpi_help(metric: str) -> str:
    return G.tooltip(metric)


# ── Charts ───────────────────────────────────────────────────────────────────
def multi_line(panel: pd.DataFrame, title: str, ysuffix: str = "", height: int = 360, highlight: list[str] | str | None = None,
               industry: bool = False, metric: str | None = None) -> go.Figure:
    """One line per company; selected companies bold, others faded; optional dashed industry line."""
    cmap = D.colors()
    hl = [highlight] if isinstance(highlight, str) else (highlight or [])
    fig = go.Figure()
    for col in panel.columns:
        dim = bool(hl) and col not in hl
        fig.add_trace(go.Scatter(
            x=panel.index, y=panel[col], name=col, mode="lines+markers",
            line=dict(color=cmap[col], width=3.5 if col in hl else 2.2),
            marker=dict(size=9 if col in hl else 7, line=dict(color="#fff", width=2)),
            opacity=0.3 if dim else 1.0,
            hovertemplate=f"{col}: %{{y:,.1f}}{ysuffix}<extra></extra>",
        ))
        fig.add_annotation(x=panel.index[-1], y=panel[col].iloc[-1], text=f" {col}", showarrow=False,
                           xanchor="left", font=dict(size=11, color=T.INK2), opacity=0.3 if dim else 1)
    if industry and metric:
        s = IND.industry_series(metric)["Average"]
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=IND_LABEL, mode="lines+markers",
                                 line=dict(color=IND_COLOR, width=3, dash="dash"), marker=dict(size=7, symbol="diamond"),
                                 hovertemplate=f"Industry avg: %{{y:,.1f}}{ysuffix}<extra></extra>"))
    fig.update_layout(title=title, yaxis_ticksuffix=ysuffix, showlegend=True, margin=dict(r=80))
    return T.style_fig(fig, height)


def compare_line(names: list[str], metric: str, title: str, ysuffix: str = "", height: int = 340) -> go.Figure:
    fig = go.Figure()
    for i, n in enumerate(names):
        s = series(n, metric)
        if s.empty:
            continue
        ind = n == IND_LABEL
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=n, mode="lines+markers",
                                 line=dict(color=color(n), width=3.5 if i == 0 else 2.4, dash="dash" if ind else "solid"),
                                 marker=dict(size=8, symbol="diamond" if ind else "circle", line=dict(color="#fff", width=1.5)),
                                 hovertemplate=f"{n}: %{{y:,.1f}}{ysuffix}<extra></extra>"))
    fig.update_layout(title=title, yaxis_ticksuffix=ysuffix, showlegend=True)
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


def impact_html(imp: dict) -> str:
    """Effect of a news item on the three statements, what management is doing, and what more to do."""
    if not imp:
        return ""
    rows = [("P&L", imp.get("pl")), ("Balance sheet", imp.get("bs")), ("Cash flow", imp.get("cf")),
            ("Already doing", imp.get("doing")), ("What more to do", imp.get("should"))]
    cells = "".join(f'<div class="ib"><div class="ibl">{a}</div><div>{b}</div></div>' for a, b in rows if b)
    return f'<div class="impact">{cells}</div>'


def bullets(items: list[str], cls: str = "") -> str:
    return f'<ul class="{cls}" style="margin:0;padding-left:18px">' + "".join(f"<li style='margin:4px 0'>{i}</li>" for i in items) + "</ul>"
