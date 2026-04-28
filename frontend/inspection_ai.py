"""
PropCompassAI — Inspection Report AI
Gemini-powered inspection PDF analyzer
Categorizes issues, estimates costs, generates negotiation strategy
"""

import os
import json
import logging
from urllib import response
from google import genai
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configure Gemini ──────────────────────────────────────────────────
def get_gemini_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            pass
    return genai.Client(api_key=api_key)

# ── Main Analysis Function ────────────────────────────────────────────
def analyze_inspection_report(pdf_bytes: bytes, property_address: str = "") -> dict:
    """
    Upload inspection PDF to Gemini and extract structured issue list.
    Returns dict with critical/important/minor issues + cost estimates.
    """
    try:
        model = get_gemini_model()

        prompt = f"""You are a professional home inspector and real estate expert.
Analyze this home inspection report for: {property_address or 'the subject property'}.

Extract ALL issues mentioned in the report and categorize each one.

Return ONLY a valid JSON object with this exact structure — no markdown, no explanation:

{{
  "property_address": "{property_address}",
  "summary": "2-3 sentence overall summary of the property condition",
  "total_issues": 0,
  "critical_count": 0,
  "important_count": 0,
  "minor_count": 0,
  "estimated_total_min": 0,
  "estimated_total_max": 0,
  "negotiation_recommendation": "Specific recommendation for price reduction or repair request",
  "issues": [
    {{
      "category": "Critical",
      "system": "Roof/Electrical/Plumbing/HVAC/Foundation/etc",
      "description": "Clear description of the issue",
      "location": "Where in the home",
      "cost_min": 500,
      "cost_max": 2000,
      "priority": "Fix before closing",
      "notes": "Why this matters"
    }}
  ]
}}

CATEGORIZATION RULES:
- Critical: Safety hazards, structural issues, major system failures, water intrusion, electrical hazards, foundation issues. These MUST be fixed.
- Important: Items needing repair soon — worn roof, aging HVAC, plumbing leaks, moisture issues, pest damage. Should be negotiated.
- Minor: Cosmetic issues, small repairs, maintenance items under $500. Nice to fix but not urgent.

COST ESTIMATION RULES:
- Provide realistic repair cost ranges in USD
- Base costs on current NC contractor rates
- If multiple same-type issues exist combine them
- Foundation issues: $3,000-$30,000
- Roof replacement: $8,000-$20,000
- HVAC replacement: $5,000-$12,000
- Electrical panel: $1,500-$4,000
- Water heater: $800-$2,000
- Minor repairs: $100-$500 each

Extract EVERY issue mentioned — do not skip anything.
Return ONLY the JSON object."""

        # Upload PDF to Gemini
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        with open(tmp_path, 'rb') as f:
                pdf_content = f.read()
        import base64
        pdf_b64 = base64.b64encode(pdf_content).decode()
        response = model.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "application/pdf", "data": pdf_b64}}
                    ]
                }
            ]
        )

        # Clean and parse response
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        result = json.loads(text)

        # Calculate totals
        critical = [i for i in result.get("issues", []) if i.get("category") == "Critical"]
        important = [i for i in result.get("issues", []) if i.get("category") == "Important"]
        minor = [i for i in result.get("issues", []) if i.get("category") == "Minor"]

        result["critical_count"]  = len(critical)
        result["important_count"] = len(important)
        result["minor_count"]     = len(minor)
        result["total_issues"]    = len(result.get("issues", []))

        # Recalculate cost totals
        total_min = sum(i.get("cost_min", 0) for i in result.get("issues", []))
        total_max = sum(i.get("cost_max", 0) for i in result.get("issues", []))
        result["estimated_total_min"] = total_min
        result["estimated_total_max"] = total_max

        # Clean up temp file
        os.unlink(tmp_path)

        logger.info(f"Inspection analysis complete: {result['total_issues']} issues found")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return _error_result("Could not parse AI response. Please try again.")
    except Exception as e:
        logger.error(f"Inspection analysis failed: {e}")
        return _error_result(str(e))


def _error_result(msg: str) -> dict:
    return {
        "error": msg,
        "summary": "",
        "total_issues": 0,
        "critical_count": 0,
        "important_count": 0,
        "minor_count": 0,
        "estimated_total_min": 0,
        "estimated_total_max": 0,
        "negotiation_recommendation": "",
        "issues": []
    }


# ── Negotiation Strategy Generator ───────────────────────────────────
def generate_negotiation_strategy(
    result: dict,
    purchase_price: float,
    property_address: str = ""
) -> str:
    """
    Generate a detailed negotiation strategy based on inspection findings.
    """
    try:
        model = get_gemini_model()

        total_min = result.get("estimated_total_min", 0)
        total_max = result.get("estimated_total_max", 0)
        critical_count  = result.get("critical_count", 0)
        important_count = result.get("important_count", 0)
        minor_count     = result.get("minor_count", 0)

        critical_issues  = [i for i in result.get("issues", []) if i.get("category") == "Critical"]
        important_issues = [i for i in result.get("issues", []) if i.get("category") == "Important"]

        critical_text  = "\n".join([f"- {i['description']} (${i['cost_min']:,}-${i['cost_max']:,})" for i in critical_issues])
        important_text = "\n".join([f"- {i['description']} (${i['cost_min']:,}-${i['cost_max']:,})" for i in important_issues])

        prompt = f"""You are an expert real estate negotiator in North Carolina.

Property: {property_address}
Purchase price: ${purchase_price:,.0f}
Total repair cost estimate: ${total_min:,} - ${total_max:,}
Critical issues ({critical_count}):
{critical_text}

Important issues ({important_count}):
{important_text}

Minor issues: {minor_count} items

Write a professional negotiation strategy in plain English. Include:

1. RECOMMENDED APPROACH (ask seller to fix OR price reduction OR credit)
2. SPECIFIC DOLLAR AMOUNT to request
3. PRIORITY ITEMS seller must fix before closing
4. ITEMS acceptable as closing cost credit
5. WALK AWAY trigger (if any)
6. TALKING POINTS for your realtor to use

Keep it practical and specific to NC real estate.
Write in clear paragraphs — no bullet points."""

        response = model.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text

    except Exception as e:
        logger.error(f"Negotiation strategy failed: {e}")
        return f"Could not generate negotiation strategy: {str(e)}"