"""Analyst notes (data/notes.json): the short 'why' write-up shown under each chart, with source links."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from core import data as D


def _path(seg: str) -> Path:
    return D.DATA_DIR / D.SEGMENTS[seg]["notes"]


@st.cache_data(show_spinner=False)
def _load(path: str, mtime: float) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _all(seg: str | None = None) -> dict:
    p = _path(seg or D.segment())
    if not p.exists():
        return {"company": {}, "peer": {}}
    return _load(str(p), p.stat().st_mtime)


def company(cid: str, theme: str) -> dict | None:
    try:
        seg = D.segment_of(cid)
    except KeyError:
        return None
    return _all(seg)["company"].get(cid, {}).get(theme)


def peer(key: str) -> dict | None:
    return _all()["peer"].get(key)


def screener(cid: str) -> dict:
    return {"title": f"Screener.in: {D.company(cid)['short']} consolidated financials",
            "url": f"https://www.screener.in/company/{D.symbol(cid)}/consolidated/"}


def sources_md(sources: list[dict]) -> str:
    seen, out = set(), []
    for s in sources or []:
        if s.get("url") and s["url"] not in seen:
            seen.add(s["url"])
            out.append(f'<a href="{s["url"]}" target="_blank">{s["title"]}</a>')
    return " · ".join(out)
