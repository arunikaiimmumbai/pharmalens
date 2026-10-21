# PharmaLens.ai — Agentic Pharma Intelligence

Live, interactive intelligence dashboard + AI analyst for six Indian pharma companies:
**Alembic · Ajanta · Ipca · Mankind · Alkem · Glenmark** (consolidated, FY22–FY26 + Q1 FY27).

Prepared by **Arunika Sherry** · IIM Mumbai Mentorship Program · Mentor: **Phalgun Rudrapatna**

## What's inside
| Page | What it does |
|---|---|
| 🧬 Command Center | Portfolio KPIs, live market pulse, positioning map, PharmaLens scorecard, partner so-whats, news pulse |
| 🏢 Company Deep-Dive | Profile, market / geographic / manufacturing / R&D / therapy footprints, 6-month news, insights |
| 📊 P&L Lab | P&L bridge, common-size P&L, 5-yr trends, CAGR table, cost elasticity, correlation matrix, pooled explorer |
| ⚖️ Ratio Benchmark | 33-KPI master table (best/worst highlighted), radar, KPI spotlight, 5-yr ratio trends, DuPont |
| 🧪 Regulatory & Pipeline | USFDA status, ANDA/DMF engine, R&D vs margin, US-share risk |
| 📰 News & Signals | Signal timeline, news→KPI heatmap, curated + live Google News, event study vs Nifty Pharma |
| 🎯 Strategy Room | What's working / not, Top-5 problem statements, consulting opportunity map, digitisation journey |
| 🤖 AI Analyst | Tool-using AI agent (10 tools, free Gemini by default) with visible trace; offline rule-based mode without a key |
| 📚 Sources & Method | Sources, methodology, caveats, KPI dictionary |

## Cost: ₹0
Everything runs on free tiers: GitHub (free), Streamlit Community Cloud (free hosting), Google Gemini API (free tier).
Without any key the app still works fully; the AI Analyst then runs in free offline mode.

## Deploy (free) — GitHub + Streamlit Community Cloud
1. Create a free GitHub account → New repository `pharmalens` (Public) → "uploading an existing file" → drag in everything inside this folder → Commit.
2. Get a free Gemini key: https://aistudio.google.com/apikey → Create API key → copy it.
3. Go to https://share.streamlit.io → sign in with GitHub → Create app → choose the repo, branch `main`, file `app.py`.
4. Advanced settings → Secrets → paste:
   ```
   GEMINI_API_KEY = "your-free-key"
   ```
5. Deploy. You get a free link like `https://pharmalens-yourname.streamlit.app`.

## Run on your laptop (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Updating the data
All curated data lives in `data/companies.json` (financials, footprints, news, problem statements, digital scores).
Edit it in GitHub → commit → the app redeploys automatically. Each quarter: append the new quarter, roll the 5-year window, add news.

## Architecture
```
app.py                 navigation + sidebar
core/data.py           data loader + ratio/KPI engine (CAGR, ROE, elasticity, correlations)
core/insights.py       rule-based growth/opportunity/risk engine + PharmaLens score
core/live.py           yfinance prices, Google News RSS, sentiment, event study
core/agent.py          AI agent (free Gemini / Groq, optional Claude) with 10 tools + offline analyst
core/theme.py          white/blue pharma design system (CSS, Plotly template, SVG motifs)
views/*.py             one file per page
data/companies.json    curated dataset with sources
```

_Public information only; academic project; not investment advice._
