"""'Ask the analyst' side panel, available on every page.

1. Pick what to ask about: any chart or text registered by the current page (or the whole page).
2. Click a suggested question or type your own.
3. While it works you see each step live, and the answer streams in as it is written.
4. Answers are short (summary + key points), can include charts, end with source links, and carry an automatic
   number check. Repeat questions are answered instantly from a shared cache.
5. 'Agent history' lists every question, the tools used, time taken, outcome and your 👍/👎 rating.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from core import agent as A
from core import agent_extras as AX
from core import data as D
from core import industry as IND

WHOLE_PAGE = "This whole page"
KEY_METRICS = ["sales_cagr", "ebitda_margin", "roce", "roic", "employee_pct", "material_pct", "inventory_days", "debtor_days", "ccc",
               "cfo_pat", "net_debt_ebitda", "pe"]


def _suggestions(item: dict | None) -> list[str]:
    if not item:
        return ["Summarise what this page tells me in plain English.",
                "Compare the six on EBITDA margin and ROCE, with a chart.",
                "Where could a consultant add the most value, and what is it worth?"]
    t = item["title"]
    if item.get("company"):
        short = D.company(item["company"])["short"]
        return [f"Why does {t} look like this?",
                f"How does {short} compare with the industry and the other five? Show a chart.",
                f"What is the size of the prize if {short} reached the industry median on its weakest cost or working-capital metric?"]
    return [f"What is the main takeaway from {t}?",
            f"Which company stands out in {t}, and why?",
            f"What does {t} mean for a consulting pitch?"]


def _key_numbers(item: dict | None) -> str:
    """Pre-packed numbers so most questions need no tool call at all."""
    k = D.kpi_table()
    ind = {m: IND.industry_value(m)["avg"] for m in KEY_METRICS}
    if item and item.get("company"):
        sh = D.company(item["company"])["short"]
        if sh not in k.index:
            return ""
        r = k.loc[sh]
        parts = [f"{D.KPI_DEFS[m][0]} {D.fmt(m, r[m])}" + (f" (industry {D.fmt(m, ind[m])})" if ind[m] is not None else "")
                 for m in KEY_METRICS if m in r.index]
        return f"Key FY26 numbers for {sh}: " + "; ".join(parts) + "."
    cols = ["sales_cagr", "ebitda_margin", "roce", "inventory_days", "ccc", "cfo_pat"]
    rows = [f"{n}: " + ", ".join(f"{D.KPI_DEFS[m][0]} {D.fmt(m, r[m])}" for m in cols) for n, r in k.iterrows()]
    rows.append("Industry: " + ", ".join(f"{D.KPI_DEFS[m][0]} {D.fmt(m, ind.get(m) or IND.industry_value(m)['avg'])}" for m in cols))
    return "Key FY26 numbers (" + D.segment_label() + "): " + " | ".join(rows) + "."


def _context(item: dict | None, page: str) -> str:
    keys = _key_numbers(item)
    if not item:
        items = st.session_state.get("_items", [])
        return f"[Page context] Page: {page}. Peer set: {D.segment_label()}. Items on this page: " + "; ".join(i["title"] for i in items[:20]) + f". {keys}"
    note = item.get("note") or {}
    srcs = "; ".join(f"{s['title']}: {s['url']}" for s in note.get("sources", []))
    who = f" Company id: {item['company']}." if item.get("company") else ""
    met = f" Metric key: {item['metric']}." if item.get("metric") else ""
    return (f"[Page context] Page: {page}. Peer set: {D.segment_label()}. The user is asking about: {item['title']}.{who}{met} "
            f"Data shown: {item.get('facts', '')} {keys} Analyst note: {note.get('text', '')} "
            f"What the company is already doing: {note.get('doing', 'not recorded')}. "
            f"Where a consultant can help: {note.get('angle') or 'not recorded'}. Sources available: {srcs}")


def _rate(aid: str) -> None:
    val = st.session_state.get(f"fb_{aid}")
    for r in st.session_state.get("agent_log", []):
        if r.get("id") == aid:
            r["rating"] = {1: "👍", 0: "👎"}.get(val, "")


def _ask(question: str, item: dict | None, page: str, live) -> None:
    log = st.session_state.setdefault("agent_log", [])
    chat = st.session_state.setdefault("panel_chat", [])
    steps: list[dict] = []
    aid = uuid.uuid4().hex[:10]
    t0 = time.time()
    has_ai = bool(A.get_api_key())
    ctx = _context(item, page)
    words = question.lower().split()
    follow_up = len(words) <= 5 or (bool(words) and words[0] in ("and", "also"))
    prev = chat[-2]["content"] if len(chat) >= 2 and follow_up else ""  # short follow-ups ("and Cipla?") depend on the last question
    key = AX.cache_key(question, item["title"] if item else WHOLE_PAGE, ((item or {}).get("facts", "") + "|" + prev),
                       A.get_model() if has_ai else "offline")
    hit = AX.cache_get(key)
    outcome, engine, cached = "answered", A.provider_label() if has_ai else "Offline analyst", False
    if hit:
        ans, charts, chk, engine, cached = hit["answer"], hit.get("charts", []), hit.get("check"), hit.get("engine", engine), True
        outcome = "instant (saved answer)"
    else:
        with live.container():
            status = st.status("Analyst is working…", expanded=True)
            text_ph = st.empty()
        buf = {"t": ""}

        def on_step(step, tool, args):
            steps.append({"step": step, "tool": tool, "args": args})
            status.write(f"• {AX.step_label(tool, args)}")

        def on_text(delta):
            if delta is None:
                buf["t"] = ""
                text_ph.empty()
                return
            buf["t"] += delta
            text_ph.markdown(buf["t"] + " ▌")

        run = {"charts": [], "evidence": [ctx, question]}
        chk = None
        try:
            if has_ai:
                history = [{"role": m["role"], "content": m["content"]} for m in chat[-6:]]
                msgs = history + [{"role": "user", "content": f"{question}\n\n{ctx}"}]
                ans = A.run_agent(msgs, on_step=on_step, on_text=on_text, run=run)
                engine = run.get("engine", engine)
                chk = AX.verify_numbers(ans, run["evidence"])
            else:
                ans = A.offline_answer(question, on_step=on_step, item=item)
        except Exception as e:  # fall back, explain in plain English
            outcome = "fell back to offline analyst"
            ans = A.offline_answer(question, on_step=on_step, item=item) + f"\n\n> The AI couldn't answer, so this reply comes from the offline analyst. Reason: {A.friendly_error(e)}"
        charts = run["charts"]
        status.update(label=f"Done in {time.time() - t0:.1f}s · {len(steps)} step{'s' if len(steps) != 1 else ''}", state="complete", expanded=False)
        live.empty()
        if has_ai and outcome == "answered":
            AX.cache_put(key, {"answer": ans, "charts": charts, "check": chk, "engine": engine})
    secs = time.time() - t0
    chat += [{"role": "user", "content": question},
             {"role": "assistant", "content": ans, "id": aid, "charts": charts, "check": chk, "engine": engine, "secs": round(secs, 1),
              "tools": len(steps), "cached": cached}]
    log.append({"id": aid, "time": datetime.now().strftime("%H:%M:%S"), "page": page, "about": item["title"] if item else WHOLE_PAGE,
                "question": question, "engine": engine, "tools_used": len(steps), "seconds": round(secs, 1),
                "outcome": outcome, "number_check": AX.check_caption(chk)[:2] if chk else "", "rating": "", "steps": steps})


@st.fragment
def render() -> None:
    """Runs as a fragment: asking a question reruns only this panel, not the whole page."""
    page = st.session_state.get("_page", "")
    items = st.session_state.get("_items", [])
    st.markdown('<div class="panelhead"><b>🤖 Ask the analyst</b><div class="muted">Pick a chart or text on this page, then click a '
                'question or type your own. It can compare, chart, calculate, read a linked report and search the web. '
                'Answers cite their sources.</div></div>', unsafe_allow_html=True)

    titles = [WHOLE_PAGE] + [i["title"] for i in items]
    want = st.session_state.pop("panel_item", None)
    if want in titles:
        st.session_state["panel_pick"] = want
    if st.session_state.get("panel_pick") not in titles:
        st.session_state["panel_pick"] = WHOLE_PAGE
    pick = st.selectbox("What do you want to ask about?", titles, key="panel_pick")
    item = next((i for i in items if i["title"] == pick), None)

    live = st.empty()  # live progress and streaming text appear here
    st.markdown('<div class="muted" style="font-size:.78rem;margin-top:4px">Suggested questions</div>', unsafe_allow_html=True)
    for j, q in enumerate(_suggestions(item)):
        if st.button(q, key=f"sugg_{pick}_{j}", use_container_width=True):
            _ask(q, item, page, live)

    with st.form("panel_form", clear_on_submit=True, border=False):
        q = st.text_area("Or type your own question", height=80,
                         placeholder="e.g. Why is this lower than the industry? · Compare Alkem and Cipla on margin · Read <link> and summarise the US business")
        if st.form_submit_button("Ask", type="primary", use_container_width=True) and q.strip():
            _ask(q.strip(), item, page, live)

    chat = st.session_state.get("panel_chat", [])
    if chat:
        box = st.container(height=560)
        pairs = [(chat[i], chat[i + 1]) for i in range(0, len(chat) - 1, 2)]
        with box:
            for qq, aa in reversed(pairs):
                st.markdown(f'<div class="q">❓ {qq["content"]}</div>', unsafe_allow_html=True)
                st.markdown(aa["content"])
                for j, spec in enumerate(aa.get("charts") or []):
                    try:
                        AX.render_chart(spec, key=f"ch_{aa.get('id', '')}_{j}")
                    except Exception:
                        st.caption("The chart could not be drawn.")
                cap = AX.check_caption(aa.get("check"))
                if cap:
                    st.caption(cap)
                meta = []
                if aa.get("cached"):
                    meta.append("⚡ instant (saved answer)")
                if aa.get("secs") is not None and not aa.get("cached"):
                    meta.append(f"{aa['secs']}s")
                if aa.get("tools"):
                    meta.append(f"{aa['tools']} tool{'s' if aa['tools'] != 1 else ''}")
                if aa.get("engine"):
                    meta.append(aa["engine"])
                if meta:
                    st.caption(" · ".join(meta))
                if aa.get("id"):
                    st.feedback("thumbs", key=f"fb_{aa['id']}", on_change=_rate, args=(aa["id"],))
                st.markdown("---")
        if st.button("🧹 Clear answers", use_container_width=True):
            st.session_state["panel_chat"] = []
            st.rerun(scope="fragment")

    log = st.session_state.get("agent_log", [])
    with st.expander(f"🕘 Agent history ({len(log)})"):
        if not log:
            st.caption("Every question you ask is listed here with the tools the agent used, the time it took and your rating.")
        else:
            df = pd.DataFrame([{k: v for k, v in r.items() if k not in ("steps", "id")} for r in reversed(log)])
            st.dataframe(df, hide_index=True, use_container_width=True)
            for r in reversed(log[-10:]):
                st.markdown(f"**{r['time']} · {r['about']}** {r.get('rating', '')}  \n{r['question']}")
                if r["steps"]:
                    st.markdown("".join(f'<div class="agent-trace">step {s["step"]} · <b>{s["tool"]}</b>'
                                        f'({", ".join(f"{k}={v}" for k, v in s["args"].items())})</div>' for s in r["steps"]),
                                unsafe_allow_html=True)
            md = "\n\n".join(f"**{r['time']} | {r['page']} | {r['about']}**\nQ: {r['question']}\nEngine: {r['engine']}, "
                             f"tools: {', '.join(s['tool'] for s in r['steps']) or 'none'}, {r['seconds']}s, {r['outcome']}"
                             f"{', rating ' + r['rating'] if r.get('rating') else ''}" for r in log)
            st.download_button("⬇️ Download history", md.encode(), "finance_lens_agent_history.md", "text/markdown")
