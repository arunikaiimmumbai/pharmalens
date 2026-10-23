"""'Ask the analyst' side panel, available on every page.

1. Pick what to ask about: any chart or text registered by the current page (or the whole page).
2. Click a suggested question or type your own.
3. Answers follow one format (what it checks, how it's calculated, what it means, what the company is already
   doing, what more can be done) and end with source links.
4. 'Agent history' lists every question, the item it was about, each tool the agent used and how long it took.
"""
from __future__ import annotations

import time
from datetime import datetime

import pandas as pd
import streamlit as st

from core import agent as A

WHOLE_PAGE = "This whole page"


def _suggestions(item: dict | None) -> list[str]:
    if not item:
        return ["Summarise what this page tells me in plain English.",
                "Which company looks strongest here and why?",
                "Where could a consultant add the most value, based on this page?"]
    t = item["title"]
    if item.get("company"):
        return [f"Why does {t} look like this?",
                f"How does {t} compare with the industry and the other five?",
                f"What should the company or a consultant do about {t}?"]
    return [f"What is the main takeaway from {t}?",
            f"Which company stands out in {t}, and why?",
            f"What does {t} mean for a consulting pitch?"]


def _context(item: dict | None, page: str) -> str:
    if not item:
        items = st.session_state.get("_items", [])
        return f"[Page context] Page: {page}. Items on this page: " + "; ".join(i["title"] for i in items[:20]) + "."
    note = item.get("note") or {}
    srcs = "; ".join(f"{s['title']}: {s['url']}" for s in note.get("sources", []))
    who = f" Company id: {item['company']}." if item.get("company") else ""
    met = f" Metric key: {item['metric']}." if item.get("metric") else ""
    return (f"[Page context] Page: {page}. The user is asking about: {item['title']}.{who}{met} "
            f"Data shown: {item.get('facts', '')} Analyst note: {note.get('text', '')} "
            f"What the company is already doing: {note.get('doing', 'not recorded')}. "
            f"Where a consultant can help: {note.get('angle') or 'not recorded'}. Sources available: {srcs}")


def _ask(question: str, item: dict | None, page: str) -> None:
    log = st.session_state.setdefault("agent_log", [])
    chat = st.session_state.setdefault("panel_chat", [])
    steps: list[dict] = []

    def on_step(step, tool, args):
        steps.append({"step": step, "tool": tool, "args": args})

    t0 = time.time()
    engine = A.provider_label() if A.get_api_key() else "Offline analyst"
    outcome = "answered"
    with st.spinner("Analyst is checking the data…"):
        try:
            if A.get_api_key():
                history = [{"role": m["role"], "content": m["content"]} for m in chat[-6:]]
                msgs = history + [{"role": "user", "content": f"{question}\n\n{_context(item, page)}"}]
                ans = A.run_agent(msgs, on_step=on_step)
            else:
                ans = A.offline_answer(question, on_step=on_step, item=item)
        except Exception as e:  # fall back, explain in plain English
            outcome = "fell back to offline analyst"
            ans = A.offline_answer(question, on_step=on_step, item=item) + f"\n\n> The AI couldn't answer, so this reply comes from the offline analyst. Reason: {A.friendly_error(e)}"
    secs = time.time() - t0
    chat += [{"role": "user", "content": question}, {"role": "assistant", "content": ans}]
    log.append({"time": datetime.now().strftime("%H:%M:%S"), "page": page, "about": item["title"] if item else WHOLE_PAGE,
                "question": question, "engine": engine, "tools_used": len(steps), "seconds": round(secs, 1),
                "outcome": outcome, "steps": steps})


@st.fragment
def render() -> None:
    """Runs as a fragment: asking a question reruns only this panel, not the whole page."""
    page = st.session_state.get("_page", "")
    items = st.session_state.get("_items", [])
    st.markdown('<div class="panelhead"><b>🤖 Ask the analyst</b><div class="muted">Pick a chart or text on this page, then click a '
                'question or type your own. Answers cite their sources.</div></div>', unsafe_allow_html=True)

    titles = [WHOLE_PAGE] + [i["title"] for i in items]
    want = st.session_state.pop("panel_item", None)
    if want in titles:
        st.session_state["panel_pick"] = want
    if st.session_state.get("panel_pick") not in titles:
        st.session_state["panel_pick"] = WHOLE_PAGE
    pick = st.selectbox("What do you want to ask about?", titles, key="panel_pick")
    item = next((i for i in items if i["title"] == pick), None)

    st.markdown('<div class="muted" style="font-size:.78rem;margin-top:4px">Suggested questions</div>', unsafe_allow_html=True)
    for j, q in enumerate(_suggestions(item)):
        if st.button(q, key=f"sugg_{pick}_{j}", use_container_width=True):
            _ask(q, item, page)

    with st.form("panel_form", clear_on_submit=True, border=False):
        q = st.text_area("Or type your own question", height=80, placeholder="e.g. Why is this lower than the industry?")
        if st.form_submit_button("Ask", type="primary", use_container_width=True) and q.strip():
            _ask(q.strip(), item, page)

    chat = st.session_state.get("panel_chat", [])
    if chat:
        box = st.container(height=520)
        pairs = [(chat[i]["content"], chat[i + 1]["content"]) for i in range(0, len(chat) - 1, 2)]
        for qq, aa in reversed(pairs):
            box.markdown(f'<div class="q">❓ {qq}</div>', unsafe_allow_html=True)
            box.markdown(aa)
            box.markdown("---")
        if st.button("🧹 Clear answers", use_container_width=True):
            st.session_state["panel_chat"] = []
            st.rerun(scope="fragment")

    log = st.session_state.get("agent_log", [])
    with st.expander(f"🕘 Agent history ({len(log)})"):
        if not log:
            st.caption("Every question you ask is listed here with the tools the agent used.")
        else:
            df = pd.DataFrame([{k: v for k, v in r.items() if k != "steps"} for r in reversed(log)])
            st.dataframe(df, hide_index=True, use_container_width=True)
            for r in reversed(log[-10:]):
                st.markdown(f"**{r['time']} · {r['about']}**  \n{r['question']}")
                if r["steps"]:
                    st.markdown("".join(f'<div class="agent-trace">step {s["step"]} · <b>{s["tool"]}</b>'
                                        f'({", ".join(f"{k}={v}" for k, v in s["args"].items())})</div>' for s in r["steps"]),
                                unsafe_allow_html=True)
            md = "\n\n".join(f"**{r['time']} | {r['page']} | {r['about']}**\nQ: {r['question']}\nEngine: {r['engine']}, "
                             f"tools: {', '.join(s['tool'] for s in r['steps']) or 'none'}, {r['seconds']}s, {r['outcome']}" for r in log)
            st.download_button("⬇️ Download history", md.encode(), "finance_lens_agent_history.md", "text/markdown")
