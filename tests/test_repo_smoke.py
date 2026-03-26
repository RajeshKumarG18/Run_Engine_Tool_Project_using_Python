import io
import unittest
from contextlib import redirect_stdout

from attention_arbitrage_engine import AttentionArbitrage, FacelessRevenueEngine, MicroOfferStack
from automation_hub import run_automation_cycle


class RepoSmokeTests(unittest.TestCase):
    def test_attention_arbitrage_scores_are_sorted(self):
        arbitrage = AttentionArbitrage()
        opportunities = arbitrage.scan_market_gaps()
        scores = [item["arbitrage_score"] for item in opportunities]

        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(len(opportunities), 6)

    def test_offer_stack_metrics_are_coherent(self):
        stack = MicroOfferStack()
        offers = stack.generate_offer_stack()
        metrics = stack.calculate_stack_value()

        expected_conversion_rate = sum(offer["conversion_estimate"] for offer in offers)
        expected_value = sum(offer["price"] * offer["conversion_estimate"] for offer in offers)

        self.assertAlmostEqual(metrics["total_conversion_rate"], expected_conversion_rate)
        self.assertAlmostEqual(metrics["expected_value_per_visitor"], expected_value)
        self.assertGreater(metrics["average_order_value"], 0)

    def test_campaign_projection_uses_reasonable_conversion_math(self):
        engine = FacelessRevenueEngine()
        with redirect_stdout(io.StringIO()):
            engine.initialize()

        result = engine.run_campaign("Smoke Test", 100)

        self.assertLess(result["expected_conversions"], 100)
        self.assertGreater(result["expected_revenue"], 0)
        self.assertLess(result["conversion_rate"], 1)

    def test_automation_cycle_returns_expected_summary_keys(self):
        with redirect_stdout(io.StringIO()):
            result = run_automation_cycle()

        self.assertEqual(
            set(result.keys()),
            {
                "viral_opportunities",
                "content_generated",
                "posts_scheduled",
                "orders_processed",
                "revenue_generated",
            },
        )


if __name__ == "__main__":
    unittest.main()
