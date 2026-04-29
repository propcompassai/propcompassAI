"""
PropCompassAI — Inspection Report AI
Uses Vertex AI Gemini Vision — GCP billing
"""

import os
import json
import logging
import vertexai
from vertexai.generative_models import GenerativeModel, Part

logger = logging.getLogger(__name__)

GCP_PROJECT  = "propcompassai"
GCP_LOCATION = "us-central1"
MODEL_NAME   = "gemini-2.5-flash"

VENDOR_CATEGORIES = {
    "Roof":        {"category": "Roofing Contractor",     "icon": "🏠"},
    "HVAC":        {"category": "HVAC Technician",        "icon": "❄️"},
    "Plumbing":    {"category": "Plumber",                "icon": "🔧"},
    "Electrical":  {"category": "Electrician",            "icon": "⚡"},
    "Foundation":  {"category": "Foundation Specialist",  "icon": "🏗️"},
    "Pest":        {"category": "Pest Control",           "icon": "🐛"},
    "Mold":        {"category": "Mold Remediation",       "icon": "🧪"},
    "Structural":  {"category": "Structural Engineer",    "icon": "🔩"},
    "Drywall":     {"category": "Handyman / Painter",     "icon": "🎨"},
    "Flooring":    {"category": "Flooring Specialist",    "icon": "🪵"},
    "Water Heater":{"category": "Plumber",                "icon": "🔧"},
    "Windows":     {"category": "Window Contractor",      "icon": "🪟"},
    "Appliances":  {"category": "Appliance Repair",       "icon": "🔌"},
    "Landscaping": {"category": "Landscaper",             "icon": "🌿"},
    "Gutters":     {"category": "Gutter Specialist",      "icon": "🌧️"},
    "Garage":      {"category": "Garage Door Specialist", "icon": "🚗"},
    "General":     {"category": "Handyman",               "icon": "🔨"},
}

SAMPLE_VENDORS = {
    "Roofing Contractor":    [{"name":"Triangle Roofing Pro","rating":4.9,"reviews":127,"phone":"919-555-0101","premium":True,"years":15}],
    "HVAC Technician":       [{"name":"CoolAir HVAC Services","rating":4.8,"reviews":203,"phone":"919-555-0201","premium":True,"years":12}],
    "Plumber":               [{"name":"Holly Springs Plumbing","rating":4.9,"reviews":178,"phone":"919-555-0301","premium":True,"years":20}],
    "Electrician":           [{"name":"Triangle Electric Co","rating":4.8,"reviews":245,"phone":"919-555-0401","premium":True,"years":18}],
    "Foundation Specialist": [{"name":"Carolina Foundation Fix","rating":4.9,"reviews":67,"phone":"919-555-0501","premium":True,"years":22}],
    "Pest Control":          [{"name":"Triangle Pest Guard","rating":4.8,"reviews":312,"phone":"919-555-0601","premium":True,"years":16}],
    "Mold Remediation":      [{"name":"Clean Air NC","rating":4.9,"reviews":78,"phone":"919-555-0701","premium":True,"years":11}],
    "Handyman / Painter":    [{"name":"Fix It Fast Triangle","rating":4.7,"reviews":234,"phone":"919-555-0801","premium":True,"years":8}],
    "Flooring Specialist":   [{"name":"Triangle Floor Pros","rating":4.8,"reviews":145,"phone":"919-555-0901","premium":True,"years":13}],
    "Handyman":              [{"name":"Fix It Fast Triangle","rating":4.7,"reviews":234,"phone":"919-555-0801","premium":True,"years":8}],
}

def get_vendor_for_system(system: str) -> dict:
    for key, info in VENDOR_CATEGORIES.items():
        if key.lower() in system.lower():
            return {"category": info["category"], "icon": info["icon"],
                    "vendors": SAMPLE_VENDORS.get(info["category"], [])}
    return {"category": "Handyman", "icon": "🔨", "vendors": SAMPLE_VENDORS.get("Handyman", [])}

def get_gemini_model():
    try:
        import streamlit as st
        from google.oauth2 import service_account
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION, credentials=credentials)
        else:
            vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
    except Exception as e:
        logger.error(f"Vertex AI init failed: {e}")
        raise e
    return GenerativeModel(MODEL_NAME)

def analyze_inspection_report(pdf_bytes: bytes, property_address: str = "") -> dict:
    # ── Check cache first ─────────────────────────────────────────
    try:
        from inspection_cache import get_cached_result, save_to_cache
        cached = get_cached_result(pdf_bytes, property_address)
        if cached:
            return cached
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")

    try:
        model = get_gemini_model()
        prompt = f"""You are a professional home inspector. Analyze this inspection report for: {property_address or 'the subject property'}.
Return ONLY valid JSON — no markdown, no explanation:
{{"property_address":"{property_address}","summary":"2-3 sentence summary","total_issues":0,"critical_count":0,"important_count":0,"minor_count":0,"estimated_total_min":0,"estimated_total_max":0,"negotiation_recommendation":"Specific recommendation with dollar amount","issues":[{{"category":"Critical","system":"Roof","description":"Issue description","location":"Where in home","cost_min":500,"cost_max":2000,"priority":"Fix before closing","notes":"Why this matters"}}]}}
Categories: Critical=safety/structural/major, Important=repair soon, Minor=cosmetic
Systems: Roof, HVAC, Plumbing, Electrical, Foundation, Pest, Mold, Structural, Drywall, Flooring, Water Heater, Windows, Appliances, Landscaping, Gutters, Garage, General
NC CONTRACTOR RATES 2026 — use EXACTLY these ranges every time:
CRITICAL: Foundation $3K-30K, Roof replacement $8K-20K, Roof sheathing $500-2K, Electrical panel $1.5K-4K, Structural $2K-10K, Water intrusion $1K-8K
IMPORTANT: HVAC replacement $5K-12K, HVAC repair $150-600, Water heater $800-2K, Roof repair $300-1.5K, Window replacement $300-800each, Flooring $200-800, Plumbing $200-1.5K
MINOR: Paint/trim $100-500, Door adjustment $50-200, Drywall $100-400, Doorbell $100-300, Door stoppers $20-100, Air filter $20-50, Garage door $50-200
CRITICAL issues MUST have higher cost estimates. Be consistent — same issue = same cost range every time.
Return ONLY the JSON object."""
        pdf_part = Part.from_data(data=pdf_bytes, mime_type="application/pdf")
        from vertexai.generative_models import GenerationConfig

        response = model.generate_content(
            [prompt, pdf_part],
            generation_config=GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192,
            )
        )
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        result = json.loads(text)
        issues = result.get("issues", [])
        result["critical_count"]      = len([i for i in issues if i.get("category") == "Critical"])
        result["important_count"]     = len([i for i in issues if i.get("category") == "Important"])
        result["minor_count"]         = len([i for i in issues if i.get("category") == "Minor"])
        result["total_issues"]        = len(issues)
        result["estimated_total_min"] = sum(i.get("cost_min", 0) for i in issues)
        result["estimated_total_max"] = sum(i.get("cost_max", 0) for i in issues)
        for issue in result["issues"]:
            vm = get_vendor_for_system(issue.get("system", "General"))
            issue["vendor_category"]      = vm["category"]
            issue["vendor_icon"]          = vm["icon"]
            issue["recommended_vendors"]  = vm["vendors"]
        logger.info(f"Inspection analysis complete: {result['total_issues']} issues found")

        # ── Save to cache ─────────────────────────────────────────
        try:
            from inspection_cache import save_to_cache
            save_to_cache(pdf_bytes, property_address, result)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

        return result
    except json.JSONDecodeError as e:
        return _error_result(f"Could not parse AI response: {e}")
    except Exception as e:
        logger.error(f"Inspection analysis failed: {e}")
        return _error_result(str(e))

def _error_result(msg):
    return {"error":msg,"summary":"","total_issues":0,"critical_count":0,"important_count":0,"minor_count":0,"estimated_total_min":0,"estimated_total_max":0,"negotiation_recommendation":"","issues":[]}

def generate_negotiation_strategy(result: dict, purchase_price: float, property_address: str = "") -> str:
    try:
        model = get_gemini_model()
        critical  = [i for i in result.get("issues",[]) if i.get("category")=="Critical"]
        important = [i for i in result.get("issues",[]) if i.get("category")=="Important"]
        ctext = "\n".join([f"- {i['description']} ${i['cost_min']:,}-${i['cost_max']:,}" for i in critical])
        itext = "\n".join([f"- {i['description']} ${i['cost_min']:,}-${i['cost_max']:,}" for i in important])
        prompt = f"""NC real estate negotiation expert. Property: {property_address}. Price: ${purchase_price:,.0f}.
Repair estimate: ${result.get('estimated_total_min',0):,}-${result.get('estimated_total_max',0):,}
Critical ({len(critical)}): {ctext}
Important ({len(important)}): {itext}
Write practical NC negotiation strategy: recommended approach, exact dollar amount, priority fixes, credit items, walk-away trigger, talking points."""
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
            )
        )
        return response.text
    except Exception as e:
        return f"Could not generate strategy: {str(e)}"

