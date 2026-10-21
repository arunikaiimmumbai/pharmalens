"""Sources & Method."""
import pandas as pd
import streamlit as st

from core import data as D
from core import theme as T


def render():
    meta = D.meta()
    T.hero("Sources & Method", "How every number was built, where it came from, and what to be careful with.",
           [meta["basis"].split(".")[0]])

    T.section("Data sources")
    for s in meta["sources"]:
        link = f': <a href="{s["url"]}" target="_blank">{s["url"]}</a>' if s["url"] else ""
        st.markdown(f"- {s['name']}{link}", unsafe_allow_html=True)
    st.markdown("- Live layer: Yahoo Finance (via `yfinance`) for prices & Nifty Pharma; Google News RSS for headlines (refreshed every 15–30 min).")

    T.section("Per-company source links", "news & filings used")
    rows = []
    for c in D.companies():
        for n in c["news"]:
            rows.append({"Company": c["short"], "Date": n["date"], "Item": n["title"], "Source": n["url"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                 column_config={"Source": st.column_config.LinkColumn(display_text="open ↗")})

    T.section("Methodology")
    st.markdown("""
- **Basis:** consolidated, March year-end. FY26 = year ended 31-Mar-2026; Q1 FY27 = Apr–Jun 2026. ₹ crore.
- **EBITDA** = operating profit before other income (Screener definition). **ROCE** as reported by Screener; **ROE** = PAT ÷ average net worth.
- **Cost lines** (material, employee, manufacturing, other) from Screener cost schedules (% of sales); ₹ values derived = % × revenue. *Indirect* = manufacturing + other.
- **CAGR** = 4-year compound growth FY22→FY26. **Cost growth vs revenue growth** = how fast a cost grew each year divided by how fast revenue grew (above 1 = cost growing faster).
- **Correlations:** within-company (n = 5 years) are directional only; pooled (30 company-years) are more robust but mix structural differences.
- **Financial score:** min–max normalised KPIs (0–100) within the peer set, averaged per pillar, weighted Growth 25 / Profitability 25 / Returns 20 / Cash 15 / Balance sheet 15.
- **Sentiment:** curated items hand-scored (+1/0/−1); live headlines scored with a pharma-specific lexicon (e.g. "OAI", "warning letter" negative; "approval", "EIR" positive).
- **Share price reaction:** the 'extra move' is the share's change minus the Nifty Pharma index's change, from the day before the news to three trading days after.
- **Digital maturity** and **therapy weights** are my estimates from public information. Check them with management interviews and IQVIA data.
""")

    T.section("Data caveats")
    for c in D.companies():
        for n in c.get("data_notes", []):
            st.markdown(f"- **{c['short']}:** {n}")

    T.section("KPI dictionary")
    kd = pd.DataFrame([{"Key": k, "KPI": v[0], "Unit": v[1], "Better when": {True: "higher", False: "lower", None: "context"}[v[2]]}
                       for k, v in D.KPI_DEFS.items()])
    st.dataframe(kd, hide_index=True, use_container_width=True)
    st.warning("Academic project using publicly available information. Not investment advice. Verify figures against company filings before external use.")
    T.footer(meta)
