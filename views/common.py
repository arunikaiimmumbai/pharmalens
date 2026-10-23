"""Shared view helpers: company picker, compare bar, analyst notes, page-item registry for the analyst panel, charts."""
from __future__ import annotations

import numpy as np
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
    """Analyst note for a chart, kept out of the way: a small '💡 Analyst note' button opens a pop-up with what is
    happening, what the company is doing, where a consultant can help, and sources. Only notes marked as useful
    for a consultant ('show') get the button; every note still feeds the analyst panel."""
    note = (N.company(company, theme) if company and theme else None) or (N.peer(peer) if peer else None) or {}
    register(title, company=company, metric=metric, theme=theme, note=note, facts=facts)
    text = f"{note.get('text', '')} {extra}".strip()
    if not text or not note.get("show", True):
        return
    a, b, _ = st.columns([1.5, 0.85, 6.5], vertical_alignment="center")
    with a.popover("💡 Analyst note", use_container_width=True):
        st.markdown(f'<div class="pop-h">{title}</div>', unsafe_allow_html=True)
        parts = [("What is happening", text), ("What the company is doing", note.get("doing")),
                 ("Where a consultant can help", note.get("angle"))]
        for lab, val in parts:
            if val:
                st.markdown(f'<div class="pop-l">{lab}</div><div class="pop-t">{val}</div>', unsafe_allow_html=True)
        src = N.sources_md(note.get("sources", []))
        if src:
            st.markdown(f'<div class="pop-s">Sources: {src}</div>', unsafe_allow_html=True)
    b.button("💬 Ask", key=f"ask_{title}", on_click=_open_panel, args=(title,), help="Ask the analyst about this chart",
             use_container_width=True)


# ── Comparison block (same on every page) ────────────────────────────────────
def comparison_block(key: str, focus: str | None, cmp: dict, metrics: list[str], title: str = "Side-by-side comparison",
                     year: str = "FY26") -> None:
    """Shown whenever 'Compare with' has a selection: a table of the chosen metrics for every selected company and the
    industry, best value highlighted, plus one chart that switches between this year's snapshot and the 5-year trend."""
    names = entities(focus, cmp)
    comps = [n for n in names if n != IND_LABEL]
    if len(names) < 2:
        return
    hib_of = {m: D.KPI_DEFS[m][2] for m in metrics}
    vals = {n: {m: value(n, m, year) for m in metrics} for n in names}
    with st.container(border=True):
        st.markdown(f'<div class="section" style="margin-top:4px"><div class="bar"></div><h3>{title}</h3>'
                    f'<span class="tag">{year} · ' + " vs ".join(names) + "</span></div>", unsafe_allow_html=True)
        left, right = st.columns([1.05, 1], gap="medium")
        with left:
            rows = []
            for m in metrics:
                row = {"Metric": D.KPI_DEFS[m][0]}
                for n in names:
                    v = vals[n][m]
                    row[n] = None if v is None or (isinstance(v, float) and not np.isfinite(v)) else float(v)
                rows.append(row)
            tbl = pd.DataFrame(rows).set_index("Metric")
            ind = tbl[IND_LABEL] if IND_LABEL in tbl.columns else None

            def style(r):
                m = metrics[list(tbl.index).index(r.name)]
                hib = hib_of[m]
                out = [""] * len(r)
                cv = pd.to_numeric(r[comps], errors="coerce")
                if hib is not None and cv.notna().sum() >= 2:
                    best = cv.idxmax() if hib else cv.idxmin()
                    out[list(r.index).index(best)] = "background-color:#E3F6EC;color:#0B7A43;font-weight:700"
                for i, col in enumerate(r.index):
                    if col == IND_LABEL:
                        out[i] = "background-color:#F1F5F9;color:#475569;font-style:italic"
                    elif ind is not None and hib is not None and pd.notna(r[col]) and pd.notna(ind[r.name]) and not out[i]:
                        worse = r[col] < ind[r.name] if hib else r[col] > ind[r.name]
                        if worse:
                            out[i] = "color:#B71C1C"
                return out

            disp = tbl.copy().astype(object)
            for m, (idx, r) in zip(metrics, tbl.iterrows()):
                for n in names:
                    v = r[n]
                    disp.loc[idx, n] = "–" if v is None or pd.isna(v) else D.fmt(m, v)
            st.dataframe(disp.style.apply(lambda r: style(tbl.loc[r.name]), axis=1), use_container_width=True,
                         height=38 + 35 * len(metrics))
            note = "Green = best of the companies shown."
            if IND_LABEL in names:
                beats = []
                for n in comps:
                    k_ = sum(1 for m in metrics if hib_of[m] is not None and vals[n][m] is not None and vals[IND_LABEL][m] is not None
                             and np.isfinite(vals[n][m]) and ((vals[n][m] > vals[IND_LABEL][m]) == bool(hib_of[m])))
                    tot = sum(1 for m in metrics if hib_of[m] is not None and vals[IND_LABEL][m] is not None)
                    beats.append(f"{n} beats the industry on {k_} of {tot}")
                note += " Red = worse than the industry average. " + "; ".join(beats) + "."
            st.caption(note)
        with right:
            c1, c2 = st.columns([1.4, 1])
            pick = c1.selectbox("Chart this metric", metrics, format_func=lambda m: D.KPI_DEFS[m][0], key=f"cb_m_{key}")
            trend_ok = pick in D.panel(pick).columns.tolist() or not pick.endswith("_cagr")
            view = c2.radio("View", ["Snapshot", "5-year trend"], key=f"cb_v_{key}", horizontal=True,
                            disabled=pick.endswith("_cagr") or pick in ("pe", "mcap_cr", "rnd_pct"))
            unit = D.KPI_DEFS[pick][1]
            suf = "%" if unit == "%" else "x" if unit == "x" else " d" if unit == "days" else ""
            if view == "Snapshot" or pick.endswith("_cagr") or pick in ("pe", "mcap_cr", "rnd_pct"):
                pts = [(n, vals[n][pick]) for n in comps if vals[n][pick] is not None and np.isfinite(vals[n][pick])]
                hib = hib_of[pick]
                pts.sort(key=lambda x: x[1], reverse=hib is not False)
                fig = go.Figure(go.Bar(y=[p[0] for p in pts], x=[p[1] for p in pts], orientation="h",
                                       marker_color=[color(p[0]) for p in pts], marker_cornerradius=6,
                                       text=[D.fmt(pick, p[1]) for p in pts], textposition="outside",
                                       hovertemplate="%{y}: %{x:,.2f}<extra></extra>"))
                iv = vals.get(IND_LABEL, {}).get(pick) if IND_LABEL in names else None
                if iv is not None and np.isfinite(iv):
                    fig.add_vline(x=iv, line_dash="dash", line_color=IND_COLOR, line_width=2,
                                  annotation_text=f"Industry {D.fmt(pick, iv)}", annotation_position="top")
                xs = [p[1] for p in pts] + ([iv] if iv is not None and np.isfinite(iv) else [])
                lo, hi = min(0, min(xs)), max(xs)
                fig.update_layout(title=f"{D.KPI_DEFS[pick][0]}, {year} (best first)", yaxis=dict(autorange="reversed"),
                                  xaxis=dict(range=[lo * 1.25, hi * 1.3], ticksuffix=suf), hovermode="closest", showlegend=False)
                st.plotly_chart(T.style_fig(fig, 90 + 52 * len(pts)), use_container_width=True)
            else:
                st.plotly_chart(compare_line(names, pick, f"{D.KPI_DEFS[pick][0]}, FY22 to FY26", suf, 300), use_container_width=True)
            if IND_LABEL in names:
                st.caption(IND.note(pick, year))
    register(f"{title} ({', '.join(names)})", kind="table",
             note={"text": "Side-by-side comparison of the selected companies and the industry average.",
                   "sources": [{"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"},
                               {"title": "Nifty Pharma constituents", "url": IND.meta()["constituents_source"]["url"]}]},
             facts="; ".join(f"{D.KPI_DEFS[m][0]}: " + ", ".join(f"{n} {D.fmt(m, vals[n][m]) if vals[n][m] is not None else '–'}" for n in names)
                             for m in metrics))


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
