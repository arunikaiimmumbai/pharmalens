"""Finance Lens agent: LLM tool-use loop (free Gemini by default; Groq or Claude optional) over the curated dataset + live feeds.

The agent plans, calls tools (financials, KPI comparisons, correlations, news, scenarios),
reads the results and writes a consultant-grade answer. If no API key is configured the
OfflineAnalyst answers from the deterministic insight engine instead.
"""
from __future__ import annotations

import json
import os
import re
import threading

import numpy as np
import pandas as pd
import streamlit as st

from core import data as D
from core import glossary as G
from core import industry as IND
from core import insights as I
from core import live as L
from core import notes as N
from core import agent_extras as AX

DEFAULT_MODEL = "claude-sonnet-5-5"


def system_prompt() -> str:
    """System prompt for the active peer set."""
    m = D.meta()
    others = "; ".join(f"{D.SEGMENTS[k]['label']}: {D.SEGMENTS[k]['names']}" for k in D.available_segments() if k != D.segment())
    return SYSTEM_PROMPT.format(segment=D.segment_label(), names=D.SEGMENTS[D.segment()]["names"], others=others or "none",
                                one_offs=m.get("one_offs", "check the data notes for acquisitions and one-off income."))

SYSTEM_PROMPT = """You are a financial analyst and senior strategy consultant specialising in Indian pharma.
You analyse six listed companies, the "{segment}" peer set: {names} (consolidated, FY22 to FY26 plus Q1 FY27; INR crore),
and compare them with the industry: the average of the 20 Nifty Pharma companies (tool get_industry_benchmark) and
published Indian pharma market growth (IQVIA, Pharmarack).

You can also answer about the other peer set ({others}); tools accept any of these company names.

Rules:
- Be fast. The page context already contains the chart's numbers and the company's key ratios with the industry average: if that is enough, answer straight away without tools. Otherwise call the tools you need together in one round (they run in parallel).
- Use calculate for any arithmetic, and for 'size of the prize' questions (cash released or extra EBITDA if a metric reached the industry median, average, best peer or a target).
- When the user asks to compare, show, plot, chart or rank, call make_chart (and mention the chart in one line).
- Use search_web ONLY when the app's data and tools cannot answer: very recent events, facts outside the app, or companies not in the app. Mark every web fact with "(web)" and cite its link.
- When the user gives a link to a report, results or web page, call read_document and quote page numbers.
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
    {"name": "list_companies", "description": "List the companies of both peer sets with ids, tickers, peer set and one-line positioning.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_company_profile", "description": "Profile & footprints (market, geography, manufacturing, R&D, therapy), regulatory/ANDA status, guidance, consensus, shareholding.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string", "description": "id or name, e.g. 'alkem'"}}, "required": ["company"]}},
    {"name": "get_financials", "description": "Five-year (FY22–FY26) series for one company. Metrics include sales, ebitda, pat, ebitda_margin, gross_margin, pat_margin, roce, roe, employee_pct, material_pct, indirect_pct, other_cost_pct, inventory_days, debtor_days, payable_days, ccc, wc_days, borrowings, de_ratio, debt_ebitda, interest_cover, cfo, cfo_pat, fcf_proxy, asset_turnover, fixed_asset_turnover, sales_growth, employee_growth, indirect_growth. Also returns quarterly (Q1 FY26–Q1 FY27).",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}, "metrics": {"type": "array", "items": {"type": "string"}}}, "required": ["company"]}},
    {"name": "compare_kpis", "description": "Cross-company KPI table for FY26 (or another year) with peer median and rank. Also accepts sales_cagr, ebitda_cagr, pat_cagr, pe, pb, ev_ebitda, mcap_cr, rnd_pct, us_share, india_share.",
     "input_schema": {"type": "object", "properties": {"metrics": {"type": "array", "items": {"type": "string"}}, "year": {"type": "string", "default": "FY26"},
                                                     "companies": {"type": "array", "items": {"type": "string"}, "description": "optional; may mix both peer sets"}}, "required": ["metrics"]}},
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
    {"name": "search_web", "description": "Free web search (Google Search via Gemini, or DuckDuckGo). Use only when the app's data cannot answer: very recent news, facts outside the app, or other companies. Results are labelled as web results.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "a specific search query, e.g. 'Cipla Q2 FY27 results October 2026'"}}, "required": ["query"]}},
    {"name": "read_document", "description": "Open a public link (annual report PDF, results release, investor presentation or web page) and return the passages most relevant to the question, with page numbers.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}, "question": {"type": "string", "description": "what to look for in the document"}}, "required": ["url"]}},
    {"name": "calculate", "description": "Calculator. Either give 'expression' (arithmetic only, e.g. '(462-282)/365*2330'), or give company + metric (+ target) for the size of the prize: cash released (inventory_days, debtor_days, payable_days) or extra EBITDA per year (employee_pct, material_pct, indirect_pct, other_cost_pct, manufacturing_pct, ebitda_margin) if the company reached the target. target: industry_median (default), industry_average, best_peer, or a number.",
     "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}, "company": {"type": "string"}, "metric": {"type": "string"},
                                                     "target": {"type": "string", "description": "industry_median, industry_average, best_peer or a number"}}}},
    {"name": "make_chart", "description": "Draw a chart in the answer. mode 'snapshot' = one bar per company for FY26 (with the industry line); mode 'trend' = FY22 to FY26 lines. companies: list of names, or ['all'] for the current peer set; names from the other peer set are allowed.",
     "input_schema": {"type": "object", "properties": {"metric": {"type": "string", "description": "e.g. ebitda_margin, roce, inventory_days, ccc, employee_pct, sales_cagr"},
                                                     "companies": {"type": "array", "items": {"type": "string"}},
                                                     "mode": {"type": "string", "enum": ["snapshot", "trend"]},
                                                     "include_industry": {"type": "boolean"}}, "required": ["metric"]}},
    {"name": "run_scenario", "description": "Simple 2-year projection (FY27E, FY28E) from FY26 base given revenue growth % and EBITDA margin %; returns EBITDA and an EV implied at a given EV/EBITDA multiple.",
     "input_schema": {"type": "object", "properties": {"company": {"type": "string"}, "revenue_growth_pct": {"type": "number"}, "ebitda_margin_pct": {"type": "number"}, "ev_ebitda_multiple": {"type": "number", "default": 20}}, "required": ["company", "revenue_growth_pct", "ebitda_margin_pct"]}},
]


def resolve(company: str) -> str:
    """Company id from a name or id; searches the current peer set first, then the other set."""
    q = (company or "").lower().strip().replace("’", "'")
    if not q:
        raise ValueError("No company given.")
    for c in D.all_companies():
        if q in (c["id"], c["short"].lower(), c["name"].lower()) or q in c["name"].lower() or c["id"] in q \
                or c["short"].lower().replace("'", "") in q.replace("'", ""):
            return c["id"]
    raise ValueError(f"Unknown company '{company}'. Use one of: {', '.join(c['short'] for c in D.all_companies())}")


def _resolve_many(names) -> list[str]:
    if not names or any(str(n).lower() in ("all", "all six", "everyone") for n in names):
        return [c["id"] for c in D.companies()]
    out = []
    for n in names:
        try:
            cid = resolve(str(n))
        except ValueError:
            continue
        if cid not in out:
            out.append(cid)
    return out or [c["id"] for c in D.companies()]


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


def _web_key() -> tuple[str | None, str | None]:
    """Gemini key for web search (works even when Groq or Claude answer)."""
    key = _secret("GEMINI_API_KEY") or (st.session_state.get("user_api_key") if get_provider() == "gemini" else None)
    model = st.session_state.get("_resolved_model_gemini") or _secret("GEMINI_MODEL") or PROVIDERS["gemini"]["default_model"]
    return key, model


def run_tool(name: str, args: dict, run: dict | None = None) -> dict:
    try:
        if name == "list_companies":
            return {"companies": [{"id": c["id"], "name": c["name"], "ticker": c["ticker"], "peer_set": D.segment_label(D.segment_of(c["id"])),
                                   "tagline": c["tagline"]} for c in D.all_companies()]}

        if name == "search_web":
            key, model = _web_key()
            return AX.search_web(args.get("query", ""), api_key=key, model=model, provider="gemini" if key else None)

        if name == "read_document":
            return AX.read_document(args.get("url", ""), args.get("question", ""))

        if name == "calculate":
            if args.get("expression"):
                return {"expression": args["expression"], "result": round(AX.safe_eval(args["expression"]), 4)}
            cid = resolve(args.get("company", ""))
            tgt = args.get("target") or "industry_median"
            try:
                tgt = float(tgt)
            except (TypeError, ValueError):
                pass
            return AX.size_of_prize(cid, args.get("metric", ""), tgt)

        if name == "make_chart":
            cids = _resolve_many(args.get("companies"))
            spec = AX.chart_spec(args.get("metric", "ebitda_margin"), cids, args.get("mode") or "snapshot",
                                 args.get("include_industry", True) is not False)
            if run is not None:
                run.setdefault("charts", []).append(spec)
            return {"chart": "drawn under the answer", "data": spec.get("values") or spec.get("series"), "industry": spec.get("industry"),
                    "sources": [{"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"}]}

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
            if args.get("companies"):
                ka = D.kpi_table_all(args.get("year", "FY26"))
                keep = [D.company(c)["short"] for c in _resolve_many(args["companies"])]
                k = ka.loc[[x for x in keep if x in ka.index]]
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


def run_agent(messages: list[dict], on_step=None, max_steps: int = 4, on_text=None, run: dict | None = None) -> str:
    """Agentic loop over the configured provider. `messages` = [{role, content}] (strings).
    on_step(step, tool, args) reports progress; on_text(delta) streams the answer (on_text(None) = clear);
    `run` collects charts, the evidence the answer was built on, and which engine answered."""
    run = run if run is not None else {}
    run.setdefault("charts", [])
    run.setdefault("evidence", [])
    if get_provider() == "anthropic":
        return _no_em_dash(_run_anthropic(messages, on_step, max_steps, run))
    return _no_em_dash(_run_openai_compatible(messages, on_step, max_steps, on_text, run))


def _script_ctx():
    for mod in ("streamlit.runtime.scriptrunner_utils.script_run_context", "streamlit.runtime.scriptrunner"):
        try:
            m = __import__(mod, fromlist=["get_script_run_ctx", "add_script_run_ctx"])
            return m.get_script_run_ctx, m.add_script_run_ctx
        except Exception:
            continue
    return (lambda: None), (lambda t, c=None: t)


def _run_tools(calls: list[tuple[str, dict]], step: int, on_step, run: dict) -> list[dict]:
    """Runs the requested tools at the same time (threads keep the Streamlit session so the peer set is right)."""
    get_ctx, add_ctx = _script_ctx()
    ctx = get_ctx()
    results: list[dict] = [{} for _ in calls]

    def work(i: int, name: str, args: dict) -> None:
        results[i] = _clean(run_tool(name, args, run))

    threads = []
    for i, (name, args) in enumerate(calls):
        if on_step:
            on_step(step, name, args)
        if len(calls) == 1:
            work(0, name, args)
            continue
        t = threading.Thread(target=work, args=(i, name, args), daemon=True)
        add_ctx(t, ctx)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=60)
    for r in results:
        run["evidence"].append(AX.evidence_dump(r))
    return results


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


def _lite_model(client) -> str | None:
    """A lighter, faster Gemini model with its own free quota, used as the first backup."""
    try:
        ids = [m.id.replace("models/", "") for m in client.models.list()]
    except Exception:
        return None
    lite = [i for i in ids if "flash-lite" in i and not any(x in i for x in ("tts", "live", "image", "preview"))]
    return sorted(lite, reverse=True)[0] if lite else None


def _engines() -> list[dict]:
    """Primary engine, then free backups: a lighter Gemini model, then Groq if a Groq key is set."""
    prov = get_provider() or "gemini"
    out = [{"prov": prov, "key": get_api_key(), "model": get_model()}]
    if prov == "gemini":
        out.append({"prov": "gemini", "key": get_api_key(), "model": "__lite__"})
    if prov != "groq" and _secret("GROQ_API_KEY"):
        out.append({"prov": "groq", "key": _secret("GROQ_API_KEY"), "model": _secret("GROQ_MODEL") or PROVIDERS["groq"]["default_model"]})
    return out


def _is_capacity_error(e: Exception) -> bool:
    from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError  # noqa: WPS433

    if isinstance(e, (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)):
        return True
    code = getattr(e, "status_code", None)
    return code in (429, 500, 502, 503, 504) or "quota" in str(e).lower() or "exhausted" in str(e).lower()


def _run_openai_compatible(messages: list[dict], on_step=None, max_steps: int = 4, on_text=None, run: dict | None = None) -> str:
    from openai import OpenAI  # noqa: WPS433

    run = run if run is not None else {"charts": [], "evidence": []}
    last_err = None
    for i, eng in enumerate(_engines()):
        base = _secret(f"{eng['prov'].upper()}_BASE_URL") or PROVIDERS[eng["prov"]]["base_url"]  # override only for testing
        client = OpenAI(api_key=eng["key"], base_url=base, timeout=40, max_retries=1)
        model = eng["model"]
        if model == "__lite__":
            model = _lite_model(client)
            if not model:
                continue
        stream = on_text is not None and not st.session_state.get("_no_stream")
        for attempt in range(2):  # second attempt = same engine without streaming, if streaming misbehaves
            try:
                if on_text and attempt:
                    on_text(None)
                text = _openai_loop(client, eng["prov"], model, messages, on_step, max_steps, on_text if stream else None, run)
                run["engine"] = f"{PROVIDERS[eng['prov']]['label']} · {model}" + (" (backup)" if i else "")
                return text
            except Exception as e:  # noqa: BLE001
                last_err = e
                if _is_capacity_error(e):
                    break  # try the next engine
                if stream and attempt == 0:
                    st.session_state["_no_stream"] = True
                    stream = False
                    continue
                raise
    if last_err:
        raise last_err
    raise RuntimeError("No AI engine is configured.")


def _stream_call(client, kw: dict, on_text) -> dict:
    """Streams one model turn. Text goes to on_text as it arrives; tool calls are rebuilt piece by piece,
    keeping every extra field (Gemini's thought_signature) so the turn can be replayed exactly."""
    text, tools = [], {}
    for chunk in client.chat.completions.create(**kw, stream=True):
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            text.append(delta.content)
            if on_text and not tools:
                on_text(delta.content)
        for tcd in delta.tool_calls or []:
            d = tcd.model_dump(exclude_none=True)
            idx = d.pop("index", len(tools))
            acc = tools.setdefault(idx, {"id": None, "type": "function", "function": {"name": "", "arguments": ""}})
            if d.get("id"):
                acc["id"] = d["id"]
            fn = d.pop("function", {}) or {}
            if fn.get("name") and not acc["function"]["name"]:
                acc["function"]["name"] = fn["name"]
            if fn.get("arguments"):
                acc["function"]["arguments"] += fn["arguments"]
            for k_, v_ in d.items():
                if k_ not in ("id", "type"):
                    acc[k_] = v_
        extra = getattr(delta, "model_extra", None) or {}
        if extra.get("extra_content") and tools:
            tools[max(tools)]["extra_content"] = extra["extra_content"]
    calls = [tools[k_] for k_ in sorted(tools)]
    for j, c in enumerate(calls):
        c["id"] = c["id"] or f"call_{j}"
    if calls and text and on_text:
        on_text(None)  # the text was a preamble to tool calls, not the answer
    turn = {"role": "assistant", "content": "".join(text)}
    if calls:
        turn["tool_calls"] = calls
    return {"content": "".join(text), "calls": calls, "turn": turn}


def _plain_call(client, kw: dict) -> dict:
    msg = client.chat.completions.create(**kw).choices[0].message
    turn = msg.model_dump(exclude_none=True)  # keeps Gemini's thought_signature on each tool call
    turn["role"] = "assistant"
    turn.setdefault("content", "")
    calls = turn.get("tool_calls") or []
    return {"content": msg.content or "", "calls": calls, "turn": turn}


def _openai_loop(client, prov: str, model: str, messages: list[dict], on_step, max_steps: int, on_text, run: dict) -> str:
    from openai import BadRequestError, NotFoundError  # noqa: WPS433

    convo = [{"role": "system", "content": system_prompt()}] + [{"role": m["role"], "content": m["content"]} for m in messages]

    def call(choice: str) -> dict:
        kw = dict(model=model, messages=convo, tools=OPENAI_TOOLS, tool_choice=choice, max_tokens=1000)
        if prov == "gemini" and not st.session_state.get("_no_reasoning_param"):
            kw["extra_body"] = {"reasoning_effort": "low"}
        try:
            return _stream_call(client, kw, on_text) if on_text else _plain_call(client, kw)
        except BadRequestError as e:
            if "extra_body" not in kw or "reason" not in str(e).lower():
                raise
            st.session_state["_no_reasoning_param"] = True  # model doesn't accept it; don't try again
            kw.pop("extra_body")
            return _stream_call(client, kw, on_text) if on_text else _plain_call(client, kw)

    for step in range(max_steps):
        choice = "none" if step == max_steps - 1 else "auto"  # last round must answer, not research
        try:
            try:
                out = call(choice)
            except BadRequestError:
                if choice != "none":
                    raise
                out = call("auto")  # provider doesn't accept tool_choice='none'
        except NotFoundError:
            alt = _pick_model(client, prov)
            if not alt or alt == model:
                raise
            model = alt
            st.session_state[f"_resolved_model_{prov}"] = alt
            out = call(choice)
        if not out["calls"]:
            return out["content"]
        convo.append(out["turn"])
        reqs = []
        for tc in out["calls"]:
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            reqs.append((tc["function"]["name"], args))
        results = _run_tools(reqs, step + 1, on_step, run)
        for tc, res in zip(out["calls"], results):
            convo.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(res, default=str)[:7000]})
    return "I hit the step limit while researching. Try a narrower question."


def _run_anthropic(messages: list[dict], on_step=None, max_steps: int = 4, run: dict | None = None) -> str:
    import anthropic  # noqa: WPS433

    run = run if run is not None else {"charts": [], "evidence": []}
    client = anthropic.Anthropic(api_key=get_api_key())
    convo = [{"role": m["role"], "content": m["content"]} for m in messages]
    for step in range(max_steps):
        resp = client.messages.create(model=get_model(), max_tokens=1000, system=system_prompt(), tools=TOOLS, messages=convo)
        if resp.stop_reason != "tool_use":
            run["engine"] = f"{PROVIDERS['anthropic']['label']} · {get_model()}"
            return "".join(b.text for b in resp.content if b.type == "text")
        blocks = []
        for b in resp.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        convo.append({"role": "assistant", "content": blocks})
        uses = [b for b in resp.content if b.type == "tool_use"]
        outs = _run_tools([(b.name, b.input) for b in uses], step + 1, on_step, run)
        convo.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(o, default=str)[:7000]}
                                                   for b, o in zip(uses, outs)]})
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
