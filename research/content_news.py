"""Adds a financial-statement impact view to every curated news item:
pl / bs / cf = effect on P&L, balance sheet, cash flow; doing = what management is already doing (from the
item or the company's disclosures); should = what more the company or a consultant could do."""
import json
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "data" / "companies.json"


def n(pl, bs, cf, doing, should):
    return {"pl": pl, "bs": bs, "cf": cf, "doing": doing, "should": should}


IMPACT = {
    # Alembic
    "Clonidine": n("Adds US revenue; small single launch, so gross margin effect is minor.", "Adds a little inventory and receivables for the launch.",
                   "Launch stock uses cash before sales arrive.", "About 15 US launches planned for the rest of FY27.",
                   "Launch only where competition is thin; stage launch stock to avoid adding to 462 inventory days."),
    "Ciprodex": n("Higher-margin sterile product once launched; supports US growth and margin.", "Uses existing complex-product capacity, which helps absorb new plants.",
                  "Positive once sales start; little extra capex.", "Moving its pipeline toward complex products (eye, ear, injectables).",
                  "Prioritise complex launches that fill the under-used new plants; track return on each plant."),
    "Analyst & investor": n("No direct effect.", "No direct effect.", "No direct effect.", "Management is promoting the upgraded mid-teens growth guidance.",
                            "Pair the growth story with a public working-capital target; investors are watching cash, not only growth."),
    "Q1 FY27: revenue +26%": n("Revenue +26%, but margin only ~15% because R&D is ~9% of sales and the Pivya launch costs money.", "Receivables and inventory rise with US growth.",
                               "Growth absorbs cash; PAT +12% only.", "FY27 growth guidance raised to mid-teens.",
                               "Separate one-off bosutinib sales from the base; cap R&D at a % of sales; set an inventory-days target."),
    "Q4 FY26": n("EBITDA margin troughed at 12.3% as R&D hit 11% of sales and branded launch costs rose.", "Borrowings rose to ₹1,430 Cr.",
                 "Interest cost rising (+17%); cash flow under pressure.", "Launched Pivya (specialty brand) in Feb 2026.",
                 "Stage-gate R&D spend by expected return; working-capital release to repay debt."),
    # Ajanta
    "Sep-2026 IPM data: Ajanta": n("India sales growing faster than the market, mostly from volume, which is the healthy kind of growth.", "No major effect.",
                                   "Supports steady cash from India.", "Volume-led growth across its branded portfolio.",
                                   "Use the momentum to fix cardiology, where it is losing share (7% vs market 14%)."),
    "Q1 FY27: revenue +25%": n("Revenue +25%, PAT +31%; US +57%, but Asia branded −16%.", "₹400 Cr interim dividend reduces reserves.",
                               "Dividend paid exceeded the quarter's profit, so cash falls.", "Returning cash to shareholders; scaling US.",
                               "Turnaround plan for Asia branded; fix collections before raising payouts further."),
    "Paithan": n("No immediate P&L effect; removes a risk to future US launches.", "No effect.", "No effect.",
                 "Plant cleared (VAI = minor issues only).", "Use Paithan for the next wave of US filings; keep inspection readiness."),
    "FY26: revenue +17% to ₹5,453": n("Revenue +17%, ROCE ~33%; R&D raised to ₹252 Cr.", "Receivables jumped (debtor days 93 → 124).",
                            "Cash from operations only ₹529 Cr, half of profit (0.5x).", "Investing in US growth and R&D.",
                            "Order-to-cash review: distributor credit terms, collections incentives, receivables ageing."),
    "Block-period": n("No charge yet; outcome 'cannot be determined'.", "Possible future tax liability (contingent).", "Possible future cash outflow.",
                      "Returns filed after the Aug 2025 tax search.", "Disclose a range of possible outcomes; keep a provision policy ready."),
    # Ipca
    "Sep-2026 IPM: Ipca": n("Domestic sales growing faster than the market (16% vs 13.5%).", "No major effect.", "Supports cash flow.",
                            "Outgrowing the market in both chronic and acute.", "Reduce dependence on pain (53% of sales) by pushing chronic launches."),
    "Stock hits record high": n("No direct effect.", "No direct effect.", "No direct effect.", "Delivering on raised guidance.",
                                "Valuation now prices in margin delivery; Unichem synergies must arrive to justify it."),
    "Q1 FY27: revenue +21%": n("Revenue +21%, EBITDA +50%, margin 22.9%: operating leverage plus API recovery.", "No major effect.",
                               "Stronger profit improves cash.", "Guidance raised to 14–16% growth and 23% margin; personnel cost down 1.4 points of sales.",
                               "Lock in cost gains with a procurement and productivity programme."),
    "Unichem Q1": n("Unichem margin only 11% vs Ipca's base ~26%, which drags the group margin.", "No effect.", "No effect.",
                    "API source transfer to Unichem has started but synergies are still 'minimal'.",
                    "Synergy tracking office: API switch, joint buying, plant consolidation (₹150–250 Cr EBITDA prize)."),
    "Capex ₹700": n("Higher depreciation later; no immediate profit effect.", "Fixed assets up ₹700–800 Cr; USD loans repaid, so debt very low.",
                    "Cash out for capex.", "Building new API plants at Dewas and Wardha.",
                    "Phase capex to demand; target utilisation before new spend to protect ROCE (17%)."),
    # Mankind
    "Armed Cell": n("Adds R&D-type losses for years; no revenue soon.", "~₹511 Cr investment added to assets.", "Cash out of ~₹511 Cr while acquisition debt is still being repaid.",
                    "Entering cell therapy (CAR-T) for long-term growth.", "Set a clear innovation budget and milestones; explain the strategy to investors."),
    "Releases pledge": n("No direct effect.", "Shows acquisition debt being refinanced or repaid.", "No direct effect.",
                         "Reducing BSV acquisition debt (net debt down to 0.9x EBITDA).", "Keep deleveraging before further deals."),
    "Q1 FY27: revenue +13%": n("Margin up 2.5 points to 26.3%; tax rate up to 25.4% as Sikkim tax breaks end.", "Net debt ₹3,377 Cr (0.9x EBITDA).",
                               "Debt repayment absorbs cash.", "Improving margins after the BSV merger.",
                               "Plan for a higher tax rate; fix consumer healthcare growth (+4%)."),
    "Vistar": n("New division adds cost first, sales later.", "Rivotril brand purchase adds intangibles.", "Cash out for the brand.",
                "Building depth in CNS; AI drug-discovery partnership.", "Measure new-division productivity per rep from day one."),
    "FY26: revenue +17% to ₹14,278": n("Revenue +17%, but PAT −3.4% due to BSV interest (₹644 Cr) and D&A (₹886 Cr).", "Goodwill and intangibles from BSV lift capital; ROCE fell from 26% to 14%.",
                                       "Strong cash (CFO ₹3,121 Cr) used to repay debt.", "Integrating BSV; exports +34.5%.",
                                       "BSV cross-selling through 16,800 reps to earn back the cost of capital."),
    "Income-tax proceedings": n("No charge yet.", "₹1,909 Cr shown as a possible liability.", "Possible future outflow.",
                                "Management says it is confident of its position.", "Scenario-plan the downside; disclose the timeline."),
    # Alkem
    "Macquarie": n("No direct effect.", "No direct effect.", "No direct effect.", "Investors split: BUY at ₹6,000 vs SELL at ₹4,638.",
                   "Investor messaging on the Daman fix and tax outlook."),
    "52-week low": n("No direct effect.", "No direct effect.", "No direct effect.", "Share price reflects Daman, tax and US guidance worries.",
                     "Show a credible Daman remediation timeline; that is the main share-price trigger."),
    "Q1 FY27: revenue +11%": n("Revenue +11%, margin down 1.4 points; PAT −22% due to 30–32% tax rate.", "No major effect.",
                               "Lower profit means lower cash.", "Added 1,200 reps; US guidance cut.",
                               "Rep productivity review before more hiring; tax structure review."),
    "Daman": n("US sales at risk: Daman supplies ~45% of US revenue; remediation costs rise.", "Possible inventory write-offs if products can't ship.",
               "Remediation spend; lower US collections.", "Remediation expected to take 6–12 months.",
               "Independent remediation team, e-quality systems, and a backup plant for key US products."),
    "Occlutech": n("About ₹400 Cr of FY27 sales at breakeven, so group margin dips.", "Acquisition adds goodwill.", "Cash out for the deal.",
                   "Entering medical devices (structural heart).", "Integration plan with a clear path to profit."),
    "Q4/FY26": n("EBITDA crossed ₹3,000 Cr (20.4%); exceptional charges for the labour code and a property impairment.", "Impairment reduces asset value.",
                 "Operating cash steady (~₹1,960 Cr).", "Launched semaglutide early (~11% unit share).",
                 "Strip one-offs in reporting; build the chronic franchise around semaglutide."),
    # Glenmark
    "Goa (Colvale)": n("No immediate effect; unlocks future US approvals from Goa.", "No effect.", "No effect.",
                       "Fixed FDA issues; warning letter closed.", "Keep inspection-ready; file pending products from Goa quickly."),
    "Q1 FY27: revenue +23%": n("Revenue +23% (core >18%); margin 20% once licensing is excluded.", "No major effect.", "Healthy cash.",
                               "First generic Flovent HFA with 180-day exclusivity.", "Report core and licensing income separately."),
    "FY27 margin guidance": n("Normal margin is 21–22%, not FY26's 27%.", "Target net working capital below 115 days.",
                              "Working-capital target would release cash.", "Holding margin guidance despite input inflation.",
                              "Working-capital programme to meet the 115-day target."),
    "FY26: revenue +27.5%": n("Revenue +27.5%, margin 26.9% boosted by the AbbVie upfront payment.", "Borrowings cut to ₹594 Cr.",
                              "Cash from operations ₹3,445 Cr.", "13 US launches; 52 ANDAs pending.",
                              "Turn the windfall into recurring profit: reinvest in launches with clear returns."),
    "price-fixing": n("US$29.6M settlement over 5 years.", "Liability booked and closed.", "Small yearly cash outflow.",
                      "Settled a legacy legal case.", "None needed beyond compliance monitoring."),
    # Sector
    "Indian pharma market grew 13.5%": n("Market growth supports India revenues for all six.", "No effect.", "No effect.",
                                         "Companies outgrowing the market: Ajanta, Ipca, Glenmark.", "Track share gains vs the market monthly, by therapy."),
    "Section 232 100% tariff": n("Generics excluded for now; specialty brands may face tariffs.", "No effect.", "No effect.",
                                 "Indian firms rely on the generics exclusion.", "Map each company's US product mix by tariff exposure."),
    "generics tariff path": n("If applied, US margins fall sharply after 2 years unless companies build US plants.", "Possible US plant capex.",
                              "Capex for US manufacturing.", "0% for 2 years gives time to adapt.",
                              "US footprint options study: contract manufacturing, partner plants, price strategy."),
    "API, solvent & logistics inflation": n("Material and freight costs up, so gross margin falls.", "Higher inventory value.", "More cash tied up in stock.",
                                            "Flagged on Q1 calls; API-integrated firms (Alembic, Ipca) are cushioned.",
                                            "Procurement and price-pass-through programme; dual sourcing."),
}

data = json.load(open(P, encoding="utf-8"))
items = [n_ for c in data["companies"] for n_ in c["news"]] + data["meta"]["sector_news"]
missing = []
for item in items:
    hit = [v for k, v in IMPACT.items() if k in item["title"]]
    if len(hit) != 1:
        missing.append((item["title"], len(hit)))
        continue
    item["statement_impact"] = hit[0]
print("matched", len(items) - len(missing), "of", len(items), "| problems:", missing)
json.dump(data, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
