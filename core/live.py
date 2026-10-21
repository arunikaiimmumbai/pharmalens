"""Live layer: market prices (Yahoo Finance via yfinance) and news (Google News RSS).

Everything degrades gracefully: if the network or a provider is unavailable the app keeps
running on the curated dataset and says so on screen.
"""
from __future__ import annotations

import re
import urllib.parse
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import streamlit as st

BENCHMARK = "^CNXPHARMA"  # Nifty Pharma index on Yahoo Finance

POS = {"approval", "approves", "approved", "surge", "surges", "jumps", "jump", "beats", "beat", "record", "upgrade", "upgrades",
       "raises", "raised", "growth", "rises", "rise", "gains", "launch", "launches", "closeout", "vai", "eir", "strong", "profit up",
       "acquire", "acquires", "expands", "buy", "outperform", "exclusivity", "first generic", "rallies", "soars", "milestone"}
NEG = {"warning letter", "oai", "import alert", "483", "observations", "falls", "fall", "drops", "drop", "decline", "declines",
       "cut", "cuts", "downgrade", "downgrades", "loss", "probe", "search", "recall", "penalty", "tariff", "slump", "plunge",
       "weak", "misses", "miss", "sell", "lawsuit", "litigation", "settlement", "pressure", "52-week low", "slides", "dips"}

CATEGORY_RULES = [
    ("Regulatory", r"usfda|fda|anda|warning letter|oai|vai|eir|483|inspection|approval|tentative"),
    ("Results", r"q[1-4]|quarter|results|profit|revenue|ebitda|earnings|pat"),
    ("M&A", r"acquir|acquisition|stake|merger|buyout|deal"),
    ("Policy", r"tariff|nppa|price control|gst|policy|government|ministry|section 232"),
    ("Investor", r"target|upgrade|downgrade|rating|broker|shares|stock|52-week"),
    ("Launch", r"launch|introduc|unveil"),
]


def lexicon_sentiment(text: str) -> int:
    t = text.lower()
    p = sum(1 for w in POS if w in t)
    n = sum(1 for w in NEG if w in t)
    return int(np.sign(p - n))


def categorise(text: str) -> str:
    t = text.lower()
    for cat, rx in CATEGORY_RULES:
        if re.search(rx, t):
            return cat
    return "General"


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_news(query: str, days: int = 180, limit: int = 40) -> tuple[pd.DataFrame, str | None]:
    """Google News RSS search. Returns (frame, error)."""
    try:
        import feedparser  # noqa: WPS433
    except Exception as e:  # pragma: no cover
        return pd.DataFrame(), f"feedparser not installed ({e})"
    q = urllib.parse.quote(f'"{query}" when:{days}d')
    url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        return pd.DataFrame(), f"News feed unreachable ({e})"
    rows = []
    for e in feed.entries[:limit]:
        title = re.sub(r"\s+-\s+[^-]+$", "", e.get("title", ""))
        src = e.get("source", {}).get("title", "") if isinstance(e.get("source"), dict) else ""
        try:
            dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            dt = None
        rows.append({"date": dt, "title": title, "source": src, "url": e.get("link", ""),
                     "sentiment": lexicon_sentiment(title), "category": categorise(title)})
    df = pd.DataFrame(rows)
    if df.empty:
        return df, "No live items returned (feed blocked or empty)."
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(None)
    cutoff = datetime.utcnow() - timedelta(days=days)
    df = df[df["date"] >= cutoff].sort_values("date", ascending=False).drop_duplicates("title")
    return df, None


@st.cache_data(ttl=60 * 15, show_spinner=False)
def fetch_prices(tickers: tuple[str, ...], period: str = "1y") -> tuple[pd.DataFrame, str | None]:
    """Adjusted close prices for tickers + Nifty Pharma benchmark."""
    try:
        import yfinance as yf  # noqa: WPS433
    except Exception as e:  # pragma: no cover
        return pd.DataFrame(), f"yfinance not installed ({e})"
    try:
        data = yf.download(list(tickers) + [BENCHMARK], period=period, interval="1d",
                           auto_adjust=True, progress=False, threads=True)
        if data is None or data.empty:
            return pd.DataFrame(), "Market data provider returned no data."
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
        close = close.dropna(how="all")
        return close, None
    except Exception as e:
        return pd.DataFrame(), f"Market data unavailable ({e})"


@st.cache_data(ttl=60 * 15, show_spinner=False)
def fetch_quote(ticker: str) -> dict:
    try:
        import yfinance as yf  # noqa: WPS433
        fi = yf.Ticker(ticker).fast_info
        return {"price": float(fi["last_price"]), "prev": float(fi["previous_close"]),
                "mcap_cr": float(fi["market_cap"]) / 1e7 if fi.get("market_cap") else None}
    except Exception:
        return {}


def event_study(prices: pd.DataFrame, ticker: str, events: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    """Abnormal return (stock − Nifty Pharma) from t-1 to t+window trading days around each news date."""
    if prices.empty or ticker not in prices or BENCHMARK not in prices:
        return pd.DataFrame()
    px = prices[[ticker, BENCHMARK]].dropna()
    out = []
    for _, ev in events.iterrows():
        d = pd.Timestamp(ev["date"]).normalize()
        idx = px.index.searchsorted(d)
        if idx <= 0 or idx + window >= len(px):
            continue
        p0 = px.iloc[idx - 1]
        p1 = px.iloc[idx + window]
        r_s = p1[ticker] / p0[ticker] - 1
        r_b = p1[BENCHMARK] / p0[BENCHMARK] - 1
        out.append({"date": ev["date"], "title": ev["title"], "sentiment": ev.get("sentiment", 0),
                    "stock_ret_%": r_s * 100, "bench_ret_%": r_b * 100, "abnormal_%": (r_s - r_b) * 100})
    return pd.DataFrame(out)
