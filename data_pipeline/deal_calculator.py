"""
deal_calculator.py

The financial brain of PropCompass.
Takes property details + market data and calculates
every investment metric an investor needs.

All formulas here are standard real estate investment math.
Knowing these cold is also excellent for interviews with
PropTech companies.
"""

import os
import math
from datetime import datetime, timezone
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
DATASET    = os.getenv("BQ_DATASET")


# ── Formula 1: Monthly Mortgage Payment ──────────────────────────
def calculate_monthly_mortgage(
    purchase_price:   float,
    down_payment_pct: float,
    annual_rate:      float,
    loan_years:       int = 30
) -> dict:
    """
    Calculate monthly mortgage payment using standard amortization.

    Formula: M = P × [r(1+r)^n] / [(1+r)^n - 1]

    Where:
        M = monthly payment
        P = loan principal (purchase price - down payment)
        r = monthly interest rate (annual rate / 12)
        n = total number of payments (years × 12)

    Example:
        $300,000 home, 20% down, 6.5% rate, 30 years
        P = $240,000
        r = 0.065/12 = 0.00542
        n = 360
        M = $1,517/month
    """
    loan_amount   = purchase_price * (1 - down_payment_pct / 100)
    monthly_rate  = annual_rate / 100 / 12
    num_payments  = loan_years * 12

    if monthly_rate == 0:
        monthly_payment = loan_amount / num_payments
    else:
        monthly_payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** num_payments
        ) / (
            (1 + monthly_rate) ** num_payments - 1
        )

    return {
        "loan_amount":      round(loan_amount, 2),
        "monthly_payment":  round(monthly_payment, 2),
        "total_paid":       round(monthly_payment * num_payments, 2),
        "total_interest":   round(
            monthly_payment * num_payments - loan_amount, 2
        ),
    }


# ── Formula 2: Monthly Expenses ──────────────────────────────────
def calculate_monthly_expenses(
    purchase_price:  float,
    monthly_rent:    float,
    tax_annual:      float = None,
    insurance_rate:  float = 0.5,    # % of purchase price annually
    vacancy_rate:    float = 8.0,    # % of rent lost to vacancy
    maintenance_rate:float = 1.0,    # % of purchase price annually
    mgmt_rate:       float = 8.0,    # % of rent for property mgmt
    include_mgmt:    bool  = True,
) -> dict:
    """
    Calculate all monthly operating expenses.

    Standard expense estimates for buy-and-hold investing:
    - Insurance:    0.5% of purchase price per year
    - Vacancy:      8% of gross rent (about 1 month/year empty)
    - Maintenance:  1% of purchase price per year
    - Management:   8-10% of rent (if using property manager)
    - Property tax: use actual from ATTOM or estimate 1.2%/year

    These are industry-standard estimates used by investors
    when actual numbers aren't available.
    """
    # Property tax monthly
    if tax_annual and tax_annual > 0:
        tax_monthly = tax_annual / 12
    else:
        # Estimate: 1.2% of purchase price annually
        tax_monthly = purchase_price * 0.012 / 12

    # Insurance monthly
    insurance_monthly = purchase_price * (insurance_rate / 100) / 12

    # Vacancy loss monthly
    vacancy_monthly = monthly_rent * (vacancy_rate / 100)

    # Maintenance monthly
    maintenance_monthly = purchase_price * (maintenance_rate / 100) / 12

    # Property management monthly
    mgmt_monthly = monthly_rent * (mgmt_rate / 100) if include_mgmt else 0

    total_expenses = (
        tax_monthly +
        insurance_monthly +
        vacancy_monthly +
        maintenance_monthly +
        mgmt_monthly
    )

    return {
        "tax_monthly":         round(tax_monthly, 2),
        "insurance_monthly":   round(insurance_monthly, 2),
        "vacancy_monthly":     round(vacancy_monthly, 2),
        "maintenance_monthly": round(maintenance_monthly, 2),
        "mgmt_monthly":        round(mgmt_monthly, 2),
        "total_expenses":      round(total_expenses, 2),
    }


# ── Formula 3: Cash Flow ──────────────────────────────────────────
def calculate_cash_flow(
    monthly_rent:    float,
    monthly_mortgage:float,
    monthly_expenses:float,
) -> dict:
    """
    Monthly cash flow = Rent - Mortgage - Expenses

    Positive = money in your pocket every month ✅
    Negative = you pay out of pocket every month ❌

    Also calculates NOI (Net Operating Income):
    NOI = Annual Rent - Annual Expenses (before mortgage)
    Used to calculate cap rate.
    """
    monthly_noi      = monthly_rent - monthly_expenses
    monthly_cashflow = monthly_rent - monthly_mortgage - monthly_expenses
    annual_noi       = monthly_noi * 12
    annual_cashflow  = monthly_cashflow * 12

    return {
        "monthly_noi":      round(monthly_noi, 2),
        "monthly_cashflow": round(monthly_cashflow, 2),
        "annual_noi":       round(annual_noi, 2),
        "annual_cashflow":  round(annual_cashflow, 2),
    }


# ── Formula 4: Cap Rate ───────────────────────────────────────────
def calculate_cap_rate(
    annual_noi:     float,
    purchase_price: float,
) -> float:
    """
    Cap Rate = (Annual NOI / Purchase Price) × 100

    Measures return on investment ignoring financing.
    Higher = better investment.

    Rules of thumb:
    - Below 4%:  Usually overpriced or low-growth market
    - 4% - 6%:  Stable market, lower risk
    - 6% - 8%:  Good investment market ✅
    - Above 8%: High return but often higher risk area

    Cap rate is the most important single metric for
    comparing investment properties.
    """
    if purchase_price <= 0:
        return 0.0
    return round((annual_noi / purchase_price) * 100, 2)


# ── Formula 5: Cash-on-Cash Return ───────────────────────────────
def calculate_cash_on_cash(
    annual_cashflow:  float,
    purchase_price:   float,
    down_payment_pct: float,
) -> float:
    """
    Cash-on-Cash Return = (Annual Cash Flow / Cash Invested) × 100

    Measures return on YOUR actual cash investment (down payment).
    More relevant than cap rate for leveraged investors.

    Cash invested = down payment + closing costs
    We estimate closing costs as 2% of purchase price.

    Rules of thumb:
    - Below 4%:   Poor return — better off in index funds
    - 4% - 8%:   Acceptable ✅
    - 8% - 12%:  Good ✅✅
    - Above 12%: Excellent ✅✅✅
    """
    down_payment   = purchase_price * (down_payment_pct / 100)
    closing_costs  = purchase_price * 0.02   # Estimate 2% closing costs
    cash_invested  = down_payment + closing_costs

    if cash_invested <= 0:
        return 0.0
    return round((annual_cashflow / cash_invested) * 100, 2)


# ── Formula 6: Gross Rent Multiplier ─────────────────────────────
def calculate_grm(
    purchase_price: float,
    monthly_rent:   float,
) -> float:
    """
    GRM = Purchase Price / Annual Rent

    Quick way to compare properties without detailed analysis.
    Lower GRM = better deal.

    Rules of thumb:
    - Below 8:   Excellent deal ✅✅✅
    - 8 - 12:    Good deal ✅✅
    - 12 - 15:   Fair deal ✅
    - Above 15:  Likely overpriced ❌

    Used as a quick screening tool before deeper analysis.
    """
    annual_rent = monthly_rent * 12
    if annual_rent <= 0:
        return 0.0
    return round(purchase_price / annual_rent, 2)


# ── Formula 7: 5-Year Projection ─────────────────────────────────
def calculate_five_year_projection(
    purchase_price:   float,
    monthly_cashflow: float,
    annual_cashflow:  float,
    appreciation_rate:float = 3.5,  # Average US appreciation
    rent_growth_rate: float = 2.5,  # Average rent growth
) -> list:
    """
    Project property value and cash flow over 5 years.

    Assumes:
    - Property appreciates at appreciation_rate % per year
    - Rent grows at rent_growth_rate % per year
    - Expenses grow at 2% per year (inflation)

    Returns list of yearly snapshots.
    """
    projections = []
    current_value    = purchase_price
    current_cashflow = annual_cashflow

    for year in range(1, 6):
        current_value    *= (1 + appreciation_rate / 100)
        current_cashflow *= (1 + rent_growth_rate / 100)

        projections.append({
            "year":              year,
            "property_value":    round(current_value, 2),
            "annual_cashflow":   round(current_cashflow, 2),
            "total_appreciation":round(current_value - purchase_price, 2),
        })

    return projections


# ── Formula 8: Deal Score ─────────────────────────────────────────
def calculate_deal_score(
    cap_rate:          float,
    cash_on_cash:      float,
    monthly_cashflow:  float,
    grm:               float,
    neighborhood_score:float = 50.0,
) -> dict:
    """
    Proprietary deal score 0-100 combining all metrics.
    This is our AI-like scoring before Vertex AI model is trained.
    Week 3 will replace this with a trained ML model.

    Scoring weights:
    - Cash flow positive:  25 points
    - Cap rate:            25 points
    - Cash-on-cash:        20 points
    - GRM:                 15 points
    - Neighborhood:        15 points
    """
    score = 0
    reasons = []

    # ── Cash Flow Score (25 points) ───────────────────────────────
    if monthly_cashflow >= 500:
        score += 25
        reasons.append(f"Strong cash flow: ${monthly_cashflow:,.0f}/mo")
    elif monthly_cashflow >= 200:
        score += 18
        reasons.append(f"Positive cash flow: ${monthly_cashflow:,.0f}/mo")
    elif monthly_cashflow >= 0:
        score += 10
        reasons.append(f"Break-even cash flow: ${monthly_cashflow:,.0f}/mo")
    else:
        score += 0
        reasons.append(
            f"⚠️ Negative cash flow: ${monthly_cashflow:,.0f}/mo"
        )

    # ── Cap Rate Score (25 points) ────────────────────────────────
    if cap_rate >= 8:
        score += 25
        reasons.append(f"Excellent cap rate: {cap_rate}%")
    elif cap_rate >= 6:
        score += 18
        reasons.append(f"Good cap rate: {cap_rate}%")
    elif cap_rate >= 4:
        score += 10
        reasons.append(f"Fair cap rate: {cap_rate}%")
    else:
        score += 3
        reasons.append(f"⚠️ Low cap rate: {cap_rate}%")

    # ── Cash-on-Cash Score (20 points) ───────────────────────────
    if cash_on_cash >= 10:
        score += 20
        reasons.append(f"Excellent CoC return: {cash_on_cash}%")
    elif cash_on_cash >= 6:
        score += 14
        reasons.append(f"Good CoC return: {cash_on_cash}%")
    elif cash_on_cash >= 3:
        score += 8
        reasons.append(f"Fair CoC return: {cash_on_cash}%")
    else:
        score += 2
        reasons.append(f"⚠️ Low CoC return: {cash_on_cash}%")

    # ── GRM Score (15 points) ────────────────────────────────────
    if grm <= 8:
        score += 15
        reasons.append(f"Excellent GRM: {grm}")
    elif grm <= 12:
        score += 10
        reasons.append(f"Good GRM: {grm}")
    elif grm <= 15:
        score += 5
        reasons.append(f"Fair GRM: {grm}")
    else:
        score += 0
        reasons.append(f"⚠️ High GRM: {grm}")

    # ── Neighborhood Score (15 points) ───────────────────────────
    if neighborhood_score >= 70:
        score += 15
        reasons.append(f"Strong neighborhood score: {neighborhood_score}")
    elif neighborhood_score >= 50:
        score += 10
        reasons.append(f"Average neighborhood score: {neighborhood_score}")
    else:
        score += 4
        reasons.append(
            f"⚠️ Below average neighborhood: {neighborhood_score}"
        )

    # ── Recommendation ────────────────────────────────────────────
    if score >= 70:
        recommendation = "BUY"
        emoji = "🟢"
    elif score >= 45:
        recommendation = "WATCH"
        emoji = "🟡"
    else:
        recommendation = "AVOID"
        emoji = "🔴"

    return {
        "deal_score":      score,
        "recommendation":  recommendation,
        "emoji":           emoji,
        "top_reasons":     reasons[:3],  # Top 3 reasons
    }


# ── Master Function: Analyze Any Deal ────────────────────────────
def analyze_deal(
    address:          str,
    purchase_price:   float,
    monthly_rent:     float,
    down_payment_pct: float  = 20.0,
    zip_code:         str    = None,
    tax_annual:       float  = None,
    include_mgmt:     bool   = True,
) -> dict:
    """
    Master function — analyzes a complete real estate deal.
    This is called by the FastAPI endpoint in Week 5.

    Takes: address + purchase price + expected rent
    Returns: complete investment analysis

    Example:
        analyze_deal(
            address        = "123 Main St, Raleigh NC",
            purchase_price = 350000,
            monthly_rent   = 2200,
            down_payment_pct = 20
        )
    """
    print(f"\n{'='*55}")
    print(f"  ANALYZING: {address}")
    print(f"{'='*55}")
    print(f"  Purchase Price:  ${purchase_price:,.0f}")
    print(f"  Monthly Rent:    ${monthly_rent:,.0f}")
    print(f"  Down Payment:    {down_payment_pct}%")

    # ── Step 1: Get current mortgage rate from BigQuery ───────────
    client      = bigquery.Client(project=PROJECT_ID)
    rate_query  = f"""
        SELECT mortgage_rate_30yr
        FROM `{PROJECT_ID}.{DATASET}.market_rates`
        WHERE mortgage_rate_30yr IS NOT NULL
        ORDER BY rate_date DESC
        LIMIT 1
    """
    rate_result = list(client.query(rate_query).result())
    annual_rate = rate_result[0]["mortgage_rate_30yr"] if rate_result else 7.0
    print(f"  Current 30yr Rate: {annual_rate}%")

    # ── Step 2: Get neighborhood data from BigQuery ───────────────
    neighborhood_score = 50.0  # Default
    if zip_code:
        nbr_query = f"""
            SELECT
                median_income,
                vacancy_rate,
                poverty_rate,
                owner_occupied_pct
            FROM `{PROJECT_ID}.{DATASET}.neighborhood`
            WHERE zip_code = '{zip_code}'
            LIMIT 1
        """
        nbr_result = list(client.query(nbr_query).result())
        if nbr_result:
            row = nbr_result[0]
            # Simple neighborhood score formula
            # High income + low vacancy + low poverty = good score
            income_score  = min(
                (row["median_income"] or 50000) / 1000, 40
            )
            vacancy_score = max(
                20 - (row["vacancy_rate"] or 10), 0
            )
            poverty_score = max(
                20 - (row["poverty_rate"] or 15), 0
            )
            neighborhood_score = min(
                income_score + vacancy_score + poverty_score, 100
            )
            print(f"  Neighborhood Score: {neighborhood_score:.1f}/100")

    # ── Step 3: Calculate mortgage ────────────────────────────────
    mortgage = calculate_monthly_mortgage(
        purchase_price, down_payment_pct, annual_rate
    )

    # ── Step 4: Calculate expenses ────────────────────────────────
    expenses = calculate_monthly_expenses(
        purchase_price, monthly_rent,
        tax_annual=tax_annual,
        include_mgmt=include_mgmt,
    )

    # ── Step 5: Calculate cash flow ───────────────────────────────
    cashflow = calculate_cash_flow(
        monthly_rent,
        mortgage["monthly_payment"],
        expenses["total_expenses"],
    )

    # ── Step 6: Calculate investment metrics ─────────────────────
    cap_rate    = calculate_cap_rate(
        cashflow["annual_noi"], purchase_price
    )
    coc_return  = calculate_cash_on_cash(
        cashflow["annual_cashflow"], purchase_price, down_payment_pct
    )
    grm         = calculate_grm(purchase_price, monthly_rent)
    projections = calculate_five_year_projection(
        purchase_price, cashflow["monthly_cashflow"],
        cashflow["annual_cashflow"]
    )

  # ── Step 7: Get ML prediction from BigQuery ───────────────────
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ml_engine.bigquery_ml import predict_single_deal
        ml_result = predict_single_deal(
            client            = client,
            cap_rate          = cap_rate,
            cash_on_cash      = coc_return,
            monthly_cashflow  = cashflow["monthly_cashflow"],
            gross_rent_mult   = grm,
            neighborhood_score= neighborhood_score,
            purchase_price    = purchase_price,
            monthly_rent      = monthly_rent,
            down_payment_pct  = down_payment_pct,
        )
        # Use ML prediction
        # Get numeric score from regressor model
        score_query = f"""
            SELECT predicted_deal_score
            FROM ML.PREDICT(
                MODEL `{PROJECT_ID}.{DATASET}.deal_score_regressor`,
                (
                    SELECT
                        CAST({cap_rate} AS FLOAT64)            AS cap_rate,
                        CAST({coc_return} AS FLOAT64)          AS cash_on_cash,
                        CAST({cashflow["monthly_cashflow"]} AS FLOAT64) AS monthly_cashflow,
                        CAST({grm} AS FLOAT64)                 AS gross_rent_mult,
                        CAST({neighborhood_score} AS FLOAT64)  AS neighborhood_score,
                        CAST({purchase_price} AS FLOAT64)      AS purchase_price,
                        CAST({monthly_rent} AS FLOAT64)        AS monthly_rent,
                        CAST({down_payment_pct} AS FLOAT64)    AS down_payment_pct
                )
            )
        """
        score_result = list(client.query(score_query).result())
        ml_score = round(score_result[0]["predicted_deal_score"], 1) if score_result else 0
        ml_score = max(0, min(100, ml_score))  # Clamp between 0-100
        scoring = {
            "deal_score":     ml_score,  # Regressor score added below
            "recommendation": ml_result["recommendation"].replace("PASS", "AVOID"),
            "emoji":          {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(
                                ml_result["recommendation"], "⚪"
                              ),
            "top_reasons":    [
                f"ML confidence: {ml_result['probabilities'].get(ml_result['recommendation'], 0):.1f}%",
                f"Cap rate: {cap_rate}%",
                f"Cash flow: ${cashflow['monthly_cashflow']:,.0f}/mo",
            ],
            "probabilities":  ml_result.get("probabilities", {}),
        }
        print(f"  🤖 ML Model: {scoring['emoji']} {scoring['recommendation']}")
        if ml_result.get("probabilities"):
            for label, prob in sorted(
                ml_result["probabilities"].items(),
                key=lambda x: x[1], reverse=True
            ):
                print(f"     {label}: {prob:.1f}%")
    except Exception as e:
        # Fallback to rule-based scoring if ML unavailable
        print(f"  ⚠️  ML unavailable, using rules: {e}")
        scoring = calculate_deal_score(
            cap_rate, coc_return,
            cashflow["monthly_cashflow"],
            grm, neighborhood_score,
        )

    # ── Step 8: Build complete result ────────────────────────────
    result = {
        "address":           address,
        "purchase_price":    purchase_price,
        "monthly_rent":      monthly_rent,
        "down_payment_pct":  down_payment_pct,
        "annual_rate":       annual_rate,

        # Mortgage
        "loan_amount":       mortgage["loan_amount"],
        "monthly_mortgage":  mortgage["monthly_payment"],

        # Expenses
        "monthly_expenses":  expenses["total_expenses"],
        "expense_breakdown": expenses,

        # Cash Flow
        "monthly_noi":       cashflow["monthly_noi"],
        "monthly_cashflow":  cashflow["monthly_cashflow"],
        "annual_cashflow":   cashflow["annual_cashflow"],

        # Investment Metrics
        "cap_rate":          cap_rate,
        "cash_on_cash":      coc_return,
        "grm":               grm,
        "neighborhood_score":neighborhood_score,

        # AI Score
        "deal_score":        scoring.get("deal_score") or 0,
        "recommendation":    scoring["recommendation"].replace("PASS", "AVOID"),
        "top_reasons":       scoring["top_reasons"],

        # Projections
        "five_year":         projections,

        # Metadata
        "analyzed_at":       datetime.now(timezone.utc).isoformat(),
    }

    # ── Step 9: Print results ─────────────────────────────────────
    print(f"\n  {'─'*45}")
    print(f"  💰 FINANCIAL ANALYSIS")
    print(f"  {'─'*45}")
    print(f"  Monthly Mortgage:  ${mortgage['monthly_payment']:>10,.2f}")
    print(f"  Monthly Expenses:  ${expenses['total_expenses']:>10,.2f}")
    print(f"  Monthly Rent:      ${monthly_rent:>10,.2f}")
    print(f"  {'─'*45}")
    print(f"  Monthly Cash Flow: ${cashflow['monthly_cashflow']:>10,.2f}")
    print(f"  Annual Cash Flow:  ${cashflow['annual_cashflow']:>10,.2f}")
    print(f"\n  📊 INVESTMENT METRICS")
    print(f"  {'─'*45}")
    print(f"  Cap Rate:          {cap_rate:>10.2f}%")
    print(f"  Cash-on-Cash:      {coc_return:>10.2f}%")
    print(f"  Gross Rent Mult:   {grm:>10.2f}x")
    print(f"\n  📈 5-YEAR PROJECTION")
    print(f"  {'─'*45}")
    for yr in projections:
        print(
            f"  Year {yr['year']}: "
            f"Value ${yr['property_value']:>12,.0f} | "
            f"Cash Flow ${yr['annual_cashflow']:>8,.0f}"
        )
    print(f"\n  🎯 AI DEAL SCORE")
    print(f"  {'─'*45}")
    print(f"  Score: {scoring['deal_score']}/100")
    print(f"  {scoring['emoji']} Recommendation: {scoring['recommendation']}")
    print(f"\n  Top Reasons:")
    for reason in scoring["top_reasons"]:
        print(f"    • {reason}")
    print(f"  {'─'*45}\n")

    # ── Step 10: Save to BigQuery ─────────────────────────────────
    save_analysis_to_bigquery(result)

    return result


def save_analysis_to_bigquery(result: dict) -> None:
    """
    Save every deal analysis to BigQuery deal_scores table.
    This builds our ML training dataset over time.
    Every analysis = one training example for Vertex AI.
    """
    import pandas as pd

    client   = bigquery.Client(project=PROJECT_ID)
    TABLE_ID = f"{PROJECT_ID}.{DATASET}.deal_scores"

    row = {
        "analysis_id":        f"deal_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "address":            result["address"],
        "purchase_price":     result["purchase_price"],
        "down_payment_pct":   result["down_payment_pct"],
        "monthly_rent":       result["monthly_rent"],
        "monthly_mortgage":   result["monthly_mortgage"],
        "monthly_expenses":   result["monthly_expenses"],
        "monthly_cashflow":   result["monthly_cashflow"],
        "cap_rate":           result["cap_rate"],
        "cash_on_cash":       result["cash_on_cash"],
        "gross_rent_mult":    result["grm"],
        "deal_score":         float(result["deal_score"]),
        "neighborhood_score": result["neighborhood_score"],
        "recommendation":     result["recommendation"],
        "analyzed_at":        datetime.now(timezone.utc),
    }

    df = pd.DataFrame([row])
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=True,
    )
    load_job = client.load_table_from_dataframe(
        df, TABLE_ID, job_config=job_config
    )
    load_job.result()
    print(f"  ✅ Analysis saved to BigQuery")


if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompass — Deal Calculator Engine")
    print("=" * 55)

    result4 = analyze_deal(
        address          = "222 Cashflow Lane, Durham, NC 27701",
        purchase_price   = 160000,
        monthly_rent     = 1600,
        down_payment_pct = 20,
        zip_code         = "27701",
        tax_annual       = 1600,
        include_mgmt     = False,
    )
    print("\n" + "=" * 55)
    print("  ✅ Deal Calculator Complete!")
    print("  Next: Build Vertex AI model (Week 3)")
    print("=" * 55)