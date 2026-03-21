"""
fred_pipeline.py
Pulls mortgage rates from FRED API into BigQuery.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID   = os.getenv("GCP_PROJECT_ID")
DATASET      = os.getenv("BQ_DATASET")
FRED_API_KEY = os.getenv("FRED_API_KEY")
TABLE_ID     = f"{PROJECT_ID}.{DATASET}.market_rates"

FRED_SERIES = {
    "mortgage_rate_30yr": "MORTGAGE30US",
    "mortgage_rate_15yr": "MORTGAGE15US",
    "fed_funds_rate":     "FEDFUNDS",
    "inflation_rate":     "CPIAUCSL",
}

def fetch_fred_series(series_id: str) -> dict:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":         series_id,
        "api_key":           FRED_API_KEY,
        "file_type":         "json",
        "observation_start": "2020-01-01",
        "sort_order":        "desc",
        "limit":             100,
    }
    print(f"   Fetching: {series_id}...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code} — {response.text}")
        return {}

    data = response.json()
    result = {}
    for obs in data.get("observations", []):
        if obs["value"] != ".":
            result[obs["date"]] = float(obs["value"])

    print(f"   ✅ Got {len(result)} observations")
    return result


def build_dataframe() -> pd.DataFrame:
    print("\n📊 Fetching data from FRED API...")
    all_series = {}
    for field_name, series_id in FRED_SERIES.items():
        all_series[field_name] = fetch_fred_series(series_id)

    all_dates = set()
    for series_data in all_series.values():
        all_dates.update(series_data.keys())

    rows = []
    for date_str in sorted(all_dates, reverse=True):
        row = {
            "rate_date":          date_str,
            "mortgage_rate_30yr": all_series["mortgage_rate_30yr"].get(date_str),
            "mortgage_rate_15yr": all_series["mortgage_rate_15yr"].get(date_str),
            "fed_funds_rate":     all_series["fed_funds_rate"].get(date_str),
            "inflation_rate":     all_series["inflation_rate"].get(date_str),
            "ingested_at":        datetime.now(timezone.utc).isoformat(),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    print(f"\n✅ Built DataFrame: {len(df)} rows")
    print(f"   Date range: {df['rate_date'].min()} → {df['rate_date'].max()}")
    print(f"   Latest 30yr rate: {df['mortgage_rate_30yr'].iloc[0]}%")
    return df


def load_to_bigquery(df: pd.DataFrame) -> None:
    print(f"\n⬆️  Loading to BigQuery...")
    print(f"   Table: {TABLE_ID}")

    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("rate_date",          "DATE"),
            bigquery.SchemaField("mortgage_rate_30yr", "FLOAT"),
            bigquery.SchemaField("mortgage_rate_15yr", "FLOAT"),
            bigquery.SchemaField("fed_funds_rate",     "FLOAT"),
            bigquery.SchemaField("inflation_rate",     "FLOAT"),
            bigquery.SchemaField("ingested_at",        "TIMESTAMP"),
        ]
    )

    df["rate_date"] = pd.to_datetime(df["rate_date"]).dt.date

    load_job = client.load_table_from_dataframe(
        df, TABLE_ID, job_config=job_config
    )
    load_job.result()

    table = client.get_table(TABLE_ID)
    print(f"   ✅ Loaded successfully!")
    print(f"   ✅ Total rows in BigQuery: {table.num_rows}")


def get_current_mortgage_rate() -> float:
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT mortgage_rate_30yr
        FROM `{TABLE_ID}`
        WHERE mortgage_rate_30yr IS NOT NULL
        ORDER BY rate_date DESC
        LIMIT 1
    """
    result = list(client.query(query).result())
    if result:
        return result[0]["mortgage_rate_30yr"]
    return 7.0


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — FRED Mortgage Rate Pipeline")
    print("=" * 55)

    df = build_dataframe()
    load_to_bigquery(df)

    print("\n🔍 Verifying — Latest rate from BigQuery:")
    rate = get_current_mortgage_rate()
    print(f"   Current 30yr mortgage rate: {rate}%")

    print("\n" + "=" * 55)
    print("  ✅ FRED Pipeline Complete!")
    print("=" * 55)