"""
PropCompassAI — Stripe Billing
Handles subscription creation, upgrade and webhook
"""

import os
import logging
import streamlit as st

logger = logging.getLogger(__name__)

# ── Pricing ───────────────────────────────────────────────────
PLANS = {
    "pro": {
        "name":        "PropCompassAI Pro",
        "price":       29,
        "price_id":    "price_PLACEHOLDER_PRO",  # Replace after Stripe setup
        "features": [
            "✅ Unlimited deal analyses",
            "✅ Gemini AI explanations",
            "✅ PDF investment reports",
            "✅ Inspection Report AI",
            "✅ Repair request emails",
            "✅ Negotiation strategy",
            "✅ Realtor advisor",
            "✅ Deal chatbot",
            "✅ Priority support",
        ]
    },
    "realtor": {
        "name":        "PropCompassAI Realtor",
        "price":       49,
        "price_id":    "price_PLACEHOLDER_REALTOR",
        "features": [
            "✅ Everything in Pro",
            "✅ Unlimited clients",
            "✅ Branded PDF reports",
            "✅ CRM (coming soon)",
            "✅ Deal funnel (coming soon)",
            "✅ Priority support",
        ]
    }
}

def get_stripe():
    """Initialize Stripe with secret key."""
    try:
        import stripe
        key = None
        try:
            key = st.secrets.get("STRIPE_SECRET_KEY")
        except:
            key = os.getenv("STRIPE_SECRET_KEY")
        if not key:
            logger.warning("Stripe key not found")
            return None
        stripe.api_key = key
        return stripe
    except Exception as e:
        logger.error(f"Stripe init failed: {e}")
        return None

def get_stripe_publishable_key() -> str:
    """Get publishable key for frontend."""
    try:
        key = st.secrets.get("STRIPE_PUBLISHABLE_KEY")
        if not key:
            key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        return key
    except:
        return os.getenv("STRIPE_PUBLISHABLE_KEY", "")

def create_checkout_session(
    user_email: str,
    user_id:    str,
    plan:       str = "pro"
) -> str:
    """Create Stripe checkout session and return URL."""
    try:
        stripe = get_stripe()
        if not stripe:
            return None

        plan_data = PLANS.get(plan, PLANS["pro"])
        
        # Get base URL
        try:
            base_url = st.secrets.get(
                "APP_URL",
                "https://propcompassai.streamlit.app"
            )
        except:
            base_url = "https://propcompassai.streamlit.app"

        session = stripe.checkout.Session.create(
            payment_method_types = ["card"],
            mode                 = "subscription",
            customer_email       = user_email,
            line_items           = [{
                "price":    plan_data["price_id"],
                "quantity": 1,
            }],
            metadata = {
                "user_id": user_id,
                "plan":    plan,
            },
            success_url = f"{base_url}?upgrade=success",
            cancel_url  = f"{base_url}?upgrade=cancelled",
        )
        logger.info(f"Checkout session created for {user_email}")
        return session.url

    except Exception as e:
        logger.error(f"Checkout session failed: {e}")
        return None

def create_portal_session(customer_id: str) -> str:
    """Create Stripe billing portal session."""
    try:
        stripe = get_stripe()
        if not stripe:
            return None

        try:
            base_url = st.secrets.get(
                "APP_URL",
                "https://propcompassai.streamlit.app"
            )
        except:
            base_url = "https://propcompassai.streamlit.app"

        session = stripe.billing_portal.Session.create(
            customer   = customer_id,
            return_url = base_url,
        )
        return session.url

    except Exception as e:
        logger.error(f"Portal session failed: {e}")
        return None

def update_user_tier_in_bigquery(
    user_id:     str,
    tier:        str,
    customer_id: str = ""
):
    """Update user tier in BigQuery after successful payment."""
    try:
        from google.oauth2 import service_account
        from google.cloud import bigquery

        try:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            client = bigquery.Client(
                project     = "propcompassai",
                credentials = credentials
            )
        except:
            client = bigquery.Client(project="propcompassai")

        query = f"""
            UPDATE `propcompassai.prop_compass.users`
            SET tier = '{tier}',
                stripe_customer_id = '{customer_id}'
            WHERE user_id = '{user_id}'
        """
        client.query(query).result()
        logger.info(f"Updated user {user_id} to tier {tier}")

    except Exception as e:
        logger.error(f"BigQuery tier update failed: {e}")

def render_upgrade_banner(user: dict, usage: dict):
    """Show upgrade banner for free users."""
    tier      = usage.get("tier", "free")
    used      = usage.get("used", 0)
    limit     = usage.get("limit", 3)
    remaining = usage.get("remaining", 3)

    if tier != "free":
        return

    # Show warning when running low
    if remaining <= 1:
        st.markdown(f"""
        <div style='background:rgba(241,58,48,0.1);
                    border:1px solid rgba(241,58,48,0.3);
                    border-left:4px solid #F13A30;
                    border-radius:10px;padding:14px 16px;
                    margin:10px 0;'>
            <div style='font-weight:700;color:#F13A30;
                        font-size:14px;margin-bottom:6px;'>
                ⚠️ Only {remaining} analysis remaining this month!
            </div>
            <div style='color:#CBD5E1;font-size:13px;'>
                Upgrade to Pro for unlimited analyses — $29/month
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_pricing_page(user: dict):
    """Render the full pricing/upgrade page."""
    st.markdown("### 💳 Upgrade to PropCompassAI Pro")
    st.markdown("Unlock unlimited analyses and all premium features!")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div style='background:rgba(16,28,52,0.9);
                    border:1px solid rgba(99,130,255,0.2);
                    border-radius:14px;padding:20px;
                    text-align:center;'>
            <div style='color:#94A3B8;font-size:12px;
                        text-transform:uppercase;
                        letter-spacing:0.1em;'>Current Plan</div>
            <div style='font-size:1.8rem;font-weight:800;
                        color:#F0F4FF;margin:8px 0;'>FREE</div>
            <div style='font-size:2rem;font-weight:800;
                        color:#F0F4FF;'>$0<span style='font-size:14px;
                        color:#64748B;'>/month</span></div>
            <div style='margin-top:16px;text-align:left;'>
                <div style='color:#CBD5E1;font-size:13px;
                            margin-bottom:6px;'>✅ 3 analyses per month</div>
                <div style='color:#CBD5E1;font-size:13px;
                            margin-bottom:6px;'>✅ Basic metrics</div>
                <div style='color:#64748B;font-size:13px;
                            margin-bottom:6px;'>❌ No PDF reports</div>
                <div style='color:#64748B;font-size:13px;
                            margin-bottom:6px;'>❌ No AI explanation</div>
                <div style='color:#64748B;font-size:13px;
                            margin-bottom:6px;'>❌ No Inspection AI</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style='background:rgba(13,110,253,0.15);
                    border:2px solid #0D6EFD;
                    border-radius:14px;padding:20px;
                    text-align:center;position:relative;'>
            <div style='position:absolute;top:-12px;
                        left:50%;transform:translateX(-50%);
                        background:#0D6EFD;color:white;
                        padding:2px 16px;border-radius:100px;
                        font-size:11px;font-weight:700;'>
                MOST POPULAR
            </div>
            <div style='color:#60A5FA;font-size:12px;
                        text-transform:uppercase;
                        letter-spacing:0.1em;'>Pro Plan</div>
            <div style='font-size:1.8rem;font-weight:800;
                        color:#F0F4FF;margin:8px 0;'>PRO</div>
            <div style='font-size:2rem;font-weight:800;
                        color:#F0F4FF;'>$29<span style='font-size:14px;
                        color:#64748B;'>/month</span></div>
            <div style='margin-top:16px;text-align:left;'>
                {''.join([f"<div style='color:#CBD5E1;font-size:13px;margin-bottom:6px;'>{f}</div>" for f in PLANS['pro']['features']])}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Upgrade button
    if st.button(
        "🚀 Upgrade to Pro — $29/month",
        type="primary",
        use_container_width=True,
        key="upgrade_btn"
    ):
        checkout_url = create_checkout_session(
            user_email = user.get("email", ""),
            user_id    = user.get("user_id", ""),
            plan       = "pro"
        )
        if checkout_url:
            st.markdown(f"""
            <script>window.open('{checkout_url}', '_blank');</script>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style='text-align:center;margin-top:10px;'>
                <a href='{checkout_url}' target='_blank'
                   style='background:linear-gradient(135deg,#0D6EFD,#1a7fff);
                          color:white;padding:12px 32px;border-radius:100px;
                          text-decoration:none;font-weight:700;font-size:14px;'>
                    Click here to complete payment →
                </a>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Payment system not configured yet — launching May 27th!")

    st.markdown("""
    <div style='text-align:center;color:#64748B;font-size:12px;margin-top:12px;'>
        🔒 Secured by Stripe · Cancel anytime · No hidden fees
    </div>
    """, unsafe_allow_html=True)

def check_upgrade_success():
    """Check if user returned from successful Stripe checkout."""
    try:
        params = st.query_params
        if params.get("upgrade") == "success":
            st.success("🎉 Welcome to PropCompassAI Pro! Your account has been upgraded.")
            st.query_params.clear()
    except:
        pass
