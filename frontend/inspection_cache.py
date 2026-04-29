"""
PropCompassAI — Inspection Report Cache
Saves and retrieves inspection results from BigQuery
Same address + same PDF = same result every time!
"""

import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_bigquery_client():
    """Get BigQuery client using Streamlit secrets."""
    try:
        import streamlit as st
        from google.oauth2 import service_account
        from google.cloud import bigquery
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return bigquery.Client(project="propcompassai", credentials=credentials)
    except Exception as e:
        logger.error(f"BigQuery client failed: {e}")
    return None

def get_pdf_hash(pdf_bytes: bytes) -> str:
    """Generate unique hash for PDF content."""
    return hashlib.md5(pdf_bytes).hexdigest()

def get_cached_result(pdf_bytes: bytes, property_address: str) -> dict:
    """Check BigQuery cache for existing analysis."""
    try:
        client = get_bigquery_client()
        if not client:
            return None

        pdf_hash = get_pdf_hash(pdf_bytes)
        address_clean = property_address.strip().lower()

        query = f"""
            SELECT analysis_json
            FROM `propcompassai.prop_compass.inspection_cache`
            WHERE pdf_hash = '{pdf_hash}'
               OR LOWER(property_address) = '{address_clean}'
            ORDER BY analyzed_at DESC
            LIMIT 1
        """
        rows = list(client.query(query).result())
        if rows:
            logger.info(f"Cache HIT for {property_address}")
            return json.loads(rows[0].analysis_json)

        logger.info(f"Cache MISS for {property_address}")
        return None

    except Exception as e:
        logger.error(f"Cache lookup failed: {e}")
        return None

def save_to_cache(pdf_bytes: bytes, property_address: str,
                  result: dict, purchase_price: float = 0):
    """Save analysis result to BigQuery cache."""
    try:
        client = get_bigquery_client()
        if not client:
            return

        pdf_hash  = get_pdf_hash(pdf_bytes)
        cache_id  = f"{pdf_hash[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        row = {
            "cache_id":        cache_id,
            "property_address": property_address,
            "pdf_hash":        pdf_hash,
            "analysis_json":   json.dumps(result),
            "purchase_price":  purchase_price,
            "analyzed_at":     datetime.utcnow().isoformat(),
            "total_issues":    result.get("total_issues", 0),
            "critical_count":  result.get("critical_count", 0),
            "important_count": result.get("important_count", 0),
            "minor_count":     result.get("minor_count", 0),
            "total_cost_min":  result.get("estimated_total_min", 0),
            "total_cost_max":  result.get("estimated_total_max", 0),
        }

        client.insert_rows_json(
            "propcompassai.prop_compass.inspection_cache",
            [row]
        )
        logger.info(f"Cached inspection result for {property_address}")

    except Exception as e:
        logger.error(f"Cache save failed: {e}")
