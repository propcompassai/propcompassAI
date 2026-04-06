
"""
auth/firebase_auth.py
PropCompassAI — Firebase Authentication

Handles:
- Google Sign-In
- Email/Password login
- User session management
- Usage tracking (free vs pro tier)
"""

import os
import json
import pyrebase
import logging
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── Firebase Config ───────────────────────────────────────────────
FIREBASE_CONFIG = {
    "apiKey":            os.getenv("FIREBASE_API_KEY"),
    "authDomain":        os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId":         os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket":     os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId":             os.getenv("FIREBASE_APP_ID"),
    "databaseURL":       ""
}

# ── Initialize Firebase ───────────────────────────────────────────
try:
    firebase  = pyrebase.initialize_app(FIREBASE_CONFIG)
    auth_client = firebase.auth()
    logger.info("✅ Firebase Auth initialized")
except Exception as e:
    auth_client = None
    logger.warning(f"⚠️ Firebase unavailable: {e}")

# ── Tier Limits ───────────────────────────────────────────────────
TIER_LIMITS = {
    "free":  3,    # analyses per month
    "pro":   999,  # unlimited
    "team":  999,  # unlimited
}

def sign_in_with_email(email: str, password: str) -> dict:
    """Sign in with email and password."""
    try:
        user = auth_client.sign_in_with_email_and_password(email, password)
        return {
            "success":      True,
            "user_id":      user["localId"],
            "email":        user["email"],
            "id_token":     user["idToken"],
            "display_name": user.get("displayName", email.split("@")[0]),
        }
    except Exception as e:
        error_msg = str(e)
        if "INVALID_PASSWORD" in error_msg or "EMAIL_NOT_FOUND" in error_msg:
            return {"success": False, "error": "Invalid email or password"}
        elif "TOO_MANY_ATTEMPTS" in error_msg:
            return {"success": False, "error": "Too many attempts. Please try again later."}
        else:
            return {"success": False, "error": "Login failed. Please try again."}

def create_account(email: str, password: str, display_name: str = "") -> dict:
    """Create new account with email and password."""
    try:
        user = auth_client.create_user_with_email_and_password(email, password)
        # Update display name
        if display_name:
            auth_client.update_profile(
                user["idToken"],
                display_name = display_name
            )
        # Save user to BigQuery
        save_user_to_bigquery(
            user_id      = user["localId"],
            email        = email,
            display_name = display_name or email.split("@")[0],
            provider     = "email",
        )
        return {
            "success":      True,
            "user_id":      user["localId"],
            "email":        email,
            "id_token":     user["idToken"],
            "display_name": display_name or email.split("@")[0],
        }
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            return {"success": False, "error": "Email already registered. Please sign in."}
        elif "WEAK_PASSWORD" in error_msg:
            return {"success": False, "error": "Password must be at least 6 characters."}
        else:
            return {"success": False, "error": f"Registration failed: {str(e)}"}

def save_user_to_bigquery(
    user_id:      str,
    email:        str,
    display_name: str,
    provider:     str = "email",
    tier:         str = "free"
):
    """Save or update user in BigQuery users table."""
    try:
        client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID", "propcompassai"))
        query  = f"""
            MERGE `propcompassai.prop_compass.users` T
            USING (SELECT
                '{user_id}'      AS user_id,
                '{email}'        AS email,
                '{display_name}' AS display_name,
                '{provider}'     AS provider,
                '{tier}'         AS tier,
                CURRENT_TIMESTAMP() AS created_at,
                CURRENT_TIMESTAMP() AS last_login
            ) S
            ON T.user_id = S.user_id
            WHEN MATCHED THEN
                UPDATE SET last_login = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
                INSERT (user_id, email, display_name, provider, tier, created_at, last_login)
                VALUES (S.user_id, S.email, S.display_name, S.provider, S.tier, S.created_at, S.last_login)
        """
        client.query(query).result()
        logger.info(f"✅ User saved: {email}")
    except Exception as e:
        logger.error(f"BigQuery user save failed: {e}")

def get_user_usage(user_id: str) -> dict:
    """Get user's analysis count for current month."""
    try:
        client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID", "propcompassai"))
        query  = f"""
            SELECT
                u.tier,
                u.display_name,
                u.email,
                COUNT(a.analysis_id) AS analyses_this_month
            FROM `propcompassai.prop_compass.users` u
            LEFT JOIN `propcompassai.prop_compass.user_analyses` a
                ON u.user_id = a.user_id
                AND DATE_TRUNC(CAST(a.analyzed_at AS DATE), MONTH) = DATE_TRUNC(CURRENT_DATE(), MONTH)
            WHERE u.user_id = '{user_id}'
            GROUP BY u.tier, u.display_name, u.email
        """
        results = list(client.query(query).result())
        if results:
            row   = results[0]
            tier  = row["tier"]
            limit = TIER_LIMITS.get(tier, 3)
            used  = row["analyses_this_month"]
            return {
                "tier":          tier,
                "display_name":  row["display_name"],
                "email":         row["email"],
                "used":          used,
                "limit":         limit,
                "remaining":     max(0, limit - used),
                "can_analyze":   used < limit,
            }
        return {"tier": "free", "used": 0, "limit": 3, "remaining": 3, "can_analyze": True}
    except Exception as e:
        logger.error(f"Usage check failed: {e}")
        return {"tier": "free", "used": 0, "limit": 3, "remaining": 3, "can_analyze": True}

def log_analysis(user_id: str, address: str, recommendation: str):
    """Log an analysis to BigQuery for usage tracking."""
    try:
        client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID", "propcompassai"))
        query  = f"""
            INSERT INTO `propcompassai.prop_compass.user_analyses`
            (analysis_id, user_id, address, recommendation, analyzed_at)
            VALUES (
                GENERATE_UUID(),
                '{user_id}',
                '{address[:200]}',
                '{recommendation}',
                CURRENT_TIMESTAMP()
            )
        """
        client.query(query).result()
    except Exception as e:
        logger.error(f"Analysis log failed: {e}")