# Finance Lens: Agentic Pharma Intelligence

Live, interactive intelligence dashboard + AI analyst for two peer sets of Indian pharma companies (consolidated, FY22–FY26 + Q1 FY27),
chosen at the top of the Overview page. Each set is compared within itself and against the same industry benchmark (the 20 Nifty Pharma companies):

- **Mid-size Pharma** (FY26 sales ₹5,000 to 15,000 Cr): Alembic · Ajanta · Ipca · Mankind · Alkem · Glenmark
- **Pharma Majors** (FY26 sales above ₹27,000 Cr): Sun Pharma · Dr Reddy's · Cipla · Lupin · Aurobindo · Zydus

The sets are named by size of sales rather than stock-market "cap" labels, which AMFI revises every six months
(on the 2026 lists Dr Reddy's, Lupin, Zydus and Mankind sit in mid cap). Open `...?segment=major` to start on the Majors.

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

Data files: `data/companies.json` (Mid-size Pharma), `data/companies_majors.json` (Pharma Majors, built by `research/build_majors.py`), `data/notes_majors.json`, `data/industry.json` (Nifty Pharma benchmark), `data/notes.json` (analyst notes).
Rebuild scripts and raw extracts are in `research/`.

## Cost: ₹0
Everything runs on free tiers: GitHub (free), Streamlit Community Cloud (free hosting), Google Gemini API (free tier).
Without any key the app still works fully; the AI Analyst then runs in free offline mode.

**The analyst panel:** answers stream in as they are written, with each step shown live. The 16 tools cover the app's data
(both peer sets), the industry benchmark, a calculator for "size of the prize", charts inside answers, reading a linked
report (PDF or web page), and web search (Google Search through your Gemini key, DuckDuckGo as backup), used only when the
app's data can't answer and always labelled "(web)". Repeat questions are answered instantly from a shared cache. If the free
quota runs out it switches to a lighter Gemini model (or Groq if `GROQ_API_KEY` is set). Every answer gets an automatic
number check against the data it used, and a 👍/👎 rating recorded in the agent history.


## Live financial statements (automatic)

The financial statements refresh themselves in the background, the same way the news does. Every 6 hours the app checks
**Screener.in** (which compiles each company's results filed with NSE/BSE) for all 21 companies: the 12 in the app plus the
other Nifty Pharma members, so the industry benchmark stays current. It reads the annual P&L, balance sheet, cash flow,
ratios, the last five quarters, market data and shareholding, plus Screener's expense and cash breakdowns.

- **Checked before use:** core lines present for five years, positive sales, cost shares that add up, and past years within
  25% of the checked data. A company that fails keeps its saved numbers; the reason shows on Sources & Method.
- **Where you see it:** the sidebar ("Financials: live for N of 21 companies"), a "New results" banner on Overview, and the
  "Live financial statements feed" table on Sources & Method (with a "Check for new results now" button).
- **New year:** the five-year window moves forward (e.g. to FY23 to FY27) once every company has published the new year.
- **Not automatic:** written analysis (notes, SWOT, problems, news impact) stays dated to when it was researched.
- **Switch off:** set `LIVE_FINANCIALS = "off"` in Streamlit Secrets to use only the saved data.

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
core/agent.py          AI agent (free Gemini / Groq, optional Claude) with 16 tools, streaming, parallel tools, backup model + offline analyst
core/live_fin.py       live financial statements: background refresh from Screener.in, checks, merge
core/agent_extras.py   web search, read a document, calculator and size of the prize, charts in answers, number check, answer cache
core/theme.py          white/blue pharma design system (CSS, Plotly template, SVG motifs)
views/*.py             one file per page
data/companies.json    curated dataset with sources
```

_Public information only; academic project; not investment advice._
