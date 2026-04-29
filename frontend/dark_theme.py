"""
PropCompassAI — Dark Theme UI Components
Glassmorphism + Midnight Blue + Vibrant Accents
Add this to frontend/app.py at the top of the main app section
"""

DARK_THEME_CSS = """
<style>
/* ── Google Fonts ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

/* ── CSS Variables ────────────────────────────────────────── */
:root {
    --bg-deep:       #0B1120;
    --bg-card:       rgba(16, 28, 52, 0.85);
    --bg-glass:      rgba(13, 22, 45, 0.75);
    --bg-input:      rgba(255,255,255,0.05);
    --accent-blue:   #0D6EFD;
    --accent-blue2:  #3B82F6;
    --accent-red:    #F13A30;
    --accent-green:  #10B981;
    --accent-amber:  #F59E0B;
    --accent-gold:   #F5C842;
    --text-primary:  #F0F4FF;
    --text-secondary:#94A3B8;
    --text-muted:    #4A5568;
    --border-glass:  rgba(99,130,255,0.15);
    --border-glow:   rgba(13,110,253,0.4);
    --shadow-card:   0 8px 32px rgba(0,0,0,0.4);
    --shadow-glow:   0 0 30px rgba(13,110,253,0.2);
    --blur:          blur(12px);
    --radius-lg:     16px;
    --radius-xl:     24px;
    --radius-pill:   100px;
}

/* ── Global Reset ─────────────────────────────────────────── */
.stApp {
    background: linear-gradient(135deg, #0B1120 0%, #0D1B35 50%, #0A1628 100%) !important;
    font-family: 'Nunito', sans-serif !important;
    min-height: 100vh;
}

/* Animated background grid */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background-image:
        linear-gradient(rgba(13,110,253,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(13,110,253,0.04) 1px, transparent 1px);
    background-size: 60px 60px;
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B35 0%, #091527 100%) !important;
    border-right: 1px solid var(--border-glass) !important;
}

[data-testid="stSidebar"] > div {
    background: transparent !important;
}

/* ── All Text ─────────────────────────────────────────────── */
.stApp, .stApp p, .stApp div, .stApp span,
.stApp label, .stApp .stMarkdown {
    color: var(--text-primary) !important;
    font-family: 'Nunito', sans-serif !important;
}

/* ── Metric Cards ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1.2rem 1rem !important;
    backdrop-filter: var(--blur) !important;
    box-shadow: var(--shadow-card) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}

[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--shadow-card), var(--shadow-glow) !important;
}

[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 1.8rem !important;
    font-weight: 800 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent-blue), #1a7fff) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-pill) !important;
    padding: 0.6rem 1.8rem !important;
    font-weight: 700 !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.25s !important;
    box-shadow: 0 4px 15px rgba(13,110,253,0.35) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(13,110,253,0.5) !important;
    background: linear-gradient(135deg, #1a7fff, var(--accent-blue)) !important;
}

/* Primary/Analyze button — Red Capsule */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent-red), #ff5a50) !important;
    box-shadow: 0 4px 20px rgba(241,58,48,0.4),
                0 0 40px rgba(241,58,48,0.15) !important;
    font-size: 1rem !important;
    padding: 0.75rem 2.5rem !important;
    letter-spacing: 0.04em !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #ff5a50, var(--accent-red)) !important;
    box-shadow: 0 8px 30px rgba(241,58,48,0.6),
                0 0 60px rgba(241,58,48,0.2) !important;
    transform: translateY(-3px) !important;
}

/* Secondary/Ghost button */
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1.5px solid var(--accent-blue) !important;
    color: var(--accent-blue) !important;
    box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover {
    background: rgba(13,110,253,0.1) !important;
    box-shadow: 0 0 20px rgba(13,110,253,0.2) !important;
}

/* Sign Out button */
button[data-testid="signout_btn"] {
    background: rgba(255,255,255,0.08) !important;
    color: var(--text-secondary) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    box-shadow: none !important;
}

/* ── Input Fields ─────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > div {
    background: var(--bg-input) !important;
    border: 1.5px solid var(--border-glass) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-family: 'Nunito', sans-serif !important;
    padding: 0.6rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 3px rgba(13,110,253,0.15) !important;
    outline: none !important;
}

.stTextInput > div > div > input::placeholder {
    color: var(--text-muted) !important;
}

/* ── Sliders ──────────────────────────────────────────────── */
.stSlider > div > div > div {
    background: var(--accent-blue) !important;
}

.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
    background: var(--accent-blue) !important;
    color: white !important;
    border-radius: 6px !important;
}

/* ── Expanders ────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: rgba(16,28,52,0.9) !important;
    border: 1px solid rgba(99,130,255,0.15) !important;
    border-radius: 10px !important;
    color: #F0F4FF !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.8rem 1rem !important;
    transition: all 0.2s !important;
    display: flex !important;
    align-items: center !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

.streamlit-expanderHeader p {
    color: #F0F4FF !important;
    font-size: 0.88rem !important;
    margin: 0 !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

/* Fix address input pink border */
.stTextInput > div > div > input {
    border-color: rgba(99,130,255,0.2) !important;
    caret-color: #0D6EFD !important;
}

.stTextInput > div > div > input:focus {
    border-color: #0D6EFD !important;
    box-shadow: 0 0 0 2px rgba(13,110,253,0.15) !important;
}

.streamlit-expanderHeader:hover {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 15px rgba(13,110,253,0.15) !important;
}

.streamlit-expanderContent {
    background: rgba(13, 22, 45, 0.6) !important;
    border: 1px solid var(--border-glass) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
    padding: 1rem !important;
}

/* ── Dividers ─────────────────────────────────────────────── */
hr {
    border-color: var(--border-glass) !important;
    opacity: 0.5 !important;
}

/* ── Success / Info / Warning / Error ─────────────────────── */
.stSuccess {
    background: rgba(16,185,129,0.1) !important;
    border: 1px solid rgba(16,185,129,0.3) !important;
    border-radius: 10px !important;
    color: #6EE7B7 !important;
}

.stInfo {
    background: rgba(13,110,253,0.1) !important;
    border: 1px solid rgba(13,110,253,0.3) !important;
    border-radius: 10px !important;
    color: #93C5FD !important;
}

.stWarning {
    background: rgba(245,158,11,0.1) !important;
    border: 1px solid rgba(245,158,11,0.3) !important;
    border-radius: 10px !important;
    color: #FCD34D !important;
}

.stError {
    background: rgba(241,58,48,0.1) !important;
    border: 1px solid rgba(241,58,48,0.3) !important;
    border-radius: 10px !important;
    color: #FCA5A5 !important;
}

/* ── Spinner ──────────────────────────────────────────────── */
.stSpinner > div {
    border-top-color: var(--accent-blue) !important;
}

/* ── DataFrames ───────────────────────────────────────────── */
.stDataFrame {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
    border-radius: var(--radius-pill) !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--border-glass) !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-pill) !important;
    color: var(--text-secondary) !important;
    font-weight: 600 !important;
    padding: 0.4rem 1.2rem !important;
    transition: all 0.2s !important;
}

.stTabs [aria-selected="true"] {
    background: var(--accent-blue) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(13,110,253,0.4) !important;
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb {
    background: rgba(13,110,253,0.4);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--accent-blue);
}
</style>
"""

# ── PropCompassAI Hero Banner ──────────────────────────────────────────
def render_hero_banner(current_page: str) -> None:
    """Render the top hero banner with navigation buttons."""
    import streamlit as st

    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #0D1B35 0%, #0A1628 60%, #0B1120 100%);
        border: 1px solid rgba(99,130,255,0.15);
        border-radius: 20px;
        padding: 2rem 2.5rem 0;
        margin-bottom: 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    '>
        <!-- Compass wireframe background -->
        <div style='
            position: absolute;
            right: -60px; top: -60px;
            width: 340px; height: 340px;
            border-radius: 50%;
            border: 1.5px solid rgba(13,110,253,0.08);
            pointer-events: none;
        '></div>
        <div style='
            position: absolute;
            right: -20px; top: -20px;
            width: 260px; height: 260px;
            border-radius: 50%;
            border: 1.5px solid rgba(13,110,253,0.12);
            pointer-events: none;
        '></div>
        <div style='
            position: absolute;
            right: 20px; top: 20px;
            width: 180px; height: 180px;
            border-radius: 50%;
            border: 1.5px solid rgba(13,110,253,0.16);
            pointer-events: none;
        '></div>
        <!-- Glow orb -->
        <div style='
            position: absolute;
            right: 80px; top: 30px;
            width: 80px; height: 80px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(13,110,253,0.3), transparent);
            pointer-events: none;
        '></div>

        <!-- Content -->
        <div style='position: relative; z-index: 1;'>
            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 6px;'>
                <div style='
                    background: linear-gradient(135deg, #0D6EFD, #3B82F6);
                    width: 36px; height: 36px;
                    border-radius: 10px;
                    display: flex; align-items: center;
                    justify-content: center;
                    font-size: 18px;
                    box-shadow: 0 4px 15px rgba(13,110,253,0.4);
                '>🧭</div>
                <span style='
                    font-family: Space Grotesk, sans-serif;
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: #F0F4FF;
                    letter-spacing: -0.02em;
                '>PropCompassAI</span>
                <span style='
                    background: rgba(13,110,253,0.2);
                    border: 1px solid rgba(13,110,253,0.4);
                    color: #60A5FA;
                    font-size: 0.65rem;
                    font-weight: 700;
                    padding: 2px 8px;
                    border-radius: 100px;
                    letter-spacing: 0.1em;
                '>BETA</span>
            </div>
            <p style='
                color: #64748B;
                font-size: 0.85rem;
                margin: 0 0 1.5rem 0;
                font-weight: 500;
            '>AI-powered real estate intelligence · Analyze deals in seconds</p>
        </div>
    </div>

    <!-- Navigation buttons straddling the banner bottom -->
    <div style='
        display: flex;
        gap: 8px;
        margin: -1px 0 1.5rem 0;
        padding: 0 2.5rem;
        background: linear-gradient(180deg,
            rgba(10,22,40,0.8) 0%,
            transparent 100%);
        padding-top: 12px;
        padding-bottom: 16px;
    '>
        <a href='?page=deal' style='text-decoration:none'>
            <div style='
                background: {"linear-gradient(135deg, #0D6EFD, #1a7fff)" if current_page == "Deal Analyzer" else "rgba(255,255,255,0.05)"};
                border: 1.5px solid {"transparent" if current_page == "Deal Analyzer" else "rgba(99,130,255,0.2)"};
                color: {"white" if current_page == "Deal Analyzer" else "#94A3B8"};
                padding: 8px 20px;
                border-radius: 100px;
                font-size: 0.85rem;
                font-weight: 700;
                cursor: pointer;
                box-shadow: {"0 4px 15px rgba(13,110,253,0.35)" if current_page == "Deal Analyzer" else "none"};
                transition: all 0.2s;
                font-family: Nunito, sans-serif;
            '>🔍 Deal Analyzer</div>
        </a>
        <a href='?page=inspection' style='text-decoration:none'>
            <div style='
                background: {"linear-gradient(135deg, #0D6EFD, #1a7fff)" if current_page == "Inspection AI" else "rgba(255,255,255,0.05)"};
                border: 1.5px solid {"transparent" if current_page == "Inspection AI" else "rgba(99,130,255,0.2)"};
                color: {"white" if current_page == "Inspection AI" else "#94A3B8"};
                padding: 8px 20px;
                border-radius: 100px;
                font-size: 0.85rem;
                font-weight: 700;
                cursor: pointer;
                box-shadow: {"0 4px 15px rgba(13,110,253,0.35)" if current_page == "Inspection AI" else "none"};
                font-family: Nunito, sans-serif;
            '>📋 Inspection AI</div>
        </a>
    </div>
    """, unsafe_allow_html=True)


# ── Glass Panel Container ──────────────────────────────────────────────
def glass_panel_start() -> str:
    return """
    <div style='
        background: rgba(13, 22, 45, 0.75);
        border: 1px solid rgba(99,130,255,0.15);
        border-radius: 20px;
        padding: 1.5rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4),
                    inset 0 1px 0 rgba(255,255,255,0.05);
        margin-bottom: 1.5rem;
    '>
    """

def glass_panel_end() -> str:
    return "</div>"


# ── Metric Glass Card ──────────────────────────────────────────────────
def metric_glass(label: str, value: str, color: str = "#0D6EFD",
                  icon: str = "") -> str:
    return f"""
    <div style='
        background: rgba(13,22,45,0.8);
        border: 1px solid rgba(99,130,255,0.15);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        transition: transform 0.2s;
        position: relative;
        overflow: hidden;
    '>
        <div style='
            position: absolute; top: 0; left: 0;
            right: 0; height: 3px;
            background: {color};
            border-radius: 16px 16px 0 0;
        '></div>
        <div style='
            font-size: 2rem;
            font-weight: 800;
            color: {color};
            font-family: Space Grotesk, sans-serif;
            line-height: 1;
            margin: 0.3rem 0;
        '>{icon}{value}</div>
        <div style='
            font-size: 0.7rem;
            color: #64748B;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 4px;
        '>{label}</div>
    </div>
    """


# ── Section Header ─────────────────────────────────────────────────────
def section_header(title: str, subtitle: str = "") -> str:
    return f"""
    <div style='margin: 1.5rem 0 1rem;'>
        <div style='
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 4px;
        '>
            <div style='
                width: 3px; height: 20px;
                background: linear-gradient(180deg, #0D6EFD, #3B82F6);
                border-radius: 2px;
            '></div>
            <h3 style='
                font-family: Space Grotesk, sans-serif;
                font-size: 1.1rem;
                font-weight: 700;
                color: #F0F4FF;
                margin: 0;
                letter-spacing: -0.01em;
            '>{title}</h3>
        </div>
        {f'<p style="color:#64748B;font-size:0.82rem;margin:0 0 0 13px;">{subtitle}</p>' if subtitle else ''}
    </div>
    """


# ── Issue Card ─────────────────────────────────────────────────────────
def issue_card_header(category: str, system: str, desc: str,
                       cost_min: int, cost_max: int,
                       vendor_icon: str = "🔨") -> str:
    colors = {
        "Critical":  ("#F13A30", "rgba(241,58,48,0.1)",  "rgba(241,58,48,0.3)"),
        "Important": ("#F59E0B", "rgba(245,158,11,0.1)", "rgba(245,158,11,0.3)"),
        "Minor":     ("#10B981", "rgba(16,185,129,0.1)", "rgba(16,185,129,0.3)"),
    }
    clr, bg, border = colors.get(category, ("#0D6EFD", "rgba(13,110,253,0.1)", "rgba(13,110,253,0.3)"))

    return f"""
    <div style='
        background: {bg};
        border: 1px solid {border};
        border-left: 4px solid {clr};
        border-radius: 10px;
        padding: 10px 14px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    '>
        <div>
            <span style='
                background: {clr};
                color: white;
                font-size: 0.65rem;
                font-weight: 800;
                padding: 2px 8px;
                border-radius: 100px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin-right: 8px;
            '>{category}</span>
            <span style='color:#94A3B8;font-size:0.8rem;font-weight:600;'>
                {vendor_icon} {system}
            </span>
            <div style='color:#F0F4FF;font-size:0.88rem;margin-top:4px;font-weight:500;'>
                {desc[:80]}{'...' if len(desc)>80 else ''}
            </div>
        </div>
        <div style='
            text-align: right;
            min-width: 100px;
        '>
            <div style='
                font-family: Space Grotesk, sans-serif;
                font-size: 1rem;
                font-weight: 700;
                color: {clr};
            '>${cost_min:,}–${cost_max:,}</div>
            <div style='color:#64748B;font-size:0.7rem;'>est. repair</div>
        </div>
    </div>
    """


# ── User Profile Card ──────────────────────────────────────────────────
def user_profile_card(name: str, email: str, tier: str,
                        used: int, limit: int) -> str:
    pct = min(100, int(used / max(limit, 1) * 100))
    tier_color = "#F5C842" if tier == "pro" else "#0D6EFD"
    return f"""
    <div style='
        background: rgba(16,28,52,0.9);
        border: 1px solid rgba(99,130,255,0.15);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    '>
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
            <div style='
                width: 36px; height: 36px;
                border-radius: 50%;
                background: linear-gradient(135deg, #0D6EFD, #3B82F6);
                display: flex; align-items: center;
                justify-content: center;
                font-size: 14px; font-weight: 700;
                color: white;
                flex-shrink: 0;
            '>{name[0].upper() if name else 'U'}</div>
            <div>
                <div style='
                    color: #F0F4FF;
                    font-weight: 700;
                    font-size: 0.88rem;
                    line-height: 1.2;
                '>{name}</div>
                <div style='color:#64748B;font-size:0.72rem;'>{email}</div>
            </div>
            <div style='
                margin-left: auto;
                background: rgba({("245,200,66" if tier=="pro" else "13,110,253")},0.15);
                border: 1px solid rgba({("245,200,66" if tier=="pro" else "13,110,253")},0.4);
                color: {tier_color};
                font-size: 0.65rem;
                font-weight: 800;
                padding: 2px 8px;
                border-radius: 100px;
                text-transform: uppercase;
            '>{tier}</div>
        </div>
        <div style='margin-bottom:6px;'>
            <div style='
                display: flex;
                justify-content: space-between;
                color: #64748B;
                font-size: 0.72rem;
                margin-bottom: 4px;
            '>
                <span>Analyses used</span>
                <span>{used}/{limit}</span>
            </div>
            <div style='
                background: rgba(255,255,255,0.06);
                border-radius: 100px;
                height: 4px;
                overflow: hidden;
            '>
                <div style='
                    width: {pct}%;
                    height: 100%;
                    background: {"#F5C842" if pct > 80 else "#0D6EFD"};
                    border-radius: 100px;
                    transition: width 0.5s;
                '></div>
            </div>
        </div>
    </div>
    """


# ── Rate Display ───────────────────────────────────────────────────────
def rate_display(rate_30: float, rate_15: float, as_of: str) -> str:
    return f"""
    <div style='
        background: rgba(16,28,52,0.9);
        border: 1px solid rgba(99,130,255,0.15);
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
    '>
        <div style='
            color: #64748B;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 12px;
        '>📊 Current Market Rates</div>

        <div style='margin-bottom: 12px;'>
            <div style='
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 4px;
            '>
                <div style='
                    width: 3px; height: 28px;
                    background: linear-gradient(180deg, #0D6EFD, #3B82F6);
                    border-radius: 2px;
                    flex-shrink: 0;
                '></div>
                <div>
                    <div style='
                        font-family: Space Grotesk, sans-serif;
                        font-size: 1.8rem;
                        font-weight: 800;
                        color: #0D6EFD;
                        line-height: 1;
                    '>{rate_30:.2f}%</div>
                    <div style='color:#64748B;font-size:0.72rem;'>30-Year Fixed</div>
                </div>
            </div>
        </div>

        <div style='margin-bottom: 8px;'>
            <div style='
                display: flex;
                align-items: center;
                gap: 8px;
            '>
                <div style='
                    width: 3px; height: 24px;
                    background: linear-gradient(180deg, #10B981, #34D399);
                    border-radius: 2px;
                    flex-shrink: 0;
                '></div>
                <div>
                    <div style='
                        font-family: Space Grotesk, sans-serif;
                        font-size: 1.5rem;
                        font-weight: 800;
                        color: #10B981;
                        line-height: 1;
                    '>{rate_15:.2f}%</div>
                    <div style='color:#64748B;font-size:0.72rem;'>15-Year Fixed</div>
                </div>
            </div>
        </div>

        <div style='color:#4A5568;font-size:0.7rem;'>As of: {as_of}</div>
    </div>
    """


# ── Cost Context Banner ────────────────────────────────────────────────
def cost_context_banner(total_min: int, total_max: int,
                          purchase_price: float) -> str:
    pct = (total_max / purchase_price * 100) if purchase_price > 0 else 0
    if pct > 3:
        color, bg, icon = "#F13A30", "rgba(241,58,48,0.1)", "⚠️"
        msg = "Significant repairs — negotiate price reduction!"
    elif pct > 1:
        color, bg, icon = "#F59E0B", "rgba(245,158,11,0.1)", "📋"
        msg = "Moderate repairs — consider requesting credits."
    else:
        color, bg, icon = "#10B981", "rgba(16,185,129,0.1)", "✅"
        msg = "Minor repairs relative to purchase price."

    return f"""
    <div style='
        background: {bg};
        border: 1px solid {color}44;
        border-left: 4px solid {color};
        border-radius: 12px;
        padding: 12px 16px;
        margin: 1rem 0;
        display: flex;
        align-items: center;
        gap: 12px;
    '>
        <span style='font-size:1.3rem;'>{icon}</span>
        <div>
            <div style='
                font-weight: 700;
                color: {color};
                font-size: 0.88rem;
            '>Repair Cost: ${total_min:,}–${total_max:,}
            ({pct:.1f}% of purchase price)</div>
            <div style='color:#94A3B8;font-size:0.8rem;margin-top:2px;'>
                {msg}
            </div>
        </div>
    </div>
    """


# ── Vendor CTA ────────────────────────────────────────────────────────
def vendor_cta_card(vendor_cat: str, vendor_icon: str,
                     form_link: str = "#") -> str:
    return f"""
    <div style='
        background: rgba(16,185,129,0.06);
        border: 1px solid rgba(16,185,129,0.2);
        border-radius: 12px;
        padding: 12px 14px;
        margin-top: 10px;
    '>
        <div style='
            font-size: 0.82rem;
            font-weight: 700;
            color: #34D399;
            margin-bottom: 6px;
        '>{vendor_icon} Need a {vendor_cat}?</div>
        <div style='
            font-size: 0.75rem;
            color: #64748B;
            margin-bottom: 8px;
            line-height: 1.5;
        '>
            Building our NC vendor network!
            Be the first verified {vendor_cat} in your area.<br>
            <strong style='color:#94A3B8;'>$49/month · 3 months FREE for founding members</strong>
        </div>
        <a href='{form_link}' target='_blank' style='
            display: inline-block;
            background: linear-gradient(135deg, #059669, #10B981);
            color: white;
            padding: 5px 14px;
            border-radius: 100px;
            text-decoration: none;
            font-size: 0.75rem;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(16,185,129,0.3);
        '>🚀 Join Vendor Network →</a>
    </div>
    """


# ── Floating Chat Button ───────────────────────────────────────────────
FLOATING_CHAT_CSS = """
<style>
.floating-chat {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
}

.chat-bubble {
    background: rgba(13,22,45,0.95);
    border: 1px solid rgba(99,130,255,0.25);
    border-radius: 12px 12px 0 12px;
    padding: 8px 14px;
    color: #94A3B8;
    font-size: 0.78rem;
    font-weight: 500;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    white-space: nowrap;
}

.chat-btn {
    width: 48px; height: 48px;
    background: linear-gradient(135deg, #0D6EFD, #3B82F6);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(13,110,253,0.5),
                0 0 0 4px rgba(13,110,253,0.15);
    transition: transform 0.2s;
    animation: pulse 3s infinite;
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 4px 20px rgba(13,110,253,0.5), 0 0 0 4px rgba(13,110,253,0.15); }
    50% { box-shadow: 0 4px 20px rgba(13,110,253,0.7), 0 0 0 8px rgba(13,110,253,0.1); }
}

.chat-btn:hover { transform: scale(1.1); }
</style>

<div class='floating-chat'>
    <div class='chat-bubble'>💬 How can we help? Chat now</div>
    <div class='chat-btn'>🧭</div>
</div>
/* Fix top white header bar */
header[data-testid="stHeader"] {
    background: #0B1120 !important;
    border-bottom: 1px solid rgba(99,130,255,0.1) !important;
}

/* Fix sidebar profile card blank */
[data-testid="stSidebar"] .element-container {
    background: transparent !important;
}

[data-testid="stSidebar"] .stMarkdown div {
    background: transparent !important;
    color: #F0F4FF !important;
}
"""
