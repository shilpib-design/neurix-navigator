"""
Comprehensive Unit Test Suite for Neurix Navigator v0.1 Core Foundation.

Tests cover all 15 core architectural requirements without making live network calls
or consuming vendor API credits.
"""

import unittest
import time
from core.models import (
    AcquisitionRequest,
    CustomerPreferences,
    TargetProfile,
    CapabilityMetadata,
    HealthState,
    FailureCategory,
    PriorityPreference
)
from core.intelligence import TargetIntelligence
from core.rate_card import RateCardRegistry, ProviderRateCard, VolumeTier
from core.registry import ProviderRegistry
from core.candidate import CandidateGenerator
from core.optimizer import EconomicOptimizer
from core.fallback import FallbackManager
from core.learning import LearningEngine
from core.policy import PolicyEngine
from core.meter import CustomerUsageMeter
from core.storage import LeanStorageManager
from core.pipeline import UnifiedPipeline


class TestNavigatorV01Core(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry()
        self.rate_card_registry = RateCardRegistry()

    # 1. Provider Registration
    def test_01_provider_registration(self):
        cap = CapabilityMetadata(
            provider_id="NewVendor",
            capability_id="NewVendor_API",
            enabled=True,
            estimated_cost=0.0008
        )
        self.registry.register(cap)
        retrieved = self.registry.get("NewVendor_API")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.provider_id, "NewVendor")

    # 2. Provider Addition Without Decision Engine Modification
    def test_02_provider_addition_without_engine_changes(self):
        optimizer = EconomicOptimizer(self.rate_card_registry, exploration_rate=0.0)
        generator = CandidateGenerator(self.registry)

        profile = TargetProfile(
            domain="Amazon",
            url_pattern="/dp/*",
            inferred_country="US",
            country_confidence=1.0,
            target_type="pdp",
            location_sensitivity=False,
            browser_likelihood=0.6,
            required_capabilities=["pdp_extraction"]
        )
        prefs = CustomerPreferences()

        # Add brand new capability
        new_cap = CapabilityMetadata(
            provider_id="UltraScrape",
            capability_id="UltraScrape_API",
            enabled=True,
            country_capabilities=["US"],
            target_capabilities=["pdp"],
            estimated_cost=0.0001,  # Cheaper cost
            historical_metrics={"success_rate": 0.99, "validation_rate": 0.95, "avg_latency_ms": 1000, "sample_size": 50}
        )
        self.registry.register(new_cap)
        self.rate_card_registry.register(ProviderRateCard(
            provider_id="UltraScrape",
            capability_id="UltraScrape_API",
            base_rate=0.0001
        ))

        candidates = generator.generate_candidates(profile, prefs)
        selected_cascade, metrics, _ = optimizer.select_optimal_strategy(candidates, profile, prefs)

        self.assertIn("UltraScrape_API", [c.capability_id for c in candidates])
        self.assertEqual(selected_cascade[0].capability_id, "UltraScrape_API")

    # 3. Provider Disabling
    def test_03_provider_disabling(self):
        generator = CandidateGenerator(self.registry)
        profile = TargetProfile(
            domain="Flipkart",
            url_pattern="/p/*",
            inferred_country="IN",
            country_confidence=1.0,
            target_type="pdp",
            location_sensitivity=False,
            browser_likelihood=0.4
        )
        prefs = CustomerPreferences()

        # Disable Context.dev
        self.registry.set_enabled("Context.dev", False)
        candidates = generator.generate_candidates(profile, prefs)
        cand_ids = [c.capability_id for c in candidates]

        self.assertNotIn("Context.dev", cand_ids)
        # Verify metadata remains accessible in registry
        cap = self.registry.get("Context.dev")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.current_health, HealthState.DISABLED)

    # 4. Country Capability Filtering
    def test_04_country_capability_filtering(self):
        generator = CandidateGenerator(self.registry)
        prefs = CustomerPreferences()

        # US Profile
        us_profile = TargetProfile(domain="Kroger", url_pattern="/p/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.9)
        us_cands = generator.generate_candidates(us_profile, prefs)
        for c in us_cands:
            self.assertIn("US", c.country_capabilities)

        # IN Profile
        in_profile = TargetProfile(domain="Purplle", url_pattern="/p/*", inferred_country="IN", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.2)
        in_cands = generator.generate_candidates(in_profile, prefs)
        for c in in_cands:
            self.assertIn("IN", c.country_capabilities)

    # 5. Target Profile Generation
    def test_05_target_profile_generation(self):
        req1 = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        prof1 = TargetIntelligence.analyze(req1)
        self.assertEqual(prof1.domain, "Amazon")
        self.assertEqual(prof1.inferred_country, "US")

        req2 = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm123456789")
        prof2 = TargetIntelligence.analyze(req2)
        self.assertEqual(prof2.domain, "Flipkart")
        self.assertEqual(prof2.inferred_country, "IN")

    # 6. Candidate Generation
    def test_06_candidate_generation(self):
        generator = CandidateGenerator(self.registry)
        profile = TargetIntelligence.analyze(AcquisitionRequest(url="https://www.purplle.com/product/cream"))
        candidates = generator.generate_candidates(profile, CustomerPreferences())
        self.assertGreater(len(candidates), 0)

    # 7. Cost-Based Single Strategy Selection
    def test_07_cost_based_single_strategy_selection(self):
        optimizer = EconomicOptimizer(self.rate_card_registry, exploration_rate=0.0)

        c1 = CapabilityMetadata(provider_id="P1", capability_id="C1", estimated_cost=0.010, historical_metrics={"validation_rate": 0.90, "avg_latency_ms": 1000})
        c2 = CapabilityMetadata(provider_id="P2", capability_id="C2", estimated_cost=0.001, historical_metrics={"validation_rate": 0.85, "avg_latency_ms": 1000})

        profile = TargetProfile(domain="Test", url_pattern="/p/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.5)
        prefs = CustomerPreferences(min_success_rate=0.70)

        selected_cascade, metrics, _ = optimizer.select_optimal_strategy([c1, c2], profile, prefs)
        # C2 should be chosen first because its cost per validated is much lower ($0.001/0.85 < $0.010/0.90)
        self.assertEqual(selected_cascade[0].capability_id, "C2")

    # 8. Cascade Selection Math (A -> B -> C)
    def test_08_cascade_selection_math(self):
        optimizer = EconomicOptimizer(self.rate_card_registry, exploration_rate=0.0)

        c1 = CapabilityMetadata(provider_id="CheapAPI", capability_id="CheapAPI", estimated_cost=0.001, historical_metrics={"validation_rate": 0.50, "avg_latency_ms": 1000})
        c2 = CapabilityMetadata(provider_id="BrowserProxy", capability_id="BrowserProxy", estimated_cost=0.005, historical_metrics={"validation_rate": 0.90, "avg_latency_ms": 5000})

        profile = TargetProfile(domain="Test", url_pattern="/p/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.5)

        # Dual cascade (CheapAPI -> BrowserProxy)
        # Expected validation = 0.50 + (1 - 0.50)*0.90 = 0.95
        # Expected cost = 0.001 + (1 - 0.50)*0.005 = 0.0035
        # Cost per validated = 0.0035 / 0.95 = 0.003684
        eval_cascade = optimizer.evaluate_cascade([c1, c2], profile)
        self.assertAlmostEqual(eval_cascade["expected_validation"], 0.95, places=4)
        self.assertAlmostEqual(eval_cascade["expected_cost"], 0.0035, places=4)

    # 9. Failure-Aware Fallback
    def test_09_failure_aware_fallback(self):
        fallback_mgr = FallbackManager(self.registry)

        cap_api = CapabilityMetadata(provider_id="API1", capability_id="API1", browser_support=False, historical_metrics={"validation_rate": 0.5, "avg_latency_ms": 2000})
        cap_browser = CapabilityMetadata(provider_id="Browser1", capability_id="Browser1", browser_support=True, historical_metrics={"validation_rate": 0.9, "avg_latency_ms": 10000})

        remaining = [cap_api, cap_browser]

        # On BLOCK_PAGE failure, Browser capability should be promoted to front
        adjusted = fallback_mgr.adjust_cascade_on_failure(remaining, cap_api, FailureCategory.BLOCK_PAGE.value)
        self.assertEqual(adjusted[0].capability_id, "Browser1")

    # 10. Confidence Calculation
    def test_10_confidence_calculation(self):
        engine = PolicyEngine()
        conf_low = engine.calculate_confidence(sample_size=2, success_rate=0.50)
        conf_high = engine.calculate_confidence(sample_size=50, success_rate=0.90)
        self.assertGreater(conf_high, conf_low)

    # 11. Real-Time Policy Promotion
    def test_11_realtime_policy_promotion(self):
        engine = PolicyEngine(min_sample_size=3, min_confidence=0.50, min_improvement_margin=0.05)
        profile = TargetProfile(domain="Purplle", url_pattern="/p/*", inferred_country="IN", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.2)

        # Baseline initial policy
        engine.evaluate_and_promote(profile, ["Context.dev"], {"cost_per_validated": 0.0020}, sample_size=1)

        # Evaluate superior cascade with sample size = 5
        promoted, new_policy = engine.evaluate_and_promote(
            profile, ["String", "Context.dev"], {"cost_per_validated": 0.0010}, sample_size=5
        )

        self.assertTrue(promoted)
        self.assertEqual(new_policy.selected_cascade, ["String", "Context.dev"])

    # 12. Billing & Metering
    def test_12_billing_metering(self):
        meter = CustomerUsageMeter(base_customer_price=0.05, infra_cost_per_req=0.0001)
        req = AcquisitionRequest(url="https://amazon.com/dp/123", customer_id="cust_test")

        record = meter.record_transaction(
            request=req,
            target_domain="Amazon",
            validated_result=True,
            response_size_bytes=50000,
            processing_time_ms=1200,
            provider_cost=0.0020
        )

        self.assertEqual(record.customer_id, "cust_test")
        self.assertEqual(record.billable_unit, 1)
        self.assertEqual(record.customer_price, 0.05)
        self.assertEqual(record.provider_cost, 0.0020)
        self.assertEqual(record.gross_margin, 0.0479)

    # 13. Telemetry Generation
    def test_13_telemetry_generation(self):
        learning = LearningEngine(self.registry)
        obs = learning.record_observation(
            capability_id="Context.dev",
            domain="Amazon",
            country="US",
            success=True,
            validated=True,
            latency_ms=1200,
            bytes_count=45000,
            estimated_cost=0.0010
        )
        self.assertEqual(obs["capability_id"], "Context.dev")
        self.assertTrue(obs["validated"])

    # 14. Raw Data TTL Metadata Storage
    def test_14_raw_data_ttl_metadata(self):
        storage = LeanStorageManager(raw_ttl_seconds=600, retain_raw_html=False)
        meta = storage.store_raw_payload_metadata(
            request_id="req_001",
            capability_id="Context.dev",
            html_payload="<html><body>Sensitive or Large Content</body></html>"
        )

        self.assertEqual(meta["request_id"], "req_001")
        self.assertEqual(meta["content_preview"], "SUPPRESSED_PER_LEAN_STORAGE_POLICY")
        self.assertGreater(meta["expires_at"], meta["created_at"])

    # 16. Provider Re-enabling & Lifecycle Preservation
    def test_16_provider_reenabling(self):
        generator = CandidateGenerator(self.registry)
        profile = TargetProfile(domain="Amazon", url_pattern="/dp/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.5)
        prefs = CustomerPreferences()

        # Step 1: Disable Context.dev
        self.registry.set_enabled("Context.dev", False)
        cands_disabled = generator.generate_candidates(profile, prefs)
        self.assertNotIn("Context.dev", [c.capability_id for c in cands_disabled])

        # Step 2: Re-enable Context.dev
        self.registry.set_enabled("Context.dev", True)
        cands_enabled = generator.generate_candidates(profile, prefs)
        self.assertIn("Context.dev", [c.capability_id for c in cands_enabled])

        # Step 3: Verify historical metrics preserved
        cap = self.registry.get("Context.dev")
        self.assertEqual(cap.current_health, HealthState.AVAILABLE)
        self.assertGreater(cap.historical_metrics["sample_size"], 0)

    # 17. Volume Tier & Dynamic Rate Card Calculation
    def test_17_volume_tier_marginal_rate_calculation(self):
        rate_card = ProviderRateCard(
            provider_id="TieredVendor",
            capability_id="TieredVendor_API",
            base_rate=0.0010,
            volume_tiers=[
                VolumeTier(min_volume=0, max_volume=10000, unit_cost=0.0010),
                VolumeTier(min_volume=10000, max_volume=50000, unit_cost=0.0007),
                VolumeTier(min_volume=50000, max_volume=None, unit_cost=0.0004)
            ]
        )
        self.rate_card_registry.register(rate_card)

        # Tier 1 (Volume = 5,000)
        rate_t1 = self.rate_card_registry.get_marginal_cost("TieredVendor", "TieredVendor_API")
        self.assertEqual(rate_t1, 0.0010)

        # Tier 2 (Volume = 15,000)
        self.rate_card_registry.record_usage("TieredVendor", "TieredVendor_API", units=15000)
        rate_t2 = self.rate_card_registry.get_marginal_cost("TieredVendor", "TieredVendor_API")
        self.assertEqual(rate_t2, 0.0007)

        # Tier 3 (Volume = 60,000)
        self.rate_card_registry.record_usage("TieredVendor", "TieredVendor_API", units=45000)
        rate_t3 = self.rate_card_registry.get_marginal_cost("TieredVendor", "TieredVendor_API")
        self.assertEqual(rate_t3, 0.0004)


if __name__ == "__main__":
    unittest.main()

