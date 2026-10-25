"""Builds data/notes_majors.json: plain-English analyst notes for the Pharma Majors peer set.
Each note: text (what is happening), doing (what the company is doing), angle (where a consultant can help),
show (only notes useful to a consultant appear on screen; all feed the analyst), sources.
Run after build_majors.py: python research/build_majors_notes.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "data" / "companies_majors.json", encoding="utf-8"))
SRC = {c["id"]: c for c in D["companies"]}
SYM = {"sun": "SUNPHARMA", "drreddy": "DRREDDY", "cipla": "CIPLA", "lupin": "LUPIN", "aurobindo": "AUROPHARMA", "zydus": "ZYDUSLIFE"}


def scr(cid):
    return {"title": f"Screener.in: {SRC[cid]['short']} consolidated financials", "url": f"https://www.screener.in/company/{SYM[cid]}/consolidated/"}


def src(cid, *idx):
    """Screener plus the company's brand/news sources picked by index."""
    out = [scr(cid)]
    c = SRC[cid]
    pool = c["brands"].get("sources", []) + [{"title": n["title"][:80], "url": n["url"]} for n in c["news"]]
    for i in idx:
        if i < len(pool):
            out.append(pool[i])
    return out


def n(text, doing, angle, show, sources):
    return {"text": text, "doing": doing, "angle": angle, "show": show, "sources": sources}


C = {
"sun": {
 "growth": n("Sales grew about 11% a year (FY22 to FY26). India (+16% in Q1 FY27) and innovative medicines (+12.8%) are growing, while US generics shrink (−9.7%) as lenalidomide fades.",
             "Guiding high single-digit growth for FY27; buying Organon (about US$6.2 bn of sales) to add scale.",
             "Organon integration and a clear plan for the shrinking US generics book.", True, src("sun", 0, 2, 5)),
 "margin": n("Margin is high (about 28%) because India brands and innovative medicines earn more than generics. Raw material cost fell from 36% to 26% of sales. Launch spending on Leqselvi and Unloxcyt held Q1 FY27 profit growth to under 3%.",
             "Spending to launch innovative products; tax rate about 27.8% until Organon closes.",
             "Launch payback review: scale or stop each innovative product on clear milestones.", True, src("sun", 1, 2)),
 "returns": n("ROCE rose from 17% to 21% as margins improved. Sun holds about ₹12,400 Cr of net cash, which lowers returns on paper; Organon will add large debt and goodwill.",
              "Using cash and debt for Organon.", "Post-deal returns plan so ROCE does not fall the way Mankind's did after BSV.", True, src("sun", 3, 5)),
 "wc": n("Sun holds 363 days of stock, high for a company this size, and it has risen from 315 days in FY22. Suppliers are paid in 232 days, which hides some of it.",
         "No public stock target.", "Inventory programme across 40 sites with a cash target.", True, src("sun")),
 "cash": n("Cash from operations is about 1.1 times profit and the company had about ₹12,400 Cr net cash before Organon. Free cash flow dipped in FY26 as investments rose.",
           "Holding cash for Organon.", "", True, src("sun", 3)),
 "cost": n("Staff cost rose from about 11.7% to 14.0% of sales over FY24 to FY26 as Sun built US specialty teams. Other expenses (27% of sales) include heavy launch marketing.",
           "Investing in specialty sales teams in the US.", "Specialty sales force sizing and marketing return review.", True, src("sun")),
 "geo": n("India is 33% of sales, US formulations 29%, emerging markets 19% and rest of world 15%. The US generics share keeps falling while innovative medicines rise.",
          "Organon adds women's health and biosimilars in about 140 countries.", "Country portfolio review after Organon: where to invest, where to exit.", True, src("sun", 2)),
 "brands": n("Sun leads India with 8.5% share and 30 brands in the top 300. It is #1 with psychiatrists, neurologists, cardiologists, gastroenterologists, diabetologists and dermatologists.",
             "Growing India share (8.1% to 8.5%).", "", True, src("sun", 0)),
 "rnd": n("R&D is 6.1% of sales, with 30% on innovative medicines. 40 plants worldwide; Halol is still OAI with the US FDA and under an import alert.",
          "Specialty pipeline: Leqselvi, Unloxcyt, Ilumya; semaglutide in India and South Africa.", "Halol remediation and an R&D portfolio review.", True, src("sun", 0)),
 "quarter": n("Q1 FY27 sales +10.1% and profit +27%, but EBITDA only +2.7% as launch costs rose.", "Guidance unchanged.", "", False, src("sun", 2)),
 "debt": n("Almost no net debt today. Organon (US$11.75 bn) will change that at close.", "Planning deal financing.", "", False, src("sun", 5)),
},
"drreddy": {
 "growth": n("Sales grew about 12% a year to FY25, then only 3% in FY26 as US lenalidomide (generic Revlimid) ended. India (+16%) and emerging markets (+23%) are growing; North America fell 22%.",
             "Semaglutide relaunch in Nov 2026; biosimilars (abatacept goal date 22 Dec 2026).",
             "Size the lenalidomide gap and rank the replacements by value and timing.", True, src("drreddy", 1, 2, 3)),
 "margin": n("Margin fell from 28% (FY24) to 19% (FY26), and to 5% in Q4 FY26 and 11% in Q1 FY27. The high-profit US product ended and a semaglutide API problem cost ₹240 Cr.",
             "Guiding 20%+ EBITDA margin for FY27.", "Cost reset for a smaller US business, plus supply-risk control for launches.", True, src("drreddy", 0, 2)),
 "returns": n("ROCE halved from 27% to 13% as profit fell while capital stayed. Returns recover only if new launches replace lenalidomide profit.",
              "Cut capex to ₹1,600 to 1,700 Cr.", "Capital allocation review: which bets earn above the cost of capital.", True, src("drreddy", 0)),
 "wc": n("Cash cycle is about 247 days. Debtor days (110) are high because US and emerging-market customers take longer to pay.",
         "No public target.", "Collections and inventory programme by market.", True, src("drreddy")),
 "cash": n("Cash from operations is 1.4 times profit and Dr Reddy's still holds net cash (US$261 M in Sep 2026), but free cash flow has been negative for two years.",
           "Lowered capex.", "", True, src("drreddy", 0)),
 "cost": n("Staff cost is about 17% of sales and other expenses rose to 20%. Costs were built for a larger US business.",
           "No public cost programme.", "Zero-based cost review across SG&A and US infrastructure.", True, src("drreddy", 0)),
 "geo": n("North America is 34% of sales (down from about 45%), emerging markets 20%, India 19%, Europe 17% (with acquired NRT brands) and API 10%.",
          "Shifting growth to India and emerging markets.", "Market prioritisation and India sales-force productivity.", True, src("drreddy", 2)),
 "brands": n("India rank #9 to #10 with 15 brands in the top 300. New engines: semaglutide (Obeda), NRT brands in Europe, QDENGA dengue vaccine.",
             "Launched semaglutide in India on day one.", "", True, src("drreddy", 0)),
 "rnd": n("R&D was cut 12% to 7.2% of sales in FY26 and is guided back to 7 to 8%. Pipeline: semaglutide (10 countries), abatacept and rituximab biosimilars.",
          "Abatacept FDA decision 22 Dec 2026.", "Biosimilar launch plan with a backup if the FDA asks for more data.", True, src("drreddy", 0, 1)),
 "quarter": n("Q1 FY27 profit fell 69% and Q2 FY27 profit fell 36%; Q2 margin recovered to 20.6%.", "Semaglutide relaunch in Nov 2026.", "", False, src("drreddy", 1, 3)),
 "debt": n("Still net cash, though borrowings rose to about ₹7,700 Cr.", "Holding net cash.", "", False, src("drreddy")),
},
"cipla": {
 "growth": n("Sales grew only about 7% a year. India is strong (record ₹3,452 Cr in Q1 FY27, +12%), but US sales fell 28% in dollars as lenalidomide ended and lanreotide supply broke.",
             "Generic Advair (Jul 2026) and Ventolin approvals; target US$1 bn US run-rate by end FY27.",
             "US launch excellence for inhalers and a supply fix for lanreotide.", True, src("cipla", 2, 3, 4)),
 "margin": n("Margin dropped from about 26% to 16.7% (Q1 FY27): the high-profit US products fell away and gross margin fell 6 points.",
             "Guiding 18.5 to 20% for FY27, weighted to H2.", "Margin bridge and procurement programme.", True, src("cipla", 4)),
 "returns": n("ROCE fell from 23% to 15% as US profit fell. Over ₹10,500 Cr of net cash also lowers returns.",
              "Holding large cash.", "Capital allocation plan: in-licensing, M&A or payouts.", True, src("cipla", 5)),
 "wc": n("Inventory rose from 217 to 252 days (FY24 to FY26); cash cycle 202 days, the second-lowest of the six but rising.",
         "No public target.", "Inventory release with S&OP, especially Africa and US launch stock.", True, src("cipla")),
 "cash": n("Cash from operations is about equal to profit and Cipla has over ₹10,500 Cr net cash.", "Debt-free.", "", True, src("cipla", 5)),
 "cost": n("Staff cost rose from 13.9% to 17.6% of sales (FY22 to FY26), the biggest rise of the six, as sales grew slowly.",
           "New CEO from Apr 2026.", "Organisation and cost review under the new CEO.", True, src("cipla", 6)),
 "geo": n("India is 45% of sales, North America 24%, Africa 15% and emerging markets and Europe 13%.", "Building a US-made inhaler franchise (InvaGen, New York).",
          "Tariff-proof US supply plan.", True, src("cipla", 3)),
 "brands": n("India respiratory leader; Foracort crossed ₹1,000 Cr. Branded Rx grew 15.4% in Q1 FY27.", "Partnerships: Lilly (Yurpeak), MannKind (inhaled insulin).",
             "", True, src("cipla", 0)),
 "rnd": n("R&D is about 7% of sales. Pithampur, a key inhaler plant, has been under an FDA warning letter since Nov 2023 and got 7 new observations in Aug 2026.",
          "Responding to the FDA; Goa VAI.", "Remediation PMO and a second site for key inhalers.", True, src("cipla", 2)),
 "quarter": n("Q1 FY27 profit fell 39% on the US drop; India hit a record.", "H2 recovery guided.", "", False, src("cipla", 4)),
 "debt": n("Debt-free with over ₹10,500 Cr net cash.", "", "", False, src("cipla", 5)),
},
"lupin": {
 "growth": n("Sales grew about 14% a year and 23% in FY26, led by US products with few competitors (tolvaptan, mirabegron). Those now face competition, so FY27 growth is guided to high single digits.",
             "FY28 launches: ranibizumab, Dulera, a new apixaban form.", "Launch sequencing to bridge FY27 to FY28.", True, src("lupin", 0, 1)),
 "margin": n("Lupin's margin went from about 1% in FY22 to 29% in FY26, one of the biggest turnarounds among large Indian drugmakers. Material cost fell from 38% to 25% of sales. FY27 margin is guided to about 25%.",
             "Guiding about 25% margin.", "Margin bridge by product so the reset is no worse than guided.", True, src("lupin", 0, 1, 2)),
 "returns": n("ROCE of 30% is the best of the six, at the lowest P/E (14.8x). The market expects the US profit to fade.",
              "Paid a 900% dividend.", "Investor story on FY28 launches to close the valuation gap.", True, src("lupin", 2)),
 "wc": n("Inventory rose from 261 to 303 days, but suppliers are paid in 208 days, so the cash cycle fell to 181 days, the best of the six.",
         "Working capital 90 days on company basis (Q1 FY27).", "Inventory programme before supplier terms tighten.", True, src("lupin", 1)),
 "cash": n("Cash from operations is 1.4 times profit. Net cash fell from ₹4,636 Cr to ₹2,831 Cr after buying VISUfarma.", "Acquired VISUfarma.", "", True, src("lupin", 1)),
 "cost": n("Staff cost fell from 16.3% to 13.0% of sales as sales grew faster than headcount: classic operating leverage.",
           "Holding costs while sales grew.", "", True, src("lupin")),
 "geo": n("US is 42% of sales, India 30%, emerging markets 13%, other developed markets 11% and API 4%. High US share means high tariff and price-erosion risk.",
          "Guiding US sales above US$1 bn in FY27.", "US price-erosion and tariff scenarios.", True, src("lupin", 2)),
 "brands": n("India #8 with chronic at about 67% of India sales; diabetes grew 31.8% (1.8x the market) in Q1 FY27.",
             "Pushing chronic therapies.", "India field-force productivity to lift growth above the market.", True, src("lupin", 1)),
 "rnd": n("R&D is 7.5% of sales; pipeline of 30+ injectables and 20+ respiratory products. Pithampur Unit II is OAI with the US FDA.",
          "Remediation in progress; Ankleshwar and Somerset VAI.", "Remediation PMO for Pithampur.", True, src("lupin", 1)),
 "quarter": n("Q1 FY27 sales +33%, margin 30%; competition expected from Q2.", "", "", False, src("lupin", 1)),
 "debt": n("Net cash about ₹2,831 Cr after VISUfarma.", "", "", False, src("lupin", 1)),
},
"aurobindo": {
 "growth": n("Sales grew about 9% a year; Q1 FY27 +16% led by Europe (+25.6%) and growth markets (+37.7%). US grew 8%.",
             "Bought Lannett (US) for US$250 M; target US$2 bn US sales.", "Lannett integration and plant-loading plan.", True, src("aurobindo", 0, 3, 4)),
 "margin": n("Margin is about 20%, among the lowest of the six, because Aurobindo sells high-volume, low-price generics and API. Material cost is 48% of sales, the highest in the set.",
             "Steady 20 to 21% margin.", "Procurement programme on APIs and intermediates.", True, src("aurobindo", 3)),
 "returns": n("ROCE is 13% and ROIC about 8%, the lowest of the six and below a typical 12% cost of capital. Lots of plants and stock earn modest margins.",
              "Buyback of US$85 M.", "Returns programme: prune low-margin products and consolidate sites.", True, src("aurobindo", 3)),
 "wc": n("Inventory rose from 272 to 326 days, the highest of the six. Cash cycle 252 days.", "No public target.",
         "Inventory diagnostic and S&OP across the global network.", True, src("aurobindo")),
 "cash": n("Cash from operations is 1.6 times profit and free cash flow was US$98 M in Q1 FY27. Net cash shrank to US$42 M after Lannett and the buyback.",
           "Cash discipline maintained.", "", True, src("aurobindo", 3)),
 "cost": n("Staff cost is only about 10% of sales, the lowest of the six; material cost (48%) is the line that matters.",
           "", "Spend analytics on API and packaging.", True, src("aurobindo")),
 "geo": n("US formulations are 43% of sales, Europe 31%, API 12%, growth markets 10% and ARV 4%. Europe is now the growth engine.",
          "Top-10 generic company in 8 European countries.", "Europe biosimilars go-to-market.", True, src("aurobindo", 0)),
 "brands": n("A generics company rather than a brand company: almost no India branded business. Biosimilars (Zefylti, Dyrupeg, Dazublys, Bevqolva) are the new value layer.",
             "Biosimilars approved in the EU, UK and Canada; STADA licensing deal.", "Biosimilar pricing and partner strategy by country.", True, src("aurobindo", 0)),
 "rnd": n("R&D is about 4.5% of sales, the lowest of the six. 896 ANDAs filed and 737 approved. Eugia Unit-I got an FDA warning letter in Aug 2026.",
          "Says US supply continues.", "Quality programme for sterile injectables.", True, src("aurobindo", 2)),
 "quarter": n("Q1 FY27 revenue +16% and profit +25%.", "", "", False, src("aurobindo", 3)),
 "debt": n("Close to net cash (US$42 M) after Lannett.", "", "", False, src("aurobindo", 3)),
},
"zydus": {
 "growth": n("Sales grew about 15.5% a year, the fastest of the six, helped by acquisitions (Amplitude, Assertio, consumer brands). India branded +15%; US generics fell 2.6% in Q1 FY27.",
             "Guiding strong double-digit growth; 30 to 40 US launches.", "Split bought growth from own growth and track each deal.", True, src("zydus", 2, 3, 4)),
 "margin": n("FY26 margin of 31% was the best of the six, but Q1 FY27 fell to 24.1% as acquired businesses added staff, other costs, amortisation and interest.",
             "Guiding 24%+ for FY27 and 28 to 30% by FY30.", "Synergy and cost plan for the acquired businesses.", True, src("zydus", 2)),
 "returns": n("ROCE fell from 24% to 21% and ROIC from 23% to 17% as acquisitions added capital before profit.", "Buyback of ₹1,100 Cr.",
              "Deal-by-deal return tracking.", True, src("zydus", 5)),
 "wc": n("Inventory jumped from 227 to 282 days in FY26, partly from acquired businesses.", "No public target.", "Inventory programme across acquired units.", True, src("zydus")),
 "cash": n("Cash from operations was only 0.4 times profit in FY26 and free cash flow was −21% of sales, as deals and capex used cash. Net debt is now 0.7x EBITDA.",
           "Capex ₹1,500 to 1,600 Cr guided.", "Capital allocation rules for deals, capex and buybacks.", True, src("zydus", 2)),
 "cost": n("Staff cost rose to 17% of sales and jumped 38% in Q1 FY27 with acquisitions.", "", "Organisation design after the deals.", True, src("zydus", 2)),
 "geo": n("North America 44%, India 25%, consumer wellness 15%, international 11%, medtech 3%.", "Raising US specialty share from about 10% to 15%+.",
          "US specialty launch excellence.", True, src("zydus", 3)),
 "brands": n("Consumer brands lead their categories (Glucon-D, Nycil, Sugar Free); India chronic share 46.3%; first US ranibizumab biosimilar (Nufymco).",
             "Launching biosimilars in the US and India.", "", True, src("zydus", 0)),
 "rnd": n("R&D is 8.4% of sales, the highest of the six. Saroglitazar (PBC) is under FDA priority review; Biotech Park injectables VAI.",
          "Priority review; Phase III biosimilar ADC.", "R&D portfolio analytics to rank bets.", True, src("zydus", 1)),
 "quarter": n("Q1 FY27 revenue +22% but profit −36%.", "", "", False, src("zydus", 2)),
 "debt": n("Net debt 0.7x EBITDA after acquisitions.", "", "", False, src("zydus", 2)),
},
}

PEER = {
 "cmd_tiles": n("The majors are bigger and more global than the mid-size six, but their typical ROCE (about 18%) is close to the Nifty Pharma average. Inventory is the shared weak spot: four of six hold over 280 days.",
                "", "Working capital is the quickest cash win across the group.", True, []),
 "cmd_map": n("Top right: Zydus (fast growth, high margin, partly bought) and Lupin (turnaround). Lower half on margin: Cipla and Dr Reddy's, both hit by the end of US lenalidomide, and Aurobindo (low-margin volume generics). Sun sits in the middle with the most scale.",
              "", "Cipla, Dr Reddy's and Aurobindo are the clearest consulting targets.", True, []),
 "rt_table": n("Green and red mark the best and weakest of the six. A company can be best of six and still below the industry.", "", "", False, []),
 "rt_trend_roce": n("Lupin rose from a loss to 30%. Dr Reddy's fell from 27% to 13% and Cipla from 23% to 15% as US lenalidomide ended. Aurobindo stays at about 13%.",
                    "", "Dr Reddy's, Cipla and Aurobindo need a returns plan.", True, []),
 "rt_trend_roe": n("ROE follows ROCE; debt is low across the set.", "", "", False, []),
 "rt_trend_roic": n("ROIC is the after-tax return on money put into the business. Above about 12% a company creates value. Aurobindo (about 8%) and Dr Reddy's (about 9%) are below it.",
                    "", "Below-12% companies need a returns plan before chasing growth.", True, []),
 "rt_trend_ebitda_margin": n("Margins diverged in FY26: Zydus, Lupin and Sun near 28 to 31%; Dr Reddy's, Cipla and Aurobindo near 19 to 21%.", "",
                             "The gap is mostly product mix: limited-competition and branded products earn more.", True, []),
 "rt_trend_inventory_days": n("Sun (363 days) and Aurobindo (326 days) hold the most stock; all six hold more than 220 days.", "",
                              "Each 30 days of stock cut frees cash worth about 8% of yearly material cost.", True, []),
 "rt_trend_debtor_days": n("Dr Reddy's (110 days) and Sun (97 days) wait longest to be paid; Cipla (73) and Zydus (73) the least.", "", "Dr Reddy's is the clearest collections case.", True, []),
 "rt_trend_ccc": n("Cash cycle = stock days + customer days − supplier days. Lupin's 181 days is the best; Aurobindo and Dr Reddy's (about 250) the worst.", "",
                   "Aurobindo and Dr Reddy's have the most cash locked up.", True, []),
 "rt_trend_de_ratio": n("Debt is low except Zydus, which rose to 0.5 after acquisitions. Sun will add large debt for Organon.", "", "", False, []),
 "rt_trend_cfo_pat": n("Below 1 means profit is not arriving as cash. Zydus fell to 0.4 in FY26 (acquisitions and working capital).", "", "Zydus needs a cash conversion review.", True, []),
 "rt_trend_asset_turnover": n("Sales per rupee of assets is low (0.5 to 0.7) for all six: big plant networks and cash piles.", "", "", False, []),
 "rt_trend_interest_cover": n("Interest is small for all; Zydus's cover fell after deals.", "", "", False, []),
 "rt_trend_fcf_margin": n("Free cash flow = cash from operations minus all investing (plants, deals). Zydus (−21%) and Dr Reddy's were negative in FY26.", "", "", False, []),
 "rt_dupont": n("ROE = profit margin × sales per rupee of assets × borrowing. Lupin wins on margin; Aurobindo is held back by low margin; Sun by idle cash.", "",
                "Shows which lever to pull: price and cost, asset use, or funding.", True, []),
 "rg_fda": n("Four of six have an open US FDA issue: Sun (Halol), Cipla (Pithampur), Lupin (Pithampur Unit II) and Aurobindo (Eugia Unit-I).", "",
             "Quality remediation is a group-wide consulting theme for the majors.", True, []),
 "rg_anda": n("More approvals do not mean more profit: Aurobindo has the biggest US book (737 approvals) but the lowest returns; Lupin earns more from fewer, harder products.", "",
              "Product selection is worth more than filing volume.", True, []),
 "rg_rnd": n("Higher R&D does not guarantee higher margin today: Zydus and Lupin show the payoff, Dr Reddy's shows the gap when a big product ends first.", "",
             "Ask for the payback on each R&D bet.", True, []),
 "nw_timeline": n("Results misses (Dr Reddy's, Cipla) and FDA actions moved these stocks most in the last six months.", "", "", False, []),
 "nw_heat": n("US revenue and EBITDA margin are the numbers most affected by news.", "", "", False, []),
 "st_map": n("Each number counts how many of a company's five problems need that type of consulting help.", "", "", False, []),
 "pl_scatter": n("Each dot is one company in one year, so the pattern uses 30 points instead of 5.", "", "", False, []),
 "market": n("The Indian pharma market grew about 10% in FY26, with chronic therapies ahead of acute.", "", "", False, []),
}

out = {"company": C, "peer": PEER}
json.dump(out, open(ROOT / "data" / "notes_majors.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("notes:", sum(len(v) for v in C.values()), "company,", len(PEER), "peer")
