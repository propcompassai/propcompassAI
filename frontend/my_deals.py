"""
PropCompassAI — My Deals Dashboard
Renders deal history from user_analyses BigQuery table.
Add to frontend/app.py sidebar navigation.
"""

import streamlit as st
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── BigQuery client (same pattern as inspection_cache.py) ────────────────────
def get_bigquery_client():
    try:
        from google.oauth2 import service_account
        from google.cloud import bigquery
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return bigquery.Client(project="propcompassai", credentials=credentials)
        return bigquery.Client(project="propcompassai")
    except Exception as e:
        logger.error(f"BigQuery client failed: {e}")
        return None


# ── Fetch deals for this user ────────────────────────────────────────────────
def fetch_user_deals(user_id: str) -> list[dict]:
    """Pull all analyses for this user from user_analyses table."""
    try:
        from google.cloud import bigquery
        client = get_bigquery_client()
        if not client:
            return []
        query = """
            SELECT
                analysis_id,
                address AS property_address,
                analyzed_at,
                recommendation,
                deal_score,
                cap_rate,
                purchase_price,
                monthly_rent,
                analysis_type
            FROM `propcompassai.prop_compass.user_analyses`
            WHERE user_id = @user_id
            AND deal_score IS NOT NULL
            ORDER BY analyzed_at DESC
            LIMIT 100
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
            ]
        )
        rows = list(client.query(query, job_config=job_config).result())
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"fetch_user_deals failed: {e}")
        return []


# ── Helpers ──────────────────────────────────────────────────────────────────
def _rec_color(rec: str) -> str:
    rec = (rec or "").upper()
    if "BUY"   in rec: return "#10B981"
    if "WATCH" in rec: return "#F59E0B"
    if "AVOID" in rec: return "#EF4444"
    return "#64748B"

def _rec_bg(rec: str) -> str:
    rec = (rec or "").upper()
    if "BUY"   in rec: return "rgba(16,185,129,0.12)"
    if "WATCH" in rec: return "rgba(245,158,11,0.12)"
    if "AVOID" in rec: return "rgba(239,68,68,0.12)"
    return "rgba(100,116,139,0.12)"

def _fmt_date(val) -> str:
    if val is None:
        return "—"
    try:
        if hasattr(val, "strftime"):
            return val.strftime("%b %d, %Y")
        return str(val)[:10]
    except Exception:
        return str(val)

def _fmt_currency(val) -> str:
    if val is None or val == 0:
        return "—"
    return f"${float(val):,.0f}"

def _fmt_score(val) -> str:
    if val is None:
        return "—"
    return f"{float(val):.1f}"

def _fmt_cap(val) -> str:
    if val is None:
        return "—"
    return f"{float(val):.2f}%"


# ── Main render ───────────────────────────────────────────────────────────────
def render_my_deals_page(user: dict = None):
    """Render the My Deals dashboard."""

    # ── Header ───────────────────────────────────────────────────────
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1B3A6B,#0D2B52);
                padding:1.5rem 1.8rem;border-radius:12px;
                margin-bottom:1.5rem;
                border:1px solid rgba(99,130,255,0.15)'>
        <h2 style='color:white;margin:0;font-size:1.5rem'>📁 My Deals</h2>
        <p style='color:#93C5FD;margin:0.3rem 0 0;font-size:0.9rem'>
            Your complete deal analysis history — scores, cap rates, and recommendations
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Auth gate ─────────────────────────────────────────────────────
    if user is None:
        st.warning("Please log in to view your deals.")
        return

    user_id = user.get("uid") or user.get("user_id") or user.get("localId", "")
    if not user_id:
        st.error("Could not resolve user ID. Please log out and back in.")
        return

    # ── Load data ─────────────────────────────────────────────────────
    with st.spinner("Loading your deals..."):
        deals = fetch_user_deals(user_id)

    #st.write(f"DEBUG: user_id={user_id} deals={len(deals)}")
    # ── Empty state ───────────────────────────────────────────────────
    if not deals:
        st.markdown("""
        <div style='text-align:center;padding:3rem 1rem;
                    border:2px dashed rgba(99,130,255,0.2);
                    border-radius:16px;margin-top:1rem'>
            <div style='font-size:3rem;margin-bottom:0.8rem'>🏠</div>
            <div style='color:#93C5FD;font-size:1.1rem;font-weight:600;
                        margin-bottom:0.4rem'>No analyses yet</div>
            <div style='color:#64748B;font-size:0.9rem'>
                Run your first deal analysis to see it here
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Summary KPI bar ───────────────────────────────────────────────
    total      = len(deals)
    buys       = sum(1 for d in deals if "BUY"   in (d.get("recommendation") or "").upper())
    watches    = sum(1 for d in deals if "WATCH" in (d.get("recommendation") or "").upper())
    avoids     = sum(1 for d in deals if "AVOID" in (d.get("recommendation") or "").upper())
    avg_score  = (
        sum(float(d["deal_score"]) for d in deals if d.get("deal_score"))
        / max(sum(1 for d in deals if d.get("deal_score")), 1)
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi(c1, "Total Analyses", str(total),       "#93C5FD")
    _kpi(c2, "✅ BUY",          str(buys),        "#10B981")
    _kpi(c3, "👀 WATCH",        str(watches),     "#F59E0B")
    _kpi(c4, "🚫 AVOID",        str(avoids),      "#EF4444")
    _kpi(c5, "Avg Score",       f"{avg_score:.1f}", "#A78BFA")

    st.markdown("<div style='margin:1.2rem 0 0.4rem'></div>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────
    with st.expander("🔍 Filter Deals", expanded=False):
        fc1, fc2 = st.columns(2)
        with fc1:
            filter_rec = st.multiselect(
                "Recommendation",
                ["BUY", "WATCH", "AVOID"],
                default=[],
                placeholder="All"
            )
        with fc2:
            filter_type = st.multiselect(
                "Analysis Type",
                list({d.get("analysis_type", "Deal Analyzer") for d in deals}),
                default=[],
                placeholder="All types"
            )

    # Apply filters
    filtered = deals
    if filter_rec:
        filtered = [d for d in filtered
                    if any(r in (d.get("recommendation") or "").upper()
                           for r in filter_rec)]
    if filter_type:
        filtered = [d for d in filtered
                    if d.get("analysis_type") in filter_type]

    st.markdown(
        f"<div style='color:#64748B;font-size:0.82rem;margin-bottom:0.8rem'>"
        f"Showing {len(filtered)} of {total} deals</div>",
        unsafe_allow_html=True
    )

    # ── Deal cards ────────────────────────────────────────────────────
    for deal in filtered:
        rec      = (deal.get("recommendation") or "—").upper()
        address  = deal.get("property_address") or "Unknown Address"
        score    = _fmt_score(deal.get("deal_score"))
        cap      = _fmt_cap(deal.get("cap_rate"))
        price    = _fmt_currency(deal.get("purchase_price"))
        rent     = _fmt_currency(deal.get("monthly_rent"))
        dated    = _fmt_date(deal.get("analyzed_at"))
        atype    = deal.get("analysis_type") or "Deal Analyzer"
        color    = _rec_color(rec)
        bg       = _rec_bg(rec)

        with st.container():
            st.markdown(f"""
            <div style='background:rgba(13,22,45,0.85);
                        border:1px solid rgba(99,130,255,0.15);
                        border-left:4px solid {color};
                        border-radius:10px;padding:1rem 1.2rem;
                        margin-bottom:0.8rem;'>
                <div style='display:flex;justify-content:space-between;
                            align-items:flex-start;flex-wrap:wrap;gap:0.4rem'>
                    <div>
                        <div style='color:#F1F5F9;font-weight:700;
                                    font-size:1rem;margin-bottom:0.15rem'>
                            🏠 {address}
                        </div>
                        <div style='color:#64748B;font-size:0.78rem'>
                            {dated} &nbsp;·&nbsp; {atype}
                        </div>
                    </div>
                    <div style='background:{bg};border:1px solid {color};
                                color:{color};font-weight:800;font-size:0.85rem;
                                padding:0.25rem 0.9rem;border-radius:100px;
                                letter-spacing:0.05em;white-space:nowrap'>
                        {rec}
                    </div>
                </div>
                <div style='display:flex;gap:1.5rem;margin-top:0.75rem;
                            flex-wrap:wrap'>
                    {_stat_pill("Deal Score", score, "#A78BFA")}
                    {_stat_pill("Cap Rate",   cap,   "#34D399")}
                    {_stat_pill("Price",      price, "#93C5FD")}
                    {_stat_pill("Mo. Rent",   rent,  "#FCD34D")}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Export CSV ────────────────────────────────────────────────────
    if filtered:
        st.markdown("<div style='margin-top:1.2rem'></div>", unsafe_allow_html=True)
        import pandas as pd
        df = pd.DataFrame([{
            "Address":        d.get("property_address", ""),
            "Date":           _fmt_date(d.get("analyzed_at")),
            "Recommendation": d.get("recommendation", ""),
            "Deal Score":     d.get("deal_score", ""),
            "Cap Rate (%)":   d.get("cap_rate", ""),
            "Purchase Price": d.get("purchase_price", ""),
            "Monthly Rent":   d.get("monthly_rent", ""),
            "Type":           d.get("analysis_type", ""),
        } for d in filtered])

        csv = df.to_csv(index=False)
        st.download_button(
            label="⬇️ Export to CSV",
            data=csv,
            file_name=f"my_deals_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ── Small UI helpers ──────────────────────────────────────────────────────────
def _kpi(col, label: str, value: str, color: str):
    col.markdown(f"""
    <div style='background:rgba(13,22,45,0.8);
                border:1px solid rgba(99,130,255,0.12);
                border-radius:10px;padding:0.8rem 1rem;text-align:center'>
        <div style='color:{color};font-size:1.5rem;font-weight:800;
                    line-height:1.1'>{value}</div>
        <div style='color:#64748B;font-size:0.72rem;margin-top:0.2rem'>{label}</div>
    </div>
    """, unsafe_allow_html=True)


def _stat_pill(label: str, value: str, color: str) -> str:
    return f"""
    <div style='display:flex;flex-direction:column;align-items:flex-start'>
        <span style='color:#64748B;font-size:0.68rem;text-transform:uppercase;
                     letter-spacing:0.06em'>{label}</span>
        <span style='color:{color};font-weight:700;font-size:0.92rem'>{value}</span>
    </div>
    """
