"""News & Signals: curated + live news, correlated with KPIs and share-price reaction."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import live as L
from core import theme as T
from views.common import impact_html, news_html, note_box


def render():
    T.hero("News & Signals", "Six months of financial, regulatory, deal and policy news. Each item is linked to the numbers it affects, "
           "scored for sentiment and tested against share-price reaction.", ["Curated + live Google News", "KPI tagging", "Event study vs Nifty Pharma"])
    nd = D.all_news()
    nd = nd[nd["date"] >= pd.Timestamp("2026-04-19")]

    T.section("Signal timeline", "Apr → Oct 2026 · green = good news, red = bad news")
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
    bal = nd.groupby("Company")["sentiment"].agg(["sum", "count"])
    note_box("Signal timeline (6 months of news)", peer="nw_timeline",
             facts="; ".join(f"{c}: net {int(r['sum']):+d} from {int(r['count'])} items" for c, r in bal.iterrows()))

    T.section("News → KPI heat", "which numbers the news is moving · bottom row = each company's net good minus bad")
    ex = nd.explode("metrics")
    piv = ex.pivot_table(index="metrics", columns="Company", values="sentiment", aggfunc="sum", fill_value=0)
    piv = piv.loc[piv.abs().sum(axis=1).sort_values(ascending=False).index[:12]]
    tot = nd.groupby("Company")["sentiment"].sum().reindex(piv.columns).fillna(0)
    piv.loc["NET (all news)"] = tot
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale=T.DIVERGING, zmid=0, xgap=2, ygap=2,
                               text=piv.values.astype(int), texttemplate="%{text}", hovertemplate="%{x} · %{y}: net %{z}<extra></extra>"))
    fig.update_layout(hovermode="closest", yaxis=dict(autorange="reversed"))
    st.plotly_chart(T.style_fig(fig, 460), use_container_width=True)
    note_box("News to KPI heat", peer="nw_heat", facts="Net good-minus-bad news by company: " + "; ".join(f"{c} {int(v):+d}" for c, v in tot.items()))

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
        st.caption("Each card shows what the news does to the P&L, balance sheet and cash flow, what management is already doing, and what more to do.")
        for _, r in view.iterrows():
            d_ = r.to_dict()
            imp = d_.get("statement_impact") if isinstance(d_.get("statement_impact"), dict) else None
            st.markdown(news_html(d_, r["Company"]) + impact_html(imp), unsafe_allow_html=True)

    with tabs[1]:
        if not st.session_state.get("live_on", True):
            st.info("Live feeds are switched off in the sidebar.")
        else:
            pick = st.selectbox("Company", [c["id"] for c in D.companies()], format_func=lambda x: D.names()[x], key="live_news_pick",
                                index=next((i for i, c in enumerate(D.companies()) if c["id"] == st.session_state.get("focus")), 0))
            with st.spinner("Scanning Google News…"):
                live, err = L.fetch_news(D.company(pick)["name"], days=180, limit=40)
            if err:
                st.warning(f"{err} Showing the curated news only.")
            else:
                st.caption(f"{len(live)} headlines. Positive/negative is judged from keywords in the headline. Updates every 30 minutes.")
                for _, r in live.iterrows():
                    d = r.to_dict()
                    d["impact"] = d.get("source", "")
                    st.markdown(news_html(d), unsafe_allow_html=True)

    with tabs[2]:
        pick = st.selectbox("Company ", [c["id"] for c in D.companies()], format_func=lambda x: D.names()[x], key="es_pick")
        c = D.company(pick)
        px, err = L.fetch_prices((c["ticker"],), "1y") if st.session_state.get("live_on", True) else (pd.DataFrame(), "Live feeds off")
        if px.empty:
            st.warning("Share price history is not available right now, so this chart can't be shown. Try again in a few minutes.")
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
                st.info("These news items are too recent to measure the share price reaction yet.")
            else:
                st.dataframe(es.rename(columns={"date": "Date", "title": "News", "sentiment": "Good/bad (+1/−1)", "stock_ret_%": "Share move", "bench_ret_%": "Pharma index move", "abnormal_%": "Extra move"})
                             .style.format({"Share move": "{:+.1f}%", "Pharma index move": "{:+.1f}%", "Extra move": "{:+.1f}%"}),
                             hide_index=True, use_container_width=True)
                hit = (es["sentiment"] * es["abnormal_%"] > 0).mean() * 100
                st.caption(f"'Extra move' = how much the share moved beyond the pharma index, from the day before the news to three trading days after. "
                           f"The share moved in the direction the news suggested {hit:.0f}% of the time.")
    T.footer(D.meta())
