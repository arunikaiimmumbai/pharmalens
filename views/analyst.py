"""AI Analyst — agentic chat (Claude tool-use) with visible reasoning trace."""
import streamlit as st

from core import agent as A
from core import data as D
from core import theme as T

SUGGESTIONS = [
    "Compare ROCE, cash conversion and inventory days across all six — who has the biggest working-capital opportunity?",
    "Why did Alkem's PAT fall in Q1 FY27 despite 11% revenue growth? Link it to news and the Daman OAI.",
    "Build the investment thesis risks for Mankind post-BSV and the ACTx CAR-T deal.",
    "Correlate employee cost growth with revenue growth for Ajanta and tell me if operating leverage is breaking.",
    "If Alembic grows 15% and reaches 18% EBITDA margin by FY28, what EV does that imply at 18x?",
    "Give me a SWOT for Alkem and tell me which threat matters most right now.",
]


def _trace(step, tool, args):
    st.session_state._trace.append((step, tool, args))
    st.session_state._trace_box.markdown("".join(
        f'<div class="agent-trace">⚙️ step {s} · <b>{t}</b>({", ".join(f"{k}={v}" for k, v in a.items())})</div>'
        for s, t, a in st.session_state._trace), unsafe_allow_html=True)


def render():
    T.hero("AI Analyst", "An agent that plans, pulls the right data (financials, ratios, correlations, live news, prices, scenarios) "
           "and writes a partner-ready answer — with its tool trace visible.",
           ['<span class="pulse"></span> Agent online' if A.get_api_key() else "Offline analyst mode (add a free Gemini key)",
            f"Engine: {A.provider_label()} · {A.get_model() if A.get_api_key() else 'rule-based'}", "10 tools"])

    if "chat" not in st.session_state:
        st.session_state.chat = []

    st.markdown("**Try a question**")
    cols = st.columns(3)
    for i, s in enumerate(SUGGESTIONS):
        if cols[i % 3].button(s, key=f"sugg{i}", use_container_width=True):
            st.session_state.pending = s

    for m in st.session_state.chat:
        with st.chat_message(m["role"], avatar="🧬" if m["role"] == "assistant" else "👤"):
            st.markdown(m["content"])

    q = st.chat_input("Ask about any company, ratio, trend, news or problem statement…")
    q = q or st.session_state.pop("pending", None)
    if q:
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user", avatar="👤"):
            st.markdown(q)
        with st.chat_message("assistant", avatar="🧬"):
            st.session_state._trace = []
            with st.status("Agent researching…", expanded=True) as status:
                st.session_state._trace_box = st.empty()
                try:
                    if A.get_api_key():
                        ans = A.run_agent(st.session_state.chat[-10:], on_step=_trace)
                    else:
                        ans = A.offline_answer(q, on_step=_trace)
                    status.update(label=f"Done · {len(st.session_state._trace)} tool calls", state="complete", expanded=False)
                except Exception as e:
                    ans = A.offline_answer(q, on_step=_trace) + f"\n\n> ⚠️ The AI couldn't answer, so this reply comes from the offline analyst. Reason: {A.friendly_error(e)}"
                    status.update(label="Fell back to offline analyst", state="error", expanded=False)
            st.markdown(ans)
        st.session_state.chat.append({"role": "assistant", "content": ans})

    c1, c2 = st.columns([1, 5])
    if c1.button("🧹 Clear chat"):
        st.session_state.chat = []
        st.rerun()
    if st.session_state.chat:
        transcript = "\n\n".join(f"**{m['role'].upper()}**: {m['content']}" for m in st.session_state.chat)
        c2.download_button("⬇️ Download transcript (.md)", transcript.encode(), "pharmalens_analyst.md", "text/markdown")
    T.footer(D.meta())
