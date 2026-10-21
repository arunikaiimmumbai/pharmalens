"""Visual system: pharma white/blue theme, Plotly template and reusable HTML components."""
from __future__ import annotations

import base64

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

NAVY = "#0A2A66"
BLUE = "#1D4ED8"
SKY = "#3B82F6"
ICE = "#EAF2FF"
CYAN = "#06B6D4"
INK = "#0F1B33"
INK2 = "#42526E"
MUTED = "#7A8AA6"
LINE = "#DCE6F5"
GOOD = "#0F9D58"
WARN = "#D97706"
BAD = "#C62828"

# Sequential (one hue, light → dark) and diverging (two poles, grey midpoint)
SEQ_BLUES = ["#EFF5FF", "#C9DCFF", "#93B8FF", "#5B8FF5", "#2F62D8", "#173E9E", "#0A2A66"]
DIVERGING = [[0.0, "#C2410C"], [0.5, "#F3F4F6"], [1.0, "#1D4ED8"]]

# ── SVG motifs ───────────────────────────────────────────────────────────────
HEX_PATTERN = """<svg xmlns='http://www.w3.org/2000/svg' width='112' height='97' viewBox='0 0 112 97'>
<g fill='none' stroke='%23C9DCFF' stroke-width='1' opacity='0.55'>
<path d='M28 2 L56 18 L56 50 L28 66 L0 50 L0 18 Z'/>
<path d='M84 34 L112 50 L112 82 L84 98 L56 82 L56 50 Z'/>
<circle cx='28' cy='2' r='2.2' fill='%2393B8FF'/><circle cx='56' cy='50' r='2.2' fill='%2393B8FF'/>
<circle cx='0' cy='50' r='2.2' fill='%2393B8FF'/><circle cx='84' cy='98' r='2.2' fill='%2393B8FF'/>
</g></svg>"""

LOGO_SVG = """<svg width="38" height="38" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3B82F6"/><stop offset="1" stop-color="#0A2A66"/></linearGradient></defs>
<path d="M32 4 L56 18 L56 46 L32 60 L8 46 L8 18 Z" fill="url(#lg)"/>
<g stroke="#fff" stroke-width="2.4" fill="none" stroke-linecap="round">
<path d="M22 22 C 30 30, 34 34, 42 42"/><path d="M42 22 C 34 30, 30 34, 22 42"/>
<path d="M24 26 H40" opacity=".7"/><path d="M24 38 H40" opacity=".7"/><path d="M28 32 H36" opacity=".9"/></g>
<circle cx="32" cy="32" r="3" fill="#06B6D4"/></svg>"""

HELIX_SVG = """<svg viewBox="0 0 420 160" xmlns="http://www.w3.org/2000/svg" class="helix">
<defs><linearGradient id="hg" x1="0" x2="1"><stop offset="0" stop-color="#93B8FF" stop-opacity=".2"/><stop offset=".5" stop-color="#ffffff"/><stop offset="1" stop-color="#93B8FF" stop-opacity=".2"/></linearGradient></defs>
<g fill="none" stroke="url(#hg)" stroke-width="3">
<path class="s1" d="M0 80 C 35 10, 70 10, 105 80 S 175 150, 210 80 S 280 10, 315 80 S 385 150, 420 80"/>
<path class="s2" d="M0 80 C 35 150, 70 150, 105 80 S 175 10, 210 80 S 280 150, 315 80 S 385 10, 420 80"/></g>
<g stroke="#ffffff" stroke-opacity=".35" stroke-width="2">
<line x1="26" y1="40" x2="26" y2="120"/><line x1="52" y1="28" x2="52" y2="132"/><line x1="79" y1="40" x2="79" y2="120"/>
<line x1="131" y1="40" x2="131" y2="120"/><line x1="157" y1="28" x2="157" y2="132"/><line x1="184" y1="40" x2="184" y2="120"/>
<line x1="236" y1="40" x2="236" y2="120"/><line x1="262" y1="28" x2="262" y2="132"/><line x1="289" y1="40" x2="289" y2="120"/>
<line x1="341" y1="40" x2="341" y2="120"/><line x1="367" y1="28" x2="367" y2="132"/><line x1="394" y1="40" x2="394" y2="120"/></g>
<g fill="#06B6D4"><circle cx="105" cy="80" r="4"/><circle cx="210" cy="80" r="4"/><circle cx="315" cy="80" r="4"/></g></svg>"""

CAPSULE = """<svg width="22" height="22" viewBox="0 0 24 24"><g transform="rotate(-45 12 12)"><rect x="3" y="8" width="18" height="8" rx="4" fill="#EAF2FF" stroke="#1D4ED8" stroke-width="1.4"/><path d="M12 8 H17 a4 4 0 0 1 0 8 H12 Z" fill="#1D4ED8"/></g></svg>"""


def _hex_bg() -> str:
    return "data:image/svg+xml;utf8," + HEX_PATTERN.replace("\n", "")


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
:root {{ --navy:{NAVY}; --blue:{BLUE}; --sky:{SKY}; --ice:{ICE}; --cyan:{CYAN}; --ink:{INK}; --ink2:{INK2}; --muted:{MUTED}; --line:{LINE}; }}
html, body, [class*="css"], .stMarkdown, .stText, p, li, label, input, textarea, button {{ font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important; }}
.stApp {{ background: #F7FAFF url("{_hex_bg()}") repeat; background-attachment: fixed; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.2rem; max-width: 1480px; }}
h1, h2, h3, h4 {{ color: var(--navy) !important; letter-spacing: -0.02em; font-weight: 800 !important; }}
[data-testid="stSidebar"] {{ background: linear-gradient(185deg, #0A2A66 0%, #0F3A8C 55%, #1D4ED8 100%); border-right: 1px solid rgba(255,255,255,.08); }}
[data-testid="stSidebar"] * {{ color: #E8F0FF !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ border-radius: 12px; margin: 2px 6px; transition: all .2s; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background: rgba(255,255,255,.12); }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background: rgba(255,255,255,.18); box-shadow: inset 3px 0 0 #06B6D4; }}
[data-testid="stSidebar"] [data-baseweb="select"] > div {{ background: #fff !important; border-color: rgba(255,255,255,.4); }}
[data-testid="stSidebar"] [data-baseweb="select"] * {{ color: #0A2A66 !important; }}
[data-testid="stSidebar"] input {{ color: #0A2A66 !important; background:#fff !important; }}
[data-testid="stSidebarHeader"] img, [data-testid="stLogo"] {{ height: 44px !important; max-width: 230px !important; }}

/* Hero */
.hero {{ position: relative; overflow: hidden; border-radius: 24px; padding: 28px 34px; margin-bottom: 18px;
  background: radial-gradient(1200px 300px at 85% -40%, rgba(6,182,212,.45), transparent 60%),
              linear-gradient(120deg, #0A2A66 0%, #1D4ED8 60%, #3B82F6 100%);
  color: #fff; box-shadow: 0 18px 40px -18px rgba(10,42,102,.55); }}
.hero h1 {{ color: #fff !important; font-size: 2.1rem; margin: 0 0 4px 0; }}
.hero .sub {{ color: #D6E4FF; font-size: 1.02rem; max-width: 760px; }}
.hero .chip {{ display:inline-flex; gap:6px; align-items:center; background: rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.25);
  padding: 4px 12px; border-radius: 999px; font-size: .78rem; margin: 10px 6px 0 0; backdrop-filter: blur(6px); }}
.hero .helix {{ position:absolute; right:-10px; top:6px; width: 440px; opacity:.55; }}
.hero .helix .s1 {{ stroke-dasharray: 8 6; animation: flow 6s linear infinite; }}
.hero .helix .s2 {{ stroke-dasharray: 8 6; animation: flow 6s linear infinite reverse; }}
@keyframes flow {{ to {{ stroke-dashoffset: -280; }} }}
.pulse {{ width:9px; height:9px; border-radius:50%; background:#22E3A1; box-shadow:0 0 0 0 rgba(34,227,161,.7); animation: pulse 1.8s infinite; display:inline-block; }}
@keyframes pulse {{ 0% {{ box-shadow:0 0 0 0 rgba(34,227,161,.6);}} 70% {{ box-shadow:0 0 0 10px rgba(34,227,161,0);}} 100% {{ box-shadow:0 0 0 0 rgba(34,227,161,0);}} }}

/* Cards */
.card {{ background: rgba(255,255,255,.92); border: 1px solid var(--line); border-radius: 18px; padding: 16px 18px;
  box-shadow: 0 6px 22px -14px rgba(16,42,102,.35); backdrop-filter: blur(8px); height: 100%; }}
.card h4 {{ margin: 0 0 6px 0; font-size: 1.0rem; }}
.card .muted {{ color: var(--muted); font-size: .82rem; }}
.kpi {{ background: #fff; border: 1px solid var(--line); border-radius: 16px; padding: 14px 16px; position: relative; overflow: hidden;
  box-shadow: 0 6px 20px -16px rgba(16,42,102,.45); transition: transform .15s, box-shadow .15s; }}
.kpi:hover {{ transform: translateY(-2px); box-shadow: 0 14px 30px -18px rgba(29,78,216,.55); }}
.kpi::after {{ content:""; position:absolute; right:-18px; top:-18px; width:70px; height:70px; border-radius:50%;
  background: radial-gradient(circle, rgba(59,130,246,.18), transparent 70%); }}
.kpi .lab {{ color: var(--ink2); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; font-weight:600; }}
.kpi .val {{ color: var(--navy); font-size: 1.45rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; line-height: 1.25; white-space: nowrap; }}
.kpi .delta {{ font-size: .8rem; font-weight: 600; }}
.up {{ color: {GOOD}; }} .down {{ color: {BAD}; }} .flat {{ color: var(--muted); }}
.section {{ display:flex; align-items:center; gap:10px; margin: 22px 0 8px 0; }}
.section .bar {{ width: 6px; height: 26px; border-radius: 6px; background: linear-gradient(180deg, #06B6D4, #1D4ED8); }}
.section h3 {{ margin:0 !important; font-size: 1.25rem; }}
.section .tag {{ color: var(--muted); font-size: .85rem; }}
.pill {{ display:inline-block; padding: 3px 10px; border-radius: 999px; font-size: .74rem; font-weight: 600; margin: 2px 4px 2px 0;
  background: var(--ice); color: var(--blue); border: 1px solid #C9DCFF; }}
.pill.good {{ background:#E8F7EF; color:{GOOD}; border-color:#BFE8D0; }}
.pill.bad {{ background:#FDECEC; color:{BAD}; border-color:#F5C7C7; }}
.pill.warn {{ background:#FFF4E5; color:{WARN}; border-color:#FBD9A8; }}
.newsrow {{ border-left: 3px solid var(--sky); padding: 8px 12px; margin: 8px 0; background: #fff; border-radius: 0 12px 12px 0; border-top:1px solid var(--line); border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
.newsrow .d {{ color: var(--muted); font-size: .76rem; font-family: 'JetBrains Mono', monospace; }}
.newsrow .t {{ color: var(--ink); font-weight: 700; font-size: .95rem; }}
.newsrow .i {{ color: var(--ink2); font-size: .85rem; }}
.list-good li::marker {{ color: {GOOD}; }} .list-bad li::marker {{ color: {BAD}; }}
.problem {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:14px 16px; margin-bottom:10px; position:relative; }}
.problem .n {{ position:absolute; left:-12px; top:14px; width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#06B6D4,#1D4ED8);
  color:#fff; font-weight:800; display:flex; align-items:center; justify-content:center; font-size:.85rem; box-shadow:0 4px 10px rgba(29,78,216,.4); }}
.problem h5 {{ margin:0 0 6px 18px; color:var(--navy); font-size:1.02rem; }}
.problem .row {{ margin-left:18px; font-size:.88rem; color: var(--ink2); margin-bottom:4px; }}
.problem .row b {{ color: var(--ink); }}
.foot {{ color: var(--muted); font-size: .75rem; margin-top: 26px; border-top: 1px dashed var(--line); padding-top: 10px; }}
.agent-trace {{ font-family: 'JetBrains Mono', monospace; font-size: .76rem; color: #1D4ED8; background:#F1F6FF; border:1px solid #D6E4FF; border-radius:10px; padding:6px 10px; margin:4px 0; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{ background: #fff; border: 1px solid var(--line); border-radius: 12px 12px 0 0; padding: 8px 16px; font-weight: 600; }}
.stTabs [aria-selected="true"] {{ background: linear-gradient(180deg,#EAF2FF,#fff) !important; color: var(--blue) !important; border-bottom-color: #fff !important; }}
div[data-testid="stMetric"] {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:10px 14px; }}
.stButton > button {{ border-radius: 12px; border: 1px solid #C9DCFF; background: #fff; color: var(--blue); font-weight: 600; }}
.stButton > button:hover {{ border-color: var(--blue); color: #fff; background: var(--blue); }}
.stButton > button[kind="primary"] {{ background: linear-gradient(135deg, #1D4ED8, #06B6D4); color:#fff; border:none; }}
[data-testid="stChatMessage"] {{ background: rgba(255,255,255,.9); border:1px solid var(--line); border-radius: 16px; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, chips: list[str] | None = None) -> None:
    chips_html = "".join(f'<span class="chip">{c}</span>' for c in (chips or []))
    st.markdown(
        f"""<div class="hero">{HELIX_SVG}
        <div style="position:relative;z-index:2"><h1>{title}</h1><div class="sub">{subtitle}</div>{chips_html}</div></div>""",
        unsafe_allow_html=True,
    )


def section(title: str, tag: str = "") -> None:
    st.markdown(f'<div class="section"><div class="bar"></div><h3>{title}</h3><span class="tag">{tag}</span></div>',
                unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", direction: str = "flat", note: str = "") -> str:
    arrow = {"up": "▲", "down": "▼", "flat": "•"}[direction]
    d = f'<div class="delta {direction}">{arrow} {delta}</div>' if delta else ""
    n = f'<div class="muted" style="color:#7A8AA6;font-size:.72rem;margin-top:2px">{note}</div>' if note else ""
    return f'<div class="kpi"><div class="lab">{label}</div><div class="val">{value}</div>{d}{n}</div>'


def kpi_row(cards: list[str]) -> None:
    cols = st.columns(len(cards))
    for col, html in zip(cols, cards):
        col.markdown(html, unsafe_allow_html=True)


def pill(text: str, kind: str = "") -> str:
    return f'<span class="pill {kind}">{text}</span>'


def footer(meta: dict) -> None:
    st.markdown(
        f"""<div class="foot">Prepared by <b>{meta['author']}</b> · {meta['program']} · Mentor: <b>{meta['mentor']}</b> ·
        {meta['basis']} Public information only; not investment advice.</div>""",
        unsafe_allow_html=True,
    )


# ── Plotly template ──────────────────────────────────────────────────────────
def register_plotly_template() -> None:
    t = go.layout.Template()
    t.layout = go.Layout(
        font=dict(family="Plus Jakarta Sans, sans-serif", color=INK2, size=13),
        title=dict(font=dict(color=NAVY, size=16, family="Plus Jakarta Sans, sans-serif"), x=0.01, xanchor="left"),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        colorway=["#1D4ED8", "#0E9F9A", "#7C3AED", "#0284C7", "#C2410C", "#4F46E5"],
        xaxis=dict(showgrid=False, linecolor=LINE, tickcolor=LINE, zeroline=False),
        yaxis=dict(gridcolor="#EAF0FA", zeroline=False, linecolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.18, x=0, font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#0A2A66", font=dict(color="#fff", family="Plus Jakarta Sans")),
        margin=dict(l=10, r=10, t=48, b=10),
        hovermode="x unified",
    )
    pio.templates["pharma"] = t
    pio.templates.default = "pharma"


def style_fig(fig: go.Figure, height: int = 380, title: str | None = None) -> go.Figure:
    fig.update_layout(height=height)
    if title:
        fig.update_layout(title=title)
    fig.update_traces(selector=dict(type="scatter", mode="lines+markers"), line=dict(width=2.5), marker=dict(size=8))
    fig.update_traces(selector=dict(type="bar"), marker_line_width=0)
    return fig


def logo_html(meta: dict) -> str:
    return f"""<div style="display:flex;align-items:center;gap:10px;padding:6px 4px 14px 4px">{LOGO_SVG}
    <div><div style="font-weight:800;font-size:1.15rem;letter-spacing:-.01em">PharmaLens<span style="color:#06B6D4">.ai</span></div>
    <div style="font-size:.72rem;opacity:.8">Agentic pharma intelligence</div></div></div>"""
