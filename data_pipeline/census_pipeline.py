"""
census_pipeline.py
Pulls neighborhood demographic data from US Census Bureau API
and loads into BigQuery neighborhood table.

Census ACS 5-Year Survey — most reliable demographic data available
Free API — just needs an API key
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID      = os.getenv("GCP_PROJECT_ID")
DATASET         = os.getenv("BQ_DATASET")
CENSUS_API_KEY  = os.getenv("CENSUS_API_KEY")
TABLE_ID        = f"{PROJECT_ID}.{DATASET}.neighborhood"

# Census ACS5 variables we want
# Full list at: api.census.gov/data/2022/acs/acs5/variables.json
CENSUS_VARIABLES = {
    "B19013_001E": "median_income",        # Median household income
    "B01003_001E": "population",           # Total population
    "B01002_001E": "median_age",           # Median age
    "B25002_003E": "vacant_units",         # Vacant housing units
    "B25002_001E": "total_units",          # Total housing units
    "B17001_002E": "poverty_count",        # People below poverty line
    "B25003_002E": "owner_occupied",       # Owner occupied units
    "B25003_001E": "total_occupied",       # Total occupied units
}

# Target zip codes — start with North Carolina (your market)
# Add more states as you expand
TARGET_STATES = ["37"]  # North Carolina FIPS code

def fetch_census_data(state_fips: str) -> list:
    """
    Fetch Census ACS5 data for all zip codes in a state.
    ACS5 = American Community Survey 5-year estimates
    Most reliable demographic data available for free.
    """
    variables = ",".join(CENSUS_VARIABLES.keys())
    url = f"https://api.census.gov/data/2022/acs/acs5"

    params = {
        "get":  f"NAME,{variables}",
        "for":  "zip code tabulation area:*",  # All zip codes
        "key":  CENSUS_API_KEY,
    }

    print(f"   Fetching Census data for state FIPS: {state_fips}...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return []

    data = response.json()
    print(f"   ✅ Got {len(data) - 1} zip codes")
    return data


def parse_census_response(raw_data: list) -> pd.DataFrame:
    """
    Census API returns data as a list of lists.
    First row is headers, rest are data rows.
    Convert to clean DataFrame with calculated fields.
    """
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame()

    # First row is headers
    headers = raw_data[0]
    rows    = raw_data[1:]

    # Build DataFrame
    df = pd.DataFrame(rows, columns=headers)

    # Rename Census variable codes to readable names
    rename_map = {
        "zip code tabulation area": "zip_code",
        "NAME":                     "name",
        "state":                    "state_fips",
    }
    rename_map.update({k: v for k, v in CENSUS_VARIABLES.items()})
    df = df.rename(columns=rename_map)

    # Convert numeric columns from strings to numbers
    numeric_cols = list(CENSUS_VARIABLES.values())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace negative values with None
    # Census uses -666666666 for missing data
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].where(df[col] >= 0, other=None)

    # ── Calculate derived fields ──────────────────────────────────
    # Vacancy rate = vacant units / total units
    df["vacancy_rate"] = (
        df["vacant_units"] / df["total_units"] * 100
    ).round(2)

    # Poverty rate = poverty count / population
    df["poverty_rate"] = (
        df["poverty_count"] / df["population"] * 100
    ).round(2)

    # Owner occupied % = owner occupied / total occupied
    df["owner_occupied_pct"] = (
        df["owner_occupied"] / df["total_occupied"] * 100
    ).round(2)

    # Population growth — we don't have historical data yet
    # Will update this in Week 4 when we add FHFA data
    df["population_growth"] = None

    # Add state abbreviation
    df["state"] = "NC"
    df["city"]  = None  # Will enrich later

    # Add ingestion timestamp
    df["ingested_at"] = datetime.now(timezone.utc)

    # Keep only the columns we need for BigQuery
    final_cols = [
        "zip_code", "city", "state",
        "median_income", "population", "population_growth",
        "median_age", "owner_occupied_pct",
        "vacancy_rate", "poverty_rate",
        "ingested_at"
    ]
    df = df[final_cols]

    # Drop rows where zip_code is missing
    df = df.dropna(subset=["zip_code"])

    print(f"   ✅ Parsed {len(df)} zip codes")
    print(f"   Sample zip codes: {df['zip_code'].head(3).tolist()}")

    return df


def load_to_bigquery(df: pd.DataFrame) -> None:
    """
    Load neighborhood data to BigQuery.
    Uses WRITE_TRUNCATE — replaces all data each run
    so we always have the latest Census data.
    """
    if df.empty:
        print("   ❌ No data to load")
        return

    print(f"\n⬆️  Loading {len(df)} zip codes to BigQuery...")
    print(f"   Table: {TABLE_ID}")

    client = bigquery.Client(project=PROJECT_ID)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("zip_code",           "STRING"),
            bigquery.SchemaField("city",               "STRING"),
            bigquery.SchemaField("state",              "STRING"),
            bigquery.SchemaField("median_income",      "FLOAT"),
            bigquery.SchemaField("population",         "INTEGER"),
            bigquery.SchemaField("population_growth",  "FLOAT"),
            bigquery.SchemaField("median_age",         "FLOAT"),
            bigquery.SchemaField("owner_occupied_pct", "FLOAT"),
            bigquery.SchemaField("vacancy_rate",       "FLOAT"),
            bigquery.SchemaField("poverty_rate",       "FLOAT"),
            bigquery.SchemaField("ingested_at",        "TIMESTAMP"),
        ]
    )

    # Convert population to integer safely
    df["population"] = pd.to_numeric(
        df["population"], errors="coerce"
    ).astype("Int64")

    load_job = client.load_table_from_dataframe(
        df, TABLE_ID, job_config=job_config
    )
    load_job.result()

    table = client.get_table(TABLE_ID)
    print(f"   ✅ Loaded successfully!")
    print(f"   ✅ Total rows in BigQuery: {table.num_rows}")


def get_neighborhood_score(zip_code: str) -> dict:
    """
    Helper function — returns neighborhood data for a zip code.
    Called by the deal analyzer to score a property's location.
    """
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT
            zip_code,
            median_income,
            population,
            vacancy_rate,
            poverty_rate,
            owner_occupied_pct,
            median_age
        FROM `{TABLE_ID}`
        WHERE zip_code = '{zip_code}'
        LIMIT 1
    """
    results = list(client.query(query).result())
    if results:
        row = results[0]
        return {
            "zip_code":           row["zip_code"],
            "median_income":      row["median_income"],
            "population":         row["population"],
            "vacancy_rate":       row["vacancy_rate"],
            "poverty_rate":       row["poverty_rate"],
            "owner_occupied_pct": row["owner_occupied_pct"],
            "median_age":         row["median_age"],
        }
    return {}


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — Census Neighborhood Pipeline")
    print("=" * 55)

    all_dfs = []

    for state_fips in TARGET_STATES:
        print(f"\n📊 Processing state FIPS: {state_fips}")
        raw_data = fetch_census_data(state_fips)
        if raw_data:
            df = parse_census_response(raw_data)
            if not df.empty:
                all_dfs.append(df)

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        print(f"\n✅ Total zip codes: {len(final_df)}")

        # Show sample data
        print("\n📋 Sample neighborhood data:")
        sample = final_df[
            ["zip_code", "median_income", "vacancy_rate", "poverty_rate"]
        ].head(5)
        print(sample.to_string(index=False))

        load_to_bigquery(final_df)

        # Test the helper function
        test_zip = final_df["zip_code"].iloc[0]
        print(f"\n🔍 Testing get_neighborhood_score('{test_zip}'):")
        score_data = get_neighborhood_score(test_zip)
        for key, value in score_data.items():
            print(f"   {key}: {value}")
    else:
        print("❌ No data fetched — check your Census API key")

    print("\n" + "=" * 55)
    print("  ✅ Census Pipeline Complete!")
    print("  Next: Run attom_pipeline.py")
    print("=" * 55)