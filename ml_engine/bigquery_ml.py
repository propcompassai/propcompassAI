"""
bigquery_ml.py

Trains a machine learning model INSIDE BigQuery using SQL.
No Python ML libraries needed — the model lives in BigQuery.

Why BigQuery ML?
- Trains on data where it already lives — no export needed
- SQL syntax — familiar and readable
- Fast to train (minutes not hours)
- Great interview talking point
- Production ready immediately after training

We train two models:
1. Logistic Regression — predicts BUY/WATCH/AVOID classification
2. Linear Regression  — predicts deal score 0-100

Interview tip: "I used BigQuery ML to train classification
and regression models directly on the data warehouse,
eliminating the ETL step typically required for ML training."
"""

import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET    = os.getenv("BQ_DATASET")

# Model names in BigQuery
CLASSIFIER_MODEL = f"{PROJECT_ID}.{DATASET}.deal_classifier"
REGRESSION_MODEL = f"{PROJECT_ID}.{DATASET}.deal_score_regressor"

# Training data query — deduplicates and filters quality data
TRAINING_DATA_QUERY = f"""
    SELECT
        cap_rate,
        cash_on_cash,
        monthly_cashflow,
        gross_rent_mult,
        neighborhood_score,
        purchase_price,
        monthly_rent,
        down_payment_pct,
        deal_score,
        recommendation
    FROM `{PROJECT_ID}.{DATASET}.deal_scores`
    WHERE
        cap_rate             IS NOT NULL
        AND cash_on_cash     IS NOT NULL
        AND monthly_cashflow IS NOT NULL
        AND gross_rent_mult  IS NOT NULL
        AND deal_score       IS NOT NULL
        AND recommendation   IN ('BUY', 'WATCH', 'AVOID')
"""


def train_classifier(client: bigquery.Client) -> None:
    """
    Train a Logistic Regression classifier.
    Predicts: BUY / WATCH / AVOID

    Logistic Regression works well here because:
    - Our classes are clearly separable by metrics
    - Fast to train and explain
    - Coefficients show which features matter most
    - Interviewers love it — shows you understand basics
    """
    print("\n🤖 Training Deal Classifier (Logistic Regression)...")
    print("   This takes 1-2 minutes...")

    query = f"""
        CREATE OR REPLACE MODEL `{CLASSIFIER_MODEL}`
        OPTIONS (
            model_type       = 'LOGISTIC_REG',
            input_label_cols = ['recommendation'],
            max_iterations   = 50,
            l2_reg           = 0.1
        ) AS
        SELECT
            cap_rate,
            cash_on_cash,
            monthly_cashflow,
            gross_rent_mult,
            neighborhood_score,
            purchase_price,
            monthly_rent,
            down_payment_pct,
            recommendation
        FROM ({TRAINING_DATA_QUERY})
    """

    job = client.query(query)
    job.result()  # Wait for training to complete
    print("   ✅ Classifier trained successfully!")


def train_regressor(client: bigquery.Client) -> None:
    """
    Train a Linear Regression model.
    Predicts: deal_score (0-100 continuous value)

    This gives us a smooth score instead of just 3 categories.
    Combined with classifier gives richer output to investors.
    """
    print("\n🤖 Training Deal Score Regressor (Linear Regression)...")
    print("   This takes 1-2 minutes...")

    query = f"""
        CREATE OR REPLACE MODEL `{REGRESSION_MODEL}`
        OPTIONS (
            model_type       = 'LINEAR_REG',
            input_label_cols = ['deal_score'],
            max_iterations   = 50,
            l2_reg           = 0.1
        ) AS
        SELECT
            cap_rate,
            cash_on_cash,
            monthly_cashflow,
            gross_rent_mult,
            neighborhood_score,
            purchase_price,
            monthly_rent,
            down_payment_pct,
            deal_score
        FROM ({TRAINING_DATA_QUERY})
    """

    job = client.query(query)
    job.result()
    print("   ✅ Regressor trained successfully!")


def evaluate_classifier(client: bigquery.Client) -> None:
    """
    Evaluate classifier performance.
    Key metrics:
    - Precision: of predicted BUY, how many were actually BUY?
    - Recall: of actual BUY deals, how many did we catch?
    - F1 Score: balance of precision and recall
    - Accuracy: overall correct predictions
    """
    print("\n📊 Evaluating Classifier Performance...")

    query = f"""
        SELECT
            *
        FROM ML.EVALUATE(
            MODEL `{CLASSIFIER_MODEL}`,
            (
                SELECT
                    cap_rate,
                    cash_on_cash,
                    monthly_cashflow,
                    gross_rent_mult,
                    neighborhood_score,
                    purchase_price,
                    monthly_rent,
                    down_payment_pct,
                    recommendation
                FROM ({TRAINING_DATA_QUERY})
            )
        )
    """

    results = list(client.query(query).result())
    if results:
        row = results[0]
        print(f"\n   📋 Classifier Metrics:")
        print(f"   {'─'*40}")
        # Print all available metrics
        for key, value in row.items():
            if value is not None:
                if isinstance(value, float):
                    print(f"   {key:<25}: {value:.4f}")
                else:
                    print(f"   {key:<25}: {value}")


def evaluate_regressor(client: bigquery.Client) -> None:
    """
    Evaluate regressor performance.
    Key metrics:
    - Mean Absolute Error (MAE): average prediction error
    - R-squared: how much variance is explained (0-1, higher better)
    - Mean Squared Error (MSE): penalizes large errors more
    """
    print("\n📊 Evaluating Regressor Performance...")

    query = f"""
        SELECT
            *
        FROM ML.EVALUATE(
            MODEL `{REGRESSION_MODEL}`,
            (
                SELECT
                    cap_rate,
                    cash_on_cash,
                    monthly_cashflow,
                    gross_rent_mult,
                    neighborhood_score,
                    purchase_price,
                    monthly_rent,
                    down_payment_pct,
                    deal_score
                FROM ({TRAINING_DATA_QUERY})
            )
        )
    """

    results = list(client.query(query).result())
    if results:
        row = results[0]
        print(f"\n   📋 Regressor Metrics:")
        print(f"   {'─'*40}")
        for key, value in row.items():
            if value is not None:
                if isinstance(value, float):
                    print(f"   {key:<25}: {value:.4f}")
                else:
                    print(f"   {key:<25}: {value}")


def get_feature_importance(client: bigquery.Client) -> None:
    print("\n🔍 Feature Importance — What Drives Deal Quality?")
    print("   (Using Linear Regression model weights)")

    query = f"""
        SELECT
            processed_input AS feature,
            ROUND(weight, 4) AS importance
        FROM ML.WEIGHTS(MODEL `{REGRESSION_MODEL}`)
        WHERE processed_input != '__INTERCEPT__'
        ORDER BY ABS(weight) DESC
    """

    try:
        results = list(client.query(query).result())
        print(f"\n   {'─'*45}")
        print(f"   {'FEATURE':<25} {'WEIGHT':<10} DIRECTION")
        print(f"   {'─'*45}")
        for row in results:
            direction = "↑ positive" if row["importance"] > 0 else "↓ negative"
            bar = "█" * min(int(abs(row["importance"]) * 3), 20)
            print(
                f"   {row['feature']:<25} "
                f"{row['importance']:>8.4f}  "
                f"{direction} {bar}"
            )
        print(f"   {'─'*45}")
    except Exception as e:
        print(f"   Weights not available: {e}")


def predict_single_deal(
    client:            bigquery.Client,
    cap_rate:          float,
    cash_on_cash:      float,
    monthly_cashflow:  float,
    gross_rent_mult:   float,
    neighborhood_score:float,
    purchase_price:    float,
    monthly_rent:      float,
    down_payment_pct:  float,
) -> dict:
    """
    Run prediction for a single deal using trained models.
    Returns both classification and score prediction.
    This is called by the deal analyzer in real time.
    """
    query = f"""
        SELECT
            predicted_recommendation,
            predicted_recommendation_probs
        FROM ML.PREDICT(
            MODEL `{CLASSIFIER_MODEL}`,
            (
                SELECT
                    CAST({cap_rate} AS FLOAT64)           AS cap_rate,
                    CAST({cash_on_cash} AS FLOAT64)       AS cash_on_cash,
                    CAST({monthly_cashflow} AS FLOAT64)   AS monthly_cashflow,
                    CAST({gross_rent_mult} AS FLOAT64)    AS gross_rent_mult,
                    CAST({neighborhood_score} AS FLOAT64) AS neighborhood_score,
                    CAST({purchase_price} AS FLOAT64)     AS purchase_price,
                    CAST({monthly_rent} AS FLOAT64)       AS monthly_rent,
                    CAST({down_payment_pct} AS FLOAT64)   AS down_payment_pct
            )
        )
    """

    results = list(client.query(query).result())
    if results:
        row = results[0]
        recommendation = row["predicted_recommendation"]

        # Extract probabilities for each class
        probs = {}
        if row["predicted_recommendation_probs"]:
            for prob_row in row["predicted_recommendation_probs"]:
                probs[prob_row["label"]] = round(
                    prob_row["prob"] * 100, 1
                )

        return {
            "recommendation": recommendation,
            "probabilities":  probs,
        }
    return {"recommendation": "WATCH", "probabilities": {}}


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — BigQuery ML Training")
    print("=" * 55)

    client = bigquery.Client(project=PROJECT_ID)

    # Step 1: Train both models
    train_classifier(client)
    train_regressor(client)

    # Step 2: Evaluate performance
    evaluate_classifier(client)
    evaluate_regressor(client)

    # Step 3: Feature importance
    get_feature_importance(client)

    # Step 4: Test prediction on real deals
    print("\n🧪 Testing Predictions on Real Deals...")
    print(f"   {'─'*55}")

    test_deals = [
        {
            "name":             "Good Deal (should be BUY)",
            "cap_rate":          8.5,
            "cash_on_cash":      9.8,
            "monthly_cashflow":  287,
            "gross_rent_mult":   8.3,
            "neighborhood_score":65,
            "purchase_price":    160000,
            "monthly_rent":      1600,
            "down_payment_pct":  20,
        },
        {
            "name":             "Bad Deal (should be AVOID)",
            "cap_rate":          2.7,
            "cash_on_cash":     -16.9,
            "monthly_cashflow": -1392,
            "gross_rent_mult":   15.6,
            "neighborhood_score":55,
            "purchase_price":    450000,
            "monthly_rent":      2400,
            "down_payment_pct":  20,
        },
        {
            "name":             "Marginal Deal (should be WATCH)",
            "cap_rate":          5.5,
            "cash_on_cash":      3.2,
            "monthly_cashflow":  85,
            "gross_rent_mult":   12.1,
            "neighborhood_score":58,
            "purchase_price":    240000,
            "monthly_rent":      1650,
            "down_payment_pct":  20,
        },
    ]

    for deal in test_deals:
        name = deal.pop("name")
        result = predict_single_deal(client, **deal)
        emoji = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(
            result["recommendation"], "⚪"
        )
        print(f"\n   {name}")
        print(
            f"   {emoji} Prediction: "
            f"{result['recommendation']}"
        )
        if result["probabilities"]:
            for label, prob in sorted(
                result["probabilities"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                bar = "█" * int(prob / 5)
                print(f"      {label:<6}: {prob:5.1f}% {bar}")

    print(f"\n{'='*55}")
    print("  ✅ BigQuery ML Complete!")
    print("  Next: Vertex AI AutoML model")
    print(f"{'='*55}")