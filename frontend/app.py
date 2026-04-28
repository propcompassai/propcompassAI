"""
app.py
PropCompassAI — Streamlit Investor Dashboard

Pure Python web UI — no HTML/CSS/JavaScript needed.
Calls the live FastAPI backend on Cloud Run.

Run locally:  streamlit run frontend/app.py
Deploy:       Streamlit Cloud (free)
"""

import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
import os
import re
from fpdf import FPDF
import urllib.parse
from dotenv import load_dotenv
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from firebase_auth import (
    sign_in_with_email,
    create_account,
    save_user_to_bigquery,
    get_user_usage,
    log_analysis,
)
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Page Configuration ────────────────────────────────────────────
st.set_page_config(
    page_title     = "PropCompassAI",
    page_icon      = "🧭",
    layout         = "wide",
    initial_sidebar_state = "expanded",
)

# ── Session State Initialization ──────────────────────────────────
if "user"            not in st.session_state:
    st.session_state.user            = None
if "auth_mode"       not in st.session_state:
    st.session_state.auth_mode       = "login"
if "show_upgrade"    not in st.session_state:
    st.session_state.show_upgrade    = False
if "chat_open"       not in st.session_state:
    st.session_state.chat_open       = False
if "chat_history"    not in st.session_state:
    st.session_state.chat_history    = []
if "last_chat_input" not in st.session_state:
    st.session_state.last_chat_input = ""
if "last_result"     not in st.session_state:
    st.session_state.last_result     = {}
if "validated_address" not in st.session_state:
    st.session_state.validated_address = ""
if "selected_address_display" not in st.session_state:
    st.session_state.selected_address_display = ""
if "address_validated" not in st.session_state:
    st.session_state.address_validated = False
if "validated_zip"   not in st.session_state:
    st.session_state.validated_zip   = ""
if "selected_state"  not in st.session_state:
    st.session_state.selected_state  = "NC"
if "estimated_tax"   not in st.session_state:
    st.session_state.estimated_tax   = 0

# ── API Configuration ─────────────────────────────────────────────

# ── API Configuration ─────────────────────────────────────────────
API_URL = os.getenv(
    "API_URL",
    "https://prop-compass-api-1093947106211.us-central1.run.app"
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #1B3A6B 0%, #2563EB 100%);
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        color: white;
    }
    .main-header h1 {
        color: white !important;
        font-size: 2.2rem !important;
        margin: 0 !important;
    }
    .main-header p {
        color: #BFDBFE !important;
        margin: 4px 0 0 0 !important;
        font-size: 1rem !important;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 8px 0 4px;
    }
    .metric-label {
        color: #6B7280;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Recommendation badge */
    .badge-buy   { background:#DCFCE7; color:#166534; padding:8px 20px; border-radius:20px; font-weight:bold; font-size:1.1rem; }
    .badge-watch { background:#FEF3C7; color:#92400E; padding:8px 20px; border-radius:20px; font-weight:bold; font-size:1.1rem; }
    .badge-pass  { background:#FEE2E2; color:#991B1B; padding:8px 20px; border-radius:20px; font-weight:bold; font-size:1.1rem; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: bold;
        color: #1B3A6B;
        border-bottom: 2px solid #DBEAFE;
        padding-bottom: 8px;
        margin: 20px 0 16px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Approximate geographic centers for location-biased autocomplete
_STATE_CENTERS = {
    "AL": "32.8067,-86.7911", "AK": "64.2008,-153.4937", "AZ": "34.0489,-111.0937",
    "AR": "34.9697,-92.3731", "CA": "36.7783,-119.4179", "CO": "39.5501,-105.7821",
    "CT": "41.6032,-73.0877", "DE": "38.9108,-75.5277",  "FL": "27.6648,-81.5158",
    "GA": "32.1656,-82.9001", "HI": "19.8968,-155.5828", "ID": "44.0682,-114.7420",
    "IL": "40.6331,-89.3985", "IN": "40.2672,-86.1349",  "IA": "41.8780,-93.0977",
    "KS": "39.0119,-98.4842", "KY": "37.8393,-84.2700",  "LA": "30.9843,-91.9623",
    "ME": "45.2538,-69.4455", "MD": "39.0458,-76.6413",  "MA": "42.4072,-71.3824",
    "MI": "44.3148,-85.6024", "MN": "46.7296,-94.6859",  "MS": "32.3547,-89.3985",
    "MO": "37.9643,-91.8318", "MT": "46.8797,-110.3626", "NE": "41.4925,-99.9018",
    "NV": "38.8026,-116.4194","NH": "43.1939,-71.5724",  "NJ": "40.0583,-74.4057",
    "NM": "34.5199,-105.8701","NY": "42.1657,-74.9481",  "NC": "35.7596,-79.0193",
    "ND": "47.5515,-101.0020","OH": "40.4173,-82.9071",  "OK": "35.4676,-97.5164",
    "OR": "43.8041,-120.5542","PA": "41.2033,-77.1945",  "RI": "41.6809,-71.5118",
    "SC": "33.8361,-81.1637", "SD": "43.9695,-99.9018",  "TN": "35.5175,-86.5804",
    "TX": "31.9686,-99.9018", "UT": "39.3210,-111.0937", "VT": "44.5588,-72.5778",
    "VA": "37.4316,-78.6569", "WA": "47.7511,-120.7401", "WV": "38.5976,-80.4549",
    "WI": "43.7844,-88.7879", "WY": "43.0760,-107.2903",
}


def validate_and_autocomplete_address(
    partial_address: str,
    api_key: str,
    state: str = "NC"
) -> dict:
    """
    Two functions in one:
    1. Autocomplete — suggests addresses as user types
    2. Validation — confirms address exists and returns
       standardized format + lat/lng + zip code

    Uses Google Places API:
    - Autocomplete endpoint for suggestions
    - Place Details endpoint for full validation
    """
    if not partial_address or len(partial_address) < 3:
        return {"suggestions": [], "validated": None}

    # ── Autocomplete ──────────────────────────────────────────
    autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input":        partial_address,
        "types":        "address",
        "components":   "country:us",
        "key":          api_key,
        "location":     _STATE_CENTERS.get(state, "39.5,-98.35"),  # state center or US center
        "radius":       "300000",   # 300km — covers most states
        "strictbounds": "false",    # bias, not restrict
    }

    try:
        response = requests.get(autocomplete_url, params=params, timeout=5)
        data = response.json()

        suggestions = []
        place_ids   = []

        if data.get("status") == "OK":
            for prediction in data.get("predictions", []):
                desc = prediction["description"]
                # Robust state filter: match ", TX " or ", TX," or ", TX\n"
                if state and not re.search(rf',\s*{re.escape(state)}[\s,]', desc):
                    continue
                suggestions.append(desc)
                place_ids.append(prediction["place_id"])
                if len(suggestions) >= 5:
                    break
        return {
            "suggestions": suggestions,
            "place_ids":   place_ids,
            "status":      data.get("status"),
        }
    except Exception as e:
        return {"suggestions": [], "error": str(e)}


def get_place_details(place_id: str, api_key: str) -> dict:
    """
    Given a Google Place ID, returns full validated address details:
    - Formatted address
    - Street number, city, state, zip
    - Latitude and longitude
    """
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields":   "formatted_address,address_components,geometry",
        "key":      api_key,
    }

    try:
        response = requests.get(details_url, params=params, timeout=5)
        data = response.json()

        if data.get("status") != "OK":
            return {}

        result = data["result"]

        # Parse address components
        components = {}
        for comp in result.get("address_components", []):
            types = comp["types"]
            if "street_number"               in types:
                components["street_number"] = comp["long_name"]
            elif "route"                     in types:
                components["street"]        = comp["long_name"]
            elif "locality"                  in types:
                components["city"]          = comp["long_name"]
            elif "administrative_area_level_1" in types:
                components["state"]         = comp["short_name"]
            elif "postal_code"               in types:
                components["zip_code"]      = comp["long_name"]

        # Build clean address
        street = f"{components.get('street_number', '')} {components.get('street', '')}".strip()

        return {
            "formatted_address": result.get("formatted_address", ""),
            "street":            street,
            "city":              components.get("city", ""),
            "state":             components.get("state", ""),
            "zip_code":          components.get("zip_code", ""),
            "latitude":          result["geometry"]["location"]["lat"],
            "longitude":         result["geometry"]["location"]["lng"],
            "validated":         True,
        }
    except Exception as e:
        return {"error": str(e), "validated": False}

# ── Helper Functions ──────────────────────────────────────────────
def call_analyze_api(
    address:          str,
    purchase_price:   float,
    monthly_rent:     float,
    down_payment_pct: float,
    zip_code:         str,
    tax_annual:       float,
    include_mgmt:     bool,
    mgmt_rate:        float = 8.0,
    vacancy_rate:     float = 8.33,
    maintenance_rate: float = 1.0,
    insurance_rate:   float = 0.5,
    hoa_monthly:      float = 0.0,
    tax_rate:         float = 1.2,
) -> dict:
    """Call the PropCompassAI API and return results."""
    payload = {
        "address":          address,
        "purchase_price":   purchase_price,
        "monthly_rent":     monthly_rent,
        "down_payment_pct": down_payment_pct,
        "zip_code":         zip_code,
        "tax_annual":       tax_annual if tax_annual > 0 else None,
        "tax_rate":         tax_rate,
        "include_mgmt":     include_mgmt,
        "mgmt_rate":        mgmt_rate,
        "vacancy_rate":     vacancy_rate,
        "maintenance_rate": maintenance_rate,
        "insurance_rate":   insurance_rate,
        "hoa_monthly":      hoa_monthly,
    }
    response = requests.post(
        f"{API_URL}/analyze",
        json    = payload,
        timeout = 120,
    )
    response.raise_for_status()
    return response.json()


def get_current_rates() -> dict:
    """Get current mortgage rates from API."""
    try:
        response = requests.get(f"{API_URL}/rates", timeout=10)
        return response.json()
    except:
        return {"current_30yr": 7.0, "current_15yr": 6.0}


def recommendation_badge(rec: str) -> str:
    """Return colored HTML badge for recommendation."""
    badges = {
        "BUY":   ("🟢", "badge-buy",   "BUY"),
        "WATCH": ("🟡", "badge-watch", "WATCH"),
        "AVOID":  ("🔴", "badge-pass",  "AVOID"),
    }
    emoji, css, label = badges.get(rec, ("⚪", "badge-watch", rec))
    return f'<span class="{css}">{emoji} {label}</span>'

def show_login_page():
    """Show login / register page."""
    st.markdown("""
    <div style='text-align:center; padding:40px 0 20px'>
        <div style='font-size:2.5rem; font-weight:bold; color:#1B3A6B;
        font-family:Georgia;'>🧭 PropCompassAI</div>
        <div style='font-size:1rem; color:#6B7280; margin-top:8px;'>
        Your compass for every real estate decision
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Toggle login/register
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            st.markdown("#### Welcome back!")
            with st.form("login_form"):
                email    = st.text_input("Email",
                                         placeholder="your@email.com")
                password = st.text_input("Password",
                                         type="password",
                                         placeholder="Your password")
                submitted = st.form_submit_button(
                    "Sign In",
                    use_container_width=True
                )

            if submitted:
                if email and password:
                    with st.spinner("Signing in..."):
                        result = sign_in_with_email(email, password)
                    if result["success"]:
                        st.session_state.user = result
                        save_user_to_bigquery(
                            user_id      = result["user_id"],
                            email        = result["email"],
                            display_name = result.get("display_name", ""),
                            provider     = "email",
                        )
                        st.success(f"Welcome back {result['display_name']}!")
                        st.rerun()
                    else:
                        st.error(result["error"])
                else:
                    st.warning("Please enter email and password")

            st.markdown("---")
            st.markdown("""
            <div style='text-align:center; font-size:12px; color:#9CA3AF;'>
            Don't have an account? Click 'Create Account' tab above
            </div>""", unsafe_allow_html=True)

        with tab_register:
            st.markdown("#### Create your free account!")
            st.markdown("""
            <div style='background:#F0FDF4; border-radius:8px;
            padding:10px 14px; font-size:13px; color:#166534;
            margin-bottom:16px;'>
            ✅ Free plan: 3 analyses/month<br>
            ✅ PDF reports included<br>
            ✅ AI explanations included<br>
            ✅ No credit card required
            </div>""", unsafe_allow_html=True)

            with st.form("register_form"):
                name     = st.text_input("Full Name",
                                         placeholder="Your name")
                email_r  = st.text_input("Email",
                                         placeholder="your@email.com")
                pass_r   = st.text_input("Password",
                                         type="password",
                                         placeholder="Min 6 characters")
                pass_r2  = st.text_input("Confirm Password",
                                         type="password",
                                         placeholder="Repeat password")
                reg_submitted = st.form_submit_button(
                    "Create Free Account",
                    use_container_width=True
                )

            if reg_submitted:
                if not all([name, email_r, pass_r, pass_r2]):
                    st.warning("Please fill in all fields")
                elif pass_r != pass_r2:
                    st.error("Passwords do not match")
                elif len(pass_r) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    with st.spinner("Creating account..."):
                        result = create_account(email_r, pass_r, name)
                    if result["success"]:
                        st.session_state.user = result
                        st.success(f"Welcome to PropCompassAI, {name}!")
                        st.rerun()
                    else:
                        st.error(result["error"])
def show_usage_banner(user: dict):
    """Show usage limit banner for free users."""
    if "cached_usage" not in st.session_state:
        st.session_state.cached_usage = get_user_usage(user["user_id"])
    usage = st.session_state.cached_usage
    tier  = usage.get("tier", "free")

    if tier == "free":
        used      = usage.get("used", 0)
        remaining = usage.get("remaining", 3)
        color     = "#FEF3C7" if remaining > 0 else "#FEE2E2"
        text_col  = "#92400E" if remaining > 0 else "#991B1B"
        msg = (f"Free plan: {used}/3 analyses used this month — "
               f"{remaining} remaining") if remaining > 0 else \
              "Monthly limit reached — upgrade to Pro for unlimited analyses"

        st.markdown(f"""
        <div style='background:{color}; border-radius:8px;
        padding:8px 16px; font-size:13px; color:{text_col};
        margin-bottom:12px; display:flex;
        justify-content:space-between; align-items:center;'>
        <span>{msg}</span>
        </div>""", unsafe_allow_html=True)

        if remaining == 0:
            st.warning("Upgrade to Pro ($29/month) for unlimited analyses!")
            if st.button("Upgrade to Pro ↗", key="upgrade_btn"):
                st.info("Stripe billing coming soon! Email propcompass.ai@gmail.com to upgrade manually.")
        return usage.get("can_analyze", True)
    return True

def format_currency(value: float) -> str:
    """Format number as currency."""
    if value >= 0:
        return f"${value:,.0f}"
    return f"-${abs(value):,.0f}"

def clean(text) -> str:
    """Remove characters not supported by Helvetica PDF font."""
    if not text:
        return ""
    return str(text)\
        .replace("\u2014", "-")\
        .replace("\u2013", "-")\
        .replace("\u2018", "'")\
        .replace("\u2019", "'")\
        .replace("\u201c", '"')\
        .replace("\u201d", '"')\
        .replace("\u2026", "...")\
        .replace("\u2022", "-")\
        .replace("\u00e2", "")\
        .replace("\u20ac", "EUR")


def format_pct(value: float) -> str:
    """Format number as percentage."""
    return f"{value:.2f}%"


# ── Charts ────────────────────────────────────────────────────────
def build_cashflow_chart(result: dict) -> go.Figure:
    """Build 5-year cash flow projection chart."""
    years      = [f"Year {y['year']}" for y in result["five_year"]]
    values     = [y["property_value"]   for y in result["five_year"]]
    cashflows  = [y["annual_cashflow"]  for y in result["five_year"]]
    apprecn    = [y["total_appreciation"] for y in result["five_year"]]

    fig = go.Figure()

    # Property value line
    fig.add_trace(go.Scatter(
        x          = years,
        y          = values,
        name       = "Property Value",
        line       = dict(color="#2563EB", width=3),
        yaxis      = "y1",
    ))

    # Cash flow bars
    colors = ["#16A34A" if c >= 0 else "#DC2626" for c in cashflows]
    fig.add_trace(go.Bar(
        x      = years,
        y      = cashflows,
        name   = "Annual Cash Flow",
        marker = dict(color=colors),
        yaxis  = "y2",
    ))

    fig.update_layout(
        title      = "5-Year Property Value & Cash Flow Projection",
        yaxis      = dict(title="Property Value ($)", tickformat="$,.0f"),
        yaxis2     = dict(
            title    = "Annual Cash Flow ($)",
            overlaying = "y",
            side     = "right",
            tickformat = "$,.0f",
        ),
        legend     = dict(x=0.01, y=0.99),
        height     = 350,
        plot_bgcolor = "white",
        paper_bgcolor = "white",
        margin     = dict(t=50, b=40, l=60, r=60),
    )
    return fig


def build_expense_breakdown_chart(result: dict) -> go.Figure:
    """Build expense breakdown donut chart with exact amounts."""
    breakdown = result.get("expense_breakdown", {})
    mortgage  = result.get("monthly_mortgage", 0) or 0
    rent      = result.get("monthly_rent", 0) or 0

    # Build all components
    items = []

    # Mortgage first
    items.append({
        "label": "Mortgage",
        "value": mortgage,
        "color": "#1B3A6B"
    })

    # Operating expenses
    expense_map = [
        ("tax_monthly",         "Property Tax",    "#EF4444"),
        ("insurance_monthly",   "Insurance",       "#F59E0B"),
        ("vacancy_monthly",     "Vacancy",         "#8B5CF6"),
        ("maintenance_monthly", "Maintenance",     "#16A34A"),
        ("mgmt_monthly",        "Property Mgmt",   "#2563EB"),
        ("hoa_monthly",         "HOA",             "#EC4899"),
    ]

    for key, label, color in expense_map:
        val = breakdown.get(key, 0) or 0
        if val > 0:
            items.append({
                "label": label,
                "value": val,
                "color": color
            })

    total = sum(i["value"] for i in items)

    labels = [
        f"{i['label']}<br>${i['value']:,.0f}/mo ({i['value']/total*100:.1f}%)"
        if total > 0 else i['label']
        for i in items
    ]
    values = [i["value"] for i in items]
    colors = [i["color"] for i in items]

    fig = go.Figure(go.Pie(
        labels           = labels,
        values           = values,
        hole             = 0.45,
        marker           = dict(
            colors       = colors,
            line         = dict(color="white", width=2)
        ),
        textinfo         = "percent",
        hovertemplate    = "<b>%{label}</b><extra></extra>",
        textfont         = dict(size=11),
    ))

    fig.update_layout(
        title      = dict(
            text   = f"Monthly Cost Breakdown — ${total:,.0f}/mo total",
            font   = dict(size=13),
            x      = 0.5
        ),
        height     = 340,
        margin     = dict(t=50, b=20, l=20, r=20),
        legend     = dict(
            orientation = "v",
            x           = 1.02,
            y           = 0.5,
            font        = dict(size=10),
        ),
        showlegend = True,
    )

    # Add total in center
    fig.add_annotation(
        text       = f"${total:,.0f}<br>/month",
        x          = 0.5,
        y          = 0.5,
        font       = dict(size=13, color="#1B3A6B"),
        showarrow  = False,
        xref       = "paper",
        yref       = "paper",
        align      = "center",
    )

    return fig

def build_neighborhood_gauge(score: float) -> go.Figure:
    """Build neighborhood score gauge chart."""
    if score >= 70:
        color = "#16A34A"
    elif score >= 45:
        color = "#F59E0B"
    else:
        color = "#EF4444"

    fig = go.Figure(go.Indicator(
        mode  = "gauge+number",
        value = score,
        title = {"text": "Neighborhood Score"},
        gauge = {
            "axis":  {"range": [0, 100]},
            "bar":   {"color": color},
            "steps": [
                {"range": [0, 45],  "color": "#FEE2E2"},
                {"range": [45, 70], "color": "#FEF3C7"},
                {"range": [70, 100],"color": "#DCFCE7"},
            ],
            "threshold": {
                "line":  {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": score,
            }
        }
    ))
    fig.update_layout(
        height = 250,
        margin = dict(t=50, b=20, l=30, r=30),
    )
    return fig


def build_deal_score_gauge(score: float, rec: str) -> go.Figure:
    """Build deal score gauge."""
    colors = {"BUY": "#16A34A", "WATCH": "#F59E0B", "AVOID": "#EF4444"}
    color  = colors.get(rec, "#6B7280")

    fig = go.Figure(go.Indicator(
        mode  = "gauge+number",
        value = score,
        title = {"text": "AI Deal Score"},
        gauge = {
            "axis":  {"range": [0, 100]},
            "bar":   {"color": color},
            "steps": [
                {"range": [0, 45],  "color": "#FEE2E2"},
                {"range": [45, 70], "color": "#FEF3C7"},
                {"range": [70, 100],"color": "#DCFCE7"},
            ],
        }
    ))
    fig.update_layout(
        height = 250,
        margin = dict(t=50, b=20, l=30, r=30),
    )
    return fig


# ── PDF Report Generator ──────────────────────────────────────────
def generate_pdf_report(result: dict) -> bytes:
    """Generate PDF report and return as bytes."""
    from fpdf import FPDF as FPDFClass
    pdf = FPDFClass()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header background
    pdf.set_fill_color(27, 58, 107)
    pdf.rect(0, 0, 210, 35, "F")

    # Title
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(10, 8)
    pdf.cell(190, 10, "PropCompassAI - Deal Analysis Report", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(10, 20)
    pdf.cell(190, 8, f"Generated: {datetime.now().strftime('%B %d, %Y')}", align="C")

    # Reset color
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 42)

    # Property Info Section
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(27, 58, 107)
    pdf.cell(190, 8, "Property Information")
    pdf.ln(9)
    pdf.set_draw_color(37, 99, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)

    info_rows = [
        ("Address",        result.get("address", "")),
        ("Purchase Price", format_currency(result.get("purchase_price", 0))),
        ("Monthly Rent",   format_currency(result.get("monthly_rent", 0))),
        ("Down Payment",   f"{result.get('down_payment_pct', 20)}%"),
        ("Mortgage Rate",  f"{result.get('annual_rate', 7.0)}% (30-year fixed)"),
    ]

    for label, value in info_rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(130, 7, str(value))
        pdf.ln()

    pdf.ln(4)

    # Recommendation Section
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(27, 58, 107)
    pdf.cell(190, 8, "AI Investment Recommendation")
    pdf.ln(9)
    pdf.set_draw_color(37, 99, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    rec = result.get("recommendation", "WATCH")
    score = result.get("deal_score", 0) or 0
    rec_colors = {
        "BUY":   (22, 163, 74),
        "WATCH": (245, 158, 11),
        "AVOID":  (220, 38, 38),
    }
    r, g, b = rec_colors.get(rec, (107, 114, 128))
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(50, 10, f"  {rec}", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(10, 10, "")
    pdf.cell(130, 10, f"AI Score: {score}/100")
    pdf.ln(14)

    # Financial Metrics Section
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(27, 58, 107)
    pdf.cell(190, 8, "Financial Analysis")
    pdf.ln(9)
    pdf.set_draw_color(37, 99, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    metrics = [
        ("Monthly Mortgage",   format_currency(result.get("monthly_mortgage", 0) or 0)),
        ("Monthly Expenses",   format_currency(result.get("monthly_expenses", 0) or 0)),
        ("Monthly Cash Flow",  format_currency(result.get("monthly_cashflow", 0) or 0)),
        ("Annual Cash Flow",   format_currency(result.get("annual_cashflow", 0) or 0)),
        ("Cap Rate",           format_pct(result.get("cap_rate", 0) or 0)),
        ("Cash-on-Cash",       format_pct(result.get("cash_on_cash", 0) or 0)),
        ("Gross Rent Mult",    f"{result.get('grm', 0) or 0}x"),
        ("Neighborhood Score", f"{result.get('neighborhood_score', 0) or 0}/100"),
    ]

    for i, (label, value) in enumerate(metrics):
        if i % 2 == 0:
            pdf.set_fill_color(241, 245, 249)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(95, 7, f"  {label}", fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(95, 7, f"  {value}", fill=True)
        pdf.ln()

    pdf.ln(4)

    # 5-Year Projection
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(27, 58, 107)
    pdf.cell(190, 8, "5-Year Investment Projection")
    pdf.ln(9)
    pdf.set_draw_color(37, 99, 235)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    # Table header
    pdf.set_fill_color(27, 58, 107)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 7, "  Year", fill=True)
    pdf.cell(55, 7, "  Property Value", fill=True)
    pdf.cell(55, 7, "  Annual Cash Flow", fill=True)
    pdf.cell(45, 7, "  Appreciation", fill=True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    five_year = result.get("five_year", [])
    for i, yr in enumerate(five_year):
        if i % 2 == 0:
            pdf.set_fill_color(241, 245, 249)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(35, 7, f"  Year {yr.get('year', i+1)}", fill=True)
        pdf.cell(55, 7, f"  {format_currency(yr.get('property_value', 0) or 0)}", fill=True)
        pdf.cell(55, 7, f"  {format_currency(yr.get('annual_cashflow', 0) or 0)}", fill=True)
        pdf.cell(45, 7, f"  {format_currency(yr.get('total_appreciation', 0) or 0)}", fill=True)
        pdf.ln()
# ── Realtor Analysis Section ──────────────────────────────
    realtor = result.get("realtor_analysis", {})
    if realtor.get("available"):
        pdf.add_page()

        # Header
        pdf.set_fill_color(27, 58, 107)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_xy(10, 10)
        pdf.cell(190, 10, "Realtor Investment Strategy", fill=True)
        pdf.ln(14)

        pdf.set_text_color(0, 0, 0)

        # Summary
        summary = realtor.get("summary", "")
        if summary:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(230, 241, 251)
            pdf.cell(190, 8, "  Summary", fill=True)
            pdf.ln(9)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(190, 6, clean(summary))
            pdf.ln(4)

        # Diagnosis
        diagnosis = realtor.get("diagnosis", {})
        if diagnosis:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(230, 241, 251)
            pdf.cell(190, 8, "  Diagnosis", fill=True)
            pdf.ln(9)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(190, 6, clean(diagnosis.get("message", "")))
            pdf.ln(2)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(190, 6, f"  Rent-to-price ratio: {diagnosis.get('rent_to_price', 0):.2f}% (target: 0.8%+)")
            pdf.ln(6)
            pdf.set_text_color(0, 0, 0)

        # Fair Market Value
        fair = realtor.get("fair_value", {})
        if fair:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(230, 241, 251)
            pdf.cell(190, 8, "  Fair Market Value", fill=True)
            pdf.ln(9)

            fv_rows = [
                ("At 6% Cap Rate", f"${fair.get('value_at_6_cap', 0):,.0f}"),
                ("At 7% Cap Rate", f"${fair.get('value_at_7_cap', 0):,.0f}"),
                ("At 8% Cap Rate", f"${fair.get('value_at_8_cap', 0):,.0f}"),
                ("List Price",     f"${fair.get('list_price', 0):,.0f}"),
                ("Discount Needed",f"${fair.get('discount_needed', 0):,.0f} ({fair.get('discount_pct', 0):.1f}%)"),
            ]
            for i, (label, value) in enumerate(fv_rows):
                bg = (241, 245, 249) if i % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*bg)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(95, 7, f"  {label}", fill=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(95, 7, f"  {value}", fill=True)
                pdf.ln()
            pdf.ln(4)

        # Negotiation Strategy
        neg = realtor.get("negotiation", {})
        if neg:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(230, 241, 251)
            pdf.cell(190, 8, "  Negotiation Strategy", fill=True)
            pdf.ln(9)

            neg_rows = [
                ("Max Price for BUY",    f"${neg.get('max_price_for_buy', 0):,.0f}"),
                ("Max Price for WATCH",  f"${neg.get('max_price_for_watch', 0):,.0f}"),
                ("Suggested Opening Offer", f"${neg.get('suggested_offer', 0):,.0f}"),
                ("Price Reduction Needed",  f"${neg.get('reduction_needed', 0):,.0f} ({neg.get('reduction_pct', 0):.1f}%)"),
            ]
            for i, (label, value) in enumerate(neg_rows):
                bg = (241, 245, 249) if i % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*bg)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(95, 7, f"  {label}", fill=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(95, 7, f"  {value}", fill=True)
                pdf.ln()
            pdf.ln(4)

        # Value-Add Scenarios
        scenarios = realtor.get("scenarios", [])
        if scenarios:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(230, 241, 251)
            pdf.cell(190, 8, "  Value-Add Scenarios", fill=True)
            pdf.ln(9)

            for scenario in scenarios:
                rec = scenario.get("recommendation", "WATCH")
                best = " - RECOMMENDED" if scenario.get("best") else ""

                # Scenario header
                pdf.set_fill_color(27, 58, 107)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(190, 7, f"  {scenario.get('name', '')}{best}", fill=True)
                pdf.ln(8)

                pdf.set_text_color(0, 0, 0)
                sc_rows = [
                    ("Target Price",    f"${scenario.get('target_price', 0):,.0f}"),
                    ("Target Rent",     f"${scenario.get('target_rent', 0):,.0f}/mo"),
                    ("New Cash Flow",   f"${scenario.get('new_cashflow', 0):,.0f}/mo"),
                    ("New Cap Rate",    f"{scenario.get('new_cap_rate', 0):.2f}%"),
                    ("Recommendation",  rec),
                ]
                for i, (label, value) in enumerate(sc_rows):
                    bg = (241, 245, 249) if i % 2 == 0 else (255, 255, 255)
                    pdf.set_fill_color(*bg)
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(95, 6, f"  {label}", fill=True)
                    pdf.set_font("Helvetica", "", 9)
                    pdf.cell(95, 6, f"  {value}", fill=True)
                    pdf.ln()

                # Action
                pdf.set_fill_color(220, 252, 231)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(22, 101, 52)
                pdf.multi_cell(190, 6, clean(f"  Action: {scenario.get('action', '')}"), fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)

    # ── AI Explanation Section ────────────────────────────────
    ai_explanation = result.get("ai_explanation", "")
    if ai_explanation:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(230, 241, 251)
        pdf.cell(190, 8, "  AI Investment Analysis (Gemini 2.5 Flash)", fill=True)
        pdf.ln(9)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_fill_color(239, 246, 255)
        pdf.multi_cell(190, 6, clean(ai_explanation), fill=True)
        pdf.ln(4)

    # Footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.set_y(-25)
    pdf.multi_cell(190, 4,
        "DISCLAIMER: This report is generated by PropCompassAI for informational purposes only. "
        "It does not constitute financial, investment, or legal advice. "
        "Consult a licensed financial advisor, CPA, or real estate attorney before making investment decisions. "
        "PropCompassAI | PropCompass.AI",
        align="C"
    )

    return bytes(pdf.output())


# ══ MAIN UI ════════════════════════════════════════════════════════

# ── Auth Gate ─────────────────────────────────────────────────────
if not st.session_state.user:
    show_login_page()
    st.stop()

# ── User is logged in ─────────────────────────────────────────────
user = st.session_state.user
# ── Header ────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧭 PropCompassAI</h1>
    <p>Your compass for every real estate decision — AI-powered deal analysis</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
     # ── User Profile ──────────────────────────────────────────
    usage = get_user_usage(user["user_id"])
    st.markdown(f"""
    <div style='background:#EFF6FF; border-radius:8px;
    padding:10px 14px; margin-bottom:12px;'>
    <div style='font-size:13px; font-weight:600;
    color:#1B3A6B;'>👤 {user.get('display_name', 'User')}</div>
    <div style='font-size:11px; color:#6B7280;
    margin-top:2px;'>{user.get('email', '')}</div>
    <div style='font-size:11px; color:#6B7280; margin-top:4px;'>
    Plan: <b>{usage.get('tier','free').upper()}</b> |
    {usage.get('used',0)}/{usage.get('limit',3)} analyses
    </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", key="signout_btn", use_container_width=True):
        st.session_state.user         = None
        st.session_state.chat_history = []
        st.session_state.last_result  = {}
        st.rerun()
    st.markdown("---")
    st.markdown("### 📊 Current Market")

    # Show live rates
    with st.spinner("Loading rates..."):
        rates = get_current_rates()

    st.metric(
        "30-Year Rate",
        f"{rates.get('current_30yr', 7.0):.2f}%",
    )
    st.metric(
        "15-Year Rate",
        f"{rates.get('current_15yr', 6.0):.2f}%",
    )
    st.caption(f"As of: {rates.get('as_of', 'N/A')}")

    st.markdown("---")
    st.markdown("### ⚙️ Analysis Settings")

    down_payment = st.slider(
        "Down Payment %",
        min_value = 5,
        max_value = 40,
        value     = 20,
        step      = 5,
    )

    mgmt_rate = st.slider(
        "Property Management (% of rent)",
        min_value = 0,
        max_value = 15,
        value     = 8,
        step      = 1,
        help      = "0% = self managed, 8% = standard, 12-15% = premium/vacation"
    )
    if mgmt_rate == 0:
        st.caption("Self managed — no management fee")
    elif mgmt_rate <= 8:
        st.caption(f"{mgmt_rate}% = standard property manager")
    else:
        st.caption(f"{mgmt_rate}% = premium property manager")
    include_mgmt = mgmt_rate > 0

    st.markdown("---")
    st.markdown("### 🔧 Expense Assumptions")

    vacancy_months = st.slider(
        "Vacancy (months/year)",
        min_value = 0.0,
        max_value = 3.0,
        value     = 1.0,
        step      = 0.5,
        help      = "How many months per year property sits vacant"
    )
    vacancy_rate = round((vacancy_months / 12) * 100, 2)
    st.caption(f"= {vacancy_rate}% vacancy rate")

    maintenance_rate = st.slider(
        "Maintenance (% of price/year)",
        min_value = 0.5,
        max_value = 5.0,
        value     = 1.0,
        step      = 0.5,
        help      = "New homes: 1%, Older homes: 2-3%, Fixer upper: 3-5%"
    )

    insurance_rate = st.slider(
        "Insurance (% of price/year)",
        min_value = 0.5,
        max_value = 1.5,
        value     = 0.5,
        step      = 0.25,
        help      = "Standard: 0.5%, High risk area: 1.0-1.5%"
    )

    
# Calculate estimated tax to show user
    # Get estimated tax from last analysis if available
    estimated_tax_annual = 0
    if "last_result" in st.session_state:
        tax_monthly = st.session_state.last_result.get(
            "expense_breakdown", {}
        ).get("tax_monthly", 0) or 0
        estimated_tax_annual = int(tax_monthly * 12)

    tax_rate = st.slider(
        "Property Tax Rate (% of price/year)",
        min_value = 0.5,
        max_value = 5.0,
        value     = 1.2,
        step      = 0.1,
        help      = "Includes property + city + school taxes. Check county website for exact rate."
    )
    st.caption("NC: 1.0-1.2% | TX: 1.8-2.5% | NJ: 2.0-4.0% | NY/IL: up to 4-5%")
    tax_annual = 0  # will be calculated from rate in API

    hoa_monthly = st.number_input(
        "HOA Monthly ($)",
        min_value = 0,
        max_value = 2000,
        value     = 0,
        step      = 25,
        help      = "Check listing for HOA fees. Enter 0 if none."
    )
   
    st.markdown("---")
    st.markdown("### 📖 Scoring Guide")
    st.markdown("""
    | Score | Rating |
    |-------|--------|
    | 70-100 | 🟢 BUY |
    | 45-69  | 🟡 WATCH |
    | 0-44   | 🔴 AVOID |
    """)

    st.markdown("---")
    st.caption("PropCompassAI v1.0 | Powered by GCP + BigQuery ML")


# ── Main Input Form ───────────────────────────────────────────────
# ── Page Navigation ───────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "Deal Analyzer"

page_col1, page_col2, page_col3 = st.columns([1, 1, 2])
with page_col1:
    if st.button("🔍 Deal Analyzer",
                 use_container_width=True,
                 type="primary" if st.session_state.current_page == "Deal Analyzer" else "secondary"):
        st.session_state.current_page = "Deal Analyzer"
        st.rerun()
with page_col2:
    if st.button("📋 Inspection AI",
                 use_container_width=True,
                 type="primary" if st.session_state.current_page == "Inspection AI" else "secondary"):
        st.session_state.current_page = "Inspection AI"
        st.rerun()

st.markdown("---")

# ── Route to correct page ─────────────────────────────────────────
if st.session_state.current_page == "Inspection AI":
    from inspection_ui import render_inspection_page
    render_inspection_page(user=st.session_state.get("user"))
    st.stop()

# ── Main Input Form ───────────────────────────────────────────────
st.markdown('<div class="section-header">🔍 Property Analysis</div>', unsafe_allow_html=True)

# ── Address Autocomplete ──────────────────────────────────────────
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Initialize session state
# ── Auth Session State ────────────────────────────────────────────
if "user"         not in st.session_state:
    st.session_state.user         = None
if "user"         not in st.session_state:
    st.session_state.user         = None
if "auth_mode"    not in st.session_state:
    st.session_state.auth_mode    = "login"
if "show_upgrade" not in st.session_state:
    st.session_state.show_upgrade = False
if "validated_address"        not in st.session_state:
    st.session_state.validated_address        = ""
if "selected_address_display" not in st.session_state:
    st.session_state.selected_address_display = ""
if "address_validated"        not in st.session_state:
    st.session_state.address_validated        = False
if "validated_zip"            not in st.session_state:
    st.session_state.validated_zip            = ""
if "selected_state"           not in st.session_state:
    st.session_state.selected_state           = "NC"
if "ac_cache_key"             not in st.session_state:
    st.session_state.ac_cache_key             = ""
if "ac_cache_results"         not in st.session_state:
    st.session_state.ac_cache_results         = {}

col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    # ── State selector ────────────────────────────────────────
    US_STATES = [
        "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
        "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
        "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
        "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
        "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
    ]

    selected_state = st.selectbox(
        "State",
        options   = US_STATES,
        index     = US_STATES.index("NC"),
        key       = "state_selector",
        help      = "Select state to filter address suggestions"
    )
    st.session_state.selected_state = selected_state

    # ── Address input ─────────────────────────────────────────
    if st.session_state.address_validated:
        st.markdown(f"""
        <div style='background:#F0FDF4; border:1px solid #86EFAC;
        border-radius:8px; padding:12px 16px; font-size:15px;
        color:#166534; font-weight:500;'>
        📍 {st.session_state.selected_address_display}
        </div>
        """, unsafe_allow_html=True)
        address_input = st.session_state.selected_address_display

        if st.button("✏️ Change address", key="change_address"):
            st.session_state.address_validated        = False
            st.session_state.validated_address        = ""
            st.session_state.selected_address_display = ""
            st.session_state.validated_zip            = ""
            st.rerun()
    else:
        address_input = st.text_input(
            "Property Address",
            placeholder = f"Start typing {selected_state} address...",
            help        = "Type 3+ characters to see suggestions",
            key         = "address_input",
        )

        # ── Auto-trigger after 3+ characters ─────────────────
        if (address_input
                and len(address_input) >= 3
                and GOOGLE_MAPS_KEY):

            # Cache results by (input, state) — avoids an API call on every rerun
            cache_key = f"{address_input}|{selected_state}"
            if cache_key != st.session_state.ac_cache_key:
                st.session_state.ac_cache_results = validate_and_autocomplete_address(
                    address_input,
                    GOOGLE_MAPS_KEY,
                    state=selected_state,
                )
                st.session_state.ac_cache_key = cache_key

            autocomplete = st.session_state.ac_cache_results
            suggestions  = autocomplete.get("suggestions", [])
            place_ids    = autocomplete.get("place_ids",   [])

            if suggestions:
                st.markdown("**Suggestions:**")
                for i, (suggestion, place_id) in enumerate(
                    zip(suggestions, place_ids)
                ):
                    if st.button(
                        f"📍 {suggestion}",
                        key = f"suggestion_{i}",
                        use_container_width = True,
                    ):
                        details = get_place_details(place_id, GOOGLE_MAPS_KEY)
                        if details.get("validated"):
                            clean = details["formatted_address"].replace(", USA", "")
                            st.session_state.validated_address        = clean
                            st.session_state.selected_address_display = clean
                            st.session_state.validated_zip            = details.get("zip_code", "")
                            st.session_state.address_validated        = True
                            st.rerun()

        elif address_input and len(address_input) < 3:
            st.caption("Keep typing — suggestions appear after 3 characters")
        elif address_input and len(address_input) >= 3 and len(address_input) < 8:
            st.caption("💡 Tip: Type street name for better results e.g. '608 Skygrove'")

        if not GOOGLE_MAPS_KEY:
            st.caption("⚠️ Add GOOGLE_MAPS_API_KEY to .env for autocomplete")

    # Final address to use
    address = (
        st.session_state.selected_address_display
        if st.session_state.address_validated
        else address_input
    )

with col2:
    purchase_price = st.number_input(
        "Purchase Price ($)",
        min_value = 50000,
        max_value = 5000000,
        value     = 280000,
        step      = 5000,
        format    = "%d"
    )

with col3:
    monthly_rent = st.number_input(
        "Expected Monthly Rent ($)",
        min_value = 500,
        max_value = 20000,
        value     = 2200,
        step      = 50,
        format    = "%d"
    )

# Use validated zip or extract from address string
zip_code = st.session_state.get("validated_zip") or None
if not zip_code and address:
    zip_match = re.search(r'\b(\d{5})\b', address)
    if zip_match:
        zip_code = zip_match.group(1)

# Quick ratio indicator
if purchase_price > 0 and monthly_rent > 0:
    ratio = (monthly_rent / purchase_price) * 100
    color = "🟢" if ratio >= 0.8 else "🟡" if ratio >= 0.6 else "🔴"
    st.caption(f"{color} Rent-to-Price Ratio: {ratio:.2f}% {'(Good — above 0.8%)' if ratio >= 0.8 else '(Low — below 0.8%)'}")

# Analyze button
analyze_clicked = st.button(
    "🔍 Analyze This Deal",
    type = "primary",
    use_container_width = True,
)


# ── Results ───────────────────────────────────────────────────────
if analyze_clicked:
    if not address:
        st.error("Please enter a property address")
    else:
        with st.spinner("🤖 AI is analyzing this deal..."):
            try:
                result = call_analyze_api(
                    address           = address,
                    purchase_price    = float(purchase_price),
                    monthly_rent      = float(monthly_rent),
                    down_payment_pct  = float(down_payment),
                    zip_code          = zip_code or "",
                    tax_annual        = 0,
                    tax_rate          = float(tax_rate),
                    include_mgmt      = include_mgmt,
                    mgmt_rate         = float(mgmt_rate),
                    vacancy_rate      = float(vacancy_rate),
                    maintenance_rate  = float(maintenance_rate),
                    insurance_rate    = float(insurance_rate),
                    hoa_monthly       = float(hoa_monthly),
                )

                 # Save result to session state for sidebar tax display
                st.session_state.last_result = result
                # Log analysis for usage tracking
                log_analysis(
                    user_id        = user["user_id"],
                    address        = address,
                    recommendation = result.get("recommendation", ""),
                )
                # ── Recommendation Banner ─────────────────────────
                st.markdown("---")
                rec = result["recommendation"]
                score = result["deal_score"]

                col_rec, col_score, col_reasons = st.columns([2, 2, 3])

                with col_rec:
                    st.markdown(
                        f"<div style='text-align:center; padding:20px'>"
                        f"<div style='font-size:1rem; color:#6B7280'>AI Recommendation</div>"
                        f"<div style='margin-top:8px'>{recommendation_badge(rec)}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with col_score:
                    st.markdown(
                        f"<div style='text-align:center; padding:20px'>"
                        f"<div style='font-size:1rem; color:#6B7280'>Deal Score</div>"
                        f"<div style='font-size:2.5rem; font-weight:bold; color:#1B3A6B'>{score}/100</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with col_reasons:
                    st.markdown("**Top Reasons:**")
                    for reason in result.get("top_reasons", []):
                        st.markdown(f"• {reason}")

                # ── Key Metrics Row ───────────────────────────────
                st.markdown('<div class="section-header">💰 Financial Metrics</div>', unsafe_allow_html=True)

                m1, m2, m3, m4, m5, m6 = st.columns(6)

                cashflow = result["monthly_cashflow"]
                cf_delta = "positive" if cashflow >= 0 else "negative"

                with m1:
                    st.metric(
                        "Monthly Cash Flow",
                        format_currency(cashflow),
                    )
                with m2:
                    st.metric("Cap Rate",          format_pct(result.get("cap_rate", 0) or 0))
                with m3:
                    st.metric("Cash-on-Cash",      format_pct(result.get("cash_on_cash", 0) or 0))
                with m4:
                    st.metric("Gross Rent Mult",   f"{result.get('grm', 0) or 0}x")
                with m5:
                    st.metric("Monthly Mortgage",  format_currency(result.get("monthly_mortgage", 0) or 0))
                with m6:
                    st.metric("Annual Cash Flow",  format_currency(result.get("annual_cashflow", 0) or 0))

                # ── Charts Row ────────────────────────────────────
                st.markdown('<div class="section-header">📈 Charts & Analysis</div>', unsafe_allow_html=True)

                chart1, chart2 = st.columns(2)

                with chart1:
                    st.plotly_chart(
                        build_cashflow_chart(result),
                        use_container_width = True,
                    )

                with chart2:
                    st.plotly_chart(
                        build_expense_breakdown_chart(result),
                        use_container_width = True,
                    )

                # ── Gauge Row ─────────────────────────────────────
                gauge1, gauge2 = st.columns(2)

                with gauge1:
                    st.plotly_chart(
                        build_deal_score_gauge(
                            result["deal_score"],
                            result["recommendation"]
                        ),
                        use_container_width = True,
                    )

                with gauge2:
                    st.plotly_chart(
                        build_neighborhood_gauge(result["neighborhood_score"]),
                        use_container_width = True,
                    )

                # ── 5-Year Projection Table ───────────────────────
                st.markdown('<div class="section-header">📅 5-Year Projection</div>', unsafe_allow_html=True)

                proj_data = []
                for yr in result["five_year"]:
                    proj_data.append({
                        "Year":               f"Year {yr.get('year', '')}",
                        "Property Value":     format_currency(yr.get("property_value", 0) or 0),
                        "Annual Cash Flow":   format_currency(yr.get("annual_cashflow", 0) or 0),
                        "Total Appreciation": format_currency(yr.get("total_appreciation", 0) or 0),
                    })

                st.dataframe(
                    pd.DataFrame(proj_data),
                    use_container_width = True,
                    hide_index          = True,
                )


                # ── Gemini AI Explanation ─────────────────────────
                st.markdown('<div class="section-header">🤖 AI Investment Analysis</div>', unsafe_allow_html=True)

                with st.spinner("🤖 Gemini 2.5 Flash is analyzing this deal..."):
                    try:
                        explain_response = requests.post(
                            f"{API_URL}/explain",
                            json    = result,
                            timeout = 30,
                        )
                        explain_data  = explain_response.json()
                        explanation   = explain_data.get("explanation", "")
                        model_used    = explain_data.get("model", "AI")
                        status        = explain_data.get("status", "")

                         # Save explanation to result for PDF
                        if explanation:
                            result["ai_explanation"] = explanation
                        if explanation:
                            st.markdown(f"""
                            <div style='background:#EFF6FF; border-left:4px solid #2563EB;
                            border-radius:8px; padding:16px 20px; margin:8px 0;
                            font-size:15px; color:#1E3A5F; line-height:1.6;'>
                            💬 {explanation}
                            </div>
                            """, unsafe_allow_html=True)
                            if status == "success":
                                st.caption(f"⚡ Powered by {model_used}")
                            else:
                                st.caption(f"📊 {model_used}")

                    except Exception as e:
                        st.caption("AI explanation unavailable.")

                # ── PDF Download ──────────────────────────────────
                st.markdown('<div class="section-header">📄 Download Report</div>', unsafe_allow_html=True)

                try:
                    pdf_bytes = generate_pdf_report(result)
                    pdf_data  = bytes(pdf_bytes)
                except Exception as pdf_err:
                    st.error(f"PDF Error: {pdf_err}")
                    pdf_data = None

                if pdf_data:
                    st.download_button(
                        label               = "📥 Download PDF Investment Report",
                        data                = pdf_data,
                        file_name           = "PropCompassAI_Report.pdf",
                        mime                = "application/pdf",
                        use_container_width = True,
                    )
                else:
                    st.warning("PDF unavailable — analysis data shown above.")
                # ── Realtor Analysis ──────────────────────────
                realtor = result.get("realtor_analysis", {})
                if realtor.get("available"):
                    st.markdown('<div class="section-header">🏠 Realtor Analysis</div>', unsafe_allow_html=True)

                    diagnosis   = realtor.get("diagnosis",   {})
                    fair_value  = realtor.get("fair_value",  {})
                    negotiation = realtor.get("negotiation", {})
                    scenarios   = realtor.get("scenarios",   [])
                    summary     = realtor.get("summary",     "")

                    # Summary box
                    st.info(f"💼 {summary}")

                    col_d, col_f = st.columns(2)

                    with col_d:
                        st.markdown("**🔍 Diagnosis**")
                        severity = diagnosis.get("severity", "medium")
                        color = {"high": "🔴", "medium": "🟡", "low": "🟢", "positive": "🟢"}.get(severity, "🟡")
                        st.markdown(f"{color} {diagnosis.get('message', '')}")
                        st.caption(f"Rent-to-price ratio: {diagnosis.get('rent_to_price', 0):.2f}% (target: 0.8%+)")

                    with col_f:
                        st.markdown("**💰 Fair Market Value**")
                        st.metric("At 6% cap rate", f"${fair_value.get('value_at_6_cap', 0):,.0f}")
                        st.metric("At 7% cap rate", f"${fair_value.get('value_at_7_cap', 0):,.0f}")
                        st.metric("At 8% cap rate", f"${fair_value.get('value_at_8_cap', 0):,.0f}")

                    # Negotiation strategy
                    st.markdown("**🤝 Negotiation Strategy**")
                    neg_col1, neg_col2, neg_col3 = st.columns(3)
                    with neg_col1:
                        st.metric("Max price for BUY",   f"${negotiation.get('max_price_for_buy', 0):,.0f}")
                    with neg_col2:
                        st.metric("Suggested offer",     f"${negotiation.get('suggested_offer', 0):,.0f}")
                    with neg_col3:
                        st.metric("Price reduction needed", f"${negotiation.get('reduction_needed', 0):,.0f}")

                    # Value-add scenarios
                    if scenarios:
                        st.markdown("**📈 Value-Add Scenarios**")
                        for scenario in scenarios:
                            rec   = scenario.get("recommendation", "WATCH")
                            color = "🟢" if rec == "BUY" else "🟡"
                            best  = "⭐ BEST OPTION" if scenario.get("best") else ""
                            with st.expander(f"{color} {scenario.get('name', '')} {best}"):
                                s1, s2, s3 = st.columns(3)
                                with s1:
                                    st.metric("Target Price", f"${scenario.get('target_price', 0):,.0f}")
                                with s2:
                                    st.metric("Target Rent",  f"${scenario.get('target_rent', 0):,.0f}/mo")
                                with s3:
                                    cf = scenario.get('new_cashflow', 0)
                                    st.metric("New Cash Flow", f"${cf:,.0f}/mo", delta=f"${cf:,.0f}")
                                st.success(f"✅ Action: {scenario.get('action', '')}")
                                st.caption(f"New cap rate: {scenario.get('new_cap_rate', 0):.2f}% | Recommendation: {rec}")

                st.success("✅ Analysis complete! Report ready to download.")

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. The API is warming up — please try again in 30 seconds.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to API. Check your internet connection.")
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                st.info("💡 Make sure the API is running at: " + API_URL)

else:
    # ── Welcome Screen ────────────────────────────────────────────
    st.markdown('<div class="section-header">👋 Welcome to PropCompassAI</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("""
        **🤖 AI-Powered Analysis**

        Our BigQuery ML model trained on
        219 real estate deals gives you
        institutional-grade analysis in seconds.
        """)

    with col_b:
        st.markdown("""
        **📊 8 Investment Metrics**

        Cap rate, cash-on-cash return,
        gross rent multiplier, 5-year
        projection and more.
        """)

    with col_c:
        st.markdown("""
        **📄 PDF Reports**

        Download a professional PDF
        report to share with partners,
        lenders, or your team.
        """)

    st.markdown("---")
    st.info("👆 Enter a property address and details above, then click **Analyze This Deal**")

    # Sample analysis hint
    st.markdown("**Try these example deals:**")
    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        st.code("222 Cashflow Lane\nDurham NC 27701\nPrice: $160,000\nRent: $1,600")
    with ex2:
        st.code("456 Investment Ave\nRaleigh NC 27609\nPrice: $280,000\nRent: $2,200")
    with ex3:
        st.code("789 Rental Blvd\nCharlotte NC 28201\nPrice: $220,000\nRent: $1,900")

    # ════════════════════════════════════════════════════════════
# FLOATING CHATBOT
# ════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════
# FLOATING CHATBOT
# ════════════════════════════════════════════════════════════
from streamlit_float import *
float_init()

if "chat_open"    not in st.session_state:
    st.session_state.chat_open    = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_chat_input" not in st.session_state:
    st.session_state.last_chat_input = ""

# Floating button
button_container = st.container()
with button_container:
    if st.button(
        "💬" if not st.session_state.chat_open else "✕",
        key  = "float_chat_btn",
        help = "Ask PropCompassAI Assistant"
    ):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()

button_container.float(
    "bottom: 2rem; right: 2rem; "
    "background-color: #1B3A6B; "
    "border-radius: 50%; "
    "width: 52px; height: 52px; "
    "z-index: 9999;"
)

# Chat panel
if st.session_state.chat_open:
    chat_container = st.container()
    with chat_container:
        st.markdown("""
        <div style='background:#1B3A6B; color:white;
        padding:10px 16px; border-radius:12px 12px 0 0;
        font-size:14px; font-weight:600;'>
        🤖 PropCompassAI Assistant
        </div>
        """, unsafe_allow_html=True)

        # Chat history
        history_box = st.container()
        with history_box:
            if not st.session_state.chat_history:
                st.info("Hi! Ask me anything about real estate investing or the current deal!")
            for msg in st.session_state.chat_history[-10:]:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div style='background:#F3F4F6;border-radius:8px;
                    padding:8px 10px;font-size:12px;color:#374151;
                    margin:4px 0;text-align:right;'>
                    <b>You:</b> {msg['content']}
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background:#EFF6FF;border-radius:8px;
                    padding:8px 10px;font-size:12px;color:#1E3A5F;
                    margin:4px 0;'>
                    🤖 {msg['content']}
                    </div>""", unsafe_allow_html=True)

        # Input
        user_input = st.text_input(
            "Ask a question...",
            key             = "chat_question",
            label_visibility = "collapsed",
            placeholder     = "e.g. Is this a good deal?"
        )
        col_send, col_clear = st.columns([3, 1])
        with col_send:
            send = st.button("Send ↵", use_container_width=True, key="chat_send")
        with col_clear:
            if st.button("Clear", use_container_width=True, key="chat_clear"):
                st.session_state.chat_history = []
                st.rerun()

        if send and user_input and user_input != st.session_state.get("last_chat_input", ""):
            st.session_state.last_chat_input = user_input
            st.session_state.chat_history.append({
                "role":    "user",
                "content": user_input
            })
            deal_ctx = st.session_state.get("last_result", {})
            with st.spinner("thinking..."):
                try:
                    chat_resp = requests.post(
                        f"{API_URL}/chat",
                        json    = {
                            "message":      user_input,
                            "deal_context": deal_ctx,
                            "history":      st.session_state.chat_history[:-1],
                        },
                        timeout = 30,
                    )
                    bot_reply = chat_resp.json().get(
                        "response",
                        "Sorry, I couldn't process that."
                    )
                except Exception as e:
                    bot_reply = f"Error: {str(e)}"

            st.session_state.chat_history.append({
                "role":    "assistant",
                "content": bot_reply
            })
            st.rerun()

    chat_container.float(
        "bottom: 5rem; right: 2rem; "
        "width: 340px; "
        "background: white; "
        "border-radius: 12px; "
        "box-shadow: 0 8px 32px rgba(0,0,0,0.18); "
        "border: 1px solid #E2E8F0; "
        "padding: 0; "
        "z-index: 9998;"
    )