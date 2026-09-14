"""
Comprehensive Unit Test Suite for Stage 2C Controlled Live Exploration.

Tests cover all 15 Stage 2C requirements using in-memory mock adapters without
making live network calls or consuming vendor credits.
"""

import unittest
from typing import Dict, Any

from core.models import (
    AcquisitionRequest,
    CustomerPreferences,
    TargetProfile,
    CapabilityMetadata,
    HealthState,
    FailureCategory
)
from core.registry import ProviderRegistry
from core.rate_card import RateCardRegistry
from core.candidate import CandidateGenerator
from core.exploration import ExplorationPlanner, ExplorationBudget
from core.exploration_executor import ExplorationExecutor, ControlledExplorationResult
from core.learning import LearningEngine
from core.policy import PolicyEngine
from core.pipeline import UnifiedPipeline
from providers.base import BaseProvider
from telemetry.models import ObservationStatus


class MockSuccessProvider(BaseProvider):
    """Mock provider adapter returning valid HTML."""

    def __init__(self, name: str = "MockSuccess"):
        super().__init__(name=name, env_var="MOCK_ENV_VAR")
        self.received_payloads = []

    def get_api_key(self) -> str:
        return "mock_key"

    def _fetch_raw(self, target: Dict[str, Any], api_key: str):
        self.received_payloads.append(target)
        html = b"<html><body><h1>Test Product</h1><div id='price'>$29.99</div><div id='availability'>InStock</div></body></html>"
        return 200, html, "text/html"


class MockValidationFailureProvider(BaseProvider):
    """Mock provider adapter returning HTML that fails validation (missing price)."""

    def __init__(self, name: str = "MockValFail"):
        super().__init__(name=name, env_var="MOCK_ENV_VAR")

    def get_api_key(self) -> str:
        return "mock_key"

    def _fetch_raw(self, target: Dict[str, Any], api_key: str):
        html = b"<html><body><h1>Incomplete Item</h1></body></html>"
        return 200, html, "text/html"


class MockHttpFailureProvider(BaseProvider):
    """Mock provider adapter returning HTTP 500 error."""

    def __init__(self, name: str = "MockHttpFail"):
        super().__init__(name=name, env_var="MOCK_ENV_VAR")

    def get_api_key(self) -> str:
        return "mock_key"

    def _fetch_raw(self, target: Dict[str, Any], api_key: str):
        return 500, b"", "text/html"


class TestStage2CControlledLiveExploration(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry()
        self.rate_card_registry = RateCardRegistry()
        self.learning_engine = LearningEngine(self.registry)
        self.policy_engine = PolicyEngine(min_sample_size=5, min_confidence=0.65)
        self.pipeline = UnifiedPipeline(
            registry=self.registry,
            rate_card_registry=self.rate_card_registry
        )

    # 1. Successful exploration (validated result on first attempt)
    def test_01_successful_exploration_first_attempt(self):
        mock_adapter = MockSuccessProvider("P1")
        self.registry.bind_adapter("Context.dev", mock_adapter)
        # Give Context.dev highest exploration priority for deterministic selection
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        budget = ExplorationBudget(max_attempts=2)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertTrue(res.validated)
        self.assertEqual(res.stop_reason, "VALIDATED_RESULT_FOUND")
        self.assertEqual(len(res.attempts), 1)
        self.assertEqual(res.attempts[0]["capability_id"], "Context.dev")
        self.assertEqual(res.attempts[0]["status_code"], 200)

    # 2. Acquisition success followed by validation failure and bounded fallback exploration
    def test_02_validation_failure_triggers_fallback_exploration(self):
        fail_adapter = MockValidationFailureProvider("P_ValFail")
        success_adapter = MockSuccessProvider("P_Success")

        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", success_adapter)

        # Set priorities: Context.dev first (sample_size 0), String second (sample_size 1)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0
        self.registry.get("String").historical_metrics["sample_size"] = 1

        req = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm12345")
        budget = ExplorationBudget(max_attempts=3)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertTrue(res.validated)
        self.assertEqual(res.stop_reason, "VALIDATED_RESULT_FOUND")
        self.assertEqual(len(res.attempts), 2)
        self.assertFalse(res.attempts[0]["validated"])
        self.assertTrue(res.attempts[1]["validated"])

    # 3. Exploration budget exhaustion
    def test_03_exploration_budget_exhaustion(self):
        fail_adapter = MockValidationFailureProvider("P_Fail")
        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", fail_adapter)

        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0

        req = AcquisitionRequest(url="https://www.purplle.com/product/cream")
        budget = ExplorationBudget(max_attempts=1)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertFalse(res.success)
        self.assertEqual(res.stop_reason, "BUDGET_EXHAUSTED")
        self.assertEqual(len(res.attempts), 1)
        self.assertEqual(res.budget_consumed, 1)

    # 4. Budget cannot be exceeded
    def test_04_budget_cannot_be_exceeded(self):
        fail_adapter = MockValidationFailureProvider("P_Fail")
        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", fail_adapter)
        self.registry.bind_adapter("Scrapfly", fail_adapter)

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B009999999")
        budget = ExplorationBudget(max_attempts=2)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertLessEqual(len(res.attempts), 2)
        self.assertLessEqual(res.budget_consumed, 2)
        self.assertFalse(res.success)

    # 5. Incompatible candidates are excluded
    def test_05_incompatible_candidates_excluded(self):
        # Disable String
        self.registry.set_enabled("String", False)
        mock_adapter = MockSuccessProvider("P_Context")
        self.registry.bind_adapter("Context.dev", mock_adapter)

        req = AcquisitionRequest(url="https://www.kroger.com/p/milk")
        budget = ExplorationBudget(max_attempts=3)

        res = self.pipeline.execute_exploration(req, budget)

        attempted_ids = [a["capability_id"] for a in res.attempts]
        self.assertNotIn("String", attempted_ids)

    # 6. Required country preserved through execution path
    def test_06_required_country_preserved_in_adapter_payload(self):
        mock_adapter = MockSuccessProvider("P_India")
        self.registry.bind_adapter("String", mock_adapter)
        self.registry.get("String").historical_metrics["sample_size"] = 0

        req = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm999", country="IN")
        budget = ExplorationBudget(max_attempts=1)

        self.pipeline.execute_exploration(req, budget)

        self.assertGreater(len(mock_adapter.received_payloads), 0)
        self.assertEqual(mock_adapter.received_payloads[0]["country"], "IN")

    # 7. Unsupported geography represented honestly
    def test_07_unsupported_geography_excluded(self):
        # Create capability supporting only US
        us_only_cap = CapabilityMetadata(
            provider_id="USOnlyVendor",
            capability_id="USOnlyVendor_API",
            enabled=True,
            country_capabilities=["US"],
            target_capabilities=["pdp"]
        )
        self.registry.register(us_only_cap)

        profile = TargetProfile(
            domain="Flipkart",
            url_pattern="/p/*",
            inferred_country="IN",
            country_confidence=1.0,
            target_type="pdp",
            location_sensitivity=False,
            browser_likelihood=0.2
        )
        prefs = CustomerPreferences()

        self.assertFalse(CandidateGenerator.is_compatible(us_only_cap, profile, prefs))

    # 8. Every actual attempt creates telemetry
    def test_08_every_attempt_creates_telemetry(self):
        adapter1 = MockValidationFailureProvider("P1")
        adapter2 = MockSuccessProvider("P2")
        self.registry.bind_adapter("Context.dev", adapter1)
        self.registry.bind_adapter("String", adapter2)

        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0
        self.registry.get("String").historical_metrics["sample_size"] = 1

        req = AcquisitionRequest(url="https://www.purplle.com/product/lipstick")
        budget = ExplorationBudget(max_attempts=2)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertEqual(len(res.telemetry_observations), len(res.attempts))
        self.assertEqual(len(res.telemetry_observations), 2)

    # 9. LearningEngine receives observations after attempts
    def test_09_learning_engine_receives_observations(self):
        adapter = MockSuccessProvider("P1")
        self.registry.bind_adapter("Context.dev", adapter)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001111111")
        budget = ExplorationBudget(max_attempts=1)

        executor = self.pipeline.exploration_executor
        initial_obs_count = len(executor.learning_engine.get_observations())

        res = self.pipeline.execute_exploration(req, budget)

        new_obs_count = len(executor.learning_engine.get_observations())
        self.assertEqual(new_obs_count, initial_obs_count + len(res.attempts))

    # 10. Insufficient evidence does not promote production policy
    def test_10_insufficient_evidence_does_not_promote_policy(self):
        adapter = MockSuccessProvider("P1")
        self.registry.bind_adapter("Context.dev", adapter)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0

        # Establish initial production policy baseline
        profile = TargetProfile(
            domain="Amazon", url_pattern="/dp/*", inferred_country="US",
            country_confidence=1.0, target_type="pdp", location_sensitivity=False,
            browser_likelihood=0.6
        )
        self.pipeline.policy_engine.evaluate_and_promote(
            profile, ["String"], {"cost_per_validated": 0.0010}, sample_size=10
        )

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B002222222")
        budget = ExplorationBudget(max_attempts=1)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertFalse(res.policy_promoted)

    # 11. Sufficient evidence can make capability eligible for promotion per policy rules
    def test_11_sufficient_evidence_makes_policy_eligible(self):
        engine = PolicyEngine(min_sample_size=3, min_confidence=0.50, min_improvement_margin=0.05)
        profile = TargetProfile(
            domain="Amazon",
            url_pattern="/dp/*",
            inferred_country="US",
            country_confidence=1.0,
            target_type="pdp",
            location_sensitivity=False,
            browser_likelihood=0.6
        )

        promoted, policy = engine.evaluate_and_promote(
            profile=profile,
            evaluated_cascade=["Context.dev"],
            cascade_metrics={"expected_validation": 0.95, "expected_latency": 1200, "expected_cost": 0.001, "cost_per_validated": 0.00105},
            sample_size=5
        )

        self.assertTrue(promoted)
        self.assertEqual(policy.selected_cascade, ["Context.dev"])

    # 12. Unbound capability remains a real failure
    def test_12_unbound_capability_fails_explicitly(self):
        # Unbind all adapters
        for cid in ["Context.dev", "String", "Scrapfly"]:
            cap = self.registry.get(cid)
            if cap:
                cap.adapter = None

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B003333333")
        budget = ExplorationBudget(max_attempts=1)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertFalse(res.success)
        self.assertFalse(res.validated)
        self.assertEqual(res.attempts[0]["status_code"], 500)
        self.assertIn("Unbound capability", res.attempts[0]["error"])

    # 13. No synthetic success exists
    def test_13_no_synthetic_success_exists(self):
        cap = self.registry.get("Context.dev")
        if cap:
            cap.adapter = None

        res = self.pipeline.exploration_executor._execute_capability(
            cap,
            AcquisitionRequest(url="https://test.com"),
            TargetProfile(domain="Test", url_pattern="/", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.5)
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["status_code"], 500)
        self.assertEqual(res["html"], "")
        self.assertEqual(res["error"], "Unbound capability: no adapter registered")

    # Issue 1 specific tests
    def test_issue1_planner_does_not_prematurely_consume_budget(self):
        profile = TargetProfile(domain="Amazon", url_pattern="/dp/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.6)
        candidates = [self.registry.get("Context.dev"), self.registry.get("String"), self.registry.get("Scrapfly")]
        budget = ExplorationBudget(max_attempts=3)
        decisions = self.pipeline.exploration_planner.plan(candidates, profile, CustomerPreferences(), budget)
        self.assertEqual(len(decisions), 3)
        self.assertEqual(budget.attempts_consumed, 0)
        self.assertEqual(budget.remaining, 3)

    def test_issue1_first_attempt_succeeds_consumes_exactly_one_budget_unit(self):
        mock_adapter = MockSuccessProvider("P1")
        self.registry.bind_adapter("Context.dev", mock_adapter)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0
        self.registry.get("String").historical_metrics["sample_size"] = 1

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        budget = ExplorationBudget(max_attempts=3)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertEqual(len(res.attempts), 1)
        self.assertEqual(res.budget_consumed, 1)
        self.assertEqual(res.budget_remaining, 2)

    def test_issue1_first_attempt_fails_second_executes_consumes_exactly_two_budget_units(self):
        fail_adapter = MockValidationFailureProvider("P_Fail")
        success_adapter = MockSuccessProvider("P_Success")
        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", success_adapter)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0
        self.registry.get("String").historical_metrics["sample_size"] = 1

        req = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm12345")
        budget = ExplorationBudget(max_attempts=3)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertEqual(len(res.attempts), 2)
        self.assertEqual(res.budget_consumed, 2)
        self.assertEqual(res.budget_remaining, 1)

    def test_issue1_budget_exhaustion_prevents_additional_execution(self):
        fail_adapter = MockValidationFailureProvider("P_Fail")
        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", fail_adapter)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 0

        req = AcquisitionRequest(url="https://www.purplle.com/product/cream")
        budget = ExplorationBudget(max_attempts=1)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertFalse(res.success)
        self.assertEqual(res.stop_reason, "BUDGET_EXHAUSTED")
        self.assertEqual(len(res.attempts), 1)
        self.assertEqual(res.budget_consumed, 1)
        self.assertEqual(res.budget_remaining, 0)

    def test_issue1_budget_can_never_exceed_max_attempts(self):
        fail_adapter = MockValidationFailureProvider("P_Fail")
        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", fail_adapter)
        self.registry.bind_adapter("Scrapfly", fail_adapter)

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B009999999")
        budget = ExplorationBudget(max_attempts=2)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertLessEqual(len(res.attempts), 2)
        self.assertEqual(res.budget_consumed, 2)
        self.assertEqual(res.budget_remaining, 0)
        self.assertFalse(res.success)

    # Issue 2 specific tests
    def test_issue2_historical_sample_size_at_or_above_minimum_triggers_promotion(self):
        mock_adapter = MockSuccessProvider("P1")
        self.registry.bind_adapter("Context.dev", mock_adapter)
        # Context.dev starts with sample_size 7; 1 attempt will increment it to 8 (confidence > 0.65)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 7

        profile = TargetProfile(
            domain="Amazon", url_pattern="/dp/*", inferred_country="US",
            country_confidence=1.0, target_type="pdp", location_sensitivity=False,
            browser_likelihood=0.6
        )
        # Initial policy baseline with higher cost
        self.pipeline.policy_engine.evaluate_and_promote(
            profile, ["String"], {"cost_per_validated": 0.0500}, sample_size=10
        )

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        budget = ExplorationBudget(max_attempts=1)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertTrue(res.policy_promoted)

    def test_issue2_historical_sample_size_below_minimum_prevents_promotion(self):
        mock_adapter = MockSuccessProvider("P1")
        self.registry.bind_adapter("Context.dev", mock_adapter)
        # Context.dev starts with sample_size 1; 1 attempt increments to 2 (< min_sample_size 5)
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 1

        profile = TargetProfile(
            domain="Amazon", url_pattern="/dp/*", inferred_country="US",
            country_confidence=1.0, target_type="pdp", location_sensitivity=False,
            browser_likelihood=0.6
        )
        self.pipeline.policy_engine.evaluate_and_promote(
            profile, ["String"], {"cost_per_validated": 0.0500}, sample_size=10
        )

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        budget = ExplorationBudget(max_attempts=1)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertFalse(res.policy_promoted)

    def test_issue2_multiple_executed_capabilities_use_appropriate_cumulative_evidence(self):
        fail_adapter = MockValidationFailureProvider("P_Fail")
        success_adapter = MockSuccessProvider("P_Success")
        self.registry.bind_adapter("Context.dev", fail_adapter)
        self.registry.bind_adapter("String", success_adapter)

        # Context.dev: sample_size 1 -> 2. String: sample_size 7 -> 8. Max cumulative sample_size = 8.
        self.registry.get("Context.dev").historical_metrics["sample_size"] = 1
        self.registry.get("String").historical_metrics["sample_size"] = 7

        profile = TargetProfile(
            domain="Flipkart", url_pattern="/p/*", inferred_country="IN",
            country_confidence=1.0, target_type="pdp", location_sensitivity=False,
            browser_likelihood=0.4
        )
        self.pipeline.policy_engine.evaluate_and_promote(
            profile, ["Scrapfly"], {"cost_per_validated": 0.0500}, sample_size=10
        )

        req = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm12345")
        budget = ExplorationBudget(max_attempts=2)

        res = self.pipeline.execute_exploration(req, budget)

        self.assertTrue(res.success)
        self.assertEqual(len(res.attempts), 2)
        self.assertTrue(res.policy_promoted)


if __name__ == "__main__":
    unittest.main()
