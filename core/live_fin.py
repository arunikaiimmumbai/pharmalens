"""Live financial statements: refreshed automatically in the background, like the news feed.

Source: Screener.in company pages (consolidated where the app uses consolidated accounts), which compile each company's
results filed with NSE/BSE: annual P&L, balance sheet, cash flow, ratios, quarterly results, shareholding and market data,
plus Screener's expense and 'other assets' breakdowns for cost shares and cash.

How it works
- A background thread (one per app server) checks every company every REFRESH_HOURS, gently (a pause between requests).
- Each company's numbers are checked before use: all core lines present for five years, positive sales, cost shares that
  add up, and past years that agree with the checked data (restatements are allowed, wholesale differences are not).
- A company that fails a check keeps its saved, checked numbers, and the feed status says why.
- Written analysis (notes, SWOT, problems) is not rewritten automatically; it stays dated to when it was researched.
"""
from __future__ import annotations

import copy
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

SOURCE_NAME = "Screener.in (company results filed with NSE/BSE)"
SOURCE_URL = "https://www.screener.in/"
BASE = os.environ.get("SCREENER_BASE", "https://www.screener.in")  # override only for testing
REFRESH_HOURS = 6
PAUSE_SECONDS = float(os.environ.get("LIVE_PAUSE", "2.5"))
CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "live" / "financials_live.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
                         "FinanceLens-academic-dashboard",
           "Accept-Language": "en-IN,en;q=0.9"}

ROWS = {  # Screener row label -> app field
    "profit-loss": {"Sales": "sales", "Revenue": "sales", "Expenses": "expenses_scr", "Operating Profit": "ebitda", "Financing Profit": "ebitda",
                    "Other Income": "other_income", "Interest": "interest", "Depreciation": "depreciation", "Profit before tax": "pbt",
                    "Tax %": "tax_pct", "Net Profit": "pat", "EPS in Rs": "eps", "Dividend Payout %": "div_payout"},
    "balance-sheet": {"Equity Capital": "equity_capital", "Reserves": "reserves", "Borrowings": "borrowings",
                      "Other Liabilities": "other_liabilities", "Total Liabilities": "total_assets", "Fixed Assets": "fixed_assets",
                      "CWIP": "cwip", "Investments": "investments", "Other Assets": "other_assets"},
    "cash-flow": {"Cash from Operating Activity": "cfo", "Cash from Investing Activity": "cfi", "Cash from Financing Activity": "cff"},
    "ratios": {"Debtor Days": "debtor_days", "Inventory Days": "inventory_days", "Days Payable": "payable_days",
               "Cash Conversion Cycle": "ccc", "Working Capital Days": "wc_days", "ROCE %": "roce"},
}
COST_ROWS = {"Material Cost %": "material_pct", "Manufacturing Cost %": "manufacturing_pct", "Employee Cost %": "employee_pct",
             "Other Cost %": "other_cost_pct"}
CORE = ("sales", "ebitda", "pat", "equity_capital", "reserves", "borrowings", "total_assets", "cfo")
MONTHS = {"Mar": 4, "Jun": 1, "Sep": 2, "Dec": 3}


# ── parsing helpers ──────────────────────────────────────────────────────────
def num(text) -> float | None:
    """'1,23,456' -> 123456.0 ; '12%' -> 12.0 ; '' or '-' -> None."""
    if text is None:
        return None
    t = re.sub(r"[₹,%\s]|Cr\.?", "", str(text))
    if t in ("", "-", "--", "NA", "N/A"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def label_clean(text: str) -> str:
    return re.sub(r"\s*\+\s*$", "", re.sub(r"\s+", " ", text or "").strip())


def fy_label(col: str) -> str | None:
    """'Mar 2026' -> 'FY26'. Other month-ends (a changed year-end) are ignored."""
    m = re.match(r"Mar\s+(\d{4})", col or "")
    return f"FY{int(m.group(1)) % 100:02d}" if m else None


def quarter_label(col: str) -> str | None:
    """'Sep 2026' -> 'Q2 FY27' (Indian fiscal year starts in April)."""
    m = re.match(r"(Mar|Jun|Sep|Dec)\s+(\d{4})", col or "")
    if not m:
        return None
    mon, yr = m.group(1), int(m.group(2))
    fy = yr + 1 if mon in ("Jun", "Sep", "Dec") else yr
    return f"Q{MONTHS[mon]} FY{fy % 100:02d}"


def parse_table(soup, section_id: str) -> dict:
    """{'cols': [...], 'rows': {label: [values...]}} for the first table in a section."""
    sec = soup.find(id=section_id)
    table = sec.find("table") if sec else None
    if not table:
        return {"cols": [], "rows": {}}
    cols = [re.sub(r"\s+", " ", th.get_text()).strip() for th in table.select("thead th")][1:]
    rows = {}
    for tr in table.select("tbody tr"):
        cells = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
        if len(cells) < 2:
            continue
        rows.setdefault(label_clean(cells[0]), cells[1:])
    return {"cols": cols, "rows": rows}


def parse_page(html: str) -> dict:
    from bs4 import BeautifulSoup  # noqa: WPS433

    soup = BeautifulSoup(html, "lxml")
    out = {"tables": {s: parse_table(soup, s) for s in ("profit-loss", "balance-sheet", "cash-flow", "ratios", "quarters")}}
    m = re.search(r'data-company-id="(\d+)"', html)
    out["company_id"] = m.group(1) if m else None
    top = {}
    box = soup.find(id="top-ratios")
    for li in (box.find_all("li") if box else []):
        name = li.find("span", class_="name")
        nums = [n.get_text() for n in li.find_all("span", class_="number")]
        if name and nums:
            top[re.sub(r"\s+", " ", name.get_text()).strip()] = nums
    out["top"] = top
    shp = {}
    sec = soup.find(id="quarterly-shp") or soup.find(id="shareholding")
    table = sec.find("table") if sec else None
    if table:
        for tr in table.select("tbody tr"):
            cells = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all("td")]
            if len(cells) >= 2 and num(cells[-1]) is not None:
                shp[label_clean(cells[0])] = num(cells[-1])
    out["shareholding"] = shp
    return out


def parse_schedule(js: dict) -> dict:
    """Screener schedule JSON {label: {'Mar 2026': '30%', ...}} -> {label: {'FY26': 30.0}}."""
    out = {}
    for lab, series in (js or {}).items():
        if isinstance(series, dict):
            out[label_clean(lab)] = {fy_label(k): num(v) for k, v in series.items() if fy_label(k)}
    return out


# ── fetching ─────────────────────────────────────────────────────────────────
def fetch_company(symbol: str, consolidated: bool = True, session=None) -> dict:
    """Downloads and parses one company. Raises on network or layout problems."""
    import requests  # noqa: WPS433

    s = session or requests.Session()
    url = f"{BASE}/company/{symbol}/" + ("consolidated/" if consolidated else "")
    r = s.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    page = parse_page(r.text)
    page["url"] = url
    page["schedules"] = {}
    if page["company_id"]:
        for parent, section in (("Expenses", "profit-loss"), ("Other Assets", "balance-sheet")):
            time.sleep(PAUSE_SECONDS)
            try:
                rr = s.get(f"{BASE}/api/company/{page['company_id']}/schedules/",
                           params={"parent": parent, "section": section, "consolidated": "true" if consolidated else ""},
                           headers={**HEADERS, "X-Requested-With": "XMLHttpRequest", "Referer": url}, timeout=30)
                if rr.ok:
                    page["schedules"].update(parse_schedule(rr.json()))
            except Exception:  # a missing breakdown is not fatal: cost shares fall back to checked data
                pass
    return page


# ── turning a parsed page into app fields, with checks ──────────────────────
def build_record(page: dict, saved_fin: dict | None, saved_years: list[str]) -> dict:
    """Returns {'ok': bool, 'reason': str, 'years': [...], 'financials': {...}, 'quarterly': {...}, 'quarter_labels': [...],
    'ttm': {...}, 'market': {...}, 'shareholding': {...}}."""
    t = page["tables"]
    pl = t["profit-loss"]
    fy_cols = [(i, fy_label(c)) for i, c in enumerate(pl["cols"]) if fy_label(c)]
    if len(fy_cols) < 5:
        return {"ok": False, "reason": "fewer than five annual columns found"}
    years = [fy for _, fy in fy_cols][-5:]
    fin: dict[str, list] = {}
    for sec, mapping in ROWS.items():
        tab = t[sec]
        col_idx = {fy_label(c): i for i, c in enumerate(tab["cols"]) if fy_label(c)}
        for lab, key in mapping.items():
            if lab in tab["rows"] and key not in fin:
                vals = tab["rows"][lab]
                fin[key] = [num(vals[col_idx[y]]) if y in col_idx and col_idx[y] < len(vals) else None for y in years]
    missing = [k for k in CORE if k not in fin or any(v is None for v in fin[k])]
    if missing:
        return {"ok": False, "reason": "missing lines: " + ", ".join(missing)}
    if any(v <= 0 for v in fin["sales"]):
        return {"ok": False, "reason": "non-positive sales"}
    fin["expenses"] = [round(s - e, 2) for s, e in zip(fin["sales"], fin["ebitda"])]
    fin.pop("expenses_scr", None)
    for k in ("other_income", "interest", "depreciation", "pbt", "tax_pct", "eps", "div_payout", "other_liabilities", "fixed_assets",
              "cwip", "investments", "other_assets", "cfi", "cff", "debtor_days", "inventory_days", "payable_days", "ccc", "wc_days", "roce"):
        fin.setdefault(k, [None] * 5)
        fin[k] = [0.0 if v is None and k in ("cwip", "investments", "interest") else v for v in fin[k]]

    # cost shares and cash from the breakdowns; keep a year only if the four lines add up to total costs (within 10 pts)
    sch = page.get("schedules", {})
    saved_fin = saved_fin or {}
    for lab, key in COST_ROWS.items():
        fin[key] = [sch.get(lab, {}).get(y) for y in years]
    cost_ok = []
    for i, y in enumerate(years):
        parts = [fin[k][i] for k in COST_ROWS.values()]
        opm = fin["ebitda"][i] / fin["sales"][i] * 100
        cost_ok.append(all(p is not None for p in parts) and abs(sum(parts) - (100 - opm)) <= 10)
    for i, y in enumerate(years):
        if not cost_ok[i]:
            j = saved_years.index(y) if y in saved_years else None
            for key in COST_ROWS.values():
                fin[key][i] = saved_fin.get(key, [None] * 5)[j] if j is not None and saved_fin.get(key) else None
    fin["cost_ok"] = [all(fin[k][i] is not None for k in COST_ROWS.values()) for i in range(len(years))]
    cash = sch.get("Cash Equivalents", {})
    fin["cash"] = [cash.get(y) for y in years]
    if any(v is None for v in fin["cash"]) and saved_fin.get("cash"):
        fin["cash"] = [v if v is not None else (saved_fin["cash"][saved_years.index(y)] if y in saved_years else 0.0)
                       for v, y in zip(fin["cash"], years)]
    fin["cash"] = [0.0 if v is None else v for v in fin["cash"]]

    # past years must broadly agree with the checked data (guards against reading the wrong page or a layout change)
    for i, y in enumerate(years):
        if y in saved_years and saved_fin.get("sales"):
            old = saved_fin["sales"][saved_years.index(y)]
            if old and abs(fin["sales"][i] - old) / old > 0.25:
                return {"ok": False, "reason": f"{y} sales {fin['sales'][i]:,.0f} differ from checked {old:,.0f} by more than 25%"}

    rec = {"ok": True, "reason": "", "years": years, "financials": fin}

    q = t["quarters"]
    qcols = [(i, quarter_label(c)) for i, c in enumerate(q["cols"]) if quarter_label(c)][-5:]
    if len(qcols) == 5 and all(k in q["rows"] for k in ("Sales", "Operating Profit", "Net Profit")):
        def series(lab):
            return [num(q["rows"][lab][i]) if i < len(q["rows"][lab]) else None for i, _ in qcols]
        sales_q, op_q = series("Sales"), series("Operating Profit")
    else:
        sales_q = op_q = None
    if sales_q and all(v is not None for v in sales_q + op_q):
        rec["quarterly"] = {"sales": sales_q, "ebitda": op_q, "pat": series("Net Profit"),
                            "opm": [round(o / s * 100) if s else None for s, o in zip(sales_q, op_q)]}
        rec["quarter_labels"] = [lab for _, lab in qcols]
    ttm_i = len(pl["cols"]) - 1 if pl["cols"] and pl["cols"][-1].upper() == "TTM" else None
    if ttm_i is not None:
        def ttm(lab):
            vals = pl["rows"].get(lab) or []
            return num(vals[ttm_i]) if ttm_i < len(vals) else None
        rec["ttm"] = {"sales": ttm("Sales"), "ebitda": ttm("Operating Profit"), "pat": ttm("Net Profit")}
    top = page.get("top", {})
    mk = {}
    if top.get("Market Cap"):
        mk["mcap_cr"] = num(top["Market Cap"][0])
    if top.get("Current Price"):
        mk["price"] = num(top["Current Price"][0])
    if top.get("Stock P/E"):
        mk["pe"] = num(top["Stock P/E"][0])
    if top.get("Book Value"):
        mk["book_value"] = num(top["Book Value"][0])
    if top.get("Dividend Yield"):
        mk["div_yield"] = num(top["Dividend Yield"][0])
    if top.get("High / Low") and len(top["High / Low"]) >= 2:
        mk["high_52w"], mk["low_52w"] = num(top["High / Low"][0]), num(top["High / Low"][1])
    if mk.get("price") and mk.get("book_value"):
        mk["pb"] = round(mk["price"] / mk["book_value"], 1)
    rec["market"] = {k: v for k, v in mk.items() if v is not None}
    shp = page.get("shareholding", {})
    if shp:
        rec["shareholding"] = {"Promoters": shp.get("Promoters", 0.0), "FIIs": shp.get("FIIs", 0.0), "DIIs": shp.get("DIIs", 0.0),
                               "Public": round(shp.get("Public", 0.0) + shp.get("Government", 0.0) + shp.get("Others", 0.0), 2)}
    return rec


# ── the background refresher ─────────────────────────────────────────────────
class Refresher:
    """Holds the latest live records and refreshes them on a timer in a daemon thread."""

    def __init__(self, targets: dict, saved: dict):
        # targets: symbol -> {'name', 'consolidated'} ; saved: symbol -> {'financials', 'years'}
        self.targets, self.saved = targets, saved
        self.records: dict[str, dict] = {}
        self.status: dict[str, dict] = {}
        self.version = 0
        self.last_cycle: str | None = None
        self.running = False
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._load_cache()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="financials-refresher")
        self._thread.start()

    def _load_cache(self) -> None:
        try:
            js = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            self.records, self.status = js.get("records", {}), js.get("status", {})
            self.last_cycle = js.get("last_cycle")
            self.version = 1 if self.records else 0
        except Exception:
            pass

    def _save_cache(self) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps({"records": self.records, "status": self.status, "last_cycle": self.last_cycle}), encoding="utf-8")
        except Exception:
            pass

    def due(self) -> bool:
        if not self.last_cycle:
            return True
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(self.last_cycle)).total_seconds()
        return age > REFRESH_HOURS * 3600

    def trigger(self) -> None:
        """Ask for a refresh now (used by the 'Check for new results now' button)."""
        self.last_cycle = None
        self._wake.set()

    def _loop(self) -> None:
        import requests  # noqa: WPS433

        time.sleep(5)  # let the app finish starting
        while True:
            if self.due():
                self.running = True
                session = requests.Session()
                changed = False
                for sym, tgt in self.targets.items():
                    changed |= self._refresh_one(sym, tgt, session)
                    time.sleep(PAUSE_SECONDS)
                self.last_cycle = datetime.now(timezone.utc).isoformat()
                with self._lock:
                    if changed:
                        self.version += 1
                self.running = False
                self._save_cache()
            self._wake.wait(timeout=600)
            self._wake.clear()

    def _refresh_one(self, sym: str, tgt: dict, session) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        prev = self.records.get(sym)
        sv = self.saved.get(sym, {})
        try:
            page = fetch_company(sym, tgt.get("consolidated", True), session)
            rec = build_record(page, sv.get("financials"), sv.get("years", []))
        except Exception as e:  # network, blocked, layout change
            rec = {"ok": False, "reason": f"could not fetch ({type(e).__name__}: {str(e)[:80]})"}
        st = {"name": tgt.get("name", sym), "checked": now, "source": f"{BASE}/company/{sym}/" + ("consolidated/" if tgt.get("consolidated", True) else "")}
        if not rec.get("ok"):
            st.update(state="saved", reason=rec.get("reason", ""))
            if prev:  # keep the last good live record rather than dropping back
                st.update(state="live (last good)", latest_fy=prev["years"][-1], latest_quarter=(prev.get("quarter_labels") or ["-"])[-1])
            with self._lock:
                self.status[sym] = st
            return False
        rec["fetched"] = now
        news = []
        old_years = prev["years"] if prev else sv.get("years", [])
        old_q = (prev or {}).get("quarter_labels") or sv.get("quarter_labels") or []
        if rec["years"][-1] not in old_years:
            news.append(f"New annual results: {rec['years'][-1]}")
        if rec.get("quarter_labels") and old_q and rec["quarter_labels"][-1] not in old_q:  # no baseline = nothing to call new
            news.append(f"New quarter: {rec['quarter_labels'][-1]}")
        st.update(state="live", reason="", latest_fy=rec["years"][-1], latest_quarter=(rec.get("quarter_labels") or ["-"])[-1])
        if news:
            st["new"] = news
            st["new_since"] = now
        elif self.status.get(sym, {}).get("new"):
            st["new"], st["new_since"] = self.status[sym]["new"], self.status[sym].get("new_since")
        strip = lambda r: {k: v for k, v in (r or {}).items() if k != "fetched"}  # noqa: E731
        changed = strip(prev) != strip(rec)
        with self._lock:
            self.records[sym] = rec
            self.status[sym] = st
        return changed


# ── applying live records to the app's data ─────────────────────────────────
def common_years(records: list, default: list[str]) -> list[str]:
    """The five-year window every company has, so charts and the industry average compare like with like.
    It moves forward only once all companies have published the new year (until then their saved years are used)."""
    num_ = lambda y: int(y[2:])  # noqa: E731
    lasts = [r["years"][-1] if r and r.get("ok") else default[-1] for r in records] or [default[-1]]
    end = max(min(num_(y) for y in lasts), num_(default[-1]))
    return [f"FY{(end - 4 + i) % 100:02d}" for i in range(5)]


def merge_financials(saved_fin: dict, saved_years: list[str], rec: dict | None, years: list[str]) -> dict:
    """Financial lines for `years`: live values where available, else the checked saved values."""
    out = {}
    keys = set(saved_fin) | set((rec or {}).get("financials", {}))
    for k in keys:
        vals = []
        for y in years:
            v = None
            if rec and rec.get("ok") and y in rec["years"] and k in rec["financials"]:
                v = rec["financials"][k][rec["years"].index(y)]
            if v is None and y in saved_years and k in saved_fin and saved_fin[k] is not None:
                v = saved_fin[k][saved_years.index(y)]
            vals.append(v)
        out[k] = vals
    return out


def apply_to_company(c: dict, rec: dict | None, saved_years: list[str], years: list[str]) -> dict:
    c = copy.deepcopy(c)
    if not rec or not rec.get("ok"):
        if years != saved_years:
            c["financials"] = merge_financials(c["financials"], saved_years, None, years)
        return c
    c["financials"] = merge_financials(c["financials"], saved_years, rec, years)
    if rec.get("quarterly"):
        c["quarterly"], c["quarter_labels"] = rec["quarterly"], rec["quarter_labels"]
    if rec.get("ttm") and all(v is not None for v in rec["ttm"].values()):
        c["ttm"] = rec["ttm"]
    if rec.get("market"):
        c["market"] = {**c.get("market", {}), **rec["market"], "price_date": rec["fetched"][:10]}
    if rec.get("shareholding") and sum(rec["shareholding"].values()) > 90:
        c.setdefault("market", {})["shareholding"] = rec["shareholding"]
    c["live"] = {"fetched": rec["fetched"], "latest_fy": rec["years"][-1], "latest_quarter": (rec.get("quarter_labels") or ["-"])[-1]}
    return c


# ── display helpers ──────────────────────────────────────────────────────────
def ist(iso: str | None) -> str:
    """'2026-11-06T14:30:00+00:00' -> '6 Nov, 20:00 IST'."""
    if not iso:
        return "not yet"
    from datetime import timedelta  # noqa: WPS433

    t = datetime.fromisoformat(iso) + timedelta(hours=5, minutes=30)
    return f"{t.day} {t.strftime('%b')}, {t.strftime('%H:%M')} IST"


def recent_new(status: dict, symbols: list[str], days: int = 21) -> list[tuple[str, str]]:
    """(company, what is new) for results detected in the last `days` days."""
    out = []
    now = datetime.now(timezone.utc)
    for sym in symbols:
        stt = status.get(sym, {})
        if stt.get("new") and stt.get("new_since"):
            if (now - datetime.fromisoformat(stt["new_since"])).days <= days:
                out.append((stt.get("name", sym), "; ".join(stt["new"])))
    return out
