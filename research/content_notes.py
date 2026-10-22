"""Writes data/notes.json: the 'Analyst note' shown under each chart.
company[cid][theme] = why the number looks the way it does for that company (context and reasons, with sources).
peer[key] = notes for charts that compare all six companies."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.load(open(ROOT / "data" / "companies.json", encoding="utf-8"))
SYM = {"alembic": "APLLTD", "ajanta": "AJANTPHARM", "ipca": "IPCALAB", "mankind": "MANKIND", "alkem": "ALKEM", "glenmark": "GLENMARK"}


def scr(cid):
    return {"title": f"Screener.in: {data and next(c['short'] for c in data['companies'] if c['id'] == cid)} consolidated financials",
            "url": f"https://www.screener.in/company/{SYM[cid]}/consolidated/"}


def news(cid, key):
    c = next(c for c in data["companies"] if c["id"] == cid)
    for n in c["news"]:
        if key in n["title"]:
            return {"title": n["title"][:90], "url": n["url"]}
    raise KeyError(key)


def ar(cid):
    c = next(c for c in data["companies"] if c["id"] == cid)
    return c["brands"]["sources"][0]


def note(text, *sources):
    return {"text": text, "sources": list(sources)}


COMPANY = {
    "alembic": {
        "growth": note("Revenue grew only ~8.5% a year FY22–26 because India branded sales grew ~5% against a market growing ~10–11%, and the US business was flat for two years. "
                       "Growth has now turned sharply (Q1 FY27 +26%) as new US approvals convert, partly helped by a limited-competition product (bosutinib).",
                       scr("alembic"), news("alembic", "Q1 FY27")),
        "margin": note("Margin is the lowest in the set (~15%) because Alembic spends 9–11% of sales on R&D, the most of the six, and is paying launch costs for its Pivya brand. "
                       "New plants add depreciation before they are full. Material cost is not the problem: it is broadly flat.",
                       scr("alembic"), news("alembic", "Q4 FY26")),
        "returns": note("ROCE is ~13% because two things combine: a low margin (R&D and launch costs) and about ₹2,000 Cr of new plants that are built but not yet full. "
                        "Capital is in the denominator before the revenue arrives, so returns should rise if utilisation improves.",
                        scr("alembic")),
        "wc": note("Inventory of 462 days is the highest of the six. US generics need stock ahead of each launch and Alembic has the biggest pipeline (279 filings, ~15 launches planned), "
                   "but 462 days also points to planning gaps. Every 30 days cut frees about ₹180 Cr.",
                   scr("alembic"), news("alembic", "Clonidine")),
        "cash": note("Cash from operations was ₹783 Cr in FY26 (1.2x profit), a recovery from FY25's ₹88 Cr collapse, but heavy capex means free cash flow is thin and borrowings doubled to ₹1,430 Cr.",
                     scr("alembic"), news("alembic", "Q4 FY26")),
        "cost": note("Employee cost rose from 21% to 24% of sales FY22–26 as R&D scientists and a 5,500-strong sales force were added faster than revenue grew. "
                     "Other overheads stayed flat, so people cost is the line to manage.",
                     scr("alembic")),
        "geo": note("US formulations are ~36% of revenue, the highest share of the six, so Alembic is most exposed to US pricing, FDA inspections and the proposed generics tariff. "
                    "API and ex-US markets (~34%) give some balance.",
                    scr("alembic"), ar("alembic")),
        "brands": note("India strength is in older acute brands that lead their molecules (Roxid 95% share, Althrocin 86%). These are mature, low-growth markets, which explains India growth of ~5%. "
                       "Animal health (22% of India business) is the fastest-growing part.",
                       ar("alembic")),
        "rnd": note("9 plants and the highest R&D intensity (9% of sales) reflect a strategy of building US complex generics. The payoff shows in US growth (+49% in Q1 FY27) but not yet in margin.",
                    ar("alembic"), news("alembic", "Ciprodex")),
        "quarter": note("Quarterly revenue jumped in Q1 FY27 (+26%) on US launches; margin stays near 15% because R&D and the Pivya launch absorb the gains.",
                        news("alembic", "Q1 FY27")),
        "debt": note("Debt rose to ₹1,430 Cr (1.1x EBITDA net) to fund new plants. Still comfortable, but interest cost grew 17% and adds pressure until the plants earn.",
                     scr("alembic")),
    },
    "ajanta": {
        "growth": note("Revenue grew ~13% a year, driven by US generics (+49% in FY26 from only ~51 products) and India volume growth ahead of the market. Asia branded, once the main engine, has stalled (−16% in Q1 FY27).",
                       scr("ajanta"), news("ajanta", "Q1 FY27")),
        "margin": note("Margin is the highest of the six (~27.5%) because Ajanta sells mostly branded, chronic products in India and emerging markets, and picks US products with few competitors. "
                       "Material cost fell from 29.5% to 22.2% of sales FY23–26.",
                       scr("ajanta"), ar("ajanta")),
        "returns": note("ROCE of 35% comes mainly from margin (EBIT ~24%) rather than from working assets harder. Debt is near zero and capex is modest, so capital stays lean.",
                        scr("ajanta")),
        "wc": note("Debtor days jumped from 93 to 124 in FY26 as US sales and distributor credit grew. Inventory (289 days) is in line with peers. Collections are the issue, not stock.",
                   scr("ajanta"), news("ajanta", "FY26")),
        "cash": note("Only half of FY26 profit turned into cash (CFO/PAT 0.5x) because receivables rose by ~₹670 Cr. With a ₹400 Cr dividend in Q1 FY27, cash discipline matters.",
                     scr("ajanta"), news("ajanta", "FY26")),
        "cost": note("Employee cost rose from 19.0% to 24.7% of sales FY22–26, the second-largest rise of the six, as Ajanta expanded US operations and sales teams ahead of revenue.",
                     scr("ajanta")),
        "geo": note("Revenue is spread across India (31%), US (30%), Africa (23%) and Asia (16%). The mix protects against any one market, but Asia's decline and the US tariff path are the watch points.",
                    scr("ajanta"), news("ajanta", "Q1 FY27")),
        "brands": note("Ajanta leads ophthalmology (#1) and is climbing in dermatology (#13). Cardiology, its largest therapy, grew 7% against a market growing 14%, so it is losing share there.",
                       ar("ajanta")),
        "rnd": note("R&D is 4.6% of sales, focused on first-to-market branded generics (over half its 350+ launches were first to market). Plants are digitising (electronic batch records, predictive maintenance).",
                    ar("ajanta")),
        "quarter": note("Q1 FY27 revenue rose 25% and profit 31%, led by the US (+57%). Margin held near 27%.",
                        news("ajanta", "Q1 FY27")),
        "debt": note("Borrowings rose to ₹260 Cr but Ajanta holds net cash. Balance sheet is the strongest pillar.",
                     scr("ajanta")),
    },
    "ipca": {
        "growth": note("Revenue grew ~13% a year, but part of that is the Unichem acquisition (consolidated from FY24). Domestic sales are outgrowing the market (16% vs 13.5% in Sep 2026).",
                       scr("ipca"), news("ipca", "Sep-2026")),
        "margin": note("Margin recovered from 15% to ~21% (FY23–26) and 22.9% in Q1 FY27 as API prices normalised and material cost fell from 35.8% to 25.5% of sales. "
                       "Unichem, at ~11% margin, still pulls the group average down.",
                       scr("ipca"), news("ipca", "Unichem")),
        "returns": note("ROCE is only ~17% despite better margins because Ipca carries a large asset base (25 sites, ₹4,600 Cr fixed assets) and 353 inventory days. Returns rise only if assets work harder.",
                        scr("ipca")),
        "wc": note("Inventory of 353 days reflects API backward integration (holding raw materials and intermediates) and lumpy tender and export business.",
                   scr("ipca")),
        "cash": note("Cash conversion is close to 1x and USD loans are repaid, so cash is healthy; ₹700–800 Cr of new capex will absorb part of it.",
                     scr("ipca"), news("ipca", "Capex")),
        "cost": note("Employee cost rose ~2.3 points of sales FY22–26, the smallest rise of the six, and fell 1.4 points in Q1 FY27 as revenue grew faster.",
                     scr("ipca"), news("ipca", "Q1 FY27")),
        "geo": note("Domestic formulations are ~39% of revenue, with exports, API and Unichem making up the rest. Low US exposure means low tariff risk but also less US upside.",
                    scr("ipca")),
        "brands": note("Pain management is 53% of domestic sales (Zerodol family, HCQS), so Ipca depends on one therapy. Anti-malarials are shrinking.",
                       ar("ipca")),
        "rnd": note("R&D is only ~2.5% of sales; the strategy relies on API backward integration rather than new molecules.",
                    ar("ipca")),
        "quarter": note("Q1 FY27 was strong: revenue +21%, EBITDA +50%, margin 22.9%, and guidance was raised to 14–16% growth.",
                        news("ipca", "Q1 FY27")),
        "debt": note("Borrowings fell from ₹1,481 Cr to ₹809 Cr and Ipca holds net cash. Interest is now negligible.",
                     scr("ipca")),
    },
    "mankind": {
        "growth": note("Revenue grew ~16% a year, the fastest of the six, but part is acquired: Bharat Serums (BSV) has been included since October 2024. The core India Rx business still grows ahead of the market.",
                       scr("mankind"), news("mankind", "FY26")),
        "margin": note("Margin is high (~25%) thanks to India branded generics and consumer brands with strong pricing (gross margin ~72%). It rose to 26.3% in Q1 FY27 as BSV integration progressed.",
                       scr("mankind"), news("mankind", "Q1 FY27")),
        "returns": note("ROCE halved from 32% to 14% because the BSV purchase added large goodwill and intangibles to capital, plus interest of ₹644 Cr and D&A of ₹886 Cr. The business is fine; the deal has to earn its price.",
                        scr("mankind"), news("mankind", "FY26")),
        "wc": note("Cash cycle (117 days) is among the shortest of the six, because India trade generics and consumer brands sell through quickly.",
                   scr("mankind")),
        "cash": note("Cash from operations (₹3,121 Cr) is 1.6x profit, the strongest conversion of the six; it is being used to repay BSV debt.",
                     scr("mankind")),
        "cost": note("Employee cost rose ~3.2 points of sales (to ~22.7%) as BSV's specialist teams joined and the field force grew.",
                     scr("mankind")),
        "geo": note("About 79% of revenue is India prescriptions and 6% consumer healthcare; exports (incl. BSV) are 15%. Very low US risk, but exposed to Indian price controls and tax changes.",
                    scr("mankind")),
        "brands": note("Mankind leads its consumer categories by a wide margin (Prega News ~84%, Unwanted-72 68%) and is #1 in gynaecology. Chronic share rose from 28% to 39% over eight years, which steadies growth.",
                       ar("mankind")),
        "rnd": note("R&D is only ~2.5% of sales yet Mankind is buying high-risk innovation (CAR-T biotech ACTx). 32 plants, some small, add complexity.",
                    ar("mankind"), news("mankind", "Armed Cell")),
        "quarter": note("Q1 FY27 revenue rose 13% and margin rose 2.5 points to 26.3%; profit +29% despite a higher tax rate.",
                        news("mankind", "Q1 FY27")),
        "debt": note("Net debt is ₹3,377 Cr (0.9x EBITDA) after the BSV deal and falling; pledges on BSV shares are being released.",
                     news("mankind", "Q1 FY27"), news("mankind", "Releases pledge")),
    },
    "alkem": {
        "growth": note("Revenue grew only ~8.5% a year because Alkem is concentrated in acute therapies (antibiotics, gastro, pain) that grow slower than chronic, and its trade-generics business is flat.",
                       scr("alkem"), news("alkem", "Q1 FY27")),
        "margin": note("Margin is ~20%, below the industry average, because the acute mix carries lower margins and new businesses (Enzene contract manufacturing, Occlutech devices) are loss-making or breakeven. "
                       "Material cost fell sharply (42.3% to 29.1% of sales FY23–26), which helped.",
                       scr("alkem"), news("alkem", "Occlutech")),
        "returns": note("ROCE of 21% is above the six-company median, supported by large net cash, but held back by low-margin new ventures.",
                        scr("alkem")),
        "wc": note("Working-capital days rose from 31 to 123 since FY22 as inventory and receivables grew faster than sales.",
                   scr("alkem")),
        "cash": note("Cash from operations is steady at ~₹1,900–2,000 Cr a year; Alkem holds large cash and deposits (about ₹5,500 Cr net cash by company disclosures).",
                     scr("alkem")),
        "cost": note("Employee cost rose ~3.2 points of sales FY22–26 and jumped 16% in Q1 FY27 after adding 1,200 reps and staffing the contract-manufacturing business.",
                     scr("alkem"), news("alkem", "Q1 FY27")),
        "geo": note("India is ~68% of revenue, the US ~20%. The Daman plant, now classified OAI by the US FDA, supplies about 45% of US sales.",
                    scr("alkem"), news("alkem", "Daman")),
        "brands": note("Alkem is #1 in anti-infectives (13.4% share) with Pan, Clavam and Pan-D among India's top 15 brands. It is weak in faster-growing chronic therapies (diabetes #14, CNS #14).",
                       ar("alkem")),
        "rnd": note("21 plants; R&D ~4% of sales. The Daman FDA finding shows quality systems are the priority investment.",
                    ar("alkem"), news("alkem", "Daman")),
        "quarter": note("Q1 FY27 revenue rose 11% but profit fell 22% because the tax rate jumped to 30–32%.",
                        news("alkem", "Q1 FY27")),
        "debt": note("Borrowings are ₹2,047 Cr but cash and deposits are larger, so Alkem is effectively debt-free.",
                     scr("alkem")),
    },
    "glenmark": {
        "growth": note("Revenue grew ~8.4% a year FY22–26, but the base includes Glenmark Life Sciences (sold in FY24). FY26 jumped 27.5% because of the AbbVie licensing payment.",
                       scr("glenmark"), news("glenmark", "FY26")),
        "margin": note("FY26 margin of 26.9% is inflated by AbbVie licensing income (US$700M upfront). Management's normal margin is 21–22%.",
                       scr("glenmark"), news("glenmark", "FY27 margin guidance")),
        "returns": note("ROCE of 40% is a one-off driven by licensing income. Excluding it, returns are closer to the peer median.",
                        scr("glenmark")),
        "wc": note("Cash cycle is the shortest of the six (83 days), but only because payables are stretched to 288 days; debtor days (107) and inventory (264) are high.",
                   scr("glenmark")),
        "cash": note("Cash from operations was ₹3,445 Cr in FY26 (2.5x profit) because of the licensing cash. Borrowings fell from ₹4,608 Cr (FY23) to ₹594 Cr.",
                     scr("glenmark")),
        "cost": note("Employee cost rose from 14.7% to 21.2% of sales FY22–26, the largest rise of the six, as Glenmark built specialty and innovation teams.",
                     scr("glenmark")),
        "geo": note("India ~36%, North America ~27%, Europe ~19%, emerging markets ~18%. North America is lifted by deferred licensing income.",
                    scr("glenmark")),
        "brands": note("Glenmark is #2 in dermatology and #3 in respiratory in India; Ryaltris is its top global brand. Diabetes share is slipping.",
                       ar("glenmark")),
        "rnd": note("R&D ~6.5% of sales, including the innovation unit (IGI) that burns ~US$70M a year but produced the AbbVie deal.",
                    ar("glenmark")),
        "quarter": note("Q1 FY27 revenue rose 23% (core above 18%); margin ~20% excluding licensing.",
                        news("glenmark", "Q1 FY27")),
        "debt": note("Debt is close to zero after the licensing payment and the Life Sciences sale.",
                     scr("glenmark")),
    },
}

SCR_ALL = {"title": "Screener.in consolidated financials", "url": "https://www.screener.in/"}
IND = {"title": "Industry benchmark: Nifty Pharma constituents (Screener.in)", "url": "https://www.5paisa.com/hindi/nifty-pharma-stock-list"}
IQVIA = {"title": "HDFC Sky: IPM grew 10% in FY26 (citing IQVIA)", "url": "https://hdfcsky.com/news/pharmaceuticals-ipm-11-percent-growth-in-mar-26"}

PEER = {
    "cmd_tiles": note("The six grow about as fast as the industry, but their middle margin and ROCE sit slightly below the Nifty Pharma average, which includes large, more global players such as Sun Pharma and Divi's. "
                      "The cash cycle is the clearest gap: two companies (Alembic, Ipca) hold far more inventory than the industry.", SCR_ALL, IND),
    "cmd_map": note("Companies in the top-right (Ajanta, Mankind) combine branded India or chronic portfolios with pricing power. Alembic and Alkem sit bottom-left: Alembic because R&D and new plants weigh on margin, "
                    "Alkem because of its acute and trade-generics mix. Glenmark's position is flattered by one-off licensing income.", SCR_ALL),
    "rt_table": note("Green and red mark best and weakest of the six. The Industry column is the Nifty Pharma average, so a company can be best of six and still below the industry.", SCR_ALL, IND),
    "rt_trend_roce": note("Ajanta has risen steadily on margin. Mankind fell sharply after the BSV acquisition added goodwill to capital. Glenmark's FY26 spike is licensing income. Alembic is flat because new plants are not yet full.", SCR_ALL),
    "rt_trend_roe": note("ROE follows ROCE. Companies with little debt (Ajanta, Ipca) have ROE close to ROCE; borrowing would lift ROE without improving the business.", SCR_ALL),
    "rt_trend_roic": note("ROIC is after-tax return on the money invested in operations. Above about 12% (a typical cost of capital for Indian pharma) the company creates value; below it, growth destroys value.", SCR_ALL),
    "rt_trend_ebitda_margin": note("Margins rose across the industry from FY23 as API and freight costs eased after the pandemic. Companies with branded India portfolios (Ajanta, Mankind) sit highest.", SCR_ALL, IND),
    "rt_trend_inventory_days": note("API-integrated companies (Alembic, Ipca) hold more stock because they carry raw materials and intermediates as well as finished goods.", SCR_ALL),
    "rt_trend_debtor_days": note("Debtor days rise when US sales or distributor credit grow. Ajanta's jump (93 to 124) is the sharpest move in FY26.", SCR_ALL),
    "rt_trend_ccc": note("Cash cycle = inventory + debtor days − payable days. Glenmark's low figure comes from stretching suppliers, which is not sustainable.", SCR_ALL),
    "rt_trend_de_ratio": note("Debt is low across the set. Mankind rose after the BSV deal; Alembic after funding new plants.", SCR_ALL),
    "rt_trend_cfo_pat": note("Below 1x means profit is not arriving as cash. Ajanta's 0.5x in FY26 is the warning sign; Glenmark's high figure is licensing cash.", SCR_ALL),
    "rt_trend_asset_turnover": note("Sales per rupee of assets. Mankind dropped after the BSV deal added assets; Ajanta and Glenmark are highest.", SCR_ALL),
    "rt_trend_interest_cover": note("Times operating profit covers interest. Very high values mean almost no debt; Mankind's ~4x is the lowest but still safe.", SCR_ALL),
    "rt_trend_fcf_margin": note("Free cash flow here is cash from operations minus all investing (capex, acquisitions, investments), as a share of sales. Big deal years show as negative.", SCR_ALL),
    "rt_dupont": note("ROE = profit margin × asset turnover × equity multiplier. Ajanta wins on margin; Mankind's weak spot is asset turnover after BSV; Glenmark uses more liabilities.", SCR_ALL),
    "rg_fda": note("FDA status decides whether US launches continue. Alkem's Daman OAI is the only open issue; Glenmark and Ajanta have just cleared theirs.", {"title": "US FDA warning letters", "url": "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters"}),
    "rg_anda": note("More approvals do not mean more revenue: Ajanta earns about 2.3x more US revenue per product than Alembic by choosing products with few competitors.", SCR_ALL),
    "rg_rnd": note("Higher R&D spend currently goes with lower margins because the payoff from new filings arrives years later.", SCR_ALL),
    "nw_timeline": note("Regulatory and policy news (FDA, tariffs) moved these companies more than quarterly results did in the last six months.", SCR_ALL),
    "nw_heat": note("US revenue and EBITDA margin are the two numbers most affected by news; Alkem is the only company with net negative news.", SCR_ALL),
    "st_map": note("Each number counts how many of a company's five problem statements need that type of consulting help; Digital shows how far behind the company is.", SCR_ALL),
    "pl_scatter": note("Each dot is one company in one year. With 30 points this is more reliable than one company's 5 years, but it mixes very different business models.", SCR_ALL),
    "market": note("The Indian pharma market grew ~10% in FY26 (volume 2.7%, price 4.4%, new products 2.8%), with chronic (~14%) well ahead of acute (~8%).", IQVIA),
}

out = {"company": COMPANY, "peer": PEER}
json.dump(out, open(ROOT / "data" / "notes.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(sum(len(v) for v in COMPANY.values()), "company notes,", len(PEER), "peer notes")

# What each company is already doing, per theme (from results, filings and news in the dataset).
DOING = {
    "alembic": {"growth": "Raised FY27 growth guidance to mid-teens; ~15 more US launches planned; 10 approvals and 7 launches in Q1 FY27.",
                "margin": "Moving the pipeline to complex products (Ciprodex, injectables) that earn more; no public plan yet to cap R&D spend.",
                "returns": "Ramping complex launches from the new plants; no public utilisation target.",
                "wc": "No public working-capital target; analysts flagged it at the Sep 2026 investor meetings.",
                "cash": "Borrowing to fund capex (debt ₹1,430 Cr); no public cash-release plan.",
                "cost": "Added R&D scientists and sales force; no public cost programme.",
                "geo": "Growing API (+33%) and ex-US markets (+17%) to reduce US dependence.",
                "brands": "Pushing specialty (28% of India) and animal health (22%, fastest growing).",
                "rnd": "R&D at 9-11% of sales focused on complex generics; 279 ANDAs filed.",
                "quarter": "Guidance raised after Q1 FY27.", "debt": "Debt-funded capex; interest cost +17%."},
    "ajanta": {"growth": "Scaling US (+57% in Q1 FY27); new India launches beat the market by 76%.",
               "margin": "Lower material cost (22% of sales) and US products with few competitors.",
               "returns": "Keeps capex modest and returns surplus cash (buybacks, ₹400 Cr dividend).",
               "wc": "Using digital supply tools for forecasting; no public receivables target.",
               "cash": "Paid a ₹400 Cr interim dividend; no public cash-conversion target.",
               "cost": "Digitising (SAP workflows, eBMR) and automating lines (manual work cut ~50% on one line).",
               "geo": "Diversified across India, US, Africa and Asia; Asia turnaround not yet announced.",
               "brands": "Climbing in dermatology (#16 to #13); ophthalmology #1.",
               "rnd": "R&D fully digitised and integrating AI models; Paithan plant cleared by FDA (VAI).",
               "quarter": "Q1 FY27 revenue +25%, profit +31%.", "debt": "Near-zero net debt."},
    "ipca": {"growth": "Guidance raised to 14-16% growth; domestic outgrowing the market.",
             "margin": "API recovery and Unichem source transfer; guidance of 23% margin for FY27.",
             "returns": "Repaid USD loans; new capex of ₹700-800 Cr for API plants.",
             "wc": "No public inventory target.", "cash": "Repaid all USD loans.",
             "cost": "Personnel cost down 1.4 points of sales in Q1 FY27.", "geo": "Building US/EU filings (4-5 a year).",
             "brands": "Pushing chronic (+17%) to reduce reliance on pain.", "rnd": "Biotech R&D capex announced.",
             "quarter": "Q1 FY27 EBITDA +50%.", "debt": "Borrowings down to ₹809 Cr; net cash."},
    "mankind": {"growth": "Launched 'Vistar' division and bought Rivotril (CNS); exports +34.5%.",
                "margin": "Margin up 2.5 points in Q1 FY27 as BSV integrates.",
                "returns": "Repaying BSV debt (net debt 0.9x EBITDA); pledge on BSV shares released.",
                "wc": "Short cash cycle already (117 days).", "cash": "Using strong cash flow to repay debt.",
                "cost": "SAP S/4HANA and data lake for supply chain and sales productivity.",
                "geo": "Growing exports through BSV.", "brands": "Raising chronic share (28% to 39% since FY18).",
                "rnd": "AI drug-discovery tie-up; bought 70% of CAR-T biotech ACTx.",
                "quarter": "Q1 FY27 profit +29%.", "debt": "Debt being repaid; pledges released."},
    "alkem": {"growth": "Early semaglutide launch (~11% unit share); added 1,200 reps; chronic outgrowing market.",
              "margin": "Lower material cost; new ventures (Enzene, Occlutech) still breakeven or loss-making.",
              "returns": "Holds large net cash; buying into devices (Occlutech).",
              "wc": "No public working-capital target.", "cash": "Cash from operations steady at ~₹2,000 Cr.",
              "cost": "Added 1,200 reps in Q1 FY27 (employee cost +16%).",
              "geo": "Remediating Daman after the FDA OAI (6-12 months expected).",
              "brands": "Building chronic around semaglutide and diabetes.", "rnd": "Daman remediation under way.",
              "quarter": "Q1 FY27 profit −22% on higher tax.", "debt": "Effectively debt-free."},
    "glenmark": {"growth": "13 US launches in FY26; first generic Flovent HFA with 180-day exclusivity.",
                 "margin": "Guiding 21-22% normal margin despite input inflation.",
                 "returns": "Cut debt to ₹594 Cr using the AbbVie payment.",
                 "wc": "Target of net working capital below 115 days.", "cash": "Repaid debt with licensing cash.",
                 "cost": "No public cost programme.", "geo": "Ryaltris in 55+ markets; Europe branded shift.",
                 "brands": "Launching semaglutide, Tevimbra, Brukinsa in India.", "rnd": "IGI innovation unit; out-licensed ISB 2001.",
                 "quarter": "Q1 FY27 core growth above 18%.", "debt": "Debt close to zero."},
}
for cid, themes in DOING.items():
    for th, txt in themes.items():
        if th in out["company"][cid]:
            out["company"][cid][th]["doing"] = txt
json.dump(out, open(ROOT / "data" / "notes.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("doing lines added")
