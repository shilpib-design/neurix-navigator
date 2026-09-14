"""
Comprehensive Unit Test Suite for Phase 3F Economic Routing.
Tests all 25 economic routing, CPVR, cascade, SLA, discovery, session, and pipeline integration requirements.
Uses 100% synthetic/in-memory data with zero live network calls.
"""

import unittest
import math
from core.economic_routing import EconomicRouter, EconomicRoutingDecision, CandidateEconomicProfile
from core.models import CapabilityMetadata, CustomerPreferences, TargetProfile, AcquisitionRequest, HealthState
from core.rate_card import RateCardRegistry, ProviderRateCard
from core.registry import ProviderRegistry
from core.pipeline import UnifiedPipeline
from core.discovery import DiscoveryResult, DiscoverySurface
from core.learning import LearningEngine
from core.optimizer import EconomicOptimizer


class TestEconomicRouting(unittest.TestCase):

    def setUp(self):
        self.rate_card_registry = RateCardRegistry()
        self.router = EconomicRouter(self.rate_card_registry)
        self.registry = ProviderRegistry()
        self.profile = TargetProfile(
            domain="Amazon",
            url_pattern="/dp/*",
            inferred_country="US",
            country_confidence=1.0,
            target_type="pdp",
            location_sensitivity=False,
            browser_likelihood=0.5
        )
        self.prefs = CustomerPreferences(min_success_rate=0.70, max_latency_ms=10000)

    # 1. Basic Candidate Economic Calculation
    def test_01_basic_candidate_economic_calculation(self):
        cap = CapabilityMetadata(
            provider_id="Context.dev",
            capability_id="Context.dev",
            estimated_cost=0.001,
            historical_metrics={"success_rate": 0.90, "validation_rate": 0.85, "avg_latency_ms": 1200, "sample_size": 20}
        )
        econ = self.router.evaluate_candidate(cap, self.profile, self.prefs)
        self.assertEqual(econ.capability_id, "Context.dev")
        self.assertAlmostEqual(econ.base_cost, 0.001)
        self.assertAlmostEqual(econ.estimated_success_probability, 0.90)
        self.assertAlmostEqual(econ.estimated_validation_probability, 0.85)
        self.assertEqual(econ.expected_latency_ms, 1200)

    # 2. CPVR Calculation
    def test_02_cpvr_calculation(self):
        # cost = $0.001, validated_prob = 0.80 -> CPVR = 0.001 / 0.80 = 0.00125
        cap = CapabilityMetadata(
            provider_id="P1",
            capability_id="C1",
            estimated_cost=0.001,
            historical_metrics={"success_rate": 1.0, "validation_rate": 0.80, "avg_latency_ms": 1000, "sample_size": 10}
        )
        econ = self.router.evaluate_candidate(cap, self.profile, self.prefs)
        self.assertAlmostEqual(econ.cpvr, 0.00125, places=5)

    # 3. Zero Probability Safety
    def test_03_zero_probability_handling(self):
        cap = CapabilityMetadata(
            provider_id="ZeroP",
            capability_id="ZeroP",
            estimated_cost=0.005,
            historical_metrics={"success_rate": 0.0, "validation_rate": 0.0, "avg_latency_ms": 1000, "sample_size": 5}
        )
        econ = self.router.evaluate_candidate(cap, self.profile, self.prefs)
        # Check that no DivisionByZero exception was raised and CPVR is safely set
        self.assertTrue(math.isinf(econ.cpvr) or econ.cpvr >= 9999.0)

    # 4. Validation Probability Math
    def test_04_validation_probability(self):
        cap = CapabilityMetadata(
            provider_id="P1",
            capability_id="C1",
            historical_metrics={"success_rate": 0.90, "validation_rate": 0.90, "sample_size": 10}
        )
        econ = self.router.evaluate_candidate(cap, self.profile, self.prefs)
        expected_val = 0.90 * 0.90
        self.assertAlmostEqual(econ.estimated_validated_probability, expected_val, places=4)

    # 5. Cascade Success Probability Math
    def test_05_cascade_success_probability(self):
        c1 = CapabilityMetadata(provider_id="A", capability_id="A", historical_metrics={"validation_rate": 0.50, "avg_latency_ms": 1000})
        c2 = CapabilityMetadata(provider_id="B", capability_id="B", historical_metrics={"validation_rate": 0.80, "avg_latency_ms": 2000})
        # P(cascade val) = P(A) + (1-P(A))*P(B) = 0.50 + 0.50*0.80 = 0.90
        casc_eval = self.router.evaluate_cascade([c1, c2], self.profile)
        self.assertAlmostEqual(casc_eval["expected_validation"], 0.90, places=4)

    # 6. Cascade Expected Cost Math
    def test_06_cascade_expected_cost(self):
        c1 = CapabilityMetadata(provider_id="Context.dev", capability_id="Context.dev", estimated_cost=0.001, historical_metrics={"validation_rate": 0.50, "avg_latency_ms": 1000})
        c2 = CapabilityMetadata(provider_id="String", capability_id="String", estimated_cost=0.002, historical_metrics={"validation_rate": 0.80, "avg_latency_ms": 2000})
        # Cost = Cost(A) + (1-P(A))*Cost(B) = 0.001 + 0.50*0.0015 (from rate card for String)
        cost_c1 = self.rate_card_registry.get_marginal_cost("Context.dev", "Context.dev", domain=self.profile.domain)
        cost_c2 = self.rate_card_registry.get_marginal_cost("String", "String", domain=self.profile.domain)
        expected_cost = cost_c1 + (1.0 - 0.50) * cost_c2
        casc_eval = self.router.evaluate_cascade([c1, c2], self.profile)
        self.assertAlmostEqual(casc_eval["expected_cost"], expected_cost, places=5)

    # 7. Cascade CPVR Math
    def test_07_cascade_cpvr(self):
        c1 = CapabilityMetadata(provider_id="Context.dev", capability_id="Context.dev", estimated_cost=0.001, historical_metrics={"validation_rate": 0.60, "avg_latency_ms": 1000})
        c2 = CapabilityMetadata(provider_id="Scrapfly", capability_id="Scrapfly", estimated_cost=0.002, historical_metrics={"validation_rate": 0.90, "avg_latency_ms": 2000})
        casc_eval = self.router.evaluate_cascade([c1, c2], self.profile)
        exp_val = 0.60 + (1 - 0.60) * 0.90  # 0.96
        exp_cost = 0.001 + 0.40 * 0.002     # 0.0018
        expected_cpvr = exp_cost / exp_val  # 0.001875
        self.assertAlmostEqual(casc_eval["cost_per_validated"], expected_cpvr, places=5)

    # 8. Candidate Ranking by CPVR
    def test_08_candidate_ranking(self):
        c1 = CapabilityMetadata(provider_id="Expensive", capability_id="Expensive", estimated_cost=0.010, historical_metrics={"success_rate": 1.0, "validation_rate": 0.90, "avg_latency_ms": 1000, "sample_size": 10})
        c2 = CapabilityMetadata(provider_id="Cheap", capability_id="Cheap", estimated_cost=0.001, historical_metrics={"success_rate": 1.0, "validation_rate": 0.85, "avg_latency_ms": 1000, "sample_size": 10})
        decision = self.router.route([c1, c2], self.profile, self.prefs)
        self.assertEqual(decision.selected_capability, "Cheap")
        self.assertEqual(decision.ordered_candidates[0], "Cheap")

    # 9. Cheaper but Lower Success Candidate Trade-off
    def test_09_cheaper_but_lower_success_candidate(self):
        # C1: cost $0.001, validation 0.50 -> CPVR $0.0020
        # C2: cost $0.003, validation 0.95 -> CPVR $0.00315
        # C1 should win because its CPVR is lower
        c1 = CapabilityMetadata(provider_id="C1", capability_id="C1", estimated_cost=0.001, historical_metrics={"success_rate": 1.0, "validation_rate": 0.50, "avg_latency_ms": 1000, "sample_size": 10})
        c2 = CapabilityMetadata(provider_id="C2", capability_id="C2", estimated_cost=0.003, historical_metrics={"success_rate": 1.0, "validation_rate": 0.95, "avg_latency_ms": 1000, "sample_size": 10})
        decision = self.router.route([c1, c2], self.profile, CustomerPreferences(min_success_rate=0.40))
        self.assertEqual(decision.selected_capability, "C1")

    # 10. Expensive but High Success Candidate Trade-off
    def test_10_expensive_but_high_success_candidate(self):
        # C1: cost $0.001, validation 0.05 -> CPVR $0.0200
        # C2: cost $0.003, validation 0.95 -> CPVR $0.00315
        # C2 should win because C1's low success rate makes its CPVR much higher
        c1 = CapabilityMetadata(provider_id="C1", capability_id="C1", estimated_cost=0.001, historical_metrics={"success_rate": 1.0, "validation_rate": 0.05, "avg_latency_ms": 1000, "sample_size": 10})
        c2 = CapabilityMetadata(provider_id="C2", capability_id="C2", estimated_cost=0.003, historical_metrics={"success_rate": 1.0, "validation_rate": 0.95, "avg_latency_ms": 1000, "sample_size": 10})
        decision = self.router.route([c1, c2], self.profile, CustomerPreferences(min_success_rate=0.0))
        self.assertEqual(decision.selected_capability, "C2")

    # 11. SLA Latency Rejection
    def test_11_sla_latency_rejection(self):
        # C1: cost $0.0001, latency 15000ms (exceeds max_latency_ms=5000)
        # C2: cost $0.0010, latency 2000ms (within SLA)
        c1 = CapabilityMetadata(provider_id="Slow", capability_id="Slow", estimated_cost=0.0001, historical_metrics={"success_rate": 1.0, "validation_rate": 0.90, "avg_latency_ms": 15000, "sample_size": 10})
        c2 = CapabilityMetadata(provider_id="Fast", capability_id="Fast", estimated_cost=0.0010, historical_metrics={"success_rate": 1.0, "validation_rate": 0.85, "avg_latency_ms": 2000, "sample_size": 10})
        prefs = CustomerPreferences(max_latency_ms=5000)
        decision = self.router.route([c1, c2], self.profile, prefs)
        self.assertEqual(decision.selected_capability, "Fast")
        self.assertTrue(decision.sla_met)

    # 12. SLA Success / Validation Requirement Filtering
    def test_12_sla_success_validation_requirement(self):
        c1 = CapabilityMetadata(provider_id="LowVal", capability_id="LowVal", estimated_cost=0.0001, historical_metrics={"success_rate": 1.0, "validation_rate": 0.30, "avg_latency_ms": 1000, "sample_size": 10})
        c2 = CapabilityMetadata(provider_id="HighVal", capability_id="HighVal", estimated_cost=0.0010, historical_metrics={"success_rate": 1.0, "validation_rate": 0.85, "avg_latency_ms": 1000, "sample_size": 10})
        prefs = CustomerPreferences(min_success_rate=0.80)
        decision = self.router.route([c1, c2], self.profile, prefs)
        self.assertEqual(decision.selected_capability, "HighVal")

    # 13. Unknown Evidence Handling
    def test_13_unknown_evidence_handling(self):
        cap = CapabilityMetadata(
            provider_id="NewProvider",
            capability_id="NewProvider",
            estimated_cost=0.001,
            historical_metrics={}  # Zero sample size
        )
        econ = self.router.evaluate_candidate(cap, self.profile, self.prefs)
        self.assertEqual(econ.historical_sample_size, 0)
        self.assertEqual(econ.confidence, 0.50)
        self.assertLess(econ.estimated_validated_probability, 1.0)

    # 14. Limited Historical Sample Handling
    def test_14_limited_historical_sample(self):
        c_low_sample = CapabilityMetadata(provider_id="LowSample", capability_id="LowSample", estimated_cost=0.001, historical_metrics={"validation_rate": 0.90, "sample_size": 2})
        c_high_sample = CapabilityMetadata(provider_id="HighSample", capability_id="HighSample", estimated_cost=0.001, historical_metrics={"validation_rate": 0.90, "sample_size": 50})
        econ_low = self.router.evaluate_candidate(c_low_sample, self.profile, self.prefs)
        econ_high = self.router.evaluate_candidate(c_high_sample, self.profile, self.prefs)
        self.assertGreater(econ_high.confidence, econ_low.confidence)

    # 15. Discovery Evidence Influence
    def test_15_discovery_evidence_influence(self):
        cap = CapabilityMetadata(
            provider_id="PureHTTP",
            capability_id="pure_http",
            acquisition_method="http",
            estimated_cost=0.0001,
            historical_metrics={"success_rate": 0.80, "validation_rate": 0.80, "sample_size": 10}
        )
        disc_surface = DiscoverySurface(surface_type="json_ld", url="https://amazon.com/dp/1", confidence=0.90)
        disc_res = DiscoveryResult(target="Amazon", surfaces=[disc_surface])

        econ_without = self.router.evaluate_candidate(cap, self.profile, self.prefs, discovery_result=None)
        econ_with = self.router.evaluate_candidate(cap, self.profile, self.prefs, discovery_result=disc_res)

        self.assertGreater(econ_with.estimated_validated_probability, econ_without.estimated_validated_probability)
        self.assertIn("matched_surface", econ_with.discovery_evidence)

    # 16. Weak Discovery Evidence Safety
    def test_16_weak_discovery_evidence_safety(self):
        cap = CapabilityMetadata(
            provider_id="PureHTTP",
            capability_id="pure_http",
            acquisition_method="http",
            estimated_cost=0.0001,
            historical_metrics={"success_rate": 0.50, "validation_rate": 0.50, "sample_size": 10}
        )
        weak_surface = DiscoverySurface(surface_type="json_endpoint", url="https://amazon.com/api/ref", confidence=0.40)
        disc_res = DiscoveryResult(target="Amazon", surfaces=[weak_surface])

        econ = self.router.evaluate_candidate(cap, self.profile, self.prefs, discovery_result=disc_res)
        # Weak discovery evidence should not artificially inflate validation probability to 1.0
        self.assertLess(econ.estimated_validated_probability, 0.90)

    # 17. Session-Assisted HTTP Candidate
    def test_17_session_assisted_http_candidate(self):
        cap_session = CapabilityMetadata(
            provider_id="SessionAssistedHTTP",
            capability_id="session_assisted_http",
            acquisition_method="http",
            estimated_cost=0.00015,
            historical_metrics={"success_rate": 0.95, "validation_rate": 0.90, "avg_latency_ms": 600, "sample_size": 15}
        )
        econ_no_session = self.router.evaluate_candidate(cap_session, self.profile, self.prefs, session_available=False)
        econ_with_session = self.router.evaluate_candidate(cap_session, self.profile, self.prefs, session_available=True)

        self.assertFalse(econ_no_session.eligible)
        self.assertTrue(econ_with_session.eligible)

    # 18. Multiple Candidate Ordering
    def test_18_multiple_candidate_ordering(self):
        caps = [
            CapabilityMetadata(provider_id="P1", capability_id="C1", estimated_cost=0.003, historical_metrics={"validation_rate": 0.90, "sample_size": 10}),
            CapabilityMetadata(provider_id="P2", capability_id="C2", estimated_cost=0.001, historical_metrics={"validation_rate": 0.85, "sample_size": 10}),
            CapabilityMetadata(provider_id="P3", capability_id="C3", estimated_cost=0.002, historical_metrics={"validation_rate": 0.88, "sample_size": 10}),
        ]
        decision = self.router.route(caps, self.profile, self.prefs)
        self.assertEqual(decision.selected_capability, "C2")
        self.assertEqual(decision.ordered_candidates[0], "C2")
        self.assertEqual(decision.ordered_candidates[1], "C3")
        self.assertEqual(decision.ordered_candidates[2], "C1")

    # 19. Explainable Routing Decision
    def test_19_explainable_routing_decision(self):
        c1 = CapabilityMetadata(provider_id="P1", capability_id="C1", estimated_cost=0.001, historical_metrics={"validation_rate": 0.85, "avg_latency_ms": 1000, "sample_size": 10})
        decision = self.router.route([c1], self.profile, self.prefs)
        self.assertIn("Selected 'C1'", decision.routing_reason)
        self.assertIn("lowest expected cost per validated result", decision.routing_reason)

    # 20. EconomicRoutingDecision Serialization
    def test_20_economic_routing_decision_serialization(self):
        decision = EconomicRoutingDecision(
            selected_capability="Context.dev",
            ordered_candidates=["Context.dev", "String"],
            selected_cascade=["Context.dev", "String"],
            expected_cost=0.001,
            expected_cpvr=0.0012,
            expected_success_probability=0.90,
            expected_validation_probability=0.85,
            expected_latency_ms=1200.0,
            sla_met=True,
            routing_reason="CPVR optimal"
        )
        d = decision.to_dict()
        self.assertEqual(d["selected_capability"], "Context.dev")
        self.assertEqual(d["expected_cpvr"], 0.0012)
        self.assertTrue(d["sla_met"])

    # 21. Fallback Cascade Generation
    def test_21_fallback_cascade_generation(self):
        caps = [
            CapabilityMetadata(provider_id="P1", capability_id="C1", estimated_cost=0.001, historical_metrics={"validation_rate": 0.80, "sample_size": 10}),
            CapabilityMetadata(provider_id="P2", capability_id="C2", estimated_cost=0.002, historical_metrics={"validation_rate": 0.85, "sample_size": 10}),
            CapabilityMetadata(provider_id="P3", capability_id="C3", estimated_cost=0.003, historical_metrics={"validation_rate": 0.90, "sample_size": 10}),
        ]
        decision = self.router.route(caps, self.profile, self.prefs)
        self.assertEqual(len(decision.selected_cascade), 3)
        self.assertEqual(decision.selected_cascade[0], "C1")

    # 22. UnifiedPipeline Integration
    def test_22_unified_pipeline_integration(self):
        class MockAdapter:
            def fetch(self, target):
                return {
                    "status_code": 200,
                    "success": True,
                    "raw_content": b"<html>" + (b"z" * 150) + b"</html>",
                    "error_message": None
                }

        pipeline = UnifiedPipeline(exploration_rate=0.0)
        for cap in pipeline.registry.list_capabilities():
            pipeline.registry.bind_adapter(cap.capability_id, MockAdapter())

        pipeline.extractor_registry.register("Amazon", lambda html, req: {
            "product_name": "Widget", "price": "$10", "availability": "InStock"
        })

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B00123")
        res = pipeline.process_request(req)

        self.assertIn("routing_decision", res)
        self.assertTrue(res["routing_decision"]["sla_met"])
        self.assertIn("selected_capability", res["routing_decision"])

    # 23. Existing Optimizer Compatibility
    def test_23_existing_optimizer_compatibility(self):
        optimizer = EconomicOptimizer(self.rate_card_registry, exploration_rate=0.0)
        c1 = CapabilityMetadata(provider_id="P1", capability_id="C1", estimated_cost=0.001, historical_metrics={"validation_rate": 0.85, "avg_latency_ms": 1000})
        cascade, eval_res, _ = optimizer.select_optimal_strategy([c1], self.profile, self.prefs)
        self.assertEqual(cascade[0].capability_id, "C1")
        self.assertIn("cost_per_validated", eval_res)

    # 24. Existing Learning Engine Compatibility
    def test_24_existing_learning_compatibility(self):
        learning = LearningEngine(self.registry)
        obs = learning.record_observation(
            capability_id="Context.dev",
            domain="Amazon",
            country="US",
            success=True,
            validated=True,
            latency_ms=1000,
            bytes_count=15000,
            estimated_cost=0.001
        )
        self.assertTrue(obs["validated"])
        self.assertEqual(obs["capability_id"], "Context.dev")

    # 25. Full Regression Suite Check
    def test_25_full_regression_suite(self):
        class MockAdapter:
            def fetch(self, target):
                return {
                    "status_code": 200,
                    "success": True,
                    "raw_content": b"<html>" + (b"r" * 150) + b"</html>",
                    "error_message": None
                }

        pipeline = UnifiedPipeline(exploration_rate=0.0)
        for cap in pipeline.registry.list_capabilities():
            pipeline.registry.bind_adapter(cap.capability_id, MockAdapter())

        pipeline.extractor_registry.register("Purplle", lambda html, req: {
            "product_name": "Lotion", "price": "$15", "availability": "InStock"
        })

        req = AcquisitionRequest(url="https://www.purplle.com/product/lotion")
        res = pipeline.process_request(req)
        self.assertTrue(res["validated"])
        self.assertIn("routing_decision", res)


if __name__ == "__main__":
    unittest.main()
