"""
PropCompassAI — Inspection Report Cache
Saves and retrieves inspection results from BigQuery
"""

import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_bigquery_client():
    try:
        import streamlit as st
        from google.oauth2 import service_account
        from google.cloud import bigquery
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return bigquery.Client(
                project="propcompassai",
                credentials=credentials
            )
        return bigquery.Client(project="propcompassai")
    except Exception as e:
        logger.error(f"BigQuery client failed: {e}")
        return None

def get_pdf_hash(pdf_bytes: bytes) -> str:
    return hashlib.md5(pdf_bytes).hexdigest()

def get_cached_result(pdf_bytes: bytes, property_address: str) -> dict:
    try:
        client = get_bigquery_client()
        if not client:
            return None
        from google.cloud import bigquery
        pdf_hash = get_pdf_hash(pdf_bytes)
        addr = property_address.strip().lower()
        query = """
            SELECT analysis_json
            FROM `propcompassai.prop_compass.inspection_cache`
            WHERE pdf_hash = @pdf_hash
               OR LOWER(property_address) = @addr
            ORDER BY analyzed_at DESC
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("pdf_hash", "STRING", pdf_hash),
                bigquery.ScalarQueryParameter("addr", "STRING", addr),
            ]
        )
        rows = list(client.query(query, job_config=job_config).result())
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
    try:
        client = get_bigquery_client()
        if not client:
            logger.error("No BigQuery client!")
            return
        pdf_hash = get_pdf_hash(pdf_bytes)
        cache_id = f"{pdf_hash[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        row = {
            "cache_id":           cache_id,
            "property_address":   property_address,
            "pdf_hash":           pdf_hash,
            "analysis_json":      json.dumps(result),
            "purchase_price":     purchase_price,
            "analyzed_at":        datetime.utcnow().isoformat(),
            "total_issues":       result.get("total_issues", 0),
            "critical_count":     result.get("critical_count", 0),
            "important_count":    result.get("important_count", 0),
            "minor_count":        result.get("minor_count", 0),
            "total_cost_min":     result.get("estimated_total_min", 0),
            "total_cost_max":     result.get("estimated_total_max", 0),
        }
        errors = client.insert_rows_json(
            "propcompassai.prop_compass.inspection_cache",
            [row]
        )
        if errors:
            logger.error(f"BigQuery insert errors: {errors}")
        else:
            logger.info(f"Cache saved for: {property_address}")
    except Exception as e:
        logger.error(f"Cache save failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

def get_cached_strategy(pdf_bytes: bytes, property_address: str) -> str:
    try:
        client = get_bigquery_client()
        if not client:
            return None
        pdf_hash = get_pdf_hash(pdf_bytes)
        addr = property_address.strip().lower().replace("'","")
        query = f"""
            SELECT negotiation_strategy
            FROM `propcompassai.prop_compass.inspection_cache`
            WHERE (pdf_hash = '{pdf_hash}'
               OR LOWER(property_address) = '{addr}')
            AND negotiation_strategy IS NOT NULL
            ORDER BY analyzed_at DESC
            LIMIT 1
        """
        rows = list(client.query(query).result())
        if rows and rows[0].negotiation_strategy:
            logger.info(f"Strategy cache HIT for {property_address}")
            return rows[0].negotiation_strategy
        return None
    except Exception as e:
        logger.error(f"Strategy lookup failed: {e}")
        return None

def save_strategy_to_cache(pdf_bytes: bytes, property_address: str,
                            strategy: str):
    try:
        client = get_bigquery_client()
        if not client:
            return
        pdf_hash = get_pdf_hash(pdf_bytes)

        # Use INSERT instead of UPDATE to avoid SQL injection issues
        from datetime import datetime
        cache_id = f"strat_{pdf_hash[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Update existing row using job config with parameters
        query = """
            UPDATE `propcompassai.prop_compass.inspection_cache`
            SET negotiation_strategy = @strategy
            WHERE pdf_hash = @pdf_hash
        """
        from google.cloud import bigquery
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("strategy", "STRING", strategy),
                bigquery.ScalarQueryParameter("pdf_hash", "STRING", pdf_hash),
            ]
        )
        client.query(query, job_config=job_config).result()
        logger.info(f"Strategy saved for: {property_address}")
    except Exception as e:
        logger.error(f"Strategy save failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
