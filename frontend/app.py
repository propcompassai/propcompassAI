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
from fpdf import FPDF
import urllib.parse

# ── Page Configuration ────────────────────────────────────────────
st.set_page_config(
    page_title     = "PropCompassAI",
    page_icon      = "🧭",
    layout         = "wide",
    initial_sidebar_state = "expanded",
)

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

def validate_and_autocomplete_address(partial_address: str, api_key: str) -> dict:
    """
    Two functions in one:
    1. Autocomplete — suggests addresses as user types
    2. Validation — confirms address exists and returns
       standardized format + lat/lng + zip code

    Uses Google Places API:
    - Autocomplete endpoint for suggestions
    - Place Details endpoint for full validation
    """
    if not partial_address or len(partial_address) < 5:
        return {"suggestions": [], "validated": None}

    # ── Autocomplete ──────────────────────────────────────────
    autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input":      partial_address,
        "types":      "address",
        "components": "country:us",  # US addresses only
        "key":        api_key,
    }

    try:
        response = requests.get(autocomplete_url, params=params, timeout=5)
        data = response.json()

        suggestions = []
        place_ids = []

        if data.get("status") == "OK":
            for prediction in data.get("predictions", [])[:5]:
                suggestions.append(prediction["description"])
                place_ids.append(prediction["place_id"])

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
) -> dict:
    """Call the PropCompassAI API and return results."""
    payload = {
        "address":          address,
        "purchase_price":   purchase_price,
        "monthly_rent":     monthly_rent,
        "down_payment_pct": down_payment_pct,
        "zip_code":         zip_code,
        "tax_annual":       tax_annual if tax_annual > 0 else None,
        "include_mgmt":     include_mgmt,
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


def format_currency(value: float) -> str:
    """Format number as currency."""
    if value >= 0:
        return f"${value:,.0f}"
    return f"-${abs(value):,.0f}"


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
    """Build expense breakdown pie chart."""
    breakdown = result.get("expense_breakdown", {})

    labels = []
    values = []
    colors = ["#2563EB", "#16A34A", "#F59E0B", "#EF4444", "#8B5CF6"]

    expense_map = {
        "tax_monthly":         "Property Tax",
        "insurance_monthly":   "Insurance",
        "vacancy_monthly":     "Vacancy Loss",
        "maintenance_monthly": "Maintenance",
        "mgmt_monthly":        "Management",
    }

    for key, label in expense_map.items():
        val = breakdown.get(key, 0) or 0
        if val > 0:
            labels.append(label)
            values.append(val)

    # Add mortgage
    labels.append("Mortgage")
    values.append(result["monthly_mortgage"])

    fig = go.Figure(go.Pie(
        labels    = labels,
        values    = values,
        hole      = 0.4,
        marker    = dict(colors=colors + ["#1B3A6B"]),
    ))
    fig.update_layout(
        title  = "Monthly Cost Breakdown",
        height = 320,
        margin = dict(t=50, b=20, l=20, r=20),
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

    # Footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(190, 5, "PropCompassAI | This report is for informational purposes only. Not financial advice.", align="C")

    # Return as bytes using dest='S'
    return bytes(pdf.output())

# ══ MAIN UI ════════════════════════════════════════════════════════

# ── Header ────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🧭 PropCompassAI</h1>
    <p>Your compass for every real estate decision — AI-powered deal analysis</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
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

    include_mgmt = st.checkbox(
        "Include Property Management (8%)",
        value = True,
        help  = "Property management fees reduce cash flow but save your time"
    )

    tax_annual = st.number_input(
        "Annual Property Tax ($)",
        min_value = 0,
        max_value = 50000,
        value     = 0,
        step      = 100,
        help      = "Leave 0 to use estimated tax rate"
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
st.markdown('<div class="section-header">🔍 Property Analysis</div>', unsafe_allow_html=True)

# ── Address Autocomplete ──────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Initialize session state for address
if "validated_address" not in st.session_state:
    st.session_state.validated_address = ""
if "selected_address_display" not in st.session_state:
    st.session_state.selected_address_display = ""
if "address_validated" not in st.session_state:
    st.session_state.address_validated = False
if "validated_zip"      not in st.session_state:
    st.session_state.validated_zip      = ""
if "address_validated"  not in st.session_state:
    st.session_state.address_validated  = False
if "selected_place_id"  not in st.session_state:
    st.session_state.selected_place_id  = ""

col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    # Show validated address OR text input
    if st.session_state.address_validated:
        # Show clean validated address — hide text input
        st.markdown(f"""
        <div style='background:#F0FDF4; border:1px solid #86EFAC; 
        border-radius:8px; padding:12px 16px; font-size:15px; 
        color:#166534; font-weight:500;'>
        📍 {st.session_state.selected_address_display}
        </div>
        """, unsafe_allow_html=True)
        address_input = st.session_state.selected_address_display
    else:
        address_input = st.text_input(
            "Property Address",
            placeholder = "Start typing address...",
            help        = "Type an address to see suggestions",
            key         = "address_input",
        )

    # Show autocomplete suggestions
    if address_input and len(address_input) >= 5 and GOOGLE_MAPS_KEY:
        autocomplete = validate_and_autocomplete_address(
            address_input, GOOGLE_MAPS_KEY
        )
        suggestions = autocomplete.get("suggestions", [])
        place_ids   = autocomplete.get("place_ids", [])

        if suggestions:
            st.markdown("**Suggestions:**")
            for i, (suggestion, place_id) in enumerate(
                zip(suggestions, place_ids)
            ):
                if st.button(
                    f"📍 {suggestion}",
                    key  = f"suggestion_{i}",
                    use_container_width = True,
                ):
                    # Get full details for selected address
                    details = get_place_details(place_id, GOOGLE_MAPS_KEY)
                    if details.get("validated"):
                        clean_address = details["formatted_address"].replace(", USA", "")
                        st.session_state.validated_address  = clean_address
                        st.session_state.validated_zip      = details.get("zip_code", "")
                        st.session_state.address_validated  = True
                        st.session_state.selected_address_display = clean_address

                        st.rerun()

    # Show validated address confirmation
    if st.session_state.address_validated:
        st.success(f"✅ Validated: {st.session_state.validated_address}")
        if st.button("✏️ Change address", key="change_address"):
            st.session_state.address_validated  = False
            st.session_state.validated_address  = ""
            st.session_state.validated_zip      = ""
            st.session_state.selected_address_display = ""
            st.rerun()

    # Final address to use
    address = (
        st.session_state.selected_address_display
        if st.session_state.address_validated
        else address_input
    )

    # Validation status indicator
    if address and not st.session_state.address_validated:
        if not GOOGLE_MAPS_KEY:
            st.caption("⚠️ Add GOOGLE_MAPS_API_KEY to .env for address validation")
        else:
            st.caption("👆 Select a suggestion above to validate address")

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

# Extract zip code from address
# Use validated zip or extract from address
import re
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
                    address          = address,
                    purchase_price   = float(purchase_price),
                    monthly_rent     = float(monthly_rent),
                    down_payment_pct = float(down_payment),
                    zip_code         = zip_code or "",
                    tax_annual       = float(tax_annual),
                    include_mgmt     = include_mgmt,
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

# ── PDF Download ──────────────────────────────────
                st.markdown('<div class="section-header">📄 Download Report</div>', unsafe_allow_html=True)

                try:
                    pdf_bytes = generate_pdf_report(result)
                    pdf_data  = bytes(pdf_bytes) if pdf_bytes else None
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