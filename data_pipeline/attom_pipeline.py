"""
attom_pipeline.py
Pulls property data from ATTOM API and loads into BigQuery.

ATTOM = largest property data provider in the US
Free tier: 100 API calls/day
Each call returns detailed property info for one address

Two modes:
1. Single property lookup — used by deal analyzer in real time
2. Bulk load — loads multiple properties for ML training data
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
ATTOM_KEY    = os.getenv("ATTOM_API_KEY")
TABLE_ID     = f"{PROJECT_ID}.{DATASET}.property_facts"

# ATTOM API base URL
ATTOM_BASE   = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"

# Headers required for every ATTOM request
HEADERS = {
    "apikey": ATTOM_KEY,
    "accept": "application/json",
}


def fetch_property_by_address(
    address1: str,
    address2: str
) -> dict:
    """
    Fetch property details for a specific address.

    address1 = street address  e.g. "4529 Winona Court"
    address2 = city, state zip e.g. "Denver, CO 80212"

    Returns a clean property dict or empty dict if not found.
    """
    url = f"{ATTOM_BASE}/property/basicprofile"
    params = {
        "address1": address1,
        "address2": address2,
    }

    print(f"   Looking up: {address1}, {address2}...")
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        data = response.json()
        properties = data.get("property", [])
        if properties:
            print(f"   ✅ Found property!")
            return parse_attom_property(properties[0])
        else:
            print(f"   ⚠️  No property found for this address")
            return {}
    elif response.status_code == 401:
        print(f"   ❌ Invalid API key — check your ATTOM_API_KEY in .env")
        return {}
    elif response.status_code == 429:
        print(f"   ❌ Rate limit hit — free tier is 100 calls/day")
        return {}
    else:
        print(f"   ❌ Error {response.status_code}: {response.text[:200]}")
        return {}


def parse_attom_property(raw: dict) -> dict:
    """
    Parse raw ATTOM API response into clean property dict.
    ATTOM returns deeply nested JSON — we flatten what we need.
    """
    # ATTOM nests data in multiple objects
    identifier  = raw.get("identifier",  {})
    address     = raw.get("address",     {})
    lot         = raw.get("lot",         {})
    building    = raw.get("building",    {})
    summary     = raw.get("summary",     {})
    assessment  = raw.get("assessment",  {})
    vintage     = raw.get("vintage",     {})

    # Building details are nested further
    rooms  = building.get("rooms",  {})
    size   = building.get("size",   {})

    # Assessment splits into assessed + market + tax
    assessed = assessment.get("assessed",  {})
    tax      = assessment.get("tax",       {})

    return {
        "attom_id":         str(identifier.get("attomId", "")),
        "address":          address.get("line1", ""),
        "city":             address.get("locality", ""),
        "state":            address.get("countrySubd", ""),
        "zip_code":         address.get("postal1", ""),
        "property_type":    summary.get("proptype", ""),
        "bedrooms":         rooms.get("beds"),
        "bathrooms":        rooms.get("bathstotal"),
        "sqft":             size.get("livingsize"),
        "lot_sqft":         lot.get("lotsize2"),
        "year_built":       summary.get("yearbuilt"),
        "last_sale_price":  None,  # Requires sales history endpoint
        "last_sale_date":   None,  # Requires sales history endpoint
        "assessed_value":   assessed.get("assdttlvalue"),
        "tax_annual":       tax.get("taxamt"),
        "latitude":         raw.get("location", {}).get("latitude"),
        "longitude":        raw.get("location", {}).get("longitude"),
        "ingested_at":      datetime.now(timezone.utc),
    }


def fetch_properties_bulk(addresses: list) -> pd.DataFrame:
    """
    Fetch multiple properties and return as DataFrame.
    Used to build ML training dataset.

    addresses = list of (address1, address2) tuples
    """
    print(f"\n📊 Fetching {len(addresses)} properties from ATTOM...")
    rows = []

    for i, (address1, address2) in enumerate(addresses):
        print(f"   [{i+1}/{len(addresses)}] ", end="")
        prop = fetch_property_by_address(address1, address2)
        if prop:
            rows.append(prop)

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    print(f"\n✅ Successfully fetched {len(df)} properties")
    return df


def load_to_bigquery(df: pd.DataFrame) -> None:
    if df.empty:
        print("   ⚠️  No properties to load")
        return

    print(f"\n⬆️  Loading {len(df)} properties to BigQuery...")

    client = bigquery.Client(project=PROJECT_ID)

    # Convert types before loading
    if "last_sale_date" in df.columns:
        df["last_sale_date"] = pd.to_datetime(
            df["last_sale_date"], errors="coerce"
        ).dt.date

    for col in ["bedrooms", "sqft", "lot_sqft", "year_built"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col], errors="coerce"
            ).astype("Int64")

    for col in ["bathrooms", "last_sale_price",
                "assessed_value", "tax_annual",
                "latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Use autodetect — no schema conflicts possible
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
    )

    load_job = client.load_table_from_dataframe(
        df, TABLE_ID, job_config=job_config
    )
    load_job.result()

    table = client.get_table(TABLE_ID)
    print(f"   ✅ Loaded successfully!")
    print(f"   ✅ Total rows in BigQuery: {table.num_rows}")

def get_property_details(
    address1: str,
    address2: str
) -> dict:
    """
    Main helper function called by deal analyzer.
    1. Check if property already in BigQuery (save API calls)
    2. If not found, fetch from ATTOM API and cache in BigQuery
    3. Return property dict for deal calculation
    """
    client = bigquery.Client(project=PROJECT_ID)

    # Clean address for SQL query
    safe_address = address1.replace("'", "''")

    # Check BigQuery cache first
    query = f"""
        SELECT *
        FROM `{TABLE_ID}`
        WHERE LOWER(address) LIKE LOWER('%{safe_address}%')
        ORDER BY ingested_at DESC
        LIMIT 1
    """

    results = list(client.query(query).result())

    if results:
        print(f"   ✅ Found in BigQuery cache!")
        row = results[0]
        return {
            "attom_id":       row["attom_id"],
            "address":        row["address"],
            "city":           row["city"],
            "state":          row["state"],
            "zip_code":       row["zip_code"],
            "property_type":  row["property_type"],
            "bedrooms":       row["bedrooms"],
            "bathrooms":      row["bathrooms"],
            "sqft":           row["sqft"],
            "year_built":     row["year_built"],
            "assessed_value": row["assessed_value"],
            "tax_annual":     row["tax_annual"],
            "latitude":       row["latitude"],
            "longitude":      row["longitude"],
        }

    # Not in cache — fetch from ATTOM API
    print(f"   Fetching from ATTOM API...")
    prop = fetch_property_by_address(address1, address2)

    if prop:
        # Cache in BigQuery for future lookups
        df = pd.DataFrame([prop])
        load_to_bigquery(df)

    return prop


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — ATTOM Property Pipeline")
    print("=" * 55)

    # Test with real properties in Raleigh NC
    # These are real addresses — good test for your market
    test_properties = [
        ("1 Glenwood Ave",    "Raleigh, NC 27603"),
        ("4217 Six Forks Rd", "Raleigh, NC 27609"),
        ("800 W Morgan St",   "Raleigh, NC 27603"),
        ("105 Old Wisteria Ct", "Holly Springs, NC 27540"),
    ]

    print("\n🔍 Testing single property lookup:")
    prop = get_property_details(
        "105 Old Wisteria Ct",
        "Holly Springs, NC 27540"
    )

    if prop:
        print("\n📋 Property Details:")
        for key, value in prop.items():
            if key != "ingested_at":
                print(f"   {key}: {value}")
    else:
        print("\n⚠️  Property not found")
        print("   This could mean:")
        print("   1. ATTOM API key needs activation (check email)")
        print("   2. Address format needs adjustment")
        print("   3. Property not in ATTOM database")

    print("\n" + "=" * 55)
    print("  ✅ ATTOM Pipeline Complete!")
    print("  Next: Build deal_calculator.py")
    print("=" * 55)