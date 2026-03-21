"""
hud_pipeline.py
Pulls Fair Market Rent data from HUD (Dept of Housing & Urban Development)
and loads into BigQuery rent_estimates table.

HUD Fair Market Rents = official government rent estimates by zip code
Used by Section 8 housing program — very reliable benchmarks
Free API — just needs registration
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID  = os.getenv("GCP_PROJECT_ID")
DATASET     = os.getenv("BQ_DATASET")
TABLE_ID    = f"{PROJECT_ID}.{DATASET}.rent_estimates"

# HUD API endpoint for Fair Market Rents
# Documentation: https://www.huduser.gov/portal/dataset/fmr-api.html
HUD_BASE_URL = "https://www.huduser.gov/hudapi/public/fmr"

# HUD requires a token — get free one at:
# https://www.huduser.gov/hudapi/public/register/addApp
HUD_TOKEN = os.getenv("HUD_API_TOKEN", "")

def fetch_hud_fmr_by_zip(zip_code: str) -> list:
    """
    Fetch Fair Market Rents for a specific zip code.
    Returns list of rows (one per bedroom count).
    """
    url = f"{HUD_BASE_URL}/byzip/{zip_code}"
    headers = {"Authorization": f"Bearer {HUD_TOKEN}"}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return []

    data = response.json()
    rows = []

    # HUD returns rents for 0-4 bedrooms
    if "data" in data and "basicdata" in data["data"]:
        basic = data["data"]["basicdata"]
        rent_fields = {
            0: "Efficiency",
            1: "One-Bedroom",
            2: "Two-Bedroom",
            3: "Three-Bedroom",
            4: "Four-Bedroom",
        }
        for bedrooms, field_name in rent_fields.items():
            rent_key = field_name.replace("-", "_").lower() + "_fmr"
            # Try different key formats HUD uses
            rent_value = (
                basic.get(f"fmr_{bedrooms}") or
                basic.get(rent_key) or
                basic.get(field_name)
            )
            if rent_value:
                rows.append({
                    "zip_code":    zip_code,
                    "bedrooms":    bedrooms,
                    "rent_low":    float(rent_value) * 0.85,
                    "rent_median": float(rent_value),
                    "rent_high":   float(rent_value) * 1.15,
                    "source":      "HUD_FMR",
                    "ingested_at": datetime.now(timezone.utc),
                })
    return rows


def fetch_hud_fmr_by_state(state_code: str) -> pd.DataFrame:
    """
    Fetch Fair Market Rents for all counties in a state.
    Then maps to zip codes using our neighborhood table.
    More reliable than zip-by-zip for bulk loading.
    """
    url = f"{HUD_BASE_URL}/listCounties/{state_code}"
    headers = {"Authorization": f"Bearer {HUD_TOKEN}"}

    print(f"   Fetching HUD county list for state: {state_code}...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code} — {response.text[:200]}")
        return pd.DataFrame()

    counties = response.json()
    print(f"   ✅ Found {len(counties)} counties")

    all_rows = []
    for county in counties[:20]:  # Limit to 20 counties for speed
        county_id = county.get("fips_code") or county.get("code")
        if not county_id:
            continue

        county_url = f"{HUD_BASE_URL}/data/{county_id}"
        county_response = requests.get(county_url, headers=headers)

        if county_response.status_code != 200:
            continue

        county_data = county_response.json()

        if "data" in county_data and "basicdata" in county_data["data"]:
            basic = county_data["data"]["basicdata"]
            county_name = county.get("county_name", "Unknown")

            for bedrooms in range(5):
                rent_value = basic.get(f"fmr_{bedrooms}")
                if rent_value:
                    all_rows.append({
                        "zip_code":    county_id,
                        "bedrooms":    bedrooms,
                        "rent_low":    float(rent_value) * 0.85,
                        "rent_median": float(rent_value),
                        "rent_high":   float(rent_value) * 1.15,
                        "source":      f"HUD_FMR_{county_name}",
                        "ingested_at": datetime.now(timezone.utc),
                    })

    if all_rows:
        df = pd.DataFrame(all_rows)
        print(f"   ✅ Built {len(df)} rent estimate rows")
        return df
    return pd.DataFrame()


def build_fallback_estimates() -> pd.DataFrame:
    """
    Fallback method — build reasonable rent estimates
    using our Census data already in BigQuery.

    Formula: median_income / 3 / 12 = estimated monthly rent
    (Standard affordability guideline: rent = 30% of income)

    This is used when HUD API is unavailable or during development.
    RentCast API (Week 4) will replace this with real market data.
    """
    print("   Using Census-based fallback rent estimates...")

    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            zip_code,
            median_income,
            vacancy_rate
        FROM `{PROJECT_ID}.prop_compass.neighborhood`
        WHERE median_income IS NOT NULL
          AND median_income > 0
        LIMIT 5000
    """

    df_census = client.query(query).to_dataframe()
    print(f"   ✅ Got {len(df_census)} zip codes from Census")

    rows = []
    for _, row in df_census.iterrows():
        # Base rent estimate from income affordability formula
        base_rent = (row["median_income"] / 12) * 0.30

        # Adjust for vacancy — high vacancy = lower rents
        vacancy_adj = 1.0
        if row["vacancy_rate"] and row["vacancy_rate"] > 20:
            vacancy_adj = 0.85  # High vacancy = 15% lower rents
        elif row["vacancy_rate"] and row["vacancy_rate"] < 5:
            vacancy_adj = 1.15  # Low vacancy = 15% higher rents

        # Generate estimates for each bedroom count
        bedroom_multipliers = {
            0: 0.65,   # Studio = 65% of 1BR
            1: 1.00,   # 1BR = base
            2: 1.35,   # 2BR = 35% more
            3: 1.65,   # 3BR = 65% more
            4: 1.95,   # 4BR = 95% more
        }

        for bedrooms, multiplier in bedroom_multipliers.items():
            estimated_rent = base_rent * multiplier * vacancy_adj
            rows.append({
                "zip_code":    row["zip_code"],
                "bedrooms":    bedrooms,
                "rent_low":    round(estimated_rent * 0.85, 2),
                "rent_median": round(estimated_rent, 2),
                "rent_high":   round(estimated_rent * 1.15, 2),
                "source":      "CENSUS_ESTIMATE",
                "ingested_at": datetime.now(timezone.utc),
            })

    df = pd.DataFrame(rows)
    print(f"   ✅ Generated {len(df)} rent estimates")
    return df


def load_to_bigquery(df: pd.DataFrame) -> None:
    """Load rent estimates to BigQuery."""
    if df.empty:
        print("   ❌ No data to load")
        return

    print(f"\n⬆️  Loading {len(df)} rows to BigQuery...")
    print(f"   Table: {TABLE_ID}")

    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("zip_code",    "STRING"),
            bigquery.SchemaField("bedrooms",    "INTEGER"),
            bigquery.SchemaField("rent_low",    "FLOAT"),
            bigquery.SchemaField("rent_median", "FLOAT"),
            bigquery.SchemaField("rent_high",   "FLOAT"),
            bigquery.SchemaField("source",      "STRING"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
        ]
    )

    load_job = client.load_table_from_dataframe(
        df, TABLE_ID, job_config=job_config
    )
    load_job.result()

    table = client.get_table(TABLE_ID)
    print(f"   ✅ Loaded successfully!")
    print(f"   ✅ Total rows in BigQuery: {table.num_rows}")


def get_rent_estimate(zip_code: str, bedrooms: int) -> dict:
    """
    Helper function — returns rent estimate for a zip/bedroom combo.
    Called by deal calculator to estimate rental income.
    """
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT
            zip_code,
            bedrooms,
            rent_low,
            rent_median,
            rent_high,
            source
        FROM `{TABLE_ID}`
        WHERE zip_code = '{zip_code}'
          AND bedrooms = {bedrooms}
        LIMIT 1
    """
    results = list(client.query(query).result())
    if results:
        row = results[0]
        return {
            "zip_code":    row["zip_code"],
            "bedrooms":    row["bedrooms"],
            "rent_low":    row["rent_low"],
            "rent_median": row["rent_median"],
            "rent_high":   row["rent_high"],
            "source":      row["source"],
        }
    # Fallback if no data found
    return {
        "zip_code":    zip_code,
        "bedrooms":    bedrooms,
        "rent_low":    1200.0,
        "rent_median": 1500.0,
        "rent_high":   1800.0,
        "source":      "DEFAULT_FALLBACK",
    }


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — HUD Rent Estimates Pipeline")
    print("=" * 55)

    # Check if HUD token is available
    if HUD_TOKEN:
        print("\n🔑 HUD token found — trying HUD API...")
        df = fetch_hud_fmr_by_state("NC")
    else:
        print("\n⚠️  No HUD token — using Census-based estimates")
        print("   (This is fine for development!)")
        print("   Get free HUD token at:")
        print("   https://www.huduser.gov/hudapi/public/register/addApp")
        df = build_fallback_estimates()

    # Load to BigQuery
    load_to_bigquery(df)

    # Test the helper function
    print("\n🔍 Testing get_rent_estimate('27601', 2):")
    estimate = get_rent_estimate("27601", 2)
    for key, value in estimate.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 55)
    print("  ✅ HUD Pipeline Complete!")
    print("  Next: Run attom_pipeline.py")
    print("=" * 55)
