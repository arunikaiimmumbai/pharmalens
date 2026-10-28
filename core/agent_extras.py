"""Extra analyst skills (all free): web search, reading a document, a calculator with 'size of the prize',
charts in answers, an automatic number check, an answer cache and plain-English progress labels.

Web search uses Gemini's built-in Google Search (free daily allowance on the Gemini free tier) and falls back to
DuckDuckGo (no key). Everything found on the web is labelled as such, so it is never confused with the checked data.
"""
from __future__ import annotations

import ast
import hashlib
import io
import ipaddress
import json
import math
import operator
import re
import socket
import time
from urllib.parse import urlparse

import numpy as np
import streamlit as st

from core import data as D
from core import industry as IND

# ── Progress labels shown while the analyst works ────────────────────────────
STEP_LABELS = {
    "list_companies": "Listing the companies",
    "get_company_profile": "Reading the company profile",
    "get_financials": "Pulling five years of financials",
    "compare_kpis": "Comparing the companies",
    "correlate": "Testing how two numbers move together",
    "get_insights": "Checking growth, opportunity and risk signals",
    "get_news": "Reading the last six months of news",
    "get_problem_statements": "Reading the problem statements and SWOT",
    "get_market_data": "Checking the share price",
    "get_industry_benchmark": "Comparing with the 20 Nifty Pharma companies",
    "get_brands_and_digital": "Reading brands and the digital roadmap",
    "run_scenario": "Running a projection",
    "search_web": "Searching the web",
    "read_document": "Reading the document",
    "calculate": "Calculating",
    "make_chart": "Drawing a chart",
}


def _nice(v) -> str:
    """Company ids and metric keys in plain words."""
    if isinstance(v, list):
        return ", ".join(_nice(x) for x in v)
    v = str(v)
    if v.lower() == "all":
        return "all six"
    for c in D.all_companies():
        if v.lower() in (c["id"], c["short"].lower()):
            return c["short"]
    if v in D.KPI_DEFS:
        return D.KPI_DEFS[v][0]
    return v.replace("_", " ") if re.fullmatch(r"[a-z_]+", v) else v


def step_label(tool: str, args: dict) -> str:
    lab = STEP_LABELS.get(tool, tool.replace("_", " ").capitalize())
    parts = [_nice(args[k]) for k in ("company", "companies", "metric", "metrics", "query") if args.get(k)]
    if tool == "read_document" and args.get("url"):
        parts = [urlparse(args["url"]).netloc]
    who = " · ".join(parts)
    return f"{lab}{': ' + who[:80] if who else ''}"


# ── Answer cache (shared by every visitor, so repeat questions are instant and free) ──
CACHE_TTL = 6 * 3600
NO_CACHE_WORDS = ("latest", "today", "right now", "this morning", "live", "current price", "share price now")


@st.cache_resource(show_spinner=False)
def _cache_store() -> dict:
    return {}


def cache_key(question: str, item_title: str, facts: str, model: str) -> str | None:
    q = re.sub(r"\s+", " ", (question or "").strip().lower())
    if any(w in q for w in NO_CACHE_WORDS):
        return None
    stamp = "|".join(str(D._mtime(s)) for s in D.available_segments())
    raw = "||".join([D.segment(), item_title or "", facts or "", q, model or "", stamp])
    return hashlib.sha256(raw.encode()).hexdigest()


def cache_get(key: str | None) -> dict | None:
    if not key:
        return None
    hit = _cache_store().get(key)
    if hit and time.time() - hit["t"] < CACHE_TTL:
        return hit["v"]
    return None


def cache_put(key: str | None, value: dict) -> None:
    if not key:
        return
    store = _cache_store()
    if len(store) > 500:  # keep memory small: drop the oldest half
        for k in sorted(store, key=lambda k_: store[k_]["t"])[:250]:
            store.pop(k, None)
    store[key] = {"t": time.time(), "v": value}


# ── Web search ───────────────────────────────────────────────────────────────
def _gemini_search(query: str, api_key: str, model: str) -> dict:
    """Gemini's native Google Search grounding. Returns a short factual summary plus the web sources it used."""
    import requests  # noqa: WPS433

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": (
        "Search the web and report the key facts, with dates and numbers, for this question about Indian pharma. "
        f"Be brief (under 150 words), plain English, no opinions.\nQuestion: {query}")}]}],
        "tools": [{"google_search": {}}]}
    r = requests.post(url, params={"key": api_key}, json=body, timeout=25)
    r.raise_for_status()
    cand = (r.json().get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    chunks = cand.get("groundingMetadata", {}).get("groundingChunks", []) or []
    sources = [{"title": (c.get("web", {}).get("title") or "web source")[:90], "url": c.get("web", {}).get("uri")}
               for c in chunks if c.get("web", {}).get("uri")]
    return {"summary": text.strip(), "sources": sources[:6], "engine": "Google Search (via Gemini)"}


def _ddg_search(query: str) -> dict:
    from ddgs import DDGS  # noqa: WPS433

    hits = list(DDGS().text(query, max_results=6, region="in-en"))
    results = [{"title": h.get("title", "")[:120], "snippet": h.get("body", "")[:300], "url": h.get("href")} for h in hits if h.get("href")]
    return {"results": results, "sources": [{"title": h["title"][:90], "url": h["url"]} for h in results], "engine": "DuckDuckGo"}


def search_web(query: str, api_key: str | None = None, model: str | None = None, provider: str | None = None) -> dict:
    """Free web search: Gemini Google Search first (if a Gemini key is set), then DuckDuckGo."""
    if not (query or "").strip():
        return {"error": "empty query"}
    errors = []
    if api_key and provider == "gemini":
        try:
            out = _gemini_search(query, api_key, model or "gemini-3.8-flash")
            if out["summary"]:
                return {**out, "label": "FROM THE WEB, not the app's checked data. Say so in the answer."}
        except Exception as e:  # quota, model without search, network
            errors.append(f"Google Search: {str(e)[:120]}")
    try:
        out = _ddg_search(query)
        if out["results"]:
            return {**out, "label": "FROM THE WEB, not the app's checked data. Say so in the answer."}
        errors.append("DuckDuckGo: no results")
    except Exception as e:
        errors.append(f"DuckDuckGo: {str(e)[:120]}")
    return {"error": "Web search is not available right now. " + "; ".join(errors)}


# ── Read a document (annual report, results PDF, web page) ─────────────────
MAX_BYTES = 15 * 1024 * 1024


def _safe_url(url: str) -> str:
    """Only public http(s) addresses: blocks local and private network addresses."""
    p = urlparse(url or "")
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only http(s) links can be read.")
    for info in socket.getaddrinfo(p.hostname, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("That address is not public, so it can't be read.")
    return url


def _pages_from_bytes(raw: bytes, ctype: str, url: str) -> list[str]:
    if raw[:5] == b"%PDF-" or "pdf" in ctype or url.lower().endswith(".pdf"):
        from pypdf import PdfReader  # noqa: WPS433

        reader = PdfReader(io.BytesIO(raw))
        return [(pg.extract_text() or "") for pg in reader.pages[:400]]
    html = raw.decode("utf-8", errors="ignore")
    html = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return [text[i:i + 3000] for i in range(0, len(text), 3000)]


@st.cache_data(show_spinner=False, ttl=24 * 3600, max_entries=20)
def _fetch_pages(url: str) -> tuple[list[str], str]:
    import requests  # noqa: WPS433

    _safe_url(url)
    with requests.get(url, timeout=30, stream=True, headers={"User-Agent": "Mozilla/5.0 (FinanceLens research)"}) as r:
        r.raise_for_status()
        raw = b""
        for chunk in r.iter_content(65536):
            raw += chunk
            if len(raw) > MAX_BYTES:
                raise ValueError("The document is larger than 15 MB.")
        return _pages_from_bytes(raw, r.headers.get("content-type", "").lower(), url), r.url


def read_document(url: str, question: str = "") -> dict:
    """Returns the passages of a document most relevant to the question, with page numbers."""
    pages, final_url = _fetch_pages(url)
    words = [w for w in re.findall(r"[a-z0-9&%]+", (question or "").lower()) if len(w) > 2 and w not in
             {"the", "and", "for", "what", "how", "does", "with", "this", "that", "from", "are", "was", "which"}]
    passages = []
    for i, txt in enumerate(pages, 1):
        for j in range(0, len(txt), 1200):
            chunk = txt[j:j + 1300].strip()
            if len(chunk) < 80:
                continue
            low = chunk.lower()
            score = sum(low.count(w) for w in words) + (0.5 if re.search(r"\d", chunk) else 0)
            passages.append((score, i, chunk))
    passages.sort(key=lambda x: -x[0])
    top = passages[:5] if words else passages[:3]
    title = urlparse(final_url).netloc + urlparse(final_url).path[-60:]
    return {"pages_read": len(pages), "passages": [{"page": p, "text": t} for _, p, t in top],
            "label": "FROM A DOCUMENT you linked; quote page numbers.", "sources": [{"title": f"Document: {title}", "url": final_url}]}


# ── Calculator and 'size of the prize' ──────────────────────────────────────
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Mod: operator.mod}
_FUNCS = {"min": min, "max": max, "abs": abs, "round": round, "sqrt": math.sqrt}


def safe_eval(expr: str) -> float:
    """Arithmetic only: numbers, + - * / ** %, brackets, min, max, abs, round, sqrt. No names, no code."""
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            if isinstance(n.op, ast.Pow) and abs(ev(n.right)) > 10:
                raise ValueError("power too large")
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and not n.keywords:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise ValueError("Only arithmetic is allowed.")
    if len(expr or "") > 300:
        raise ValueError("Expression too long.")
    return float(ev(ast.parse(expr.replace(",", ""), mode="eval")))


# metric: (basis line for the rupee value, direction 'lower' or 'higher' is better, what the rupee figure means)
PRIZE = {
    "inventory_days": ("material_cost", "lower", "cash released (one-time)"),
    "debtor_days": ("sales", "lower", "cash released (one-time)"),
    "payable_days": ("material_cost", "higher", "cash released (one-time)"),
    "employee_pct": ("sales", "lower", "extra EBITDA per year"),
    "material_pct": ("sales", "lower", "extra EBITDA per year"),
    "indirect_pct": ("sales", "lower", "extra EBITDA per year"),
    "other_cost_pct": ("sales", "lower", "extra EBITDA per year"),
    "manufacturing_pct": ("sales", "lower", "extra EBITDA per year"),
    "ebitda_margin": ("sales", "higher", "extra EBITDA per year"),
}


def size_of_prize(cid: str, metric: str, target: str | float = "industry_median", year: str = "FY26") -> dict:
    """Rupee value of moving one metric to a target (industry median/average, best peer, or a number)."""
    if metric not in PRIZE:
        return {"error": f"Size of the prize works for: {', '.join(PRIZE)}"}
    df = D.financial_frame(cid)
    r = df.loc[year]
    cur = float(r[metric])
    base_col, better, meaning = PRIZE[metric]
    base = float(r[base_col])
    if isinstance(target, (int, float)):
        tgt, tlabel = float(target), "your target"
    elif target in ("industry_median", "industry_average"):
        iv = IND.industry_value(metric, year)
        tgt = iv["median" if target == "industry_median" else "avg"]
        tlabel = target.replace("_", " ")
    elif target == "best_peer":
        k = D.kpi_table(year)
        tgt = float(k[metric].min() if better == "lower" else k[metric].max())
        tlabel = "best of the six"
    else:
        tgt, tlabel = float(target), "your target"
    if tgt is None or np.isnan(cur):
        return {"error": "No value available for that metric."}
    gap = (cur - tgt) if better == "lower" else (tgt - cur)
    if metric.endswith("_days"):
        value = gap / 365 * base
        formula = f"({cur:.0f} − {tgt:.0f} days) ÷ 365 × {base_col.replace('_', ' ')} ₹{base:,.0f} Cr" if better == "lower" else \
                  f"({tgt:.0f} − {cur:.0f} days) ÷ 365 × {base_col.replace('_', ' ')} ₹{base:,.0f} Cr"
    else:
        value = gap / 100 * base
        formula = f"{abs(gap):.1f} points of sales × ₹{base:,.0f} Cr sales"
    c = D.company(cid)
    return {"company": c["short"], "metric": metric, "year": year, "current": round(cur, 1), "target": round(tgt, 1), "target_basis": tlabel,
            "value_cr": round(max(value, 0), 0), "meaning": meaning, "already_better": gap <= 0, "formula": formula,
            "sources": [{"title": f"Screener.in: {c['short']} consolidated financials", "url": f"https://www.screener.in/company/{D.symbol(cid)}/consolidated/"},
                        {"title": "Nifty Pharma constituents", "url": IND.meta()["constituents_source"]["url"]}]}


# ── Charts in answers ────────────────────────────────────────────────────────
def chart_spec(metric: str, cids: list[str], mode: str = "snapshot", include_industry: bool = True, year: str = "FY26") -> dict:
    lab = D.KPI_DEFS.get(metric, (metric.replace("_", " "),))[0]
    names = [D.company(c)["short"] for c in cids]
    spec = {"metric": metric, "label": lab, "mode": mode, "names": names, "fmt": D.KPI_DEFS.get(metric, (0, 0, 0, "{:.1f}"))[3]}
    if mode == "trend":
        spec["years"] = D.years()
        spec["series"] = {D.company(c)["short"]: [None if np.isnan(v) else round(float(v), 2) for v in D.financial_frame(c)[metric]]
                          for c in cids if metric in D.financial_frame(c).columns}
        if include_industry and metric in IND.BENCHMARKABLE:
            s = IND.industry_series(metric)["Average"]
            spec["industry"] = [None if v is None or np.isnan(v) else round(float(v), 2) for v in s]
    else:
        vals = {}
        for c in cids:
            df = D.financial_frame(c)
            if metric in df.columns:
                vals[D.company(c)["short"]] = float(df.loc[year, metric])
            else:
                k = D.kpi_table_all(year)
                sh = D.company(c)["short"]
                if metric in k.columns and sh in k.index:
                    vals[sh] = float(k.loc[sh, metric])
        spec["values"] = {k_: (None if np.isnan(v) else round(v, 2)) for k_, v in vals.items()}
        if include_industry:
            iv = IND.industry_value(metric, year)["avg"]
            spec["industry"] = None if iv is None else round(iv, 2)
        spec["year"] = year
    spec["title"] = f"{lab} · {'FY22 to FY26' if mode == 'trend' else year}"
    return spec


def render_chart(spec: dict, key: str) -> None:
    """Draws a chart spec returned by the make_chart tool (used in the analyst panel)."""
    import plotly.graph_objects as go  # noqa: WPS433

    from core import theme as T  # noqa: WPS433

    palette = ["#1D4ED8", "#0E9F9A", "#7C3AED", "#0284C7", "#C2410C", "#4F46E5", "#059669", "#DB2777", "#CA8A04", "#475569", "#0891B2", "#9333EA"]
    cmap = {}
    for seg in D.available_segments():
        cmap.update({c["short"]: c["color"] for c in D.companies(seg)})
    used = set()

    def col(n, i):
        c = cmap.get(n) or palette[i % len(palette)]
        if c in used:
            c = palette[(i + 6) % len(palette)]
        used.add(c)
        return c

    fig = go.Figure()
    if spec.get("mode") == "trend":
        for i, (n, ys) in enumerate(spec.get("series", {}).items()):
            fig.add_trace(go.Scatter(x=spec["years"], y=ys, name=n, mode="lines+markers", line=dict(width=2.5, color=col(n, i))))
        if spec.get("industry"):
            fig.add_trace(go.Scatter(x=spec["years"], y=spec["industry"], name="Industry avg", mode="lines",
                                     line=dict(dash="dash", color="#64748B", width=2)))
    else:
        items = sorted(((n, v) for n, v in spec.get("values", {}).items() if v is not None), key=lambda x: x[1], reverse=True)
        fig.add_trace(go.Bar(x=[n for n, _ in items], y=[v for _, v in items], marker_color=[col(n, i) for i, (n, _) in enumerate(items)],
                             marker_cornerradius=5, text=[spec["fmt"].format(v) for _, v in items], textposition="outside"))
        if spec.get("industry") is not None:
            fig.add_hline(y=spec["industry"], line_dash="dash", line_color="#64748B",
                          annotation_text=f"Industry {spec['fmt'].format(spec['industry'])}", annotation_font_color="#64748B")
        fig.update_layout(showlegend=False)
    fig.update_layout(title=spec.get("title", ""), hovermode="x unified" if spec.get("mode") == "trend" else "closest", margin=dict(l=8, r=8, t=48, b=8))
    st.plotly_chart(T.style_fig(fig, 300), use_container_width=True, key=key)


# ── Number check ─────────────────────────────────────────────────────────────
_NUM = re.compile(r"(?<![A-Za-z#/])(-?\d[\d,]*\.?\d*)\s*(%|x|k|cr|crore|lakh|bn|billion|mn|million|days|d\b|pts|points)?", re.I)
_SKIP = re.compile(r"\b(FY|Q[1-4]\s*FY|H[12])\s*\d{2,4}|\b20[0-3]\d\b|\[[^\]]*\]\([^)]*\)|https?://\S+", re.I)
_SCALE = {"k": 1e3, "lakh": 1e5, "bn": 1e9, "billion": 1e9, "mn": 1e6, "million": 1e6}


def _numbers(text: str) -> list[float]:
    out = []
    text = re.sub(r"\\u[0-9a-fA-F]{4}", " ", text or "")  # escaped characters must not merge with nearby digits
    for m in re.finditer(r"-?\d[\d,]*\.?\d*", text):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def verify_numbers(answer: str, evidence: list[str]) -> dict:
    """Checks that each number in the answer appears in the tool results or page context (allowing for rounding).
    Small counts, years and quarter labels are ignored."""
    body = (answer or "").split("Sources:")[0]
    body = _SKIP.sub(" ", body)
    ev = set()
    for e in evidence:
        for v in _numbers(e):
            ev.add(round(v, 4))
    ev_list = list(ev)

    def found(a: float, unit: str) -> bool:
        cands = [a] + ([a * _SCALE[unit]] if unit in _SCALE else [])
        for c in cands:
            for e in ev_list:
                if abs(abs(e) - c) <= max(0.051, 0.006 * abs(e)) or (abs(e) >= 10 and round(abs(e)) == round(c)):
                    return True
        return False

    checked, missing = 0, []
    for m in _NUM.finditer(body):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        try:
            v = float(raw.replace(",", "").rstrip("."))
        except ValueError:
            continue
        if not unit and float(v).is_integer() and abs(v) <= 12:
            continue  # counts like "3 points" or "top 5"
        checked += 1
        if not found(abs(v), unit):
            missing.append(m.group(0).strip())
    return {"checked": checked, "missing": missing[:6], "ok": not missing}


def check_caption(chk: dict | None) -> str:
    if not chk or not chk.get("checked"):
        return ""
    if chk["ok"]:
        return f"✅ Number check: all {chk['checked']} numbers match the data the analyst used."
    return (f"⚠️ Number check: {len(chk['missing'])} of {chk['checked']} numbers could not be matched to the data "
            f"({', '.join(chk['missing'])}). They may be the AI's own arithmetic; check before quoting.")


def evidence_dump(obj) -> str:
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)  # keep ₹ as a symbol so digits next to it stay intact
    except Exception:
        return str(obj)
