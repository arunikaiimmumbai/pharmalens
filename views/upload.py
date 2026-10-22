"""Data Upload (demo, placeholder for future versions): a company uploads its own numbers in a simple template and
sees its ratios benchmarked against the Nifty Pharma industry and the six companies. Nothing is stored."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import glossary as G
from core import industry as IND
from core import theme as T
from views.common import ask_button, register

YEARS = ["FY22", "FY23", "FY24", "FY25", "FY26"]
FIELDS = [
    ("Revenue", "sales"), ("Material cost", "material_cost"), ("Employee cost", "employee_cost"), ("Manufacturing cost", "manufacturing_cost"),
    ("Other expenses (SG&A)", "other_cost"), ("Depreciation", "depreciation"), ("Interest", "interest"), ("Other income", "other_income"),
    ("Tax", "tax"), ("Net worth (equity)", "net_worth"), ("Borrowings", "borrowings"), ("Cash and investments", "cash_inv"),
    ("Total assets", "total_assets"), ("Inventory", "inventory"), ("Trade receivables", "receivables"), ("Trade payables", "payables"),
    ("Cash from operations", "cfo"), ("Capex", "capex"),
]
# Clearly synthetic sample ("Company X") so the page can be demonstrated without real client data.
SAMPLE = [4000, 4500, 5100, 5700, 6300], [1600, 1760, 1940, 2110, 2330], [720, 830, 960, 1090, 1230], [280, 310, 350, 390, 430], \
         [640, 720, 820, 900, 990], [160, 180, 210, 240, 260], [60, 70, 80, 70, 60], [40, 45, 50, 55, 60], [150, 180, 200, 240, 270], \
         [3000, 3400, 3850, 4350, 4900], [900, 950, 1000, 900, 800], [300, 350, 400, 500, 650], [5200, 5800, 6400, 7000, 7600], \
         [1300, 1450, 1650, 1800, 1950], [1000, 1150, 1300, 1450, 1650], [600, 650, 720, 780, 850], [420, 520, 640, 760, 900], [350, 400, 450, 420, 400]
KEY_METRICS = ["ebitda_margin", "employee_pct", "material_pct", "roce", "roe", "inventory_days", "debtor_days", "payable_days", "ccc",
               "cfo_pat", "net_debt_ebitda", "fcf_margin", "asset_turnover", "sales_cagr"]


def template_csv(sample: bool = False) -> bytes:
    rows = []
    for (lab, _), vals in zip(FIELDS, SAMPLE):
        rows.append([lab] + (vals if sample else [""] * 5))
    return pd.DataFrame(rows, columns=["Line item (₹ Cr)"] + YEARS).to_csv(index=False).encode()


def _read(file) -> pd.DataFrame:
    name = file.name.lower()
    raw = pd.read_excel(file) if name.endswith((".xlsx", ".xls")) else pd.read_csv(file)
    raw = raw.rename(columns={raw.columns[0]: "item"})
    lab2key = {lab.lower(): key for lab, key in FIELDS}
    raw["key"] = raw["item"].astype(str).str.strip().str.lower().map(lab2key)
    raw = raw.dropna(subset=["key"]).set_index("key")
    yrs = [y for y in YEARS if y in raw.columns]
    return raw[yrs].apply(pd.to_numeric, errors="coerce").T


def ratios(f: pd.DataFrame) -> pd.DataFrame:
    s = f["sales"]
    out = pd.DataFrame(index=f.index)
    ebitda = s - f[["material_cost", "employee_cost", "manufacturing_cost", "other_cost"]].sum(axis=1)
    ebit = ebitda - f["depreciation"]
    pat = ebit - f["interest"] + f["other_income"] - f["tax"]
    out["sales"] = s
    out["ebitda_margin"] = ebitda / s * 100
    out["employee_pct"] = f["employee_cost"] / s * 100
    out["material_pct"] = f["material_cost"] / s * 100
    out["roce"] = ebit / (f["net_worth"] + f["borrowings"]) * 100
    avg_nw = ((f["net_worth"] + f["net_worth"].shift(1)) / 2).fillna(f["net_worth"])
    out["roe"] = pat / avg_nw * 100
    out["inventory_days"] = f["inventory"] / f["material_cost"] * 365
    out["debtor_days"] = f["receivables"] / s * 365
    out["payable_days"] = f["payables"] / f["material_cost"] * 365
    out["ccc"] = out["inventory_days"] + out["debtor_days"] - out["payable_days"]
    out["cfo_pat"] = f["cfo"] / pat
    out["net_debt_ebitda"] = (f["borrowings"] - f["cash_inv"]) / ebitda
    out["fcf_margin"] = (f["cfo"] - f["capex"]) / s * 100
    out["asset_turnover"] = s / f["total_assets"]
    out["sales_cagr"] = np.nan
    if len(s) >= 2 and s.iloc[0] > 0:
        out.loc[out.index[-1], "sales_cagr"] = ((s.iloc[-1] / s.iloc[0]) ** (1 / (len(s) - 1)) - 1) * 100
    return out


def render():
    T.hero("Data Upload", "Bring your own numbers: upload a company's confidential financials and benchmark them against the Nifty Pharma "
           "industry and the six companies in seconds.", ["Demo", "Nothing is stored", "Template-based", "Placeholder for future versions"])
    st.info("Demo version. Files are read in memory for this session only and never saved. For real client data, this would run in a "
            "private, access-controlled deployment.")

    T.section("What a client could use this for", "talking points for the Partner")
    uses = [("🔍 Due diligence", "Load a target's data-room numbers and see in minutes where it sits against listed peers on margin, cash and returns."),
            ("📉 Performance improvement", "A client uploads plant, brand or division data; the gaps to industry become the case and the size of the prize."),
            ("🤝 Post-merger integration", "Upload monthly numbers after a deal and track whether promised synergies are arriving."),
            ("💰 Working-capital diagnostic", "Upload inventory and receivables to find the cash that could be released."),
            ("🧭 Inside-out + outside-in", "Public data gives the outside-in view; the client's own data gives the inside-out view. Same engine for both.")]
    cols = st.columns(5)
    for col, (h, t) in zip(cols, uses):
        col.markdown(f'<div class="card"><h4>{h}</h4><div style="font-size:.85rem">{t}</div></div>', unsafe_allow_html=True)
    register("What a client could use the upload for", kind="text",
             facts=" | ".join(f"{h}: {t}" for h, t in uses))
    ask_button("What a client could use the upload for")

    T.section("1 · Get the template", "one row per line item, one column per year, ₹ Cr")
    a, b, c = st.columns(3)
    a.download_button("⬇️ Blank template (CSV)", template_csv(False), "finance_lens_template.csv", "text/csv", use_container_width=True)
    b.download_button("⬇️ Filled sample: 'Company X' (CSV)", template_csv(True), "finance_lens_sample_company_x.csv", "text/csv", use_container_width=True)
    use_sample = c.toggle("Use the sample instead of uploading", value=True, key="up_sample",
                          help="The sample is made-up data for a fictional 'Company X', for demonstrations.")

    T.section("2 · Upload", "CSV or Excel in the template format")
    up = st.file_uploader("Upload your file", type=["csv", "xlsx", "xls"], key="up_file", label_visibility="collapsed")
    try:
        if up is not None:
            f = _read(up)
            label = up.name
        elif use_sample:
            f = pd.read_csv(io.BytesIO(template_csv(True)))
            f = f.rename(columns={f.columns[0]: "item"})
            lab2key = {lab.lower(): key for lab, key in FIELDS}
            f["key"] = f["item"].str.lower().map(lab2key)
            f = f.dropna(subset=["key"]).set_index("key")[YEARS].astype(float).T
            label = "Sample: Company X (made-up data)"
        else:
            st.caption("Download the template, fill it in, and upload it here.")
            T.footer(D.meta())
            return
        missing = [lab for lab, key in FIELDS if key not in f.columns]
        if missing:
            st.error("These lines are missing from the file: " + ", ".join(missing) + ". Use the template's line names exactly.")
            return
        r = ratios(f)
    except Exception as e:
        st.error(f"Could not read the file. Check it follows the template (first column = line items, then FY22 to FY26). Detail: {e}")
        return

    T.section(f"3 · Results: {label}", "latest year vs the industry and the six companies")
    last = r.index[-1]
    k = D.kpi_table()
    rows = []
    for m in KEY_METRICS:
        v = r.loc[last, m]
        iv = IND.industry_value(m)
        hib = D.KPI_DEFS[m][2]
        dist = IND.member_values(m).replace([np.inf, -np.inf], np.nan).dropna()
        pct = (dist < v).mean() * 100 if hib is not False else (dist > v).mean() * 100
        gap = (v - iv["avg"]) if iv["avg"] is not None else None
        better = None if gap is None or hib is None or not np.isfinite(v) else bool((gap > 0) == bool(hib))
        rows.append({"Metric": D.KPI_DEFS[m][0], "You": v, "Industry avg": iv["avg"], "Industry median": iv["median"],
                     "Six-company median": k[m].median() if m in k.columns else None,
                     "Better than % of industry": pct if hib is not None else None,
                     "Verdict": "✅ better than industry" if better else ("⚠️ worse than industry" if better is False else "–"),
                     "Meaning": G.meaning(m), "_m": m, "_gap": gap, "_better": better})
    res = pd.DataFrame(rows)
    disp = res.copy()
    for col in ["You", "Industry avg", "Industry median", "Six-company median"]:
        disp[col] = [D.fmt(m, v) if v is not None and np.isfinite(v) else "–" for v, m in zip(res[col], res["_m"])]
    disp["Better than % of industry"] = [f"{v:.0f}%" if v is not None and np.isfinite(v) else "–" for v in res["Better than % of industry"]]
    st.dataframe(disp.drop(columns=["_m", "_gap", "_better"]), hide_index=True, use_container_width=True,
                 column_config={"Meaning": st.column_config.TextColumn(width="large")})
    st.caption(IND.meta()["method"])

    worst = res[res["_better"] == False].copy()  # noqa: E712
    worst["rank"] = 100 - worst["Better than % of industry"].astype(float)
    worst = worst.sort_values("rank", ascending=False).head(3)
    a, b = st.columns([1.2, 1])
    with a:
        pp = res.dropna(subset=["Better than % of industry"])
        fig = go.Figure(go.Bar(y=pp["Metric"], x=pp["Better than % of industry"], orientation="h",
                               marker_color=[T.GOOD if v >= 50 else T.BAD for v in pp["Better than % of industry"]],
                               text=[f"{v:.0f}%" for v in pp["Better than % of industry"]], textposition="outside",
                               hovertemplate="%{y}: better than %{x:.0f}% of the industry<extra></extra>"))
        fig.add_vline(x=50, line_dash="dot", line_color=T.MUTED, annotation_text="industry middle", annotation_font_color=T.MUTED)
        fig.update_layout(title="Where you stand: better than what % of the 20 Nifty Pharma companies", xaxis_range=[0, 115],
                          yaxis=dict(autorange="reversed"), hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 520), use_container_width=True)
    with b:
        st.markdown('<div class="card"><h4>Where a consultant would focus first</h4>' + "".join(
            f'<div style="margin:8px 0;font-size:.9rem"><b>{w["Metric"]}</b>: {D.fmt(w["_m"], w["You"])} vs industry {D.fmt(w["_m"], w["Industry avg"])}. '
            f'<span class="muted">{w["Meaning"]}</span></div>' for _, w in worst.iterrows()) +
            ('<div class="muted">No metric is worse than the industry average.</div>' if worst.empty else "") + "</div>", unsafe_allow_html=True)
        with st.expander("Five-year ratios for the uploaded company"):
            st.dataframe(r.T.style.format(precision=1), use_container_width=True)
    register(f"Upload results: {label}", kind="table",
             note={"text": "Uploaded company benchmarked against the 20 Nifty Pharma companies.",
                   "sources": [{"title": "Nifty Pharma constituents", "url": IND.meta()["constituents_source"]["url"]}]},
             facts="; ".join(f"{x['Metric']}: {D.fmt(x['_m'], x['You'])} vs industry {D.fmt(x['_m'], x['Industry avg'])}" for x in rows if x["Industry avg"] is not None))
    ask_button(f"Upload results: {label}")
    T.footer(D.meta())
