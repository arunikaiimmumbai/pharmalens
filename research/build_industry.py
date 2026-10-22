"""Build data/industry.json from Screener extracts (research/industry/*.csv).
The five Nifty Pharma members already covered in companies.json are referenced, not duplicated."""
import csv, json, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = {"SUNPHARMA": "Sun Pharma", "CIPLA": "Cipla", "DRREDDY": "Dr Reddy's", "LUPIN": "Lupin", "TORNTPHARM": "Torrent Pharma",
         "AUROPHARMA": "Aurobindo", "ZYDUSLIFE": "Zydus Lifesciences", "DIVISLAB": "Divi's Labs", "BIOCON": "Biocon",
         "GLAND": "Gland Pharma", "WOCKPHARMA": "Wockhardt", "LAURUSLABS": "Laurus Labs", "SAILIFE": "Sai Life Sciences",
         "PPLPHARMA": "Piramal Pharma", "ABBOTINDIA": "Abbott India"}
KEYMAP = {"Sales": "sales", "Operating Profit": "ebitda", "Other Income": "other_income", "Interest": "interest",
          "Depreciation": "depreciation", "Profit before tax": "pbt", "Tax %": "tax_pct", "Net Profit": "pat",
          "Equity Capital": "equity_capital", "Reserves": "reserves", "Borrowings": "borrowings",
          "Other Liabilities": "other_liabilities", "Total Liabilities": "total_assets", "Fixed Assets": "fixed_assets",
          "CWIP": "cwip", "Investments": "investments", "Other Assets": "other_assets",
          "Cash from Operating Activity": "cfo", "Cash from Investing Activity": "cfi", "Cash from Financing Activity": "cff",
          "Debtor Days": "debtor_days", "Inventory Days": "inventory_days", "Days Payable": "payable_days",
          "Cash Conversion Cycle": "ccc", "Working Capital Days": "wc_days", "ROCE %": "roce",
          "Material Cost %": "material_pct", "Employee Cost %": "employee_pct", "Manufacturing Cost %": "manufacturing_pct",
          "Other Cost %": "other_cost_pct", "Cash Equivalents": "cash"}

members = []
for f in sorted(glob.glob(str(ROOT / "research/industry/*.csv"))):
    sym = Path(f).stem
    fin, extra = {}, {}
    for row in csv.reader(open(f)):
        if not row or row[0] == "metric":
            continue
        k = row[0]
        if k in KEYMAP:
            fin[KEYMAP[k]] = [float(x.rstrip("%")) if x.strip() not in ("", "None") else None for x in row[1:6]]
        else:
            extra[k] = row[1] if len(row) > 1 else None
    # drop cost-% years whose four lines don't reconcile with reported operating margin (Screener schedule gaps)
    if "material_pct" in fin:
        ok = []
        for i in range(5):
            tot = sum(fin[k][i] for k in ("material_pct", "employee_pct", "manufacturing_pct", "other_cost_pct"))
            opm = fin["ebitda"][i] / fin["sales"][i] * 100
            ok.append(abs(tot - (100 - opm)) <= 10)
        fin["cost_ok"] = ok
    base = "standalone" if extra.get("Basis") == "standalone" else "consolidated"
    members.append({
        "symbol": sym, "name": NAMES[sym], "basis": base,
        "url": f"https://www.screener.in/company/{sym}/" + ("" if base == "standalone" else "consolidated/"),
        "mcap_cr": float(extra["MarketCap"]) if extra.get("MarketCap") else None,
        "pe": float(extra["PE"]) if extra.get("PE") else None,
        "financials": fin,
    })

out = {
    "index": "Nifty Pharma",
    "as_of": "2026-10-22",
    "constituents_source": {"title": "5paisa: Nifty Pharma stock list (updated 22 Oct 2026)", "url": "https://www.5paisa.com/hindi/nifty-pharma-stock-list"},
    "method": "Industry = simple average of the 20 Nifty Pharma constituents (median shown alongside). Consolidated Screener.in figures, "
              "Abbott India standalone (no subsidiaries). Cost-line shares exclude company-years where Screener's cost schedule does not reconcile "
              "with reported operating margin within 10 points.",
    "in_app_members": {"ALKEM": "alkem", "GLENMARK": "glenmark", "IPCALAB": "ipca", "MANKIND": "mankind", "AJANTPHARM": "ajanta"},
    "members": members,
    "market": [
        {"metric": "Indian pharma market growth FY26", "value": 10.0, "unit": "%", "detail": "volume ~2.7%, price ~4.4%, new products ~2.8%",
         "provider": "IQVIA", "source": {"title": "HDFC Sky: IPM grows 11% YoY in Mar-26 (citing IQVIA)", "url": "https://hdfcsky.com/news/pharmaceuticals-ipm-11-percent-growth-in-mar-26"}},
        {"metric": "Chronic vs acute growth, Mar 2026", "value": 14.0, "value2": 8.0, "unit": "%", "detail": "chronic ~14%, acute ~8% YoY",
         "provider": "IQVIA", "source": {"title": "HDFC Sky: IPM grows 11% YoY in Mar-26 (citing IQVIA)", "url": "https://hdfcsky.com/news/pharmaceuticals-ipm-11-percent-growth-in-mar-26"}},
        {"metric": "Indian pharma market growth, Sep 2026", "value": 13.5, "unit": "%", "detail": "value ~13.5%, volume ~3.4%",
         "provider": "Pharmarack", "source": {"title": "BioSpectrum India: IPM records 13.5% value growth in Sep 2026", "url": "https://www.biospectrumindia.com/news/16/28658/indian-pharma-market-records-13-5-value-growth-volume-growth-rises-to-3-in-september-2026.html"}},
    ],
}
json.dump(out, open(ROOT / "data/industry.json", "w"), indent=1)
print(len(members), "members written;", sum(1 for m in members for v in m["financials"].get("cost_ok", []) if not v), "cost-years excluded")
