"""Ranking & Scenarios: which company performs best to worst, how sure we are, and what a consulting
programme would change ('hire a consultant' what-if), plus Base / Upside / Downside scenarios."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import industry as IND
from core import ranking as R
from core import theme as T
from views.common import ask_button, register

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
SRC = [{"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"},
       {"title": "Industry benchmark: Nifty Pharma constituents", "url": "https://www.5paisa.com/hindi/nifty-pharma-stock-list"}]


def _assessment(row: pd.Series, cid: str) -> str:
    dims = row[list(R.DIMENSIONS)].astype(float).sort_values(ascending=False)
    txt = f"Strongest on {dims.index[0].lower()}; weakest on {dims.index[-1].lower()}"
    flags = [R.ACQUIRED.get(cid), R.ONE_OFF.get(cid) if R.ADJUST["on"] is False else None, R.OPEN_FDA.get(cid)]
    flags = [f for f in flags if f]
    return txt + (f". Note: {flags[0]}" if flags else "")


def render():
    T.hero("Ranking & Scenarios", "Which company is performing best to worst, how robust that ranking is, and what a consulting "
           "programme would change. Scored against the 20 Nifty Pharma companies.",
           ["Weighted scorecard", "3 lenses", "How sure are we?", "Hire-a-consultant what-if", "Base / Upside / Downside"])

    with st.expander("⚙️ Change the weights (the ranking updates live)", expanded=False):
        st.caption("Your framework: Revenue growth 20, Profitability 25, Cash generation 20, Capital efficiency 15, Balance sheet 10, "
                   "Operating efficiency 10. Then Current strength 40%, Momentum 30%, Quality 30%.")
        cols = st.columns(6)
        dw = {d: cols[i].slider(d, 0, 50, cfg["weight"], 5, key=f"w_{d}") for i, (d, cfg) in enumerate(R.DIMENSIONS.items())}
        cols = st.columns(4)
        lw = {l_: cols[i].slider(l_, 0, 100, w, 5, key=f"l_{l_}") for i, (l_, w) in enumerate(R.LENSES.items())}
        R.ADJUST["on"] = cols[3].toggle("Adjust Glenmark for one-off licensing income", value=True, key="adj_glen",
                                         help="On: Glenmark FY26 is scored at its guided normal 21.5% margin with the AbbVie upfront removed. "
                                              "Off: reported numbers, which inflate Glenmark's margin, cash and returns.")
    if sum(dw.values()) == 0 or sum(lw.values()) == 0:
        st.warning("Set at least one weight above zero.")
        return
    sc = R.scorecard(dw, lw)
    t = sc["table"]
    rob = R.robustness(2000)

    # ── Partner summary ──────────────────────────────────────────────────────
    T.section("Financial performance ranking", "score out of 100 · 100 = top of the Nifty Pharma industry on every measure")
    rows = []
    for cid, r in t.iterrows():
        rows.append({"Rank": f"{MEDAL.get(r['Rank'], '')} {int(r['Rank'])}", "Company": r["Company"], "Score /100": r["Overall"],
                     "Current strength": r["Current strength"], "Momentum": r["Momentum"], "Quality": r["Quality"],
                     "Chance of #1": rob.loc[cid, "Chance of #1"], "Assessment": _assessment(r, cid)})
    summ = pd.DataFrame(rows)
    st.dataframe(summ.style.format({"Score /100": "{:.0f}", "Current strength": "{:.0f}", "Momentum": "{:.0f}", "Quality": "{:.0f}",
                                    "Chance of #1": "{:.0f}%"})
                 .background_gradient(subset=["Score /100", "Current strength", "Momentum", "Quality"], cmap="Blues", vmin=0, vmax=100),
                 hide_index=True, use_container_width=True, column_config={"Assessment": st.column_config.TextColumn(width="large")})
    st.caption("Current strength = your six-dimension scorecard on FY26. Momentum = is it getting better (margin, ROCE, cash cycle, debt since FY23, "
               "latest quarter growth). Quality = is it sustainable (cash conversion, margin stability, ROIC above a 12% cost of capital, "
               "organic growth, no one-offs, no open FDA issue)."
               + (" Glenmark is scored on normalised FY26 numbers (licensing income removed)." if R.ADJUST["on"] else ""))
    register("Financial performance ranking", kind="table",
             note={"text": "Weighted scorecard on the user's framework, scored against the Nifty Pharma distribution.", "sources": SRC},
             facts="; ".join(f"{r['Rank']} {r['Company']} {r['Score /100']:.0f}/100 ({r['Assessment']})" for r in rows))
    ask_button("Financial performance ranking")

    top_id, last_id = t.index[0], t.index[-1]
    m1 = sc["metrics"][top_id]
    ind = {k: IND.industry_value(k)["avg"] for k in ("sales_cagr", "ebitda_margin", "fcf_margin", "roic", "net_debt_ebitda", "cfo_pat")}
    a, b = st.columns(2)
    a.markdown(f"""<div class="card" style="border-top:4px solid {T.GOOD}"><h4>Why {t.loc[top_id, 'Company']} ranks #1</h4>
        {''.join(f'<div style="font-size:.9rem;margin:3px 0">• {lab}: <b>{D.fmt(k, m1[k])}</b> <span class="muted">(industry {D.fmt(k, ind[k])})</span></div>'
                 for lab, k in [("Revenue growth a year", "sales_cagr"), ("EBITDA margin", "ebitda_margin"), ("ROIC", "roic"),
                                ("Free cash flow / sales", "fcf_margin"), ("Net debt / EBITDA", "net_debt_ebitda"), ("Cash conversion (CFO/PAT)", "cfo_pat")])}
        <div style="margin-top:8px;font-size:.88rem">Strongest on {" and ".join(d.lower() for d in t.loc[top_id, list(R.DIMENSIONS)].astype(float).sort_values(ascending=False).index[:2])}, scored against the whole industry.</div></div>""",
               unsafe_allow_html=True)
    dims1 = t.loc[top_id, list(R.DIMENSIONS)].astype(float).sort_values()
    lastd = t.loc[last_id, list(R.DIMENSIONS)].astype(float).sort_values()
    b.markdown(f"""<div class="card" style="border-top:4px solid {T.WARN}"><h4>What concerns us</h4>
        <div style="font-size:.9rem;margin:3px 0">• <b>{t.loc[top_id, 'Company']}:</b> weakest on {dims1.index[0].lower()} ({dims1.iloc[0]:.0f}/100){f"; only {D.fmt('cfo_pat', m1['cfo_pat'])} of profit turned into cash in FY26" if m1['cfo_pat'] < 0.8 else ""}.</div>
        <div style="font-size:.9rem;margin:3px 0">• <b>{t.loc[last_id, 'Company']} ranks last</b>: weakest on {lastd.index[0].lower()} ({lastd.iloc[0]:.0f}/100) and {lastd.index[1].lower()} ({lastd.iloc[1]:.0f}/100). {R.ACQUIRED.get(last_id, '')}</div>
        <div style="font-size:.9rem;margin:3px 0">• Scores are relative to the industry today; the what-if below shows what would move them.</div></div>""",
               unsafe_allow_html=True)

    # ── Scorecard detail ─────────────────────────────────────────────────────
    T.section("Scorecard by dimension", "0 to 100 · darker = closer to the top of the industry")
    det = t.set_index("Company")[list(R.DIMENSIONS)]
    det.columns = [f"{c} ({dw[c]})" for c in det.columns]
    st.dataframe(det.style.format("{:.0f}").background_gradient(cmap="Blues", vmin=0, vmax=100), use_container_width=True)
    with st.expander("See every metric, its value, the industry average and its 1 to 5 score"):
        ms = sc["metric_scores"]
        recs = []
        for dim, cfg in R.DIMENSIONS.items():
            for mkey, w, hib in cfg["metrics"]:
                rec = {"Dimension": dim, "Metric": R.LABELS[mkey], "Weight": w, "Better when": "higher" if hib else "lower",
                       "Industry avg": IND.industry_value(mkey)["avg"] if mkey in IND.BENCHMARKABLE else None}
                for cid in t.index:
                    rec[f"{D.names()[cid]} value"] = sc["metrics"][cid][mkey]
                    rec[f"{D.names()[cid]} score"] = ms.loc[cid, mkey]
                recs.append(rec)
        st.dataframe(pd.DataFrame(recs).style.format(precision=1, na_rep="–"), hide_index=True, use_container_width=True)
        st.caption("Score 1 to 5 = where the value sits among the 20 Nifty Pharma companies (5 = top). Latest-quarter growth has no industry "
                   "figure, so it is scored within the six.")
    register("Scorecard by dimension", kind="table", note={"text": "Dimension scores 0 to 100 against the industry.", "sources": SRC},
             facts="; ".join(f"{c}: " + ", ".join(f"{d} {t.set_index('Company').loc[c, d]:.0f}" for d in R.DIMENSIONS) for c in t["Company"]))
    ask_button("Scorecard by dimension")

    # ── Robustness ───────────────────────────────────────────────────────────
    T.section("How sure are we?", "the ranking re-run 2,000 times with every weight moved up to ±50%")
    a, b = st.columns([1.1, 1])
    with a:
        rb = rob.sort_values("Chance of #1")
        fig = go.Figure(go.Bar(y=rb["Company"], x=rb["Chance of #1"], orientation="h",
                               marker_color=[D.colors()[c] for c in rb["Company"]], text=[f"{v:.0f}%" for v in rb["Chance of #1"]],
                               textposition="outside", hovertemplate="%{y}: #1 in %{x:.0f}% of runs<extra></extra>"))
        fig.update_layout(title="Chance of ranking #1", xaxis_range=[0, 115], xaxis_ticksuffix="%", hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 300), use_container_width=True)
    with b:
        st.dataframe(rob.set_index("Company")[["Chance of top 3", "Median rank", "Best rank", "Worst rank"]].style.format(
            {"Chance of top 3": "{:.0f}%", "Median rank": "{:.0f}", "Best rank": "{:.0f}", "Worst rank": "{:.0f}"}), use_container_width=True)
        st.caption("If a company stays #1 under most weightings, the ranking does not depend on our choice of weights.")
    register("How sure are we? (weight robustness)", kind="chart",
             note={"text": "Monte Carlo on the weights: each run draws every weight between half and 1.5 times its base value.", "sources": SRC},
             facts="; ".join(f"{r_['Company']}: #1 in {r_['Chance of #1']:.0f}% of runs, median rank {r_['Median rank']:.0f}, range {r_['Best rank']:.0f}–{r_['Worst rank']:.0f}"
                             for _, r_ in rob.iterrows()))
    ask_button("How sure are we? (weight robustness)")

    # ── What-if ──────────────────────────────────────────────────────────────
    T.section("Hire a consultant: what-if", "pick a company, move the levers, see FY29 and the new rank")
    names = D.names()
    default = st.session_state.get("focus") or "alkem"
    cid = st.selectbox("Company", list(names), index=list(names).index(default), format_func=lambda x: names[x], key="wi_company")
    lv = {}
    lc = st.columns(3)
    for i, (k, (lab, lo, hi, dflt, step, _)) in enumerate(R.LEVERS.items()):
        lv[k] = lc[i % 3].slider(lab, float(lo), float(hi), float(dflt), float(step), key=f"lv_{k}")
    base = R.project(cid)["years"]
    likely = R.project(cid, lv, realisation=0.75)
    low = R.project(cid, lv, realisation=0.5, rnd_pays=0.0)["years"]
    high = R.project(cid, lv, realisation=1.0, rnd_pays=1.0)["years"]
    lk = likely["years"]
    ev_mult = D.kpi_table().loc[names[cid], "ev_ebitda"]
    new = R.scorecard(dw, lw, overrides={cid: R.scenario_overrides(cid, lv, 0.75)})["table"]
    old_rank, new_rank = int(t.loc[cid, "Rank"]), int(new.loc[cid, "Rank"])

    def tile(lab, key, fmt, unit=""):
        b_, l_, lo_, hi_ = base.loc["FY29", key], lk.loc["FY29", key], low.loc["FY29", key], high.loc["FY29", key]
        d_ = l_ - b_
        return T.kpi_card(lab, fmt.format(l_) + unit, f"{d_:+,.1f}{unit} vs no action", "up" if d_ >= 0 else "down",
                          f"range {fmt.format(min(lo_, hi_))} to {fmt.format(max(lo_, hi_))}{unit}")
    T.kpi_row([
        tile("FY29 revenue ₹ Cr", "Revenue", "{:,.0f}"), tile("FY29 EBITDA margin", "EBITDA margin %", "{:.1f}", "%"),
        tile("FY29 ROCE", "ROCE %", "{:.1f}", "%"), tile("FY29 ROIC", "ROIC %", "{:.1f}", "%"),
        tile("FY29 free cash flow ₹ Cr", "Free cash flow", "{:,.0f}"),
        T.kpi_card("New rank (likely)", f"#{new_rank}", f"from #{old_rank}", "up" if new_rank < old_rank else "down" if new_rank > old_rank else "flat",
                   f"value ≈ ₹{lk.loc['FY29', 'EBITDA'] * ev_mult:,.0f} Cr at {ev_mult:.0f}x EBITDA" if np.isfinite(ev_mult) else ""),
    ])
    st.caption(f"Likely = 75% of the lever benefits achieved and R&D paying off at the chance you set; low = 50% and R&D fails; high = 100% and R&D succeeds. "
               f"Working capital released in FY27: ₹{(round(likely['wc_release']) + 0):,.0f} Cr.")
    a, b = st.columns(2)
    with a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(base.index), y=base["ROCE %"], name="No action", line=dict(color=T.MUTED, dash="dot", width=2.5)))
        fig.add_trace(go.Scatter(x=list(high.index), y=high["ROCE %"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=list(low.index), y=low["ROCE %"], fill="tonexty", fillcolor="rgba(29,78,216,.15)", line=dict(width=0),
                                 name="Low to high range", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=list(lk.index), y=lk["ROCE %"], name="With the programme (likely)", line=dict(color=T.BLUE, width=3.5)))
        fig.update_layout(title=f"{names[cid]} ROCE path, FY27 to FY29", yaxis_ticksuffix="%")
        st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    with b:
        tor = R.tornado(cid)
        fig = go.Figure(go.Bar(y=tor["Lever"], x=tor["Δ overall score"], orientation="h",
                               marker_color=[T.GOOD if v >= 0 else T.BAD for v in tor["Δ overall score"]],
                               customdata=tor[["Δ ROCE FY29 (pts)", "Δ EBITDA FY29 (₹ Cr)"]].values,
                               text=[f"{v:+.1f}" for v in tor["Δ overall score"]], textposition="outside",
                               hovertemplate="%{y}<br>score %{x:+.1f}<br>ROCE %{customdata[0]:+.2f} pts<br>EBITDA ₹%{customdata[1]:+,.0f} Cr<extra></extra>"))
        span = max(abs(tor["Δ overall score"]).max(), 1)
        fig.update_layout(title="Which lever matters most? (change in score from one step)", hovermode="closest", margin=dict(l=10),
                          xaxis=dict(range=[-span * 1.35 if (tor["Δ overall score"] < 0).any() else 0, span * 1.35]))
        st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    with st.expander("Model assumptions (all editable in core/ranking.py)"):
        st.markdown(f"""
- **Base case:** revenue grows at broker consensus for FY27 where available ({R.base_growth(cid):.1f}% a year for {names[cid]}), otherwise the FY23–26 trend; margin stays at FY26 (Glenmark at its guided 21.5%).
- **Price:** +1 pt of price growth adds revenue and lifts margin by 0.6 pt (part of the price falls to profit).
- **R&D:** every +1 pt of sales on R&D costs 1 pt of margin from year one; if it pays off, it adds about 3% to revenue in FY29 (the delay reflects filing and launch time).
- **Costs:** employee and SG&A changes move margin point for point.
- **Working capital:** fewer inventory days release cash at daily material cost; fewer debtor days at daily sales; the cash lowers capital employed.
- **Capex:** adds capital and 10% a year depreciation; from the next year it adds sales at half the company's fixed-asset turnover.
- **Debt:** interest at 9% on the change in borrowings.
- **Rank:** the FY29 change against the no-action case is applied to today's metrics and re-scored against the industry.
This is an illustrative model for discussion, not a forecast.""")
    register(f"What-if for {names[cid]}", company=cid, theme="returns", kind="chart",
             note={"text": "Illustrative driver model FY27 to FY29 with consultant levers.", "sources": SRC},
             facts=f"Levers: " + ", ".join(f"{R.LEVERS[k][0]} {v:+g}" for k, v in lv.items() if v and k != "rnd_success")
                   + f". FY29 likely: revenue ₹{lk.loc['FY29', 'Revenue']:,.0f} Cr, EBITDA margin {lk.loc['FY29', 'EBITDA margin %']:.1f}%, ROCE {lk.loc['FY29', 'ROCE %']:.1f}% "
                     f"(no action {base.loc['FY29', 'ROCE %']:.1f}%), rank #{old_rank} → #{new_rank}. Biggest lever: {tor.iloc[-1]['Lever']}.")
    ask_button(f"What-if for {names[cid]}")

    # ── Scenarios ────────────────────────────────────────────────────────────
    T.section("Base, Upside and Downside", "how the ranking changes if the market moves")
    scn = R.scenario_ranking()
    a, b = st.columns([1, 1.2])
    with a:
        fig = go.Figure()
        for comp, r_ in scn.iterrows():
            fig.add_trace(go.Scatter(x=["Base", "Upside", "Downside"], y=[r_["Base rank"], r_["Upside rank"], r_["Downside rank"]],
                                     mode="lines+markers+text", name=comp, text=["", "", comp], textposition="middle right",
                                     line=dict(color=D.colors()[comp], width=3), marker=dict(size=10)))
        fig.update_layout(title="Rank under each scenario (1 = best)", yaxis=dict(autorange="reversed", dtick=1), showlegend=False,
                          xaxis=dict(range=[-0.2, 2.6]), hovermode="closest")
        st.plotly_chart(T.style_fig(fig, 340), use_container_width=True)
    with b:
        for nm, sc_ in R.SCENARIOS.items():
            st.markdown(f"**{nm}:** {sc_['desc']}")
        st.dataframe(scn.style.format(precision=0), use_container_width=True)
        movers = (scn["Downside rank"] - scn["Base rank"])
        st.caption("Biggest move in the downside: " + ", ".join(f"{c} ({int(v):+d})" for c, v in movers[movers != 0].items()) + ". "
                   "US-heavy companies fall; India-focused ones hold up.")
    register("Base, Upside and Downside scenarios", kind="chart", note={"text": "Scenario shocks scale with each company's US and India revenue share.", "sources": SRC},
             facts="; ".join(f"{c}: base #{int(r_['Base rank'])}, upside #{int(r_['Upside rank'])}, downside #{int(r_['Downside rank'])}" for c, r_ in scn.iterrows()))
    ask_button("Base, Upside and Downside scenarios")

    with st.expander("Method and sources"):
        st.markdown(f"""
- **Scorecard:** {", ".join(f"{d} {c['weight']}" for d, c in R.DIMENSIONS.items())} (your framework). Each metric scored 1 to 5 by its position among the 20 Nifty Pharma companies.
- **Lenses:** Current strength {R.LENSES['Current strength']}%, Momentum {R.LENSES['Momentum']}%, Quality {R.LENSES['Quality']}%. Momentum and quality are scored within the six.
- **Cost of capital:** {R.COST_OF_CAPITAL:.0f}% assumed for the ROIC spread.
- **Glenmark adjustment:** one-off licensing income X is removed so FY26 margin equals the guided 21.5%: (EBITDA − X) ÷ (Sales − X) = 21.5%, about ₹1,170 Cr.
- **Sources:** [Screener.in]({SRC[0]['url']}) consolidated accounts for all 25 companies; [Nifty Pharma constituents]({SRC[1]['url']}); company guidance and broker consensus from filings.
""")
    T.footer(D.meta())
