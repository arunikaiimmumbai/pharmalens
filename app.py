"""Finance Lens: agentic intelligence dashboard for Indian mid-cap pharma.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Finance Lens · Pharma Intelligence", page_icon="🧬", layout="wide",
                   initial_sidebar_state="expanded")

import sys  # noqa: E402

# Always load the newest app files. Streamlit Cloud can keep an old copy of a module in memory
# after a git push, which mixes old and new code. Dropping our own modules forces a fresh import.
for _m in [m for m in sys.modules if m in ("core", "views") or m.startswith(("core.", "views."))]:
    del sys.modules[_m]

from pathlib import Path  # noqa: E402

from core import data as D  # noqa: E402
from core import theme as T  # noqa: E402
from views import (command, company, news, panel, pnl, ranking, ratios, regulatory,  # noqa: E402
                   sources, strategy, upload)

T.inject_css()
T.register_plotly_template()
meta = D.meta()

if "focus" not in st.session_state:
    st.session_state.focus = None
if "panel_open" not in st.session_state:
    st.session_state.panel_open = False

st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")

pages = [
    st.Page(command.render, title="Company Overview", icon="🧬", url_path="overview", default=True),
    st.Page(company.render, title="Company Deep-Dive", icon="🏢", url_path="company"),
    st.Page(pnl.render, title="P&L Lab", icon="📊", url_path="pnl"),
    st.Page(ratios.render, title="Ratio Benchmark", icon="⚖️", url_path="ratios"),
    st.Page(regulatory.render, title="Regulatory & Pipeline", icon="🧪", url_path="regulatory"),
    st.Page(news.render, title="News & Signals", icon="📰", url_path="news"),
    st.Page(strategy.render, title="Strategy Room", icon="🎯", url_path="strategy"),
    st.Page(ranking.render, title="Ranking & Scenarios", icon="🏆", url_path="ranking"),
    st.Page(upload.render, title="Data Upload", icon="📤", url_path="upload"),
    st.Page(sources.render, title="Sources & Method", icon="📚", url_path="sources"),
]
nav = st.navigation(pages, position="sidebar")

with st.sidebar:
    st.markdown("---")
    ids = [None] + list(D.names().keys())
    st.selectbox("Focus company", ids, format_func=lambda x: "Select" if x is None else D.names()[x], key="focus", placeholder="Select",
                 help="Pick a company to open the Deep-Dive, P&L Lab and Strategy Room on it. Leave on Select for no focus.")
    st.toggle("Live market & news feeds", value=True, key="live_on",
              help="On: shows live share prices and news headlines. Off: shows only the saved data.")
    with st.expander("🔑 AI settings"):
        st.text_input("Free Gemini API key (optional)", type="password", key="user_api_key",
                      help="Get one free at aistudio.google.com. Better: store it in Streamlit Secrets as GEMINI_API_KEY. "
                           "Without a key the analyst answers in free offline mode.")
    st.markdown(
        f"""<div style="font-size:.74rem;opacity:.85;margin-top:14px;line-height:1.5">
        <b>{meta['author']}</b><br>{meta['program']}<br>Mentor: {meta['mentor']}</div>""",
        unsafe_allow_html=True,
    )

# Items the analyst panel can be asked about are registered fresh by each page run.
st.session_state["_items"] = []
st.session_state["_page"] = nav.title

_, top_right = st.columns([5, 1.25])
with top_right:
    st.toggle("🤖 Ask the analyst", key="panel_open", help="Opens the analyst panel on the right of this page.")

if st.session_state.panel_open:
    main, side = st.columns([2.45, 1], gap="medium")
else:
    main, side = st.container(), None


def _run_page() -> None:
    try:
        nav.run()
    except Exception:  # page reruns use BaseException, so they pass through untouched
        import traceback
        traceback.print_exc()  # full detail stays in the server logs
        if st.session_state.get("focus") is None:
            st.info("👈 Please select a company from the **Focus company** menu on the left to open this page.")
        else:
            st.info("This page could not load just now. Please refresh the browser, or pick another company "
                    "from the **Focus company** menu on the left.")


with main:
    _run_page()

if side is not None:
    with side.container(key="panel"):
        try:
            panel.render()
        except Exception:
            import traceback
            traceback.print_exc()
            st.info("The analyst panel could not load just now. Please refresh the browser.")
