"""News & Signals — curated + live news, correlated with KPIs and share-price reaction."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import live as L
from core import theme as T
from views.common import news_html


def render():
    T.hero("News & Signals", "Last six months of financial, regulatory, M&A and policy news — tagged to the KPIs they move, "
           "scored for sentiment and tested against share-price reaction.", ["Curated + live Google News", "KPI tagging", "Event study vs Nifty Pharma"])
    nd = D.all_news()
    nd = nd[nd["date"] >= pd.Timestamp("2026-04-19")]

    T.section("Signal timeline", "Apr → Oct 2026 · colour = sentiment")
    sent_col = {1: T.GOOD, 0: "#94A3B8", -1: T.BAD}
    sent_sym = {1: "triangle-up", 0: "circle", -1: "triangle-down"}
    fig = go.Figure()
    for s, lab in [(1, "Positive"), (0, "Neutral"), (-1, "Negative")]:
        g = nd[nd["sentiment"] == s]
        fig.add_trace(go.Scatter(x=g["date"], y=g["Company"], mode="markers", name=lab,
                                 marker=dict(size=16, color=sent_col[s], symbol=sent_sym[s], line=dict(color="#fff", width=2)),
                                 text=g["title"], customdata=g["category"],
                                 hovertemplate="<b>%{y}</b> · %{x|%d %b %Y}<br>%{customdata}<br>%{text}<extra></extra>"))
    fig.update_layout(hovermode="closest", yaxis=dict(categoryorder="array", categoryarray=["Sector"] + [c["short"] for c in D.companies()][::-1]))
    st.plotly_chart(T.style_fig(fig, 380), use_container_width=True)

    a, b = st.columns([1, 1])
    with a:
        T.section("News → KPI heat", "which metrics the news is moving")
        ex = nd.explode("metrics")
        piv = ex.pivot_table(index="metrics", columns="Company", values="sentiment", aggfunc="sum", fill_value=0)
        piv = piv.loc[piv.abs().sum(axis=1).sort_values(ascending=False).index[:12]]
        fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale=T.DIVERGING, zmid=0, xgap=2, ygap=2,
                                   text=piv.values, texttemplate="%{text}", hovertemplate="%{x} · %{y}: net sentiment %{z}<extra></extra>"))
        fig.update_layout(hovermode="closest", yaxis=dict(autorange="reversed"))
        st.plotly_chart(T.style_fig(fig, 420), use_container_width=True)
    with b:
        T.section("Sentiment balance", "positive − negative events")
        bal = nd[nd["Company"] != "Sector"].groupby("Company")["sentiment"].agg(["sum", "count"])
        cmap = D.colors()
        fig = go.Figure(go.Bar(x=bal.index, y=bal["sum"], marker_color=[cmap[i] for i in bal.index], marker_cornerradius=6,
                               text=[f"{s:+d} ({n} events)" for s, n in zip(bal["sum"], bal["count"])], textposition="outside",
                               hovertemplate="%{x}: net %{y:+d}<extra></extra>"))
        fig.update_layout(hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 420), use_container_width=True)

    tabs = st.tabs(["🗂️ Curated feed", "📡 Live headlines", "📈 Price reaction (event study)"])
    with tabs[0]:
        f1, f2 = st.columns(2)
        comps = f1.multiselect("Company", ["Sector"] + [c["short"] for c in D.companies()], default=[], key="nf_c")
        cats = f2.multiselect("Category", sorted(nd["category"].unique()), default=[], key="nf_cat")
        view = nd
        if comps:
            view = view[view["Company"].isin(comps)]
        if cats:
            view = view[view["category"].isin(cats)]
        c1, c2 = st.columns(2)
        for i, (_, r) in enumerate(view.iterrows()):
            (c1 if i % 2 == 0 else c2).markdown(news_html(r.to_dict(), r["Company"]), unsafe_allow_html=True)

    with tabs[1]:
        if not st.session_state.get("live_on", True):
            st.info("Live feeds are switched off in the sidebar.")
        else:
            pick = st.selectbox("Company", [c["id"] for c in D.companies()], format_func=lambda x: D.names()[x], key="live_news_pick",
                                index=[c["id"] for c in D.companies()].index(st.session_state.get("focus", "alkem")))
            with st.spinner("Scanning Google News…"):
                live, err = L.fetch_news(D.company(pick)["name"], days=180, limit=40)
            if err:
                st.warning(f"{err} — showing curated feed only.")
            else:
                st.caption(f"{len(live)} headlines · lexicon sentiment & auto-category · refreshed every 30 min")
                for _, r in live.iterrows():
                    d = r.to_dict()
                    d["impact"] = d.get("source", "")
                    st.markdown(news_html(d), unsafe_allow_html=True)

    with tabs[2]:
        pick = st.selectbox("Company ", [c["id"] for c in D.companies()], format_func=lambda x: D.names()[x], key="es_pick")
        c = D.company(pick)
        px, err = L.fetch_prices((c["ticker"],), "1y") if st.session_state.get("live_on", True) else (pd.DataFrame(), "Live feeds off")
        if px.empty:
            st.warning(f"Price history unavailable ({err}). Deploy with internet access (e.g. Streamlit Cloud) to enable the event study.")
        else:
            ev = nd[nd["id"] == pick]
            s = px[c["ticker"]].dropna()
            b = px[L.BENCHMARK].dropna()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=s.index, y=s / s.iloc[0] * 100, name=c["short"], line=dict(color=c["color"], width=2.5)))
            fig.add_trace(go.Scatter(x=b.index, y=b / b.iloc[0] * 100, name="Nifty Pharma", line=dict(color=T.MUTED, width=2, dash="dot")))
            for _, e in ev.iterrows():
                fig.add_vline(x=e["date"], line_color={1: T.GOOD, 0: "#94A3B8", -1: T.BAD}[e["sentiment"]], line_width=1, opacity=0.6)
            fig.update_layout(title=f"{c['short']} vs Nifty Pharma (indexed to 100) · vertical lines = news events", yaxis_title="Index")
            st.plotly_chart(T.style_fig(fig, 400), use_container_width=True)
            es = L.event_study(px, c["ticker"], ev, window=3)
            if es.empty:
                st.info("Not enough trading days around events yet.")
            else:
                st.dataframe(es.style.format({"stock_ret_%": "{:+.1f}%", "bench_ret_%": "{:+.1f}%", "abnormal_%": "{:+.1f}%"}),
                             hide_index=True, use_container_width=True)
                hit = (es["sentiment"] * es["abnormal_%"] > 0).mean() * 100
                st.caption(f"Abnormal return = stock − Nifty Pharma, t−1 → t+3 trading days. Sentiment direction matched price reaction in {hit:.0f}% of events.")
    T.footer(D.meta())
