"""
gemini_explainer.py
PropCompassAI — Gemini LLM Deal Explainer via Vertex AI
"""

import os
import logging

logger = logging.getLogger(__name__)

DEAL_PROMPT = """
You are PropCompassAI's expert real estate investment analyst.

Analyze this property deal and write a clear 3-4 sentence explanation
for a real estate investor. Be direct, specific, and actionable.

Property Details:
- Address: {address}
- Purchase Price: ${purchase_price:,.0f}
- Monthly Rent: ${monthly_rent:,.0f}
- Monthly Cash Flow: ${monthly_cashflow:,.0f}
- Annual Cash Flow: ${annual_cashflow:,.0f}
- Cap Rate: {cap_rate:.2f}%
- Cash-on-Cash Return: {cash_on_cash:.2f}%
- Monthly Mortgage: ${monthly_mortgage:,.0f}
- AI Deal Score: {deal_score}/100
- Recommendation: {recommendation}
- Neighborhood Score: {neighborhood_score}/100
- 5-Year Property Value: ${five_year_value:,.0f}
- 5-Year Total Appreciation: ${five_year_appreciation:,.0f}

Instructions:
1. Explain WHY this deal got the {recommendation} rating in 1 sentence
2. Highlight the strongest financial metric
3. Mention the biggest risk or concern
4. Give one specific actionable next step
5. Keep total response under 100 words
6. Write in flowing sentences — no bullet points
7. Sound like a trusted financial advisor — not a robot
"""


class GeminiExplainer:
    """
    Generates natural language deal explanations using
    Google Gemini 1.5 Flash via Vertex AI.
    """

    def __init__(self):
        self.available = False
        self.model     = None
        self._init_gemini()

    def _init_gemini(self):
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            load_dotenv(Path(__file__).parent.parent / ".env")
            from google import genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            self.client    = genai.Client(api_key=api_key)
            self.available = True
            logger.info("✅ Gemini initialized via Google GenAI SDK")
        except Exception as e:
            logger.warning(f"⚠️ Gemini unavailable: {e}")
            self.available = False

    def explain_deal(self, deal_result: dict) -> dict:
        if not self.available:
            return {
                "explanation": self._rule_based_explain(deal_result),
                "model":       "Rule Engine",
                "status":      "fallback",
                "available":   False,
            }
        try:
            prompt      = self._build_prompt(deal_result)
            response    = self.client.models.generate_content(
                model    = "gemini-2.5-flash",
                contents = prompt,
            )
            explanation = response.text.strip()
            return {
                "explanation": explanation,
                "model":       "Gemini 2.5 Flash",
                "status":      "success",
                "available":   True,
            }
        
        except Exception as e:
            logger.error(f"Gemini explain failed: {e}")
            return {
                "explanation": self._rule_based_explain(deal_result),
                "model":       "Rule Engine (Gemini unavailable)",
                "status":      "fallback",
                "available":   False,
            }
    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize user input to prevent prompt injection attacks.
        Removes common injection patterns before sending to Gemini.
        """
        if not text:
            return ""
        # Convert to string and limit length
        text = str(text)[:200]
        # Remove common prompt injection patterns
        injection_patterns = [
            "ignore previous instructions",
            "ignore all instructions",
            "disregard the above",
            "forget everything",
            "new instructions:",
            "system prompt:",
            "you are now",
            "act as",
            "jailbreak",
            "dan mode",
            "pretend you",
            "roleplay as",
            "override",
            "bypass",
            "<script>",
            "javascript:",
            "prompt:",
            "###instruction",
            "[system]",
            "[user]",
            "[assistant]",
        ]
        text_lower = text.lower()
        for pattern in injection_patterns:
            if pattern in text_lower:
                # Log the attack attempt!
                logger.warning(
                f"SECURITY: Prompt injection detected! "
                f"Pattern: '{pattern}' | "
                f"Input: '{text[:50]}...'"
            )
                return "Property Address Provided"
        return text.strip()
    
    def _build_prompt(self, deal: dict) -> str:
        five_year    = deal.get("five_year", [{}])
        last_year    = five_year[-1] if five_year else {}
        appreciation = last_year.get("total_appreciation", 0) or 0
        final_value  = last_year.get("property_value", 0) or 0
        rec = deal.get("recommendation", "WATCH").replace("PASS", "AVOID")
        return DEAL_PROMPT.format(
            address = self._sanitize_input(
                deal.get("address", "this property")
            ),
            purchase_price        = deal.get("purchase_price",   0) or 0,
            monthly_rent          = deal.get("monthly_rent",     0) or 0,
            monthly_cashflow      = deal.get("monthly_cashflow", 0) or 0,
            annual_cashflow       = deal.get("annual_cashflow",  0) or 0,
            cap_rate              = deal.get("cap_rate",         0) or 0,
            cash_on_cash          = deal.get("cash_on_cash",     0) or 0,
            monthly_mortgage      = deal.get("monthly_mortgage", 0) or 0,
            deal_score            = deal.get("deal_score",       0) or 0,
            recommendation        = rec,
            neighborhood_score    = deal.get("neighborhood_score", 0) or 0,
            five_year_value       = final_value,
            five_year_appreciation= appreciation,
        )

    def _rule_based_explain(self, deal: dict) -> str:
        rec      = deal.get("recommendation", "WATCH")
        score    = deal.get("deal_score",       0) or 0
        cap      = deal.get("cap_rate",         0) or 0
        cashflow = deal.get("monthly_cashflow", 0) or 0
        coc      = deal.get("cash_on_cash",     0) or 0

        if rec == "BUY":
            return (
                f"This property scores {score}/100 earning a BUY rating "
                f"with a strong cap rate of {cap:.2f}% and positive monthly "
                f"cash flow of ${cashflow:,.0f}. The {coc:.2f}% cash-on-cash "
                f"return provides solid income on your down payment. "
                f"Proceed with a professional inspection before making your offer."
            )
        elif rec == "WATCH":
            return (
                f"This property scores {score}/100 earning a WATCH rating — "
                f"the {cap:.2f}% cap rate shows potential but ${cashflow:,.0f} "
                f"monthly cash flow leaves little buffer for vacancies or repairs. "
                f"Consider negotiating the price down $10,000-15,000 to improve "
                f"cash flow before committing to this deal."
            )
        else:
            return (
                f"This property scores {score}/100 and receives an AVOID rating — "
                f"${cashflow:,.0f} monthly cash flow does not meet investment "
                f"thresholds at this price point. "
                f"Pass on this property and look for deals with cap rates above 6%."
            )
