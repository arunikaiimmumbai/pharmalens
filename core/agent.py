"""Finance Lens agent: LLM tool-use loop (free Gemini by default; Groq or Claude optional) over the curated dataset + live feeds.

The agent plans, calls tools (financials, KPI comparisons, correlations, news, scenarios),
reads the results and writes a consultant-grade answer. If no API key is configured the
OfflineAnalyst answers from the deterministic insight engine instead.
"""
from __future__ import annotations

import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st

from core import data as D
from core import glossary as G
from core import industry as IND
from core import insights as I
from core import live as L
from core import notes as N

DEFAULT_MODEL = "claude-sonnet-5-5"


def system_prompt() -> str:
    """System prompt for the active peer set."""
    m = D.meta()
    return SYSTEM_PROMPT.format(segment=D.segment_label(), names=D.SEGMENTS[D.segment()]["names"],
                                one_offs=m.get("one_offs", "check the data notes for acquisitions and one-off income."))

SYSTEM_PROMPT = """You are a financial analyst and senior strategy consultant specialising in Indian pharma.
You analyse six listed companies, the "{segment}" peer set: {names} (consolidated, FY22 to FY26 plus Q1 FY27; INR crore),
and compare them with the industry: the average of the 20 Nifty Pharma companies (tool get_industry_benchmark) and
published Indian pharma market growth (IQVIA, Pharmarack).

Rules:
- Be fast. The page context usually already contains the numbers: if it does, answer straight away without tools. Otherwise call at most 2 tools, together in one round if you can.
- Ground every number in tool results or the page context given to you. Call tools first; never invent figures or links.
- Explain WHY a number is what it is (business model, mix, one-offs, acquisitions, regulators, costs), not just that it is high or low.
- Always compare with the industry average and the other companies where it helps.
- Flag one-offs: {one_offs}
- Public-information analysis for an academic project: no buy/sell advice.
- Plain, simple English. Explain any technical term in a few words. Never use the em dash character.

Answer format: short and plain, under about 120 words, no headings.
Start with a one or two sentence summary that answers the question. Then 3 to 5 short bullet points covering, only where you
have the information: the calculation with the actual numbers, the reason behind it (compared with the industry), what the
company is already doing, and what more it or a consultant could do. Skip anything you don't have; never write "not available".
End with one line: Sources: followed by markdown links [title](url), taken ONLY from 'sources' fields in tool results or the page context.
"""

TOOLS = [
    {"name": "list_companies", "description": "List the six companies with ids, tickers and one-line positioning.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_company_profile", "description": "Profile & footprints (market, geography, manufacturing, R&D, therapy), regulatory/ANDA status, guidance, consensus, shareholding.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string", "description": "id or name, e.g. 'alkem'"}}, "required": ["company"]}},
    {"name": "get_financials", "description": "Five-year (FY22–FY26) series for one company. Metrics include sales, ebitda, pat, ebitda_margin, gross_margin, pat_margin, roce, roe, employee_pct, material_pct, indirect_pct, other_cost_pct, inventory_days, debtor_days, payable_days, ccc, wc_days, borrowings, de_ratio, debt_ebitda, interest_cover, cfo, cfo_pat, fcf_proxy, asset_turnover, fixed_asset_turnover, sales_growth, employee_growth, indirect_growth. Also returns quarterly (Q1 FY26–Q1 FY27).",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}, "metrics": {"type": "array", "items": {"type": "string"}}}, "required": ["company"]}},
    {"name": "compare_kpis", "description": "Cross-company KPI table for FY26 (or another year) with peer median and rank. Also accepts sales_cagr, ebitda_cagr, pat_cagr, pe, pb, ev_ebitda, mcap_cr, rnd_pct, us_share, india_share.",
     "input_schema": {"type": "object", "properties": {"metrics": {"type": "array", "items": {"type": "string"}}, "year": {"type": "string", "default": "FY26"}}, "required": ["metrics"]}},
    {"name": "correlate", "description": "Pearson correlation between two metrics. With a company: across its 5 years. Without: pooled 30 company-years. Also returns cost elasticity when x='sales'.",
     "input_schema": {"type": "object", "properties": {"x": {"type": "string"}, "y": {"type": "string"}, "company": {"type": "string"}}, "required": ["x", "y"]}},
    {"name": "get_insights", "description": "Rule-based growth / opportunity / risk insights vs peer median and financial pillar scores for one company.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}}, "required": ["company"]}},
    {"name": "get_news", "description": "Curated last-6-month news for a company (with KPI tags & impact) plus optional live Google News headlines. Use company='sector' for sector/policy news.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}, "live": {"type": "boolean", "default": False, "description": "true only if the user asks for the very latest headlines (slower)"}}, "required": ["company"]}},
    {"name": "get_problem_statements", "description": "SWOT analysis (strengths, weaknesses, opportunities, threats), top-5 consultant problem statements (evidence, answer, what to investigate, service line), what is working / not working, digital maturity and consulting opportunities.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}}, "required": ["company"]}},
    {"name": "get_market_data", "description": "Live price (if reachable) plus 1-year return vs Nifty Pharma and the curated market snapshot (mcap, P/E, P/B).",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}}, "required": ["company"]}},
    {"name": "get_industry_benchmark", "description": "Industry benchmark for a metric: average and median of the 20 Nifty Pharma companies, each member's value, plus published Indian pharma market growth (IQVIA/Pharmarack).",
     "input_schema": {"type": "object", "properties": {"metric": {"type": "string", "description": "e.g. ebitda_margin, roce, roic, inventory_days, sales_cagr"}, "year": {"type": "string", "default": "FY26"}}, "required": ["metric"]}},
    {"name": "get_brands_and_digital", "description": "Top brands and therapy areas ranked by market share or success, and the digitisation roadmap by area (score 1-5, what the company is doing, gap, consultant entry point), with sources.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}}, "required": ["company"]}},
    {"name": "run_scenario", "description": "Simple 2-year projection (FY27E, FY28E) from FY26 base given revenue growth % and EBITDA margin %; returns EBITDA and an EV implied at a given EV/EBITDA multiple.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}, "revenue_growth_pct": {"type": "number"}, "ebitda_margin_pct": {"type": "number"}, "ev_ebitda_multiple": {"type": "number", "default": 20}}, "required": ["company", "revenue_growth_pct", "ebitda_margin_pct"]}},
]


def resolve(company: str) -> str:
    q = (company or "").lower().strip()
    for c in D.companies():
        if q in (c["id"], c["short"].lower(), c["name"].lower()) or q in c["name"].lower() or c["id"] in q:
            return c["id"]
    raise ValueError(f"Unknown company '{company}'. Use one of: {', '.join(D.names())}")


def _clean(obj):
    if isinstance(obj, (np.floating, float)):
        return None if np.isnan(obj) else round(float(obj), 2)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def run_tool(name: str, args: dict) -> dict:
    try:
        if name == "list_companies":
            return {"companies": [{"id": c["id"], "name": c["name"], "ticker": c["ticker"], "tagline": c["tagline"]} for c in D.companies()]}

        if name == "get_company_profile":
            c = D.company(resolve(args["company"]))
            keys = ["name", "tagline", "profile", "market", "footprint", "regulatory", "guidance", "consensus", "data_notes"]
            return {**{k: c[k] for k in keys}, "sources": [N.screener(c["id"])] + c["brands"]["sources"]}

        if name == "get_financials":
            cid = resolve(args["company"])
            df = D.financial_frame(cid)
            m = [x for x in (args.get("metrics") or ["sales", "ebitda", "ebitda_margin", "pat", "roce", "roic", "roe", "employee_pct", "inventory_days", "cfo_pat", "fcf_margin", "net_debt_ebitda", "borrowings"]) if x in df.columns]
            c = D.company(cid)
            return {"years": list(df.index), "series": {k: df[k].tolist() for k in m},
                    "quarterly": {"labels": D.meta()["quarters"], **c["quarterly"]}, "ttm": c.get("ttm"), "notes": c.get("data_notes"),
                    "industry_average_FY26": {x: IND.industry_value(x)["avg"] for x in m},
                    "definitions": {x: G.tooltip(x) for x in m if G.tooltip(x)},
                    "analyst_notes": {th: N.company(cid, th)["text"] for th in ("growth", "margin", "returns", "wc", "cash", "cost") if N.company(cid, th)},
                    "sources": [N.screener(cid)]}

        if name == "compare_kpis":
            k = D.kpi_table(args.get("year", "FY26"))
            m = [x for x in args["metrics"] if x in k.columns]
            t = k[m]
            yr = args.get("year", "FY26")
            return {"table": t.round(2).to_dict(orient="index"), "peer_median": t.median(numeric_only=True).round(2).to_dict(),
                    "industry_average": {x: IND.industry_value(x, yr)["avg"] for x in m},
                    "rank_1_is_best": {x: D.peer_rank(k, x).to_dict() for x in m if x in D.KPI_DEFS},
                    "sources": [{"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"},
                                {"title": "Nifty Pharma constituents", "url": IND.meta()["constituents_source"]["url"]}]}

        if name == "correlate":
            x, y = args["x"], args["y"]
            if args.get("company"):
                cid = resolve(args["company"])
                df = D.financial_frame(cid)
                r = df[x].corr(df[y])
                out = {"scope": f"{D.company(cid)['short']} FY22–26 (n=5, directional only)", "r": r,
                       "x": df[x].round(2).tolist(), "y": df[y].round(2).tolist()}
                if x == "sales":
                    out["cost_elasticity"] = D.cost_elasticity(cid).round(2).to_dict(orient="records")
                return out
            pdf, r = D.pooled_correlation(x, y)
            return {"scope": "pooled 30 company-years", "r": r, "n": len(pdf)}

        if name == "get_insights":
            cid = resolve(args["company"])
            sc = I.pillar_scores().loc[D.company(cid)["short"]].to_dict()
            notes = {th: v["text"] for th, v in N._all()["company"].get(cid, {}).items()}
            srcs = [s for v in N._all()["company"].get(cid, {}).values() for s in v["sources"]]
            return {"insights": I.company_insights(cid), "pillar_scores_0_100": sc, "analyst_notes_why": notes,
                    "cross_company": I.cross_company_signals(), "sources": srcs[:8]}

        if name == "get_news":
            comp = args["company"]
            nd = D.all_news()
            if comp.lower() == "sector":
                cur = nd[nd["Company"] == "Sector"]
                q = "Indian pharma"
            else:
                cid = resolve(comp)
                cur = nd[nd["id"] == cid]
                q = D.company(cid)["name"]
            cols = [x for x in ["date", "title", "category", "sentiment", "impact", "metrics", "url", "statement_impact"] if x in cur.columns]
            out = {"curated": cur.assign(date=cur["date"].dt.strftime("%Y-%m-%d"))[cols].to_dict(orient="records"),
                   "sources": [{"title": t[:80], "url": u} for t, u in zip(cur["title"], cur["url"]) if isinstance(u, str) and u]}
            if args.get("live", False):
                live, err = L.fetch_news(q, days=180, limit=15)
                out["live"] = [] if live.empty else live.assign(date=live["date"].dt.strftime("%Y-%m-%d"))[["date", "title", "source", "sentiment", "category"]].to_dict(orient="records")
                if err:
                    out["live_error"] = err
            return out

        if name == "get_problem_statements":
            c = D.company(resolve(args["company"]))
            return {**{k: c[k] for k in ["swot", "working", "not_working", "problems", "digital", "consulting"]},
                    "sources": [N.screener(c["id"])] + [{"title": n["title"][:80], "url": n["url"]} for n in c["news"][:4]]}

        if name == "get_market_data":
            c = D.company(resolve(args["company"]))
            out = {"snapshot": c["market"]}
            q = L.fetch_quote(c["ticker"])
            if q:
                out["live_quote"] = q
            px, err = L.fetch_prices((c["ticker"],), "1y")
            if not px.empty and c["ticker"] in px:
                s = px[c["ticker"]].dropna()
                b = px[L.BENCHMARK].dropna()
                out["return_1y_%"] = (s.iloc[-1] / s.iloc[0] - 1) * 100
                out["nifty_pharma_1y_%"] = (b.iloc[-1] / b.iloc[0] - 1) * 100
            elif err:
                out["live_error"] = err
            return out

        if name == "get_industry_benchmark":
            metric, yr = args["metric"], args.get("year", "FY26")
            iv = IND.industry_value(metric, yr)
            vals = IND.member_values(metric, yr).dropna().round(2).sort_values(ascending=False)
            return {"metric": metric, "definition": G.tooltip(metric), "year": yr, "industry_average": iv["avg"], "industry_median": iv["median"],
                    "companies_counted": iv["n"], "member_values": vals.to_dict(), "method": IND.meta()["method"],
                    "market_growth": IND.market(),
                    "sources": [{"title": "Nifty Pharma constituents (5paisa, 22 Oct 2026)", "url": IND.meta()["constituents_source"]["url"]},
                                {"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"},
                                IND.market()[0]["source"]]}

        if name == "get_brands_and_digital":
            c = D.company(resolve(args["company"]))
            srcs = list(c["brands"]["sources"]) + [s for r in c["digital_roadmap"] for s in r["sources"]]
            return {"brands": c["brands"], "digital_roadmap": c["digital_roadmap"], "sources": srcs}

        if name == "run_scenario":
            cid = resolve(args["company"])
            df = D.financial_frame(cid)
            base = df["sales"].iloc[-1]
            g = args["revenue_growth_pct"] / 100
            m = args["ebitda_margin_pct"] / 100
            mult = args.get("ev_ebitda_multiple", 20)
            s27, s28 = base * (1 + g), base * (1 + g) ** 2
            e27, e28 = s27 * m, s28 * m
            net_debt = df["borrowings"].iloc[-1] - df["investments"].iloc[-1]
            return {"FY26_sales": base, "FY27E_sales": s27, "FY28E_sales": s28, "FY27E_ebitda": e27, "FY28E_ebitda": e28,
                    "implied_EV_on_FY28E": e28 * mult, "implied_equity_value": e28 * mult - net_debt,
                    "current_mcap": D.company(cid)["market"]["mcap_cr"], "assumptions": args, "sources": [N.screener(cid)]}

        return {"error": f"unknown tool {name}"}
    except Exception as e:  # tool errors go back to the model, not the user
        return {"error": str(e)}


def _secret(name: str) -> str | None:
    try:
        v = st.secrets.get(name)
    except Exception:
        v = None
    return v or os.environ.get(name)


# Free-first provider order. Gemini (Google AI Studio) has a free tier with tool calling;
# Groq has a free tier too; Anthropic is optional and paid.
PROVIDERS = {
    "gemini": {"label": "Google Gemini (free tier)", "key": "GEMINI_API_KEY", "model_key": "GEMINI_MODEL",
               "default_model": "gemini-3.8-flash", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"},
    "groq": {"label": "Groq (free tier)", "key": "GROQ_API_KEY", "model_key": "GROQ_MODEL",
             "default_model": "llama-3.3-70b-versatile", "base_url": "https://api.groq.com/openai/v1"},
    "anthropic": {"label": "Anthropic Claude (paid)", "key": "ANTHROPIC_API_KEY", "model_key": "ANTHROPIC_MODEL",
                  "default_model": DEFAULT_MODEL, "base_url": None},
}


def get_provider() -> str | None:
    """First provider with a key: secrets/env first, then a key typed in the sidebar (treated as Gemini)."""
    for name, cfg in PROVIDERS.items():
        if _secret(cfg["key"]):
            return name
    if st.session_state.get("user_api_key"):
        return "gemini"
    return None


def get_api_key() -> str | None:
    prov = get_provider()
    if not prov:
        return None
    return _secret(PROVIDERS[prov]["key"]) or st.session_state.get("user_api_key")


def get_model() -> str:
    prov = get_provider() or "gemini"
    cfg = PROVIDERS[prov]
    return st.session_state.get(f"_resolved_model_{prov}") or _secret(cfg["model_key"]) or cfg["default_model"]


def provider_label() -> str:
    prov = get_provider()
    return PROVIDERS[prov]["label"] if prov else "offline"


def _no_em_dash(text: str) -> str:
    """House style: no em dashes in anything shown to the user."""
    return re.sub(r"\s*\u2014\s*", ", ", text or "")


def run_agent(messages: list[dict], on_step=None, max_steps: int = 4) -> str:
    """Agentic loop over the configured provider. `messages` = [{role, content}] (strings)."""
    if get_provider() == "anthropic":
        return _no_em_dash(_run_anthropic(messages, on_step, max_steps))
    return _no_em_dash(_run_openai_compatible(messages, on_step, max_steps))


def _gemini_safe(schema: dict) -> dict:
    """Gemini rejects 'default' keys and objects with no properties; strip/patch them."""
    if isinstance(schema, dict):
        out = {k: _gemini_safe(v) for k, v in schema.items() if k != "default"}
        if out.get("type") == "object" and not out.get("properties"):
            out["properties"] = {"note": {"type": "string", "description": "Optional; leave empty."}}
        return out
    if isinstance(schema, list):
        return [_gemini_safe(x) for x in schema]
    return schema


OPENAI_TOOLS = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                  "parameters": _gemini_safe(t["input_schema"])}}
                for t in TOOLS]


def friendly_error(e: Exception) -> str:
    """Plain-English reason for an AI failure, shown under the offline answer."""
    msg = str(e)
    low = msg.lower()
    code = getattr(e, "status_code", None)
    if code in (401, 403) or "api key" in low or "permission" in low or "unauthenticated" in low:
        return "the AI key was rejected. Check GEMINI_API_KEY in Streamlit Secrets (no spaces, inside quotes)."
    if code == 429 or "quota" in low or "rate" in low or "exhausted" in low:
        return "the free AI quota is used up for now. Wait a minute (or until tomorrow for the daily limit) and ask again."
    if code == 404 or "not found" in low:
        return "the AI model name wasn't found. Set GEMINI_MODEL in Secrets to a model listed in Google AI Studio."
    if code == 400:
        return f"the AI service rejected the request ({msg[:160]})."
    return f"the AI service couldn't be reached ({msg[:160]})."


def _pick_model(client, prov: str) -> str | None:
    """If the configured model name is unavailable, choose a suitable one from the provider's live model list."""
    try:
        ids = [m.id.replace("models/", "") for m in client.models.list()]
    except Exception:
        return None
    if prov == "gemini":
        good = [i for i in ids if "flash" in i and not any(x in i for x in ("lite", "tts", "live", "image", "embedding", "transcribe", "translate", "preview"))]
        good = good or [i for i in ids if "flash" in i and not any(x in i for x in ("tts", "live", "image", "embedding"))]
    else:
        good = [i for i in ids if any(x in i for x in ("llama", "gpt-oss", "qwen", "kimi")) and "guard" not in i and "whisper" not in i]
    return sorted(good, reverse=True)[0] if good else None


def _run_openai_compatible(messages: list[dict], on_step=None, max_steps: int = 4) -> str:
    from openai import BadRequestError, NotFoundError, OpenAI  # noqa: WPS433

    prov = get_provider() or "gemini"
    cfg = PROVIDERS[prov]
    client = OpenAI(api_key=get_api_key(), base_url=cfg["base_url"])
    convo = [{"role": "system", "content": system_prompt()}] + [{"role": m["role"], "content": m["content"]} for m in messages]
    model = get_model()
    def call(choice: str):
        kw = dict(model=model, messages=convo, tools=OPENAI_TOOLS, tool_choice=choice, max_tokens=1000)
        if prov == "gemini" and not st.session_state.get("_no_reasoning_param"):
            try:
                return client.chat.completions.create(**kw, extra_body={"reasoning_effort": "low"})
            except BadRequestError:
                st.session_state["_no_reasoning_param"] = True  # model doesn't accept it; don't try again
        return client.chat.completions.create(**kw)

    for step in range(max_steps):
        choice = "none" if step == max_steps - 1 else "auto"  # last round must answer, not research
        try:
            try:
                resp = call(choice)
            except BadRequestError:
                if choice != "none":
                    raise
                resp = call("auto")  # provider doesn't accept tool_choice='none'
        except NotFoundError:
            alt = _pick_model(client, prov)
            if not alt or alt == model:
                raise
            model = alt
            st.session_state[f"_resolved_model_{prov}"] = alt
            resp = call(choice)
        msg = resp.choices[0].message
        calls = msg.tool_calls or []
        if not calls:
            return msg.content or ""
        # Send the assistant turn back exactly as received: Gemini attaches a 'thought_signature' to each tool
        # call (in extra_content) and rejects the next request if it is missing.
        turn = msg.model_dump(exclude_none=True)
        turn["role"] = "assistant"
        turn.setdefault("content", "")
        convo.append(turn)
        for tc in calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if on_step:
                on_step(step + 1, tc.function.name, args)
            out = _clean(run_tool(tc.function.name, args))
            convo.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out, default=str)[:7000]})
    return "I hit the step limit while researching. Try a narrower question."


def _run_anthropic(messages: list[dict], on_step=None, max_steps: int = 4) -> str:
    import anthropic  # noqa: WPS433

    client = anthropic.Anthropic(api_key=get_api_key())
    convo = [{"role": m["role"], "content": m["content"]} for m in messages]
    for step in range(max_steps):
        resp = client.messages.create(model=get_model(), max_tokens=1000, system=system_prompt(), tools=TOOLS, messages=convo)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")
        blocks = []
        for b in resp.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        convo.append({"role": "assistant", "content": blocks})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                if on_step:
                    on_step(step + 1, b.name, b.input)
                out = _clean(run_tool(b.name, b.input))
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)[:7000]})
        convo.append({"role": "user", "content": results})
    return "I hit the step limit while researching. Try a narrower question."


# ── Offline analyst (no API key) ─────────────────────────────────────────────
THEME_WORDS = {
    "growth": ("growth", "launch", "revenue"), "margin": ("margin", "cost", "r&d"), "returns": ("roce", "capital", "plant", "return"),
    "wc": ("inventory", "receivable", "working", "collection", "debtor"), "cash": ("cash", "dividend", "receivable"),
    "cost": ("cost", "rep", "employee", "people"), "debt": ("debt", "borrow", "pledge"), "geo": ("us ", "us-", "tariff", "export"),
    "brands": ("brand", "share", "therapy", "chronic"), "rnd": ("r&d", "plant", "fda", "filing"), "quarter": ("q1", "quarter"),
}


def _match_news(c: dict, theme: str | None):
    words = THEME_WORDS.get(theme or "", ())
    for n_ in sorted(c["news"], key=lambda x: x["date"], reverse=True):
        imp = n_.get("statement_impact") or {}
        blob = " ".join([n_["title"], n_.get("impact", ""), imp.get("doing", "")]).lower()
        if not words or any(w in blob for w in words):
            return n_
    return None


def _match_problem(c: dict, theme: str | None):
    words = THEME_WORDS.get(theme or "", ())
    for p in c["problems"]:
        blob = (p["title"] + " " + p["evidence"]).lower()
        if any(w in blob for w in words):
            return p
    return c["problems"][0]


def _links(sources: list[dict]) -> str:
    seen, out = set(), []
    for s_ in sources:
        if s_ and s_.get("url") and s_["url"] not in seen:
            seen.add(s_["url"])
            out.append(f"[{s_['title']}]({s_['url']})")
    return " · ".join(out) if out else "Screener.in and company filings"


def structured_answer(item: dict, question: str = "") -> str:
    """Short answer from the data behind one chart or text: a summary, then key points; missing parts are skipped."""
    cid, metric, theme = item.get("company"), item.get("metric"), item.get("theme")
    c = D.company(cid) if cid else None
    note = item.get("note") or {}
    sources = list(note.get("sources") or [])
    text = note.get("text", "")
    first = text.split(". ")
    summary = ". ".join(first[:2]).rstrip(".") + "." if text else (item.get("facts") or item.get("title", question))
    points = []
    if metric and G.formula(metric):
        calc = G.formula(metric)
        if item.get("facts"):
            calc += f". {item['facts'][:220].rstrip('.')}."
        points.append(f"How it's calculated: {calc}")
    if metric and metric in IND.BENCHMARKABLE:
        iv = IND.industry_value(metric)
        if iv["avg"] is not None:
            points.append(f"Industry (20 Nifty Pharma companies): average {D.fmt(metric, iv['avg'])}, median {D.fmt(metric, iv['median'])}")
    if len(first) > 2:
        points.append(". ".join(first[2:]).rstrip("."))
    if note.get("doing"):
        points.append(f"Already doing: {note['doing']}")
    if note.get("angle"):
        points.append(f"Where a consultant can help: {note['angle']}")
    if c:
        p = _match_problem(c, theme)
        points.append(f"What more to do: {p['answer'].split('. ')[0].rstrip('.')}")
    body = summary + "\n\n" + "\n".join(f"- {p}" for p in points[:5])
    return body + f"\n\nSources: {_links(sources)}"


def offline_answer(question: str, on_step=None, item: dict | None = None) -> str:
    if item and item.get("kind") != "page":
        if on_step:
            on_step(1, "read_chart_data", {"item": item.get("title", "")})
        return structured_answer(item, question)
    q = question.lower()
    hits = [c for c in D.companies() if c["short"].lower() in q or c["id"] in q]
    if not hits:
        hits = D.companies()
    lines = []
    srcs = []
    if len(hits) > 1 or any(w in q for w in ("compare", "vs", "versus", "peer", "best", "rank")):
        metrics = ["sales_cagr", "ebitda_margin", "roce", "roic", "employee_pct", "inventory_days", "ccc", "cfo_pat", "net_debt_ebitda"]
        if on_step:
            on_step(1, "compare_kpis", {"metrics": metrics})
        k = D.kpi_table().loc[[c["short"] for c in hits], metrics]
        lines.append("**What it's checking:** growth, profitability, returns and cash across the companies (FY26), against the industry.\n")
        hdr = "| Company | " + " | ".join(D.KPI_DEFS[m][0] for m in metrics) + " |"
        lines += [hdr, "|" + "---|" * (len(metrics) + 1)]
        for name, row in k.iterrows():
            lines.append(f"| {name} | " + " | ".join(D.fmt(m, row[m]) for m in metrics) + " |")
        lines.append("| **Industry avg** | " + " | ".join(D.fmt(m, IND.industry_value(m)["avg"]) for m in metrics) + " |")
        lines.append("\n**What it means:**")
        for s_ in I.cross_company_signals()[:3]:
            lines.append(f"- {s_}")
        srcs += [{"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"},
                 {"title": "Nifty Pharma constituents", "url": IND.meta()["constituents_source"]["url"]}]
    for c in (hits if len(hits) <= 3 else []):
        if on_step:
            on_step(2, "get_insights", {"company": c["id"]})
        theme = next((t for t, ws in THEME_WORDS.items() if any(w.strip() in q for w in ws)), "margin")
        note = N.company(c["id"], theme) or N.company(c["id"], "margin")
        lines.append(f"\n### {c['short']}")
        lines.append(structured_answer({"title": question, "company": c["id"], "theme": theme, "note": note,
                                        "facts": ""}, question))
    if srcs:
        lines.append(f"\n**Sources:** {_links(srcs)}")
    lines.append("\n_Offline analyst mode (rule-based, free). Add a free Gemini API key (Secrets: GEMINI_API_KEY) for the full reasoning agent._")
    return "\n".join(lines)
