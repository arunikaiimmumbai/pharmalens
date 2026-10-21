"""PharmaLens.ai: agentic intelligence dashboard for Indian mid-cap pharma.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="PharmaLens.ai · Pharma Intelligence", page_icon="🧬", layout="wide",
                   initial_sidebar_state="expanded")

from core import data as D  # noqa: E402
from core import theme as T  # noqa: E402
from views import (analyst, command, company, news, pnl, ratios, regulatory, sources,  # noqa: E402
                   strategy)

T.inject_css()
T.register_plotly_template()
meta = D.meta()

if "focus" not in st.session_state:
    st.session_state.focus = "alkem"

from pathlib import Path  # noqa: E402

st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")

pages = [
    st.Page(command.render, title="Command Center", icon="🧬", url_path="command", default=True),
    st.Page(company.render, title="Company Deep-Dive", icon="🏢", url_path="company"),
    st.Page(pnl.render, title="P&L Lab", icon="📊", url_path="pnl"),
    st.Page(ratios.render, title="Ratio Benchmark", icon="⚖️", url_path="ratios"),
    st.Page(regulatory.render, title="Regulatory & Pipeline", icon="🧪", url_path="regulatory"),
    st.Page(news.render, title="News & Signals", icon="📰", url_path="news"),
    st.Page(strategy.render, title="Strategy Room", icon="🎯", url_path="strategy"),
    st.Page(analyst.render, title="AI Analyst", icon="🤖", url_path="analyst"),
    st.Page(sources.render, title="Sources & Method", icon="📚", url_path="sources"),
]
nav = st.navigation(pages, position="sidebar")

with st.sidebar:
    st.markdown("---")
    ids = list(D.names().keys())
    st.selectbox("Focus company", ids, format_func=lambda x: D.names()[x], key="focus")
    st.toggle("Live market & news feeds", value=True, key="live_on",
              help="On: shows live share prices and news headlines. Off: shows only the saved data.")
    with st.expander("🔑 AI settings"):
        st.text_input("Free Gemini API key (optional)", type="password", key="user_api_key",
                      help="Get one free at aistudio.google.com. Better: store it in Streamlit Secrets as GEMINI_API_KEY. "
                           "Without a key the AI Analyst runs in free offline mode.")
    st.markdown(
        f"""<div style="font-size:.74rem;opacity:.85;margin-top:14px;line-height:1.5">
        <b>{meta['author']}</b><br>{meta['program']}<br>Mentor: {meta['mentor']}</div>""",
        unsafe_allow_html=True,
    )

nav.run()
