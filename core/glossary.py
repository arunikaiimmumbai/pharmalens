"""Plain-English meaning and formula for every metric. Used for the ⓘ tooltips, the agent's
'How it's calculated' line in offline mode, and the glossary on the Sources page."""

GLOSSARY = {
    "sales": ("All money earned from selling products in the year (also called revenue or turnover).", "Reported revenue from operations, ₹ Cr"),
    "sales_growth": ("How much revenue grew compared with last year.", "(This year − last year) ÷ last year × 100"),
    "sales_cagr": ("Steady growth per year from FY22 to FY26.", "(FY26 ÷ FY22)^(1/4) − 1"),
    "ebitda_cagr": ("Steady growth per year in operating profit, FY22 to FY26.", "(FY26 EBITDA ÷ FY22 EBITDA)^(1/4) − 1"),
    "pat_cagr": ("Steady growth per year in final profit, FY22 to FY26.", "(FY26 PAT ÷ FY22 PAT)^(1/4) − 1"),
    "ebitda_margin": ("₹ of operating profit kept from every ₹100 of sales, before interest, tax and depreciation.", "EBITDA ÷ revenue × 100"),
    "ebit_margin": ("₹ of operating profit kept from every ₹100 of sales after depreciation.", "(EBITDA − depreciation) ÷ revenue × 100"),
    "gross_margin": ("₹ left from every ₹100 of sales after paying for materials. Shows pricing power.", "(Revenue − material cost) ÷ revenue × 100"),
    "pat_margin": ("₹ of final profit (after interest and tax) from every ₹100 of sales.", "PAT ÷ revenue × 100"),
    "roce": ("Operating profit earned for every ₹100 invested by owners and lenders together.", "EBIT ÷ capital employed × 100 (as reported by Screener)"),
    "roe": ("Profit earned for every ₹100 of shareholders' money.", "PAT ÷ average net worth × 100"),
    "roa": ("Profit earned for every ₹100 of assets.", "PAT ÷ total assets × 100"),
    "roic": ("After-tax operating return on the money invested in the business. Above ~12% (a typical cost of capital) creates value.",
             "EBIT × (1 − tax rate) ÷ (net worth + net debt) × 100"),
    "employee_pct": ("Share of sales spent on salaries, including the sales force and scientists.", "Employee cost ÷ revenue × 100"),
    "material_pct": ("Share of sales spent on raw materials and ingredients.", "Material cost ÷ revenue × 100"),
    "indirect_pct": ("Share of sales spent on overheads: plant running costs plus selling, general and admin.", "(Manufacturing + other costs) ÷ revenue × 100"),
    "inventory_days": ("How long stock sits before it is sold.", "Inventory ÷ material cost × 365"),
    "debtor_days": ("How long customers take to pay.", "Receivables ÷ revenue × 365"),
    "payable_days": ("How long the company takes to pay its suppliers.", "Payables ÷ material cost × 365"),
    "ccc": ("Days cash is locked up between paying for materials and getting paid by customers. Lower is better.", "Inventory days + debtor days − payable days"),
    "wc_days": ("Net money stuck in day-to-day operations, in days of sales.", "Working capital ÷ revenue × 365"),
    "de_ratio": ("Borrowed money for every ₹1 of owners' money.", "Borrowings ÷ net worth"),
    "debt_ebitda": ("Years of operating profit needed to repay all borrowings.", "Borrowings ÷ EBITDA"),
    "net_debt_ebitda": ("Years of operating profit needed to repay debt after using cash. Negative means more cash than debt.",
                        "(Borrowings − cash − investments) ÷ EBITDA"),
    "interest_cover": ("How many times operating profit covers the interest bill.", "EBIT ÷ interest"),
    "asset_turnover": ("Sales made from every ₹1 of assets.", "Revenue ÷ total assets"),
    "fixed_asset_turnover": ("Sales made from every ₹1 of plants and machinery.", "Revenue ÷ (net fixed assets + capital work in progress)"),
    "cfo_pat": ("Share of accounting profit that actually arrived as cash. Below ~0.8x is a warning.", "Cash from operations ÷ PAT"),
    "cfo_ebitda": ("Share of operating profit that arrived as cash.", "Cash from operations ÷ EBITDA"),
    "fcf_margin": ("Cash left after all investment spending, per ₹100 of sales.", "(Cash from operations + cash from investing) ÷ revenue × 100"),
    "rnd_pct": ("Share of sales spent on research and development.", "R&D spend ÷ revenue × 100"),
    "pe": ("Price investors pay for each ₹1 of yearly profit.", "Share price ÷ earnings per share"),
    "pb": ("Price versus the owners' money in the books.", "Market cap ÷ net worth"),
    "ev_ebitda": ("Deal-style valuation that adjusts for debt and cash.", "(Market cap + debt − cash) ÷ EBITDA"),
    "mcap_cr": ("What the stock market values the whole company at.", "Share price × number of shares"),
    "us_share": ("Share of revenue from the US.", "US revenue ÷ total revenue × 100"),
    "india_share": ("Share of revenue from India.", "India revenue ÷ total revenue × 100"),
    "div_payout": ("Share of profit paid out as dividends.", "Dividends ÷ PAT × 100"),
}


def meaning(metric: str) -> str:
    return GLOSSARY.get(metric, ("", ""))[0]


def formula(metric: str) -> str:
    return GLOSSARY.get(metric, ("", ""))[1]


def tooltip(metric: str) -> str:
    m, f = GLOSSARY.get(metric, ("", ""))
    return f"{m} Formula: {f}" if m else ""
