"""
styles.py — Global CSS injection and HTML component helpers.

All visual primitives live here so the three UI modules stay clean.
Import pattern:
    from styles import inject_css, metric_card_html, medicine_card_html, ...
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Master CSS
# ---------------------------------------------------------------------------

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap');

/* ── Base ──────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Hide default Streamlit chrome */
#MainMenu  { visibility: hidden; }
footer     { visibility: hidden; }
header     { visibility: hidden; }

.main .block-container {
    padding-top: 1.75rem;
    padding-bottom: 2.5rem;
    max-width: 1280px;
}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.04);
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stSelectbox > label,
[data-testid="stSidebar"] .stTextInput  > label {
    color: #64748B !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] button {
    background: rgba(37,99,235,0.15) !important;
    border: 1px solid rgba(37,99,235,0.3) !important;
    color: #93C5FD !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(37,99,235,0.3) !important;
    color: #BFDBFE !important;
    transform: none !important;
}

/* ── Buttons ───────────────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.6rem !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.02em;
    transition: all 0.2s cubic-bezier(0.4,0,0.2,1) !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.3) !important;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(37,99,235,0.45) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Form / Inputs ─────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: var(--secondary-background-color) !important;
    border-radius: 20px;
    padding: 2rem !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
}
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stNumberInput"] div[data-baseweb="input"],
[data-testid="stTextArea"] div[data-baseweb="textarea"] {
    border-radius: 10px !important;
    border: 1.5px solid rgba(128, 128, 128, 0.2) !important;
    background: var(--background-color) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    color: var(--text-color) !important;
    background: transparent !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stDateInput"] label {
    font-weight: 600 !important;
    font-size: 0.825rem !important;
    color: var(--text-color) !important;
    margin-bottom: 0.3rem !important;
    opacity: 0.9;
}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--secondary-background-color);
    padding: 5px;
    border-radius: 12px;
    border: 1px solid rgba(128, 128, 128, 0.2);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    padding: 0.5rem 1.4rem !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: var(--text-color) !important;
    opacity: 0.6;
    background: transparent !important;
    border: none !important;
    transition: all 0.15s !important;
}
.stTabs [aria-selected="true"] {
    background: var(--background-color) !important;
    color: var(--primary-color) !important;
    opacity: 1 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
}

/* ── Dataframe ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] > div {
    border-radius: 14px !important;
    overflow: hidden !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
}

/* ── Slider ────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] label {
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    color: var(--text-color) !important;
    opacity: 0.9;
}
[data-testid="stSlider"] > div > div > div > div {
    background: #2563EB !important;
}

/* ── Alerts / notifications ────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
}

/* ── Expanders ─────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
    background: var(--secondary-background-color) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: var(--text-color) !important;
}

/* ── Divider ───────────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid rgba(128, 128, 128, 0.15) !important;
    margin: 1.5rem 0 !important;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--background-color); }
::-webkit-scrollbar-thumb { background: rgba(128, 128, 128, 0.3); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(128, 128, 128, 0.5); }
"""


def inject_css() -> None:
    """Inject the master CSS into the Streamlit page. Call once per page render."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------------------------

def sidebar_logo(role: str = "Admin Portal") -> None:
    st.sidebar.markdown(f"""
    <div style="
        padding: 1.5rem 1rem 1.25rem;
        border-bottom: 1px solid rgba(255,255,255,0.07);
        margin-bottom: 0.5rem;
        text-align: center;
    ">
        <div style="font-size:2.4rem; margin-bottom:0.4rem;">💊</div>
        <div style="font-size:1rem; font-weight:800; color:#F1F5F9; letter-spacing:0.02em;">
            PharmaSystem
        </div>
        <div style="font-size:0.68rem; color:#475569; text-transform:uppercase;
                    letter-spacing:0.1em; margin-top:0.2rem;">
            {role}
        </div>
    </div>
    """, unsafe_allow_html=True)


def sidebar_section_label(text: str) -> None:
    st.sidebar.markdown(f"""
    <div style="font-size:0.68rem; font-weight:700; color:#475569;
                text-transform:uppercase; letter-spacing:0.1em;
                padding: 0.75rem 0.25rem 0.3rem;">
        {text}
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"""
    <div style="padding:0.5rem 0 1.25rem; border-bottom:2px solid rgba(128, 128, 128, 0.15); margin-bottom:1.75rem;">
        <h1 style="font-size:1.6rem; font-weight:800; color:var(--text-color);
                   margin:0 0 0.2rem; letter-spacing:-0.02em;">{title}</h1>
        <p style="font-size:0.875rem; color:var(--text-color); opacity:0.7; margin:0; font-weight:400;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Metric cards
# ---------------------------------------------------------------------------

def metric_cards_row(cards: list) -> None:
    """
    Render a row of metric cards.
    cards: list of dicts with keys: icon, value, label, color (optional), bg (optional)
    """
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        color = card.get("color", "#2563EB")
        bg    = card.get("bg", "#EFF6FF")
        with col:
            st.markdown(f"""
            <div style="
                background: var(--secondary-background-color);
                border-radius: 16px;
                padding: 1.4rem 1.25rem;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 16px rgba(0,0,0,0.06);
                border: 1px solid rgba(128, 128, 128, 0.15);
                border-top: 4px solid {color};
                transition: transform 0.2s, box-shadow 0.2s;
            ">
                <div style="
                    width:44px; height:44px; border-radius:12px;
                    background:{bg}; display:flex; align-items:center;
                    justify-content:center; font-size:1.4rem; margin-bottom:0.9rem;
                ">{card['icon']}</div>
                <div style="font-size:2rem; font-weight:800; color:var(--text-color);
                            line-height:1; margin-bottom:0.3rem;">
                    {card['value']}
                </div>
                <div style="font-size:0.78rem; font-weight:600; color:var(--text-color); opacity:0.7;
                            text-transform:uppercase; letter-spacing:0.06em;">
                    {card['label']}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Alert banners
# ---------------------------------------------------------------------------

def alert_danger(title: str, body: str) -> None:
    st.markdown(f"""
    <div style="
        background:rgba(239, 68, 68, 0.1);
        border:1px solid rgba(239, 68, 68, 0.25); border-left:4px solid #EF4444;
        border-radius:14px; padding:1rem 1.25rem;
        margin-bottom:1.25rem; display:flex; gap:0.85rem; align-items:flex-start;
    ">
        <span style="font-size:1.3rem; flex-shrink:0;">🚨</span>
        <div>
            <div style="font-weight:700; font-size:0.92rem; color:var(--text-color);
                        margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.82rem; color:var(--text-color); opacity:0.85; line-height:1.6;">{body}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def alert_warning(title: str, body: str) -> None:
    st.markdown(f"""
    <div style="
        background:rgba(245, 158, 11, 0.1);
        border:1px solid rgba(245, 158, 11, 0.25); border-left:4px solid #F59E0B;
        border-radius:14px; padding:1rem 1.25rem; margin-bottom:1.25rem;
        display:flex; gap:0.85rem; align-items:flex-start;
    ">
        <span style="font-size:1.3rem; flex-shrink:0;">⚠️</span>
        <div>
            <div style="font-weight:700; font-size:0.92rem; color:var(--text-color);
                        margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.82rem; color:var(--text-color); opacity:0.85; line-height:1.6;">{body}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def alert_success(title: str, body: str) -> None:
    st.markdown(f"""
    <div style="
        background:rgba(16, 185, 129, 0.1);
        border:1px solid rgba(16, 185, 129, 0.25); border-left:4px solid #10B981;
        border-radius:14px; padding:1rem 1.25rem; margin-bottom:1.25rem;
        display:flex; gap:0.85rem; align-items:flex-start;
    ">
        <span style="font-size:1.3rem; flex-shrink:0;">✅</span>
        <div>
            <div style="font-weight:700; font-size:0.92rem; color:var(--text-color);
                        margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.82rem; color:var(--text-color); opacity:0.85; line-height:1.6;">{body}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Medicine card (header only — sliders remain native Streamlit below)
# ---------------------------------------------------------------------------

def medicine_card_header(name: str, use: str, price: float,
                         expiry: str, qty: int) -> None:
    stock_ok   = qty > 10
    stock_bg   = "rgba(16, 185, 129, 0.15)" if stock_ok else "rgba(239, 68, 68, 0.15)"
    stock_col  = "#10B981" if stock_ok else "#EF4444"
    stock_icon = "✓"       if stock_ok else "⚠"
    stock_text = f"{qty} in stock" if stock_ok else f"Low stock ({qty})"

    st.markdown(f"""
    <div style="
        background:var(--secondary-background-color); border-radius:16px;
        padding:1.25rem; margin-bottom:0.25rem;
        box-shadow:0 1px 3px rgba(0,0,0,0.05),0 4px 16px rgba(0,0,0,0.06);
        border:1px solid rgba(128, 128, 128, 0.15);
        border-top: 3px solid {'#10B981' if stock_ok else '#EF4444'};
        transition:transform 0.2s,box-shadow 0.2s;
    ">
        <div style="display:flex; align-items:center; gap:0.9rem; margin-bottom:0.9rem;">
            <div style="
                width:56px; height:56px; border-radius:12px;
                background:rgba(37, 99, 235, 0.08);
                display:flex; align-items:center; justify-content:center;
                font-size:1.9rem; flex-shrink:0;
            ">💊</div>
            <div style="flex:1; min-width:0;">
                <div style="font-size:1rem; font-weight:700; color:var(--text-color);
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                    {name}
                </div>
                <div style="font-size:0.78rem; color:var(--text-color); opacity:0.7; line-height:1.4;
                            margin-top:0.15rem; display:-webkit-box;
                            -webkit-line-clamp:2; -webkit-box-orient:vertical;
                            overflow:hidden;">
                    {use}
                </div>
            </div>
        </div>

        <div style="display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap;
                    margin-bottom:0.5rem;">
            <span style="
                display:inline-block;
                background:linear-gradient(135deg,#2563EB,#1D4ED8);
                color:white; font-weight:700; font-size:0.95rem;
                padding:0.28rem 0.8rem; border-radius:8px;">
                ₹ {float(price):.2f}
            </span>
            <span style="
                display:inline-flex; align-items:center; gap:0.25rem;
                background:{stock_bg}; color:{stock_col};
                font-size:0.74rem; font-weight:700;
                padding:0.28rem 0.65rem; border-radius:20px;">
                {stock_icon} {stock_text}
            </span>
        </div>

        <div style="font-size:0.74rem; color:var(--text-color); opacity:0.5; font-weight:500;">
            ⏳ Expires: {expiry}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Order total banner
# ---------------------------------------------------------------------------

def order_total_banner(item_count: int, total: float) -> None:
    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg,#2563EB 0%,#1D4ED8 100%);
        border-radius:16px; padding:1.25rem 1.75rem;
        color:white; display:flex; justify-content:space-between;
        align-items:center; margin:1rem 0;
        box-shadow:0 8px 25px rgba(37,99,235,0.35);
    ">
        <div>
            <div style="font-size:0.82rem; font-weight:500; opacity:0.8;
                        text-transform:uppercase; letter-spacing:0.06em;">
                Order Total
            </div>
            <div style="font-size:0.78rem; opacity:0.65; margin-top:0.15rem;">
                {item_count} item{'s' if item_count != 1 else ''} selected
            </div>
        </div>
        <div style="font-size:2rem; font-weight:800; letter-spacing:-0.02em;">
            ₹ {total:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Section divider with label
# ---------------------------------------------------------------------------

def section_header(icon: str, title: str) -> None:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:0.6rem;
                margin:1.75rem 0 1rem; padding-bottom:0.75rem;
                border-bottom:2px solid rgba(128, 128, 128, 0.15);">
        <span style="font-size:1.15rem;">{icon}</span>
        <span style="font-size:1rem; font-weight:700; color:var(--text-color);">{title}</span>
    </div>
    """, unsafe_allow_html=True)
