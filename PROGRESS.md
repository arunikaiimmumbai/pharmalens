# Finance Lens: build checkpoint (23 Oct 2026)

Live repo: github.com/arunikaiimmumbai/pharmalens (Streamlit Community Cloud, secret GEMINI_API_KEY).
Deck: Claude Slides artifact 6egS63ZoezP8coEFShCjT2 (14 slides; source copy in deck_source/ of the working folder).

## Done
- Name: Finance Lens (logo, tab, slide 13 title only); plain "financial" wording elsewhere.
- Industry benchmark = 20 Nifty Pharma companies (data/industry.json, built by research/build_industry.py from Screener extracts)
  + published market growth (IQVIA FY26 10%; Pharmarack Sep-26 13.5%). Grey note on every industry value.
- Compare bar on data pages (Please select / Industry / All six / companies).
- Analyst panel on every page (views/panel.py): pick a chart, suggested or free-text question, 5-part cited answers, agent history + download.
- Analyst notes under charts (data/notes.json, research/content_notes.py) incl. "already doing" lines.
- Deep-Dive: brands & therapies, cost drivers ranked, news impact on statements. P&L: margin impact + 1% sensitivity.
- Strategy: per-company digitisation roadmap with gaps and consultant entry points.
- Ranking & Scenarios (core/ranking.py): user framework weights, 3 lenses, weight robustness, what-if + tornado, Base/Upside/Downside.
  Glenmark normalised to guided 21.5% margin by default (toggle).
- Data Upload demo (template, sample "Company X", benchmark vs industry, nothing stored).
- Removed: AI Analyst page, scorecard grid on Command, radar, KPI spotlight, correlation heatmap, trajectory bars,
  duplicate quarterly/news blocks, sentiment bars, consulting pills, all-company digital radar.

## Open
- Slide 13 [app URL]; slide 14 [date] x2, [Company A]/[Company B].
- Guide docs (plain-English guide, finance basics, Q&A prep) predate this build.
