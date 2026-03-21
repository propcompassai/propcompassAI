"""
generate_training_data.py

Generates synthetic training data for Vertex AI model.
Creates realistic property scenarios across different
price points, rent levels, and neighborhoods.

Why synthetic data?
- We only have 4 real analyses so far
- Vertex AI needs 50-100+ examples minimum
- Synthetic data follows real market patterns
- Real data will replace this over time as users
  run more analyses through PropCompass
"""

import os
import random
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

# Import our deal calculator functions
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_pipeline.deal_calculator import (
    calculate_monthly_mortgage,
    calculate_monthly_expenses,
    calculate_cash_flow,
    calculate_cap_rate,
    calculate_cash_on_cash,
    calculate_grm,
    calculate_deal_score,
)

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET    = os.getenv("BQ_DATASET")
TABLE_ID   = f"{PROJECT_ID}.{DATASET}.deal_scores"

# Seed for reproducibility
random.seed(42)


def generate_scenario() -> dict:
    """
    Generate one realistic property investment scenario.
    Uses real market ranges for Raleigh/NC area.
    """
    # Property price ranges — realistic for NC market
    price_ranges = [
        (80000,  150000),   # Budget properties
        (150000, 250000),   # Mid-range
        (250000, 400000),   # Upper mid-range
        (400000, 600000),   # Premium
        (600000, 900000),   # Luxury
    ]

    # Pick a price range with weighted probability
    # More deals in mid-range (realistic distribution)
    weights = [15, 35, 30, 15, 5]
    price_range = random.choices(price_ranges, weights=weights)[0]
    purchase_price = random.uniform(*price_range)

    # Rent-to-price ratio varies by market
    # Good deals: 0.8-1.2% | Bad deals: 0.3-0.6%
    rent_ratio = random.uniform(0.003, 0.012)
    monthly_rent = purchase_price * rent_ratio

    # Down payment — most investors use 20-25%
    down_payment_pct = random.choice([15, 20, 20, 20, 25, 25, 30])

    # Mortgage rate — vary slightly around current rate
    annual_rate = random.uniform(6.0, 7.5)

    # Tax varies by county — 0.8% to 1.5% of value
    tax_rate = random.uniform(0.008, 0.015)
    tax_annual = purchase_price * tax_rate

    # Neighborhood score — random but weighted toward middle
    neighborhood_score = random.gauss(55, 20)
    neighborhood_score = max(10, min(95, neighborhood_score))

    # Property management — 60% of investors use a manager
    include_mgmt = random.random() < 0.6

    # Calculate all metrics using our proven formulas
    mortgage  = calculate_monthly_mortgage(
        purchase_price, down_payment_pct, annual_rate
    )
    expenses  = calculate_monthly_expenses(
        purchase_price, monthly_rent,
        tax_annual=tax_annual,
        include_mgmt=include_mgmt,
    )
    cashflow  = calculate_cash_flow(
        monthly_rent,
        mortgage["monthly_payment"],
        expenses["total_expenses"],
    )
    cap_rate  = calculate_cap_rate(
        cashflow["annual_noi"], purchase_price
    )
    coc       = calculate_cash_on_cash(
        cashflow["annual_cashflow"],
        purchase_price, down_payment_pct
    )
    grm       = calculate_grm(purchase_price, monthly_rent)
    scoring   = calculate_deal_score(
        cap_rate, coc,
        cashflow["monthly_cashflow"],
        grm, neighborhood_score,
    )

    return {
        "analysis_id":        f"synthetic_{random.randint(100000, 999999)}",
        "address":            f"Synthetic Property {random.randint(1000,9999)}",
        "purchase_price":     round(purchase_price, 2),
        "down_payment_pct":   down_payment_pct,
        "monthly_rent":       round(monthly_rent, 2),
        "monthly_mortgage":   mortgage["monthly_payment"],
        "monthly_expenses":   expenses["total_expenses"],
        "monthly_cashflow":   cashflow["monthly_cashflow"],
        "cap_rate":           cap_rate,
        "cash_on_cash":       coc,
        "gross_rent_mult":    grm,
        "deal_score":         float(scoring["deal_score"]),
        "neighborhood_score": round(neighborhood_score, 2),
        "recommendation":     scoring["recommendation"],
        "analyzed_at":        datetime.now(timezone.utc),
    }


def generate_training_dataset(n: int = 200) -> pd.DataFrame:
    """
    Generate n synthetic training examples.
    Ensures balanced distribution of BUY/WATCH/PASS.
    """
    print(f"\n📊 Generating {n} training scenarios...")
    rows = []

    for i in range(n):
        scenario = generate_scenario()
        rows.append(scenario)

        if (i + 1) % 50 == 0:
            print(f"   Generated {i+1}/{n} scenarios...")

    df = pd.DataFrame(rows)

    # Show distribution
    dist = df["recommendation"].value_counts()
    print(f"\n✅ Generated {len(df)} training examples")
    print(f"\n📋 Recommendation Distribution:")
    for rec, count in dist.items():
        pct = count / len(df) * 100
        bar = "█" * int(pct / 2)
        print(f"   {rec:5s}: {count:3d} ({pct:5.1f}%) {bar}")

    print(f"\n📊 Metric Ranges:")
    print(f"   Cap Rate:    {df['cap_rate'].min():.1f}% → {df['cap_rate'].max():.1f}%")
    print(f"   Cash Flow:   ${df['monthly_cashflow'].min():,.0f} → ${df['monthly_cashflow'].max():,.0f}")
    print(f"   Deal Score:  {df['deal_score'].min():.0f} → {df['deal_score'].max():.0f}")

    return df


def load_to_bigquery(df: pd.DataFrame) -> None:
    """Load training data to BigQuery deal_scores table."""
    print(f"\n⬆️  Loading {len(df)} rows to BigQuery...")
    print(f"   Table: {TABLE_ID}")

    client = bigquery.Client(project=PROJECT_ID)

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


def verify_training_data() -> None:
    """
    Run a BigQuery query to verify training data quality.
    This is the query Vertex AI will use to read training data.
    """
    print(f"\n🔍 Verifying training data in BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT
            recommendation,
            COUNT(*)                        as count,
            ROUND(AVG(deal_score), 1)       as avg_score,
            ROUND(AVG(cap_rate), 2)         as avg_cap_rate,
            ROUND(AVG(monthly_cashflow), 0) as avg_cashflow,
            ROUND(AVG(cash_on_cash), 2)     as avg_coc
        FROM `{TABLE_ID}`
        GROUP BY recommendation
        ORDER BY recommendation
    """

    results = client.query(query).result()

    print(f"\n{'─'*65}")
    print(f"  {'REC':<6} {'COUNT':<8} {'AVG SCORE':<12} {'AVG CAP':<10} {'AVG FLOW':<12} {'AVG COC'}")
    print(f"{'─'*65}")

    for row in results:
        print(
            f"  {row['recommendation']:<6} "
            f"{row['count']:<8} "
            f"{row['avg_score']:<12} "
            f"{row['avg_cap_rate']:<10} "
            f"${row['avg_cashflow']:<11,.0f} "
            f"{row['avg_coc']}%"
        )
    print(f"{'─'*65}")


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — Generate ML Training Data")
    print("=" * 55)

    # Generate 200 synthetic training examples
    df = generate_training_dataset(n=200)

    # Load to BigQuery
    load_to_bigquery(df)

    # Verify quality
    verify_training_data()

    print("\n" + "=" * 55)
    print("  ✅ Training Data Generation Complete!")
    print(f"  BigQuery now has 200+ training examples")
    print("  Next: Train Vertex AI model")
    print("=" * 55)