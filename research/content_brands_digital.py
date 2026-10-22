"""Adds brands, therapy ranking and the digitisation roadmap (with evidence and gaps) to data/companies.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "data" / "companies.json"

S = {  # sources
    "mankind_ip": {"title": "Mankind Pharma Q1 FY27 investor presentation (NSE, 30 Jul 2026)", "url": "https://nsearchives.nseindia.com/corporate/MANKIND1_30072026154612_CoveringIP.pdf"},
    "mankind_acc": {"title": "CIMdata: Accenture accelerates Mankind Pharma's digital transformation (May 2021)", "url": "https://www.cimdata.com/de/industry-summary-articles/item/15657-accenture-accelerates-mankind-pharma-s-digital-transformation-with-data-driven-cloud-platform"},
    "mankind_q1": {"title": "ScanX: Mankind Pharma Q1 results (Vistar division, AI drug-discovery tie-up)", "url": "https://scanx.trade/stock-market-news/companies/mankind-pharma-q1-results-consol"},
    "alkem_ar24": {"title": "Alkem digital annual report 2023-24: strategic priorities", "url": "https://www.alkemlabs.com/investors/digital-annual-report-2023-24/strategic-priorities.html"},
    "alkem_q2": {"title": "Alkem Q2 FY26 results presentation (Nov 2025)", "url": "https://admin.alkemlabs.com/uploads/Q2_FY_26_Results_Presentation_f934fcbd85.pdf"},
    "ajanta_ar26": {"title": "Ajanta Pharma annual report 2025-26 (NSE)", "url": "https://nsearchives.nseindia.com/annual_reports/AR_29404_AJANTPHARM_2025_2026_A_9211972_18062026105542.pdf"},
    "ajanta_web": {"title": "Ajanta Pharma: India branded generics", "url": "https://ajantapharma.com/ajanta/Business/india_branded_generics"},
    "ipca_ar25": {"title": "Ipca Laboratories annual report 2024-25", "url": "https://ipca.com/wp-content/pdf/financials/annual-reports/annual_report_2024_25.pdf"},
    "ipca_cp24": {"title": "Ipca corporate presentation (June 2024)", "url": "https://www.ipca.com/wp-content/pdf/financials/corporate-presentation/ipca-corporate-presentation-june-2024.pdf"},
    "glen_mda": {"title": "Glenmark management discussion & analysis, Q4 FY26", "url": "https://glenmark.b-cdn.net/gpl_pdfs/Financials/Quarterly/Glenmark_MDA_Q4FY26_vf.pdf"},
    "glen_top": {"title": "Glenmark: top commercial products", "url": "https://glenmarkpharma.com/top-products/"},
    "glen_ar26": {"title": "Glenmark integrated annual report FY2026", "url": "https://glenmark.b-cdn.net/gpl_pdfs/investors/reports_presentations/Annual%20Report%202025-26%20(Low%20Version).pdf"},
    "glen_wiki": {"title": "Wikipedia: Glenmark Pharmaceuticals (Telma revenue)", "url": "https://en.wikipedia.org/wiki/Glenmark_Pharmaceuticals"},
    "alembic_ip": {"title": "Alembic investor presentation, September 2025 (Q2 FY26)", "url": "https://alembicpharmaceuticals.com/webfiles/pdf/Investor/investors_presentations/2025-2026/Q2/Investor-Presentation-September-2025.pdf"},
}


def b(name, therapy, evidence, basis):
    return {"name": name, "therapy": therapy, "evidence": evidence, "basis": basis}


def t(therapy, value, detail):
    return {"therapy": therapy, "value": value, "detail": detail}


BRANDS = {
    "alembic": {
        "summary": "Ranked 20th in the Indian market (about 1.3% share). Strength is molecule leadership in older acute brands; 51% of the India business is acute, 28% specialty and 22% animal health.",
        "therapy_basis": "Share of India branded business, Q2 FY26",
        "therapies": [t("Acute (anti-infectives, cough and cold, gastro)", 51, "51% of India branded sales"),
                      t("Specialty (gynaecology, cardiology, diabetes, ophthalmology)", 28, "28%"),
                      t("Animal health", 22, "22%, growing fastest")],
        "brand_basis": "Rank and share within its molecule market, Q2 FY26",
        "brands": [b("Roxid", "Anti-infective", "#1, 95.2% share", "Molecule rank"), b("Althrocin", "Anti-infective", "#1, 86.3%", "Molecule rank"),
                   b("Deltone", "Animal health", "#1, 54.3%", "Molecule rank"), b("Elata", "Animal health", "#1, 52.5%", "Molecule rank"),
                   b("Gerijoint", "Pain", "#1, 32.1%", "Molecule rank"), b("Azithral", "Anti-infective", "#1, 30.2%", "Molecule rank"),
                   b("Crina-NCR", "Gynaecology", "#1, 29.9%", "Molecule rank"), b("Estroplus", "Gynaecology", "#2, 47.5%", "Molecule rank"),
                   b("Lactonic", "Gynaecology", "#2, 38.5%", "Molecule rank"), b("Gestofit SR", "Gynaecology", "#2, 18.1%", "Molecule rank"),
                   b("Wikoryl", "Cough and cold", "#3, 10.4%", "Molecule rank")],
        "sources": [S["alembic_ip"]],
    },
    "ajanta": {
        "summary": "Ranked 24th in India (IQVIA, Mar 2026) and #1 in ophthalmology. Over 65% of India sales are chronic; the top 10 brands make 53% of India sales and 18 brands exceed ₹25 Cr.",
        "therapy_basis": "IQVIA therapy rank (lower is better)",
        "therapies": [t("Ophthalmology", 1, "#1 (IQVIA Jun MAT 2026); grew 14% vs market 9%"),
                      t("Dermatology", 13, "#13, up from #16; grew 14% vs market 7%"),
                      t("Cardiology", 17, "#17; grew 7% vs market 14%, so losing share"),
                      t("Pain management", 27, "#27; grew 12% vs market 8%")],
        "brand_basis": "Leadership claims in company disclosures (brand sales not published)",
        "brands": [b("Feburic", "Pain (gout)", "Top position in febuxostat", "Molecule leader"),
                   b("Bimat", "Ophthalmology", "Lead brand of the #1 ophthalmology franchise", "Franchise leader"),
                   b("Met XL", "Cardiology", "Leading brand in its sub-segment", "Sub-segment leader"),
                   b("Melacare", "Dermatology", "Leading brand in its sub-segment", "Sub-segment leader"),
                   b("Atorfit CV", "Cardiology", "Named key cardiology brand", "Named brand"),
                   b("Rosutor Gold", "Cardiology", "Named key cardiology brand", "Named brand")],
        "sources": [S["ajanta_ar26"], S["ajanta_web"]],
    },
    "ipca": {
        "summary": "Ranked 16th in India (IQVIA, Mar 2025). Highly concentrated: pain management is 53% of domestic branded sales, led by the Zerodol family and HCQS; 6 brands are in India's top 300.",
        "therapy_basis": "Share of domestic branded formulations, FY25",
        "therapies": [t("Pain management", 53, "53%"), t("Cardiovascular and anti-diabetic", 17, "17%"), t("Dermatology", 6, "6%"),
                      t("Anti-bacterials", 5, "5%"), t("Urology", 5, "5%"), t("Cough preparations", 4, "4%"),
                      t("Neuro-psychiatry", 3, "3%"), t("Anti-malarials", 3, "3%"), t("Gastro-intestinal", 2, "2%")],
        "brand_basis": "Brands named in India's top 300 (sales not published)",
        "brands": [b("Zerodol-SP", "Pain", "Top 300 brand", "Top 300"), b("Zerodol-P", "Pain", "Top 300 brand", "Top 300"),
                   b("HCQS", "Rheumatology / anti-malarial", "Top 300 brand; market leader in hydroxychloroquine", "Top 300"),
                   b("Folitrax", "Rheumatology", "Top 300 brand", "Top 300"), b("Zerodol-TH", "Pain", "Top 300 brand", "Top 300")],
        "sources": [S["ipca_ar25"], S["ipca_cp24"]],
    },
    "mankind": {
        "summary": "#1 in India by prescription share (15.2%) for nine years. Leads consumer categories by a wide margin; 22 brands crossed ₹100 Cr in FY26. Chronic share rose from 28% (FY18) to 39% (FY26).",
        "therapy_basis": "Market share in the therapy (FY26)",
        "therapies": [t("Gynaecology", 10.3, "10.3% share, #1"), t("Anti-infectives", 6.0, "6.0%"), t("Cardiovascular", 5.5, "5.5%"),
                      t("Anti-diabetic", 4.5, "4.5%"), t("Respiratory", 4.5, "4.5%")],
        "brand_basis": "Category share for consumer brands; FY26 growth for prescription brands (sales not published)",
        "brands": [b("Prega News", "Consumer: pregnancy test", "#1, about 84% category share", "Category share"),
                   b("Unwanted-72", "Consumer: emergency contraceptive", "#1, 68% category share", "Category share"),
                   b("AcneStar", "Consumer: anti-acne", "#1, 34% category share", "Category share"),
                   b("Manforce", "Consumer: condoms", "#1, 28% category share", "Category share"),
                   b("Gas-O-Fast", "Consumer: antacid", "#2, 12% category share", "Category share"),
                   b("Nobeglar", "Anti-diabetic (Rx)", "+45% growth", "FY26 growth"),
                   b("Foligraf / Humog (BSV)", "Fertility (Rx)", "+39% growth", "FY26 growth"),
                   b("Glizid family", "Anti-diabetic (Rx)", "+29% growth", "FY26 growth"),
                   b("Telmikind family", "Cardiovascular (Rx)", "+21% growth", "FY26 growth")],
        "sources": [S["mankind_ip"]],
    },
    "alkem": {
        "summary": "#1 in India's acute segment and #1 in anti-infectives (13.4% share). Pan, Clavam and Pan-D are among India's top 15 brands. Weak spots: diabetes (#14), CNS (#14) and dermatology (#18).",
        "therapy_basis": "Market share and rank, Q2 FY26 (mapping read from a chart, so indicative)",
        "therapies": [t("Anti-infectives", 13.4, "13.4%, #1"), t("Gastro-intestinal", 7.9, "7.9%, #3"), t("Vitamins and nutrition", 7.0, "7.0%, #2"),
                      t("Pain", 5.6, "5.6%, #3"), t("Respiratory", 2.4, "2.4%, #7"), t("Anti-diabetic", 2.2, "2.2%, #14"),
                      t("Neuro / CNS", 1.6, "1.6%, #14"), t("Dermatology", 1.5, "1.5%, #18")],
        "brand_basis": "IQVIA brand rank in India (FY24) and company disclosures",
        "brands": [b("Pan", "Gastro", "#2 brand in India (Q2 FY26); franchise above ₹1,000 Cr", "IPM rank"),
                   b("Clavam", "Anti-infective", "#9 in India (FY24); above ₹600 Cr", "IPM rank"),
                   b("Pan-D", "Gastro", "#15 in India (FY24)", "IPM rank"),
                   b("Taxim-O", "Anti-infective", "Among India's top 50 brands", "Top 50")],
        "sources": [S["alkem_q2"], S["alkem_ar24"]],
    },
    "glenmark": {
        "summary": "Ranked 13th in India (2.34% share, IQVIA Mar 2026) and grew 1.5x the market in FY26. #2 in dermatology, #3 in respiratory, #4 in cardiac; 11 brands are in India's top 300.",
        "therapy_basis": "India market share and rank (IQVIA MAT Mar 2026)",
        "therapies": [t("Dermatology", 8.3, "8.3%, #2"), t("Cardiac", 6.1, "6.1%, #4"), t("Respiratory", 6.0, "6.0%, #3"),
                      t("Diabetes", 1.1, "1.1%, falling (sales −4%)")],
        "brand_basis": "Company's own ranking of top commercial products (global)",
        "brands": [b("Ryaltris", "Respiratory (global)", "#1 product; sold in 55+ countries", "Company rank"),
                   b("Candid", "Dermatology", "#2 product", "Company rank"),
                   b("Telma", "Cardiac", "#3 product; about ₹1,036 Cr a year by 2024", "Company rank"),
                   b("Ascoril", "Respiratory", "#4 product", "Company rank"), b("Klenzit", "Dermatology", "#5 product", "Company rank"),
                   b("Alex", "Respiratory", "#6 product", "Company rank"), b("Momate", "Dermatology", "#7 product", "Company rank"),
                   b("Tacroz", "Dermatology", "#8 product", "Company rank")],
        "sources": [S["glen_mda"], S["glen_top"], S["glen_wiki"]],
    },
}

AREAS = ["Commercial & omnichannel", "Supply chain & S&OP", "Manufacturing 4.0 & quality", "R&D & regulatory", "Finance & ERP", "Data & AI"]
NOEV = "No public disclosure found in the annual report or investor presentations."


def d(score, status, doing, gap, entry, wave, src=None):
    return {"score": score, "status": status, "doing": doing, "gap": gap, "consultant": entry, "wave": wave, "sources": [src] if src else []}


ROADMAP = {
    "alembic": [
        d(2, "Weak", "5,500+ medical reps, but no disclosed digital sales tools.", "India sales grow ~5% vs market ~11% despite a large field force.", "Rep productivity analytics and digital doctor engagement for specialty brands.", "6–18 mo", S["alembic_ip"]),
        d(2, "Weak", NOEV, "462 inventory days and a 381-day cash cycle, the worst in the set.", "Integrated S&OP and AI demand forecasting for US launches; inventory diagnostic worth ~₹500 Cr.", "0–6 mo"),
        d(3, "No public evidence", NOEV + " Clean FDA record suggests sound quality systems.", "New plants under-used; no disclosed digital batch records or plant analytics.", "Plant utilisation and OEE programme with e-batch records at the new sites.", "6–18 mo"),
        d(3, "No public evidence", "Biggest filing engine in the set (279 ANDAs), but no disclosed digital or AI tools.", "R&D is 9–11% of sales with no disclosed productivity tools.", "GenAI dossier drafting and portfolio analytics to pick fewer, better ANDAs.", "18–30 mo"),
        d(3, "No public evidence", NOEV, "Borrowings doubled; working capital not tracked publicly.", "Order-to-cash and inventory control tower on the ERP.", "0–6 mo"),
        d(2, "Weak", NOEV, "No disclosed data platform or AI use.", "Data foundation (single data lake) before any AI pilots.", "0–6 mo"),
    ],
    "ajanta": [
        d(3, "In progress", "AI-enabled learning platform ('Ajanta Academy') and year-round AI training for staff.", "No disclosed digital doctor engagement; cardiology losing share (7% vs market 14%).", "Omnichannel cardiology relaunch with rep next-best-action.", "6–18 mo", S["ajanta_ar26"]),
        d(3, "In progress", "Digital tools for real-time supply visibility and forecasting accuracy.", "Debtor days rose 93 → 124; cash conversion 0.5x.", "Order-to-cash and distributor credit analytics; collections dashboard.", "0–6 mo", S["ajanta_ar26"]),
        d(3, "In progress", "Electronic batch records integrated with equipment; predictive maintenance; automation cut manual work by ~50% on one line.", "Roll-out shown at selected sites only.", "Scale e-batch records and predictive quality across all US-facing plants.", "6–18 mo", S["ajanta_ar26"]),
        d(3, "In progress", "R&D processes fully digitised; AI models being integrated into R&D.", "Early stage; US pipeline still small (~51 products).", "AI-led product selection for the next US wave.", "18–30 mo", S["ajanta_ar26"]),
        d(3, "In progress", "SAP-enabled digital workflows and approvals; SAP SuccessFactors for HR.", "Receivables not yet under control despite SAP.", "Working-capital control tower on SAP data.", "0–6 mo", S["ajanta_ar26"]),
        d(2, "Weak", "AI used in learning and R&D; cybersecurity upgraded.", "No enterprise data platform or AI in commercial and supply chain.", "Enterprise data platform plus 2–3 AI use cases (demand, collections, rep targeting).", "6–18 mo", S["ajanta_ar26"]),
    ],
    "ipca": [
        d(2, "No public evidence", "6,476-strong field force across 21 therapy divisions; no disclosed digital tools.", "Portfolio 53% pain; needs reach in chronic therapies.", "Digital engagement for chronic launches; rep productivity analytics.", "6–18 mo", S["ipca_cp24"]),
        d(2, "No public evidence", NOEV, "353 inventory days; lumpy tenders and exports.", "Tender and export demand planning with S&OP.", "0–6 mo"),
        d(3, "No public evidence", NOEV + " Large API base (25 sites).", "Unichem integration needs common quality and plant systems.", "Plant network and quality systems harmonisation (Ipca + Unichem).", "6–18 mo"),
        d(2, "No public evidence", NOEV, "Small regulated-market pipeline (4–5 US filings a year).", "Portfolio analytics to choose US/EU filings.", "18–30 mo"),
        d(3, "No public evidence", NOEV, "Two companies (Ipca, Unichem) to bring onto one finance backbone.", "Single ERP and synergy tracking for the Unichem integration.", "0–6 mo"),
        d(2, "No public evidence", NOEV, "No disclosed data or AI programme.", "Data foundation, then API cost and yield analytics.", "6–18 mo"),
    ],
    "mankind": [
        d(3, "In progress", "Consumer business shifting online: modern trade and e-commerce reached 15% of consumer sales (Q1 FY27).", "Consumer healthcare growth stuck at ~4–9%.", "Direct-to-consumer and e-commerce growth playbook; Rx omnichannel for chronic.", "6–18 mo", S["mankind_ip"]),
        d(3, "In progress", "Supply chain redesigned with Accenture: demand planning, inventory optimisation and real-time supply data.", "BSV supply chain still to be fully integrated.", "Integrate BSV into the planning and control tower.", "6–18 mo", S["mankind_acc"]),
        d(2, "Weak", NOEV, "32 plants including small sites; first USFDA inspection only recently.", "Plant network rationalisation and e-batch records ahead of export growth.", "6–18 mo"),
        d(3, "In progress", "AI drug-discovery tie-up with Denovo Science (Jul 2026).", "R&D only ~2–3% of sales, yet buying high-risk innovation (CAR-T).", "R&D portfolio governance and stage-gate analytics.", "18–30 mo", S["mankind_q1"]),
        d(4, "Doing well", "SAP S/4HANA across finance, supply chain, sales and procurement (with Accenture).", "BSV acquisition systems to fold in.", "Synergy and capital-return tracking on the S/4HANA core.", "0–6 mo", S["mankind_acc"]),
        d(3, "In progress", "Microsoft Azure data lake with Tableau dashboards for management.", "Dashboards, not yet AI in decisions.", "Move from dashboards to AI use cases (rep targeting, demand sensing).", "18–30 mo", S["mankind_acc"]),
    ],
    "alkem": [
        d(3, "In progress", "Company says it is 'strengthening its digital footprint' and IT infrastructure; no specifics disclosed.", "Added 1,200 reps in Q1 FY27 (employee cost +16%), so rep productivity matters.", "Rep productivity and targeting analytics before adding more reps.", "0–6 mo", S["alkem_ar24"]),
        d(3, "In progress", "Digitisation 'to strengthen operational prudence' (no specifics).", "Working-capital days rose 31 → 123 since FY22.", "Inventory and receivables diagnostic with S&OP.", "0–6 mo", S["alkem_ar24"]),
        d(2, "Weak", NOEV + " Daman plant classified OAI by the US FDA (Aug 2026).", "Quality systems failed an FDA inspection at a plant behind ~45% of US sales.", "Remediation programme with electronic quality systems (e-QMS, data integrity monitoring) across sites.", "0–6 mo"),
        d(3, "No public evidence", NOEV, "Biosimilars (Enzene) and devices (Occlutech) add complexity.", "Regulatory operations and dossier automation.", "18–30 mo"),
        d(3, "In progress", "Enhanced IT infrastructure to 'streamline operations' (no specifics).", "Tax rate 30–32% and new businesses need tighter finance control.", "Group finance transformation and tax structure review.", "6–18 mo", S["alkem_ar24"]),
        d(2, "Weak", NOEV, "No disclosed data or AI programme.", "Data foundation plus AI for acute-season demand forecasting.", "6–18 mo"),
    ],
    "glenmark": [
        d(3, "In progress", "Sharper digital engagement and omnichannel reach in consumer care; e-commerce and quick-commerce growth.", "Diabetes share falling (sales −4% vs market +12%).", "Digital launch playbook for semaglutide and specialty brands.", "6–18 mo", S["glen_ar26"]),
        d(3, "No public evidence", NOEV, "Payables stretched (288 days); target net working capital below 115 days.", "Working-capital programme to hit the 115-day target.", "0–6 mo"),
        d(3, "In progress", "Compliance repair: Goa warning letter closed (Sep 2026), Monroe VAI.", "Digital quality systems not disclosed.", "Data integrity and predictive quality to keep plants clean.", "6–18 mo"),
        d(4, "Doing well", "Innovation engine (IGI): out-licensed ISB 2001 to AbbVie; chairman cites AI and data science in R&D.", "IGI burns ~US$70M a year.", "R&D portfolio valuation and partnering strategy.", "18–30 mo", S["glen_ar26"]),
        d(3, "No public evidence", NOEV, "Earnings quality: licensing income makes results lumpy.", "Management reporting that separates core and one-off income.", "0–6 mo"),
        d(3, "In progress", "Launched 'ELVIAE', an AI humanoid tool in clinics across five Asia-Pacific markets.", "AI used for patient education, not yet for internal decisions.", "AI use cases in supply chain and commercial targeting.", "18–30 mo", S["glen_ar26"]),
    ],
}

data = json.load(open(P, encoding="utf-8"))
for c in data["companies"]:
    cid = c["id"]
    c["brands"] = BRANDS[cid]
    c["digital_roadmap"] = [{"area": a, **r} for a, r in zip(AREAS, ROADMAP[cid])]
    c["digital"] = {a: r["score"] for a, r in zip(AREAS, ROADMAP[cid])}
json.dump(data, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
avg = {a: round(sum(ROADMAP[c][i]["score"] for c in ROADMAP) / 6, 2) for i, a in enumerate(AREAS)}
print("area averages:", avg)
