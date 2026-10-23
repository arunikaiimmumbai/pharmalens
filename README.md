# Finance Lens: Agentic Pharma Intelligence

Live, interactive intelligence dashboard + AI analyst for six Indian pharma companies:
**Alembic · Ajanta · Ipca · Mankind · Alkem · Glenmark** (consolidated, FY22–FY26 + Q1 FY27).

Prepared by **Arunika Sherry** · IIM Mumbai Mentorship Program · Mentor: **Dr. Phalgun Rudrapatna**

## What's inside
Every page has a **Compare with** bar (Industry = average of the 20 Nifty Pharma companies, or any of the six), an
**💡 Analyst note** pop-up under key charts (what is happening, what the company is doing, where a consultant can help, with sources), and the **🤖 Ask the analyst** panel on the right.

| Page | What it does |
|---|---|
| 🧬 Overview | Headline tiles, side-by-side comparison, Indian market growth (IQVIA), market pulse, positioning map |
| 🏢 Company Deep-Dive | Profile, brands & therapies ranked, geography, plants & R&D, cost drivers ranked, news impact on the statements, insights |
| 📊 P&L Lab | P&L bridge, cost mix, cost drivers (margin impact and 1% sensitivity), cost growth check, growth by line, test any two numbers (6 or 20 companies) |
| ⚖️ Ratio Benchmark | 36-KPI table with industry column and plain-English meaning, 5-year trends with industry line, DuPont |
| 🧪 Regulatory & Pipeline | USFDA status, ANDA/DMF engine, R&D vs margin, US-share risk |
| 📰 News & Signals | Signal timeline, news→KPI heat, news cards with P&L / balance sheet / cash flow impact and actions, live news, event study |
| 🎯 Strategy Room | What's working / not, SWOT, top-5 problem statements, consulting map, digitisation roadmap with gaps and consultant entry points |
| 🏆 Ranking & Scenarios | Weighted scorecard (growth 20, profit 25, cash 20, capital 15, balance sheet 10, efficiency 10) vs industry, 3 lenses, hire-a-consultant what-if with tornado, Base/Upside/Downside |
| 📤 Data Upload | Demo: upload a company's own numbers (template) and benchmark them vs industry; nothing stored |
| 📚 Sources & Method | Sources, industry members, method, caveats, glossary |

Data files: `data/companies.json` (six companies), `data/industry.json` (Nifty Pharma benchmark), `data/notes.json` (analyst notes).
Rebuild scripts and raw extracts are in `research/`.

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
core/insights.py       rule-based growth/opportunity/risk engine + financial score
core/live.py           yfinance prices, Google News RSS, sentiment, event study
core/agent.py          AI agent (free Gemini / Groq, optional Claude) with 10 tools + offline analyst
core/theme.py          white/blue pharma design system (CSS, Plotly template, SVG motifs)
views/*.py             one file per page
data/companies.json    curated dataset with sources
```

_Public information only; academic project; not investment advice._
