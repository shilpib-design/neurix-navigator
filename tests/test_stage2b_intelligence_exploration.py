import unittest

from core.candidate import CandidateGenerator
from core.exploration import ExplorationBudget, ExplorationPlanner
from core.intelligence import TargetIntelligence
from core.models import (
    AcquisitionRequest,
    CapabilityMetadata,
    CustomerPreferences,
    HealthState,
    TargetProfile,
)
from core.optimizer import EconomicOptimizer
from core.pipeline import UnifiedPipeline
from core.rate_card import RateCardRegistry
from core.registry import ProviderRegistry


class TestStage2BTargetIntelligence(unittest.TestCase):
    def profile(self, url, country=None, parameters=None):
        return TargetIntelligence.analyze(
            AcquisitionRequest(url=url, country=country, parameters=parameters or {})
        )

    def test_known_domains_preserve_normalization_and_country(self):
        cases = {
            "https://www.amazon.com/dp/123": ("Amazon", "US"),
            "https://www.flipkart.com/product/p/123": ("Flipkart", "IN"),
            "https://www.purplle.com/product/cream": ("Purplle", "IN"),
            "https://www.kroger.com/p/123": ("Kroger", "US"),
        }
        for url, expected in cases.items():
            profile = self.profile(url)
            self.assertEqual((profile.domain, profile.inferred_country), expected)
            self.assertGreater(profile.country_confidence, 0.9)

    def test_unknown_domain_is_generic_and_does_not_invent_country(self):
        profile = self.profile("https://shop.example.com/")
        self.assertEqual(profile.domain, "Generic")
        self.assertEqual(profile.inferred_country, "Unknown")
        self.assertEqual(profile.country_confidence, 0.0)
        self.assertEqual(profile.target_type, "homepage")

    def test_explicit_country_takes_precedence(self):
        profile = self.profile("https://www.amazon.com/dp/123", country="de")
        self.assertEqual(profile.inferred_country, "DE")
        self.assertEqual(profile.country_confidence, 1.0)

    def test_country_code_tlds(self):
        expected = {
            ".in": "IN", ".co.uk": "GB", ".ca": "CA", ".de": "DE",
            ".fr": "FR", ".au": "AU", ".sg": "SG",
        }
        for suffix, country in expected.items():
            profile = self.profile(f"https://shop.example{suffix}/product/1")
            self.assertEqual(profile.inferred_country, country)
            self.assertEqual(profile.country_confidence, 0.9)

    def test_com_does_not_imply_high_confidence_us(self):
        profile = self.profile("https://shop.example.com/product/1")
        self.assertNotEqual(profile.inferred_country, "US")
        self.assertLess(profile.country_confidence, 0.9)

    def test_product_patterns(self):
        for url in (
            "https://example.com/dp/123",
            "https://example.com/product/123",
            "https://example.com/item/123",
        ):
            profile = self.profile(url)
            self.assertEqual(profile.target_type, "pdp")

    def test_search_category_cart_checkout_and_homepage_patterns(self):
        cases = {
            "https://example.com/search?q=shoes": ("search", "/search/*"),
            "https://example.com/category/shoes": ("category", "/category/*"),
            "https://example.com/cart": ("cart", "/cart/*"),
            "https://example.com/checkout": ("checkout", "/checkout/*"),
            "https://example.com/": ("homepage", "/"),
        }
        for url, expected in cases.items():
            profile = self.profile(url)
            self.assertEqual((profile.target_type, profile.url_pattern), expected)

    def test_location_sensitive_indicators(self):
        for url in (
            "https://example.com/product/1?postalCode=10001",
            "https://example.com/product/1?location=store",
        ):
            self.assertTrue(self.profile(url).location_sensitivity)
        self.assertTrue(self.profile(
            "https://example.com/product/1", parameters={"pincode": "560001"}
        ).location_sensitivity)

    def test_ambiguous_url_is_unknown(self):
        profile = self.profile("https://example.com/account/settings")
        self.assertEqual(profile.target_type, "unknown")
        self.assertEqual(profile.url_pattern, "/unknown/*")


class TestStage2BExploration(unittest.TestCase):
    def setUp(self):
        self.profile = TargetProfile(
            domain="Generic",
            url_pattern="/unknown/*",
            inferred_country="Unknown",
            country_confidence=0.0,
            target_type="unknown",
            location_sensitivity=False,
            browser_likelihood=0.5,
        )
        self.preferences = CustomerPreferences(max_latency_ms=5000)
        self.planner = ExplorationPlanner(default_max_attempts=2)

    def capability(self, capability_id, **metrics):
        return CapabilityMetadata(
            provider_id=capability_id,
            capability_id=capability_id,
            country_capabilities=["US"],
            target_capabilities=["generic"],
            historical_metrics=metrics,
        )

    def test_unknown_target_candidates_are_eligible_and_planner_is_bounded(self):
        candidates = [
            self.capability("new-a", sample_size=0, avg_latency_ms=1000),
            self.capability("new-b", sample_size=0, avg_latency_ms=2000),
            self.capability("new-c", sample_size=0, avg_latency_ms=3000),
        ]
        compatible = [
            cap for cap in candidates
            if CandidateGenerator.is_compatible(cap, self.profile, self.preferences)
        ]
        decisions = self.planner.plan(
            compatible, self.profile, self.preferences, ExplorationBudget(max_attempts=2)
        )
        self.assertEqual([decision.capability_id for decision in decisions], ["new-a", "new-b"])
        self.assertLessEqual(len(decisions), 2)

    def test_low_sample_capability_is_prioritized_over_established_evidence(self):
        candidates = [
            self.capability("established", sample_size=20, validation_rate=0.95, avg_latency_ms=1000),
            self.capability("limited", sample_size=1, validation_rate=0.5, avg_latency_ms=1000),
        ]
        decisions = self.planner.plan(
            candidates, self.profile, self.preferences, ExplorationBudget(max_attempts=1)
        )
        self.assertEqual(decisions[0].capability_id, "limited")

    def test_strong_negative_evidence_is_suppressed(self):
        candidate = self.capability(
            "failed", sample_size=20, validation_rate=0.1,
            failure_count=5, avg_latency_ms=1000
        )
        self.assertEqual(
            self.planner.plan(
                [candidate], self.profile, self.preferences,
                ExplorationBudget(max_attempts=1)
            ),
            [],
        )

    def test_incompatible_and_sla_violating_capabilities_are_never_selected(self):
        wrong_type = CapabilityMetadata(
            provider_id="wrong-type", capability_id="wrong-type",
            target_capabilities=["pdp"], country_capabilities=["US"],
            historical_metrics={"sample_size": 0, "avg_latency_ms": 1000},
        )
        too_slow = self.capability("too-slow", sample_size=0, avg_latency_ms=10000)
        self.assertEqual(
            self.planner.plan(
                [wrong_type, too_slow], self.profile, self.preferences,
                ExplorationBudget(max_attempts=2)
            ),
            [],
        )

    def test_budget_consumption_and_exhaustion_are_enforced(self):
        candidate = self.capability("new", sample_size=0, avg_latency_ms=1000)
        budget = ExplorationBudget(max_attempts=1)
        first = self.planner.plan([candidate], self.profile, self.preferences, budget)
        second = self.planner.plan([candidate], self.profile, self.preferences, budget)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(budget.attempts_consumed, 1)
        self.assertEqual(budget.remaining, 0)
        self.assertFalse(budget.allowed)

    def test_planner_is_deterministic_for_identical_inputs(self):
        candidates = [
            self.capability("b", sample_size=0, avg_latency_ms=1000),
            self.capability("a", sample_size=0, avg_latency_ms=1000),
        ]
        def plan():
            return [
                decision.capability_id for decision in self.planner.plan(
                    candidates, self.profile, self.preferences,
                    ExplorationBudget(max_attempts=2)
                )
            ]
        self.assertEqual(plan(), plan())

    def test_optimizer_keeps_economic_selection_without_random_exploration(self):
        optimizer = EconomicOptimizer(RateCardRegistry(), exploration_rate=1.0)
        cheap = self.capability(
            "cheap", sample_size=20, validation_rate=0.9,
            avg_latency_ms=1000, estimated_cost=0.001
        )
        expensive = self.capability(
            "expensive", sample_size=20, validation_rate=0.9,
            avg_latency_ms=1000, estimated_cost=0.01
        )
        selected, metrics, is_exploration = optimizer.select_optimal_strategy(
            [cheap, expensive], self.profile, self.preferences
        )
        self.assertEqual(selected[0].capability_id, "cheap")
        self.assertFalse(is_exploration)
        self.assertIn("cost_per_validated", metrics)

    def test_pipeline_exposes_planning_without_execution(self):
        pipeline = UnifiedPipeline(registry=ProviderRegistry(), exploration_rate=1.0)
        decisions = pipeline.plan_exploration(
            AcquisitionRequest(url="https://unknown.example.com/")
        )
        self.assertLessEqual(len(decisions), 2)
        self.assertTrue(all(decision.context_key for decision in decisions))


if __name__ == "__main__":
    unittest.main()
