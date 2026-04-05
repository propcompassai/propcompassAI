"""
main.py
PropCompassAI FastAPI Backend

This is the web API that sits between the Streamlit UI
and the deal calculator engine.

Endpoints:
    POST /analyze     — Full deal analysis
    GET  /health      — Health check
    GET  /rates       — Current mortgage rates
    GET  /neighborhood — Neighborhood data by zip

Why FastAPI?
- Fastest Python web framework
- Auto-generates API documentation at /docs
- Built-in request validation using Pydantic
- Async support for handling multiple requests
- Type hints = self-documenting code
"""

import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
from ml_engine.gemini_explainer import GeminiExplainer
from ml_engine.realtor_advisor import RealtorAdvisor

# Initialize once at startup
realtor_advisor = RealtorAdvisor()

# Initialize Gemini once at startup
gemini_explainer = GeminiExplainer()
# Add project root to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

# ── FastAPI App Setup ─────────────────────────────────────────────
app = FastAPI(
    title       = "PropCompassAI API",
    description = "AI-powered real estate deal analyzer",
    version     = "1.0.0",
    docs_url    = "/docs",   # Swagger UI at /docs
    redoc_url   = "/redoc",  # ReDoc UI at /redoc
)


# ── CORS Middleware ───────────────────────────────────────────────
# Allows Streamlit frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],  # In production, restrict to your domain
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Request Models (Pydantic) ─────────────────────────────────────
# Pydantic validates incoming request data automatically
# If a required field is missing → FastAPI returns 422 error
# If wrong type → FastAPI returns clear error message

class AnalyzeRequest(BaseModel):
    """
    Request body for /analyze endpoint.
    Pydantic validates all fields automatically.
    """
    address: str = Field(
        ...,
        min_length  = 5,
        max_length  = 200,
        description = "Property street address",
        example     = "123 Main St, Raleigh, NC 27601"
    )
    purchase_price: float = Field(
        ...,
        gt          = 0,
        description = "Purchase price in USD",
        example     = 280000
    )
    monthly_rent: float = Field(
        ...,
        gt          = 0,
        description = "Expected monthly rent in USD",
        example     = 2200
    )
    down_payment_pct: float = Field(
        default     = 20.0,
        ge          = 0,
        le          = 100,
        description = "Down payment percentage",
        example     = 20.0
    )
    zip_code: Optional[str] = Field(
        default     = None,
        description = "Property zip code for neighborhood analysis",
        example     = "27601"
    )
    tax_annual: Optional[float] = Field(
        default     = None,
        description = "Annual property tax in USD",
        example     = 2800
    )
    tax_rate: float = Field(
        default     = 1.2,
        ge          = 0,
        le          = 5,
        description = "Property tax rate % of price/year",
        example     = 1.2
    )
    include_mgmt: bool = Field(
        default     = True,
        description = "Include property management fees",
        example     = True
    )
    mgmt_rate: float = Field(
        default     = 8.0,
        ge          = 0,
        le          = 15,
        description = "Property management rate % of rent",
        example     = 8.0
    )
    vacancy_rate: float = Field(
        default     = 8.33,
        ge          = 0,
        le          = 100,
        description = "Vacancy rate percentage",
        example     = 8.33
    )
    maintenance_rate: float = Field(
        default     = 1.0,
        ge          = 0,
        le          = 10,
        description = "Maintenance rate % of purchase price/year",
        example     = 1.0
    )
    insurance_rate: float = Field(
        default     = 0.5,
        ge          = 0,
        le          = 5,
        description = "Insurance rate % of purchase price/year",
        example     = 0.5
    )
    hoa_monthly: float = Field(
        default     = 0.0,
        ge          = 0,
        description = "Monthly HOA fees",
        example     = 0.0
    )
class AnalyzeResponse(BaseModel):
    """
    Response model for /analyze endpoint.
    Documents exactly what the API returns.
    """
    # Property info
    address:          str
    purchase_price:   float
    monthly_rent:     float
    down_payment_pct: float

    # Mortgage
    loan_amount:      float
    monthly_mortgage: float
    annual_rate:      float

    # Expenses
   # Expenses
    monthly_expenses:  float
    expense_breakdown: dict = {}
    realtor_analysis: dict = {}
    # Cash Flow
    monthly_cashflow: float
    annual_cashflow:  float
    monthly_noi:      float

    # Investment Metrics
    cap_rate:         float
    cash_on_cash:     float
    grm:              float

    # Neighborhood
    neighborhood_score: float

    # AI Score
    deal_score:       float
    recommendation:   str
    top_reasons:      list

    # Projections
    five_year:        list

    # Metadata
    analyzed_at:      str
    api_version:      str = "1.0.0"


# ── Health Check Endpoint ─────────────────────────────────────────
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Used by Cloud Run to verify the service is running.
    Returns 200 if healthy.
    """
    return {
        "status":    "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service":   "PropCompassAI API",
        "version":   "1.0.0",
    }


# ── Current Mortgage Rates Endpoint ──────────────────────────────
@app.get("/rates")
async def get_rates():
    """
    Returns current mortgage rates from BigQuery.
    Investors use this to understand the financing environment.
    """
    try:
        from google.cloud import bigquery
        PROJECT_ID = os.getenv("GCP_PROJECT_ID")
        DATASET    = os.getenv("BQ_DATASET")

        client = bigquery.Client(project=PROJECT_ID)
        query  = f"""
            SELECT
                rate_date,
                mortgage_rate_30yr,
                mortgage_rate_15yr,
                fed_funds_rate
            FROM `{PROJECT_ID}.{DATASET}.market_rates`
            WHERE mortgage_rate_30yr IS NOT NULL
            ORDER BY rate_date DESC
            LIMIT 5
        """
        results = list(client.query(query).result())

        return {
            "current_30yr": results[0]["mortgage_rate_30yr"] if results else 7.0,
            "current_15yr": results[0]["mortgage_rate_15yr"] if results else 6.0,
            "fed_funds":    results[0]["fed_funds_rate"]     if results else 5.25,
            "as_of":        str(results[0]["rate_date"])     if results else "N/A",
            "history":      [
                {
                    "date":    str(r["rate_date"]),
                    "rate_30": r["mortgage_rate_30yr"],
                    "rate_15": r["mortgage_rate_15yr"],
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Neighborhood Endpoint ─────────────────────────────────────────
@app.get("/neighborhood/{zip_code}")
async def get_neighborhood(zip_code: str):
    """
    Returns neighborhood demographics for a zip code.
    Used to show investors the market context.
    """
    try:
        from google.cloud import bigquery
        PROJECT_ID = os.getenv("GCP_PROJECT_ID")
        DATASET    = os.getenv("BQ_DATASET")

        client = bigquery.Client(project=PROJECT_ID)
        query  = f"""
            SELECT
                zip_code,
                median_income,
                population,
                vacancy_rate,
                poverty_rate,
                owner_occupied_pct,
                median_age
            FROM `{PROJECT_ID}.{DATASET}.neighborhood`
            WHERE zip_code = '{zip_code}'
            LIMIT 1
        """
        results = list(client.query(query).result())

        if not results:
            raise HTTPException(
                status_code = 404,
                detail      = f"Zip code {zip_code} not found"
            )

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Main Analyze Endpoint ─────────────────────────────────────────
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_deal(request: AnalyzeRequest):
    """
    Main endpoint — analyzes a real estate investment deal.

    Takes property details and returns:
    - Complete financial analysis
    - AI-powered deal score (0-100)
    - BUY / WATCH / PASS recommendation
    - 5-year projection
    - Neighborhood intelligence

    This is the core of PropCompassAI.
    """
    try:
        print(f"\n📨 Analyze request: {request.address}")
        print(f"   Price: ${request.purchase_price:,.0f}")
        print(f"   Rent:  ${request.monthly_rent:,.0f}/mo")

        # Import and call deal calculator
        from data_pipeline.deal_calculator import analyze_deal

        result = analyze_deal(
            address          = request.address,
            purchase_price   = request.purchase_price,
            monthly_rent     = request.monthly_rent,
            down_payment_pct = request.down_payment_pct,
            zip_code         = request.zip_code,
            tax_annual       = request.tax_annual,
            tax_rate         = request.tax_rate,
            include_mgmt     = request.include_mgmt,
            mgmt_rate        = request.mgmt_rate,
            vacancy_rate     = request.vacancy_rate,
            maintenance_rate = request.maintenance_rate,
            insurance_rate   = request.insurance_rate,
            hoa_monthly      = request.hoa_monthly,
        )

        print(f"   Result: {result['recommendation']} (score: {result['deal_score']})")

                # Add realtor analysis
        result["realtor_analysis"] = realtor_advisor.analyze(result)
        return AnalyzeResponse(**result)

    except Exception as e:
        print(f"❌ Error analyzing deal: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code = 500,
            detail      = f"Analysis failed: {str(e)}"
        )

@app.post("/explain")
async def explain_deal(deal_result: dict):
    
    """
    Generate Gemini AI explanation for a deal analysis result.
    Powered by Google Gemini 1.5 Flash via Vertex AI.
    """
    try:
        result = gemini_explainer.explain_deal(deal_result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: dict):
    """
    Gemini-powered real estate chatbot.
    Knows the current deal context and answers questions.
    """
    try:
        message     = request.get("message", "")
        deal_context = request.get("deal_context", {})
        history     = request.get("history", [])

        if not message:
            raise HTTPException(status_code=400, detail="Message required")

        result = gemini_explainer.chat(message, deal_context, history)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ── Run locally ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  PropCompassAI API — Starting...")
    print("  Docs: http://localhost:8080/docs")
    print("=" * 55)
    uvicorn.run(
        "main:app",
        host     = "0.0.0.0",
        port     = 8080,
        reload   = True,   # Auto-reload on code changes
        log_level= "info",
    )