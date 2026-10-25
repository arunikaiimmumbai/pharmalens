"""Sources & Method: where every number comes from, how it is calculated, and a plain-English glossary."""
import pandas as pd
import streamlit as st

from core import data as D
from core import glossary as G
from core import industry as IND
from core import theme as T


def render():
    meta = D.meta()
    T.hero("Sources & Method", "How every number was built, where it came from, and what to be careful with.",
           [meta["basis"].split(".")[0], "Industry = 20 Nifty Pharma companies", "Glossary"])

    T.section("Data sources")
    for s in meta["sources"]:
        link = f': <a href="{s["url"]}" target="_blank">{s["url"]}</a>' if s["url"] else ""
        st.markdown(f"- {s['name']}{link}", unsafe_allow_html=True)
    st.markdown("- Live layer: Yahoo Finance (via `yfinance`) for prices and the Nifty Pharma index; Google News RSS for headlines (refreshed every 15 to 30 minutes).")

    T.section("Industry benchmark", "what 'Industry' means everywhere in the app")
    im = IND.meta()
    st.markdown(f"""
- **Source A (every ratio):** the 20 companies in the **Nifty Pharma** index, the stock exchange's own definition of the pharma industry.
  Industry value = simple average of the 20; the median is shown alongside because one large or loss-making company can pull an average.
  Constituent list: [{im['constituents_source']['title']}]({im['constituents_source']['url']}).
- **Source C (market growth):** published Indian pharma market figures, used where company accounts can't answer (how fast the Indian market grows).
- **Method:** {im['method']}
- **Caveat:** Nifty Pharma is mostly large companies with scale advantages, so part of a mid-size company's gap to the industry average can be size, not management. The Pharma Majors are themselves part of the 20.""")
    st.dataframe(IND.members_table(), hide_index=True, use_container_width=True,
                 column_config={"Source": st.column_config.LinkColumn(display_text="open ↗")})
    st.markdown("**Published market figures (source C)**")
    st.dataframe(pd.DataFrame([{"Figure": m["metric"], "Value": f"{m['value']:.1f}%" + (f" / {m['value2']:.1f}%" if m.get("value2") else ""),
                                "Detail": m["detail"], "Provider": m["provider"], "Source": m["source"]["url"]} for m in IND.market()]),
                 hide_index=True, use_container_width=True, column_config={"Source": st.column_config.LinkColumn(display_text="open ↗")})

    T.section("Per-company source links", "news and filings used")
    rows = []
    for c in D.companies():
        for n in c["news"]:
            rows.append({"Company": c["short"], "Date": n["date"], "Item": n["title"], "Source": n["url"]})
        for s in c["brands"]["sources"]:
            rows.append({"Company": c["short"], "Date": "", "Item": s["title"], "Source": s["url"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"Source": st.column_config.LinkColumn(display_text="open ↗")})

    T.section("Methodology")
    st.markdown("""
- **Basis:** consolidated, March year-end. FY26 = year ended 31 March 2026; Q1 FY27 = April to June 2026. ₹ crore.
- **EBITDA** = operating profit before other income (Screener definition). **ROCE** as reported by Screener; **ROE** = PAT ÷ average net worth.
- **ROIC** = EBIT × (1 − tax rate) ÷ (net worth + net debt). **Net debt** = borrowings − cash equivalents − investments (bank deposits held in 'other assets' are not counted, so net cash can be understated, e.g. Alkem reports about ₹5,500 Cr net cash).
- **Free cash flow** = cash from operations + cash from investing (all investing, including acquisitions).
- **Cost lines** (material, employee, manufacturing, other) from Screener cost schedules (% of sales). *Indirect* = manufacturing + other.
- **CAGR** = 4-year compound growth FY22 → FY26. **Cost growth vs revenue growth** = cost growth per year ÷ revenue growth per year.
- **Correlations:** one company's 5 years are directional only; the 30-point (six companies) and ~100-point (20 industry companies) views are sturdier.
- **Ranking:** user framework (growth 20, profitability 25, cash 20, capital efficiency 15, balance sheet 10, operating efficiency 10), each metric scored 1 to 5 by its position among the 20 Nifty Pharma companies; lenses Current strength 40%, Momentum 30%, Quality 30%. Glenmark is scored on normalised FY26 numbers by default.
- **Analyst notes** (the 💡 button under key charts, shown only where they matter for a consultant) are written from the data, filings and news in this app and cite their sources. They are not generated live, so they load instantly and don't use the AI quota. The 'Ask the analyst' panel answers follow-up questions live.
- **Sentiment:** curated news hand-scored (+1 / 0 / −1); live headlines scored with a pharma keyword list.
- **Digital maturity** scores are outside-in estimates from annual reports, investor presentations and news. 'No public evidence' means nothing was disclosed, not that nothing exists.
- **Brands** are ranked from public evidence (investor presentations, annual reports); exact market shares are IQVIA paid data.
""")

    T.section("Data caveats")
    for c in D.companies():
        for n in c.get("data_notes", []):
            st.markdown(f"- **{c['short']}:** {n}")

    T.section("Glossary", "every metric in plain English, with its formula")
    gl = pd.DataFrame([{"Metric": D.KPI_DEFS.get(k, (k,))[0], "Plain meaning": v[0], "Formula": v[1],
                        "Better when": {True: "higher", False: "lower", None: "depends"}[D.KPI_DEFS[k][2]] if k in D.KPI_DEFS else "–"}
                       for k, v in G.GLOSSARY.items()])
    st.dataframe(gl, hide_index=True, use_container_width=True, height=560,
                 column_config={"Plain meaning": st.column_config.TextColumn(width="large")})
    st.warning("Academic project using publicly available information. Not investment advice. Verify figures against company filings before external use.")
    T.footer(meta)
