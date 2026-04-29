"""
PropCompassAI — Clean Dark Theme
Minimal CSS — dark background + cards + buttons only
"""

DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Space+Grotesk:wght@500;600;700&display=swap');

/* ── Background ───────────────────────────────────────────── */
.stApp {
    background: linear-gradient(135deg, #0B1120 0%, #0D1B35 50%, #0A1628 100%) !important;
    font-family: Nunito, sans-serif !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1B35 0%, #091527 100%) !important;
    border-right: 1px solid rgba(99,130,255,0.15) !important;
}

/* ── Header ───────────────────────────────────────────────── */
header[data-testid="stHeader"] {
    background: #0B1120 !important;
    border-bottom: 1px solid rgba(99,130,255,0.1) !important;
}

/* ── Metric Cards ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(16,28,52,0.9) !important;
    border: 1px solid rgba(99,130,255,0.15) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

[data-testid="stMetricValue"] {
    font-family: Space Grotesk, sans-serif !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
}

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    border-radius: 100px !important;
    font-weight: 700 !important;
    transition: all 0.2s !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #F13A30, #ff5a50) !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(241,58,48,0.4) !important;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(241,58,48,0.6) !important;
}

.stButton > button[kind="secondary"] {
    border-radius: 100px !important;
}

/* ── Expanders ────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(16,28,52,0.8) !important;
    border: 1px solid rgba(99,130,255,0.15) !important;
    border-radius: 10px !important;
}

/* ── Text Brightness ─────────────────────────────────────── */
.stApp p, .stApp div, .stApp span,
.stApp label, .stMarkdown p,
.stMarkdown li, .stMarkdown td {
    color: #CBD5E1 !important;
}

.stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stMarkdown h1,
.stMarkdown h2, .stMarkdown h3 {
    color: #F1F5F9 !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #CBD5E1 !important;
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0B1120; }
::-webkit-scrollbar-thumb {
    background: rgba(13,110,253,0.4);
    border-radius: 3px;
}
</style>
"""

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
    font-size: 0.78rem;
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
    box-shadow: 0 4px 20px rgba(13,110,253,0.5);
}
</style>
<div class="floating-chat">
    <div class="chat-bubble">💬 How can we help? Chat now</div>
    <div class="chat-btn">🧭</div>
</div>
"""
