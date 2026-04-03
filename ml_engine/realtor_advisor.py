"""
realtor_advisor.py
PropCompassAI — Realtor Advisor

Thinks like an experienced realtor:
1. Diagnoses WHY a deal fails
2. Calculates fair market value
3. Suggests negotiation range
4. Finds value-add scenarios
"""

import os
import logging

logger = logging.getLogger(__name__)

def _sanitize(self, value, default=0):
        """Ensure numeric values are within safe ranges."""
        try:
            val = float(value)
            if val < 0 or val > 100_000_000:
                return default
            return val
        except (TypeError, ValueError):
            return default
        
class RealtorAdvisor:
    """
    Analyzes deals the way an experienced realtor would.
    Gives investors actionable advice beyond just a score.
    """

    # ── Constants ─────────────────────────────────────────────
    TARGET_CAP_RATE_BUY   = 7.0   # % — minimum for BUY
    TARGET_CAP_RATE_WATCH = 6.0   # % — minimum for WATCH
    OFFER_DISCOUNT        = 0.10  # 10% below max price
    MIN_CASHFLOW_BUY      = 100   # $ minimum monthly for BUY

    def analyze(self, deal: dict) -> dict:
        """
        Full realtor analysis of a deal.
        Returns diagnosis, fair value, negotiation, scenarios.
        """
        try:
            diagnosis    = self._diagnose(deal)
            fair_value   = self._fair_market_value(deal)
            negotiation  = self._negotiation_strategy(deal, fair_value)
            scenarios    = self._value_add_scenarios(deal)
            summary      = self._summary(deal, diagnosis, negotiation)

            return {
                "diagnosis":   diagnosis,
                "fair_value":  fair_value,
                "negotiation": negotiation,
                "scenarios":   scenarios,
                "summary":     summary,
                "available":   True,
            }
        except Exception as e:
            logger.error(f"RealtorAdvisor error: {e}")
            return {"available": False, "error": str(e)}

    def _diagnose(self, deal: dict) -> dict:
        """Identify the PRIMARY reason deal fails."""
        price    = deal.get("purchase_price", 0) or 0
        rent     = deal.get("monthly_rent",   0) or 0
        cap      = deal.get("cap_rate",        0) or 0
        cashflow = deal.get("monthly_cashflow",0) or 0
        rec      = deal.get("recommendation", "WATCH")

        # Rent to price ratio
        rent_to_price = (rent / price * 100) if price > 0 else 0

        # Identify primary problem
        if rec == "BUY":
            primary = "good_deal"
            message = "This is a solid investment at current terms."
            severity = "positive"
        elif cap < 4:
            primary  = "price_too_high"
            message  = f"Price is too high for the rental income. Cap rate of {cap:.1f}% is well below the 6% minimum."
            severity = "high"
        elif cap < 6:
            primary  = "marginal_returns"
            message  = f"Returns are marginal. Cap rate {cap:.1f}% is below the 6% BUY threshold."
            severity = "medium"
        elif cashflow < 0:
            primary  = "negative_cashflow"
            message  = f"Negative cash flow of ${abs(cashflow):,.0f}/mo means paying out of pocket every month."
            severity = "high"
        else:
            primary  = "watch"
            message  = "Deal is borderline — small improvements could make it work."
            severity = "low"

        # Price vs rent relationship
        ideal_price = (rent * 12 / self.TARGET_CAP_RATE_BUY * 100) if rent > 0 else 0
        overpriced_pct = ((price - ideal_price) / ideal_price * 100) if ideal_price > 0 else 0

        return {
            "primary":       primary,
            "message":       message,
            "severity":      severity,
            "rent_to_price": round(rent_to_price, 2),
            "overpriced_pct": round(overpriced_pct, 1),
            "ideal_rent_to_price": 0.8,
        }

    def _fair_market_value(self, deal: dict) -> dict:
        """Calculate what this property SHOULD cost based on income."""
        annual_noi = deal.get("monthly_noi", 0) * 12 if deal.get("monthly_noi") else 0
        price      = deal.get("purchase_price", 0) or 0
        rent       = deal.get("monthly_rent",   0) or 0

        # Income approach valuation
        value_at_6_cap = round(annual_noi / 0.06) if annual_noi > 0 else 0
        value_at_7_cap = round(annual_noi / 0.07) if annual_noi > 0 else 0
        value_at_8_cap = round(annual_noi / 0.08) if annual_noi > 0 else 0

        # Rent multiplier approach
        gross_rent_annual = rent * 12
        value_at_grm12    = round(gross_rent_annual * 12)
        value_at_grm10    = round(gross_rent_annual * 10)

        # Average fair value
        fair_value_avg = round(
            (value_at_7_cap + value_at_grm12) / 2
        ) if value_at_7_cap > 0 else 0

        discount_from_list = price - fair_value_avg
        discount_pct       = round(
            discount_from_list / price * 100, 1
        ) if price > 0 else 0

        return {
            "value_at_6_cap":    value_at_6_cap,
            "value_at_7_cap":    value_at_7_cap,
            "value_at_8_cap":    value_at_8_cap,
            "value_at_grm12":    value_at_grm12,
            "value_at_grm10":    value_at_grm10,
            "fair_value_avg":    fair_value_avg,
            "list_price":        price,
            "discount_needed":   discount_from_list,
            "discount_pct":      discount_pct,
        }

    def _negotiation_strategy(self, deal: dict, fair_value: dict) -> dict:
        """Calculate negotiation range."""
        price          = deal.get("purchase_price", 0) or 0
        annual_noi     = deal.get("monthly_noi", 0) * 12 if deal.get("monthly_noi") else 0

        # Max prices for each rating
        max_for_buy    = round(annual_noi / (self.TARGET_CAP_RATE_BUY   / 100)) if annual_noi > 0 else 0
        max_for_watch  = round(annual_noi / (self.TARGET_CAP_RATE_WATCH / 100)) if annual_noi > 0 else 0

        # Suggested opening offer
        opening_offer  = round(max_for_buy * (1 - self.OFFER_DISCOUNT))

        # Price reduction needed
        reduction_for_buy   = price - max_for_buy
        reduction_pct       = round(reduction_for_buy / price * 100, 1) if price > 0 else 0

        # Is deal salvageable?
        salvageable = max_for_buy > (price * 0.5)

        return {
            "max_price_for_buy":   max_for_buy,
            "max_price_for_watch": max_for_watch,
            "suggested_offer":     opening_offer,
            "reduction_needed":    reduction_for_buy,
            "reduction_pct":       reduction_pct,
            "salvageable":         salvageable,
            "current_price":       price,
        }

    def _value_add_scenarios(self, deal: dict) -> list:
        """
        Three scenarios showing how to make the deal work.
        Scenario A: Negotiate price only
        Scenario B: Increase rent only
        Scenario C: Both price + rent (best)
        """
        price        = deal.get("purchase_price",  0) or 0
        rent         = deal.get("monthly_rent",    0) or 0
        mortgage     = deal.get("monthly_mortgage",0) or 0
        expenses     = deal.get("monthly_expenses",0) or 0
        annual_noi   = deal.get("monthly_noi",     0) * 12 if deal.get("monthly_noi") else 0
        down_pct     = deal.get("down_payment_pct",20) or 20

        scenarios = []

        # ── Scenario A: Price reduction only ──────────────────
        target_price_a = round(annual_noi / (self.TARGET_CAP_RATE_BUY / 100)) if annual_noi > 0 else 0
        if target_price_a > 0 and target_price_a < price:
            loan_a         = target_price_a * (1 - down_pct / 100)
            mortgage_a     = self._calc_mortgage(loan_a)
            cashflow_a     = rent - mortgage_a - expenses
            cap_a          = round(annual_noi / target_price_a * 100, 2)
            scenarios.append({
                "name":        "Negotiate price down",
                "type":        "price",
                "target_price": target_price_a,
                "target_rent":  rent,
                "new_mortgage": round(mortgage_a),
                "new_cashflow": round(cashflow_a),
                "new_cap_rate": cap_a,
                "recommendation": "BUY" if cashflow_a >= self.MIN_CASHFLOW_BUY else "WATCH",
                "action":      f"Offer ${target_price_a:,.0f} — ${price - target_price_a:,.0f} below asking",
            })

        # ── Scenario B: Rent increase only ────────────────────
        # What rent needed for BUY at current price?
        needed_noi_annual = price * (self.TARGET_CAP_RATE_BUY / 100)
        needed_noi_monthly = needed_noi_annual / 12
        current_expenses_ex_vacancy = expenses * 0.85
        target_rent_b = round(needed_noi_monthly + expenses)
        rent_increase = target_rent_b - rent
        rent_increase_pct = round(rent_increase / rent * 100, 1) if rent > 0 else 0

        if rent_increase > 0:
            cashflow_b = target_rent_b - mortgage - expenses
            cap_b      = round((target_rent_b - expenses) * 12 / price * 100, 2)
            scenarios.append({
                "name":        "Increase rental income",
                "type":        "rent",
                "target_price": price,
                "target_rent":  target_rent_b,
                "rent_increase": rent_increase,
                "rent_increase_pct": rent_increase_pct,
                "new_cashflow": round(cashflow_b),
                "new_cap_rate": cap_b,
                "recommendation": "BUY" if cashflow_b >= self.MIN_CASHFLOW_BUY else "WATCH",
                "action": f"Renovate to justify ${target_rent_b:,.0f}/mo (+${rent_increase:,.0f}/mo increase)",
            })

        # ── Scenario C: Both price + rent ─────────────────────
        target_price_c = round(price * 0.85)
        target_rent_c  = round(rent * 1.10)
        loan_c         = target_price_c * (1 - down_pct / 100)
        mortgage_c     = self._calc_mortgage(loan_c)
        cashflow_c     = target_rent_c - mortgage_c - expenses
        cap_c          = round((target_rent_c - expenses) * 12 / target_price_c * 100, 2) if target_price_c > 0 else 0

        scenarios.append({
            "name":        "Negotiate price + raise rent",
            "type":        "both",
            "target_price": target_price_c,
            "target_rent":  target_rent_c,
            "new_mortgage": round(mortgage_c),
            "new_cashflow": round(cashflow_c),
            "new_cap_rate": cap_c,
            "recommendation": "BUY" if cashflow_c >= self.MIN_CASHFLOW_BUY else "WATCH",
            "action": f"Offer ${target_price_c:,.0f} + renovate for ${target_rent_c:,.0f}/mo (+${target_rent_c - rent:,.0f}/mo increase)",
            "best":        True,
        })

        return scenarios

    def _calc_mortgage(
        self,
        loan_amount: float,
        annual_rate: float = 7.0,
        years:       int   = 30
    ) -> float:
        """Calculate monthly mortgage payment."""
        if loan_amount <= 0:
            return 0
        monthly_rate = annual_rate / 100 / 12
        n_payments   = years * 12
        if monthly_rate == 0:
            return loan_amount / n_payments
        payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)
        return round(payment, 2)

    def _summary(self, deal: dict, diagnosis: dict, negotiation: dict) -> str:
        """One paragraph summary like a realtor would say."""
        rec    = deal.get("recommendation", "WATCH")
        price  = deal.get("purchase_price", 0) or 0
        rent   = deal.get("monthly_rent",   0) or 0
        cap    = deal.get("cap_rate",        0) or 0
        max_buy = negotiation.get("max_price_for_buy", 0)
        offer   = negotiation.get("suggested_offer",   0)

        if rec == "BUY":
            return (
                f"This is a solid deal at ${price:,.0f}. "
                f"The {cap:.1f}% cap rate meets our investment threshold "
                f"and the property generates positive cash flow. "
                f"Proceed with due diligence and make an offer."
            )
        elif diagnosis.get("severity") == "high":
            return (
                f"At ${price:,.0f} this property does not work financially. "
                f"Based on the NOI the fair value is around ${max_buy:,.0f}. "
                f"If the seller won't negotiate to ${offer:,.0f} or below, "
                f"walk away and find a better deal."
            )
        else:
            return (
                f"This deal is borderline at ${price:,.0f}. "
                f"With some negotiation to ${offer:,.0f} "
                f"or a rent increase this could become a BUY. "
                f"Make a low offer and see if the seller is motivated."
            )