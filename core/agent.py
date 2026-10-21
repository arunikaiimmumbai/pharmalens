"""Pha-inance Lens agent: LLM tool-use loop (free Gemini by default; Groq or Claude optional) over the curated dataset + live feeds.

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
from core import insights as I
from core import live as L

DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = """You are a financial analyst and senior strategy consultant (MBB / Big-4 strategy practice) specialising in Indian pharma.
You analyse six listed companies: Alembic, Ajanta, Ipca, Mankind, Alkem, Glenmark (consolidated, FY22–FY26 + Q1 FY27; INR crore).

How you work:
- ALWAYS ground numbers in tool results. Call tools before answering; never invent figures. If data is missing say so.
- Prefer comparisons vs peer median, 5-year trends and CAGRs. Connect financial metrics to news and regulatory events.
- Structure answers as: **Headline** (one line, the so-what) → **Evidence** (3–6 bullets with numbers) →
  **Implications / opportunities / risks** → **What to investigate next**. Use compact markdown tables when comparing.
- Be crisp, partner-ready, hypothesis-driven. Flag data caveats (e.g. Glenmark FY26 includes AbbVie licensing income;
  Mankind consolidates BSV from Oct-2024; Ipca consolidates Unichem from FY24).
- This is public-information analysis for an academic mentorship project; it is not investment advice, so never give buy/sell calls.
- Write in plain, simple English that a non-specialist can follow. Explain any technical term in a few words.
- Never use the em dash character. Use commas, colons or full stops instead.
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
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}, "live": {"type": "boolean", "default": True}}, "required": ["company"]}},
    {"name": "get_problem_statements", "description": "SWOT analysis (strengths, weaknesses, opportunities, threats), top-5 consultant problem statements (evidence, answer, what to investigate, service line), what is working / not working, digital maturity and consulting opportunities.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}}, "required": ["company"]}},
    {"name": "get_market_data", "description": "Live price (if reachable) plus 1-year return vs Nifty Pharma and the curated market snapshot (mcap, P/E, P/B).",
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
            return {k: c[k] for k in keys}

        if name == "get_financials":
            cid = resolve(args["company"])
            df = D.financial_frame(cid)
            m = [x for x in (args.get("metrics") or ["sales", "ebitda", "ebitda_margin", "pat", "roce", "roe", "employee_pct", "inventory_days", "cfo_pat", "borrowings"]) if x in df.columns]
            c = D.company(cid)
            return {"years": list(df.index), "series": {k: df[k].tolist() for k in m},
                    "quarterly": {"labels": D.meta()["quarters"], **c["quarterly"]}, "ttm": c.get("ttm"), "notes": c.get("data_notes")}

        if name == "compare_kpis":
            k = D.kpi_table(args.get("year", "FY26"))
            m = [x for x in args["metrics"] if x in k.columns]
            t = k[m]
            return {"table": t.round(2).to_dict(orient="index"), "peer_median": t.median(numeric_only=True).round(2).to_dict(),
                    "rank_1_is_best": {x: D.peer_rank(k, x).to_dict() for x in m if x in D.KPI_DEFS}}

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
            return {"insights": I.company_insights(cid), "pillar_scores_0_100": sc, "cross_company": I.cross_company_signals()}

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
            out = {"curated": cur.assign(date=cur["date"].dt.strftime("%Y-%m-%d"))[["date", "title", "category", "sentiment", "impact", "metrics", "url"]].to_dict(orient="records")}
            if args.get("live", True):
                live, err = L.fetch_news(q, days=180, limit=15)
                out["live"] = [] if live.empty else live.assign(date=live["date"].dt.strftime("%Y-%m-%d"))[["date", "title", "source", "sentiment", "category"]].to_dict(orient="records")
                if err:
                    out["live_error"] = err
            return out

        if name == "get_problem_statements":
            c = D.company(resolve(args["company"]))
            return {k: c[k] for k in ["swot", "working", "not_working", "problems", "digital", "consulting"]}

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
                    "current_mcap": D.company(cid)["market"]["mcap_cr"], "assumptions": args}

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


def run_agent(messages: list[dict], on_step=None, max_steps: int = 8) -> str:
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


def _run_openai_compatible(messages: list[dict], on_step=None, max_steps: int = 8) -> str:
    from openai import NotFoundError, OpenAI  # noqa: WPS433

    prov = get_provider() or "gemini"
    cfg = PROVIDERS[prov]
    client = OpenAI(api_key=get_api_key(), base_url=cfg["base_url"])
    convo = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in messages]
    model = get_model()
    for step in range(max_steps):
        try:
            resp = client.chat.completions.create(model=model, messages=convo, tools=OPENAI_TOOLS, tool_choice="auto", max_tokens=2500)
        except NotFoundError:
            alt = _pick_model(client, prov)
            if not alt or alt == model:
                raise
            model = alt
            st.session_state[f"_resolved_model_{prov}"] = alt
            resp = client.chat.completions.create(model=model, messages=convo, tools=OPENAI_TOOLS, tool_choice="auto", max_tokens=2500)
        msg = resp.choices[0].message
        calls = msg.tool_calls or []
        if not calls:
            return msg.content or ""
        convo.append({"role": "assistant", "content": msg.content or "",
                      "tool_calls": [{"id": tc.id, "type": "function",
                                      "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}} for tc in calls]})
        for tc in calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if on_step:
                on_step(step + 1, tc.function.name, args)
            out = _clean(run_tool(tc.function.name, args))
            convo.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out, default=str)[:24000]})
    return "I hit the step limit while researching. Try a narrower question."


def _run_anthropic(messages: list[dict], on_step=None, max_steps: int = 8) -> str:
    import anthropic  # noqa: WPS433

    client = anthropic.Anthropic(api_key=get_api_key())
    convo = [{"role": m["role"], "content": m["content"]} for m in messages]
    for step in range(max_steps):
        resp = client.messages.create(model=get_model(), max_tokens=2500, system=SYSTEM_PROMPT, tools=TOOLS, messages=convo)
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
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)[:24000]})
        convo.append({"role": "user", "content": results})
    return "I hit the step limit while researching. Try a narrower question."


# ── Offline analyst (no API key) ─────────────────────────────────────────────
def offline_answer(question: str, on_step=None) -> str:
    q = question.lower()
    hits = [c for c in D.companies() if c["short"].lower() in q or c["id"] in q]
    if not hits:
        hits = D.companies()
    lines = []
    if len(hits) > 1 or any(w in q for w in ("compare", "vs", "versus", "peer", "best", "rank")):
        metrics = ["sales_cagr", "ebitda_margin", "roce", "roe", "employee_pct", "inventory_days", "ccc", "cfo_pat", "de_ratio", "pe"]
        if on_step:
            on_step(1, "compare_kpis", {"metrics": metrics})
        k = D.kpi_table().loc[[c["short"] for c in hits], metrics]
        lines.append("**Headline:** peer comparison on growth, profitability, returns and cash (FY26).\n")
        hdr = "| Company | " + " | ".join(D.KPI_DEFS[m][0] for m in metrics) + " |"
        lines += [hdr, "|" + "---|" * (len(metrics) + 1)]
        for name, row in k.iterrows():
            lines.append(f"| {name} | " + " | ".join(D.fmt(m, row[m]) for m in metrics) + " |")
        lines.append("")
        for s in I.cross_company_signals()[:3]:
            lines.append(f"- {s}")
    for c in (hits if "swot" in q else (hits[:3] if len(hits) <= 3 else [])):
        if on_step:
            on_step(2, "get_insights", {"company": c["id"]})
        ins = I.company_insights(c["id"])
        lines.append(f"\n### {c['short']}\n*{c['tagline']}*")
        for lab, key in [("Growth", "growth"), ("Opportunities", "opportunity"), ("Risks", "risk")]:
            if ins[key]:
                lines.append(f"**{lab}**")
                lines += [f"- {x}" for x in ins[key][:4]]
        if any(w in q for w in ("problem", "consult", "opportun", "fix", "issue")):
            lines.append("**Top problem statements**")
            lines += [f"{i}. **{p['title']}**: {p['answer']}" for i, p in enumerate(c["problems"], 1)]
        if "swot" in q or "strength" in q or "threat" in q:
            lines.append("**SWOT**")
            for key, lab in [("strengths", "Strengths"), ("weaknesses", "Weaknesses"), ("opportunities", "Opportunities"), ("threats", "Threats")]:
                lines.append(f"*{lab}:* " + "; ".join(c["swot"][key]))
        if "news" in q:
            lines.append("**Recent news**")
            lines += [f"- {n['date']}: {n['title']}" for n in c["news"][:4]]
    lines.append("\n_Offline analyst mode (rule-based, free). Add a free Gemini API key (Settings → Secrets: GEMINI_API_KEY) to switch on the full reasoning agent._")
    return "\n".join(lines)
