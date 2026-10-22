"""Analyst notes (data/notes.json): the short 'why' write-up shown under each chart, with source links."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

NOTES_PATH = Path(__file__).resolve().parent.parent / "data" / "notes.json"
SYMBOL = {"alembic": "APLLTD", "ajanta": "AJANTPHARM", "ipca": "IPCALAB", "mankind": "MANKIND", "alkem": "ALKEM", "glenmark": "GLENMARK"}


@st.cache_data(show_spinner=False)
def _load(mtime: float) -> dict:
    with open(NOTES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _all() -> dict:
    return _load(NOTES_PATH.stat().st_mtime)


def company(cid: str, theme: str) -> dict | None:
    return _all()["company"].get(cid, {}).get(theme)


def peer(key: str) -> dict | None:
    return _all()["peer"].get(key)


def screener(cid: str) -> dict:
    return {"title": f"Screener.in: {cid.title()} consolidated financials", "url": f"https://www.screener.in/company/{SYMBOL[cid]}/consolidated/"}


def sources_md(sources: list[dict]) -> str:
    seen, out = set(), []
    for s in sources or []:
        if s.get("url") and s["url"] not in seen:
            seen.add(s["url"])
            out.append(f'<a href="{s["url"]}" target="_blank">{s["title"]}</a>')
    return " · ".join(out)
