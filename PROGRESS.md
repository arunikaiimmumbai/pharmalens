# PharmaLens.ai — build checkpoint

Project: agentic pharma intelligence dashboard (Streamlit) + deploy guide + storytelling deck.
Owner: Arunika Sherry · IIM Mumbai Mentorship Program · Mentor: Dr. Phalgun Rudrapatna. No EY branding.
Companies: Alembic, Ajanta, Ipca, Mankind, Alkem, Glenmark. Basis: consolidated FY22–FY26 + Q1 FY27 (data as of 19-Oct-2026).

## Status
- [x] Research: 5-yr consolidated P&L/BS/CF/ratios/cost schedules (Screener), Q1 FY27 segments, regulatory, news Apr–Oct 2026
- [x] data/companies.json — all curated data, problems (5/co), working/not-working, digital maturity, news with sources
- [x] core/data.py — metrics engine (ratios, CAGR, elasticity, correlations)
- [x] core/theme.py — white/blue pharma CSS, hex-molecule bg, DNA helix hero, Plotly template
- [x] core/live.py — yfinance prices, Google News RSS, sentiment, event study
- [x] core/insights.py — rule-based growth/opportunity/risk engine + PharmaLens score
- [x] core/agent.py — Claude tool-use agent + offline fallback (loop verified with mock client)
- [x] app.py + views/ (Command Center, Company, P&L Lab, Ratios, Regulatory, News, Strategy Room, AI Analyst, Sources)
- [x] requirements.txt, .streamlit/config.toml, secrets example, README
- [x] Run locally + screenshots + fix (all 9 pages render, no exceptions)
- [x] Deploy guide — Claude Doc: https://claude.ai/code/artifact/f0a8e5dd-7bd1-4bb0-aed0-d4181109cb3c
- [x] Storytelling deck — Claude Slides, 13 slides: https://claude.ai/artifact/6egS63ZoezP8coEFShCjT2 (source copy in deck_source/)
- [x] Final zip + checks (all pages re-tested; analyst offline flow tested; agent loop mock-tested)

## Design decisions
- Company colours (CVD-validated): Alembic #1D4ED8, Ajanta #0E9F9A, Ipca #7C3AED, Mankind #0284C7, Alkem #C2410C, Glenmark #4F46E5
- LLM: FREE by default — Gemini via OpenAI-compatible API (GEMINI_API_KEY, model gemini-3.8-flash, auto-fallback to a listed Flash model); Groq optional free; Anthropic optional paid. No key = offline analyst.
- Data caveats: Glenmark FY22–23 incl. GLS; FY26 incl. AbbVie upfront. Mankind BSV from Oct-24. Ipca Unichem from FY24. Alkem FY24 cost split normalised.

## How to resume in a new chat
Upload pharmalens_checkpoint.zip and say: "Resume PharmaLens from PROGRESS.md — continue with the unchecked items."

## Open items for the user
- Deck placeholders: [app URL] on slide 12; [date] x2 and [Company A]/[Company B] on slide 13.
- Add free GEMINI_API_KEY in Streamlit secrets to switch on the live agent (loop mock-tested; not tested against the real API — no key here).

## Update 21-Oct-2026
- Mentor shown as "Dr. Phalgun Rudrapatna" everywhere (app meta, README, deck slides 1 & 13).
- Command Center section "Partner so-whats" renamed "Key insights".
- SWOT added: data/companies.json `swot` per company; Strategy Room SWOT grid + compare-all expander; agent tool get_problem_statements returns swot; deck slide 9 is now a SWOT table.
- ROCE story corrected (mostly margin, not capital) in insights.py and deck slides 2 & 5.
- Docs: Q&A prep https://claude.ai/artifact/E7KTmiPtYo5FyaGd1HqS6w · Walkthrough https://claude.ai/artifact/VpE2SPHNw76Xwpbt4ZVGm8
- User's repo: github.com/arunikaiimmumbai/pharmalens (config.toml landed at root, not in .streamlit/ — user advised to create .streamlit/config.toml).
