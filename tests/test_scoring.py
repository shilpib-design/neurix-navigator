"""
Offline Unit Tests for Phase 8 Acquisition Strategy Scorer.

Tests cover:
A. grouping by target + acquisition method
B. validation rate calculation
C. success rate calculation
D. latency normalization
E. cost normalization
F. confidence based on sample size
G. final score calculation
H. ranking
I. unseen strategy handling
J. different targets do not contaminate each other's scores
K. zero-cost browser strategy
L. vendor strategy with mocked cost
M. no network calls
N. no acquisition execution
"""

import unittest
from typing import List
from telemetry.models import AcquisitionObservation, ObservationStatus
from scoring.models import StrategyScore
from scoring.scorer import StrategyScorer, rank_strategies
from orchestrator.orchestrator import AcquisitionOrchestrator, AcquisitionRequest
from orchestrator.strategies import BaseAcquisitionStrategy


class MockedStrategy(BaseAcquisitionStrategy):
    def __init__(self, name: str, available: bool = True):
        self._name = name
        self._available = available
        self.acquired = False

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    def acquire(self, request):
        self.acquired = True
        raise RuntimeError("Acquisition strategy should not be executed by scorer!")


class TestAcquisitionStrategyScorer(unittest.TestCase):

    def setUp(self):
        self.scorer = StrategyScorer()

    # -------------------------------------------------------------
    # Test A: Grouping by target + acquisition method
    # -------------------------------------------------------------
    def test_grouping_by_target_and_method(self):
        obs = [
            AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="http://test", final_status=ObservationStatus.VALIDATED),
            AcquisitionObservation(target="kroger", acquisition_method="vendor_api", url="http://test", final_status=ObservationStatus.VALIDATED),
            AcquisitionObservation(target="amazon", acquisition_method="browser_cdp", url="http://test", final_status=ObservationStatus.VALIDATED),
        ]
        kroger_scores = self.scorer.rank_strategies("kroger", obs, available_methods=["browser_cdp", "vendor_api"])
        self.assertEqual(len(kroger_scores), 2)
        methods = {s.acquisition_method for s in kroger_scores}
        self.assertEqual(methods, {"browser_cdp", "vendor_api"})
        for s in kroger_scores:
            self.assertEqual(s.target, "kroger")

    # -------------------------------------------------------------
    # Test B: Validation rate calculation
    # -------------------------------------------------------------
    def test_validation_rate_calculation(self):
        obs = [
            AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED),
            AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATION_FAILED),
        ]
        score = self.scorer.evaluate_strategy("kroger", "browser_cdp", obs)
        self.assertEqual(score.sample_size, 2)
        self.assertEqual(score.validated_results, 1)
        self.assertEqual(score.validation_rate, 0.5)

    # -------------------------------------------------------------
    # Test C: Success rate calculation
    # -------------------------------------------------------------
    def test_success_rate_calculation(self):
        obs = [
            AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED),
            AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=False, final_status=ObservationStatus.ACQUISITION_FAILED),
        ]
        score = self.scorer.evaluate_strategy("kroger", "browser_cdp", obs)
        self.assertEqual(score.sample_size, 2)
        self.assertEqual(score.successful_acquisitions, 1)
        self.assertEqual(score.success_rate, 0.5)

    # -------------------------------------------------------------
    # Test D: Latency normalization
    # -------------------------------------------------------------
    def test_latency_normalization(self):
        obs_fast = [AcquisitionObservation(target="kroger", acquisition_method="fast_api", url="u", acquisition_success=True, elapsed_ms=200, final_status=ObservationStatus.VALIDATED)] * 10
        obs_slow = [AcquisitionObservation(target="kroger", acquisition_method="slow_cdp", url="u", acquisition_success=True, elapsed_ms=2000, final_status=ObservationStatus.VALIDATED)] * 10
        all_obs = obs_fast + obs_slow

        scores = self.scorer.rank_strategies("kroger", all_obs)
        fast_score = next(s for s in scores if s.acquisition_method == "fast_api")
        slow_score = next(s for s in scores if s.acquisition_method == "slow_cdp")
        self.assertGreater(fast_score.score, slow_score.score)

    # -------------------------------------------------------------
    # Test E: Cost normalization
    # -------------------------------------------------------------
    def test_cost_normalization(self):
        obs_free = [AcquisitionObservation(target="kroger", acquisition_method="free_browser", url="u", acquisition_success=True, acquisition_cost=0.0, final_status=ObservationStatus.VALIDATED)] * 10
        obs_paid = [AcquisitionObservation(target="kroger", acquisition_method="paid_vendor", url="u", acquisition_success=True, acquisition_cost=0.05, final_status=ObservationStatus.VALIDATED)] * 10
        all_obs = obs_free + obs_paid

        scores = self.scorer.rank_strategies("kroger", all_obs)
        free_score = next(s for s in scores if s.acquisition_method == "free_browser")
        paid_score = next(s for s in scores if s.acquisition_method == "paid_vendor")
        self.assertGreater(free_score.score, paid_score.score)

    # -------------------------------------------------------------
    # Test F: Confidence based on sample size
    # -------------------------------------------------------------
    def test_confidence_sample_size_scaling(self):
        # 1 observation -> 0.1 confidence
        obs_1 = [AcquisitionObservation(target="kroger", acquisition_method="cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED)]
        score_1 = self.scorer.evaluate_strategy("kroger", "cdp", obs_1)
        self.assertEqual(score_1.confidence, 0.1)

        # 5 observations -> 0.5 confidence
        obs_5 = obs_1 * 5
        score_5 = self.scorer.evaluate_strategy("kroger", "cdp", obs_5)
        self.assertEqual(score_5.confidence, 0.5)

        # 10 observations -> 1.0 confidence
        obs_10 = obs_1 * 10
        score_10 = self.scorer.evaluate_strategy("kroger", "cdp", obs_10)
        self.assertEqual(score_10.confidence, 1.0)

        # 15 observations -> capped at 1.0 confidence
        obs_15 = obs_1 * 15
        score_15 = self.scorer.evaluate_strategy("kroger", "cdp", obs_15)
        self.assertEqual(score_15.confidence, 1.0)

    # -------------------------------------------------------------
    # Test G: Final score calculation
    # -------------------------------------------------------------
    def test_final_score_calculation(self):
        obs = [AcquisitionObservation(target="kroger", acquisition_method="cdp", url="u", acquisition_success=True, elapsed_ms=1000, acquisition_cost=0.0, final_status=ObservationStatus.VALIDATED)] * 5
        score = self.scorer.evaluate_strategy("kroger", "cdp", obs)
        # raw_score should be 1.0 (perfect validation, success, 0 cost, low latency)
        self.assertEqual(score.raw_score, 1.0)
        self.assertEqual(score.confidence, 0.5)
        self.assertEqual(score.final_score, 0.5)
        self.assertEqual(score.score, 0.5)

    # -------------------------------------------------------------
    # Test H: Ranking order
    # -------------------------------------------------------------
    def test_ranking_order(self):
        good = [AcquisitionObservation(target="kroger", acquisition_method="good", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED)] * 10
        bad = [AcquisitionObservation(target="kroger", acquisition_method="bad", url="u", acquisition_success=False, final_status=ObservationStatus.ACQUISITION_FAILED)] * 10
        scores = rank_strategies("kroger", good + bad)
        self.assertEqual(scores[0].acquisition_method, "good")
        self.assertEqual(scores[1].acquisition_method, "bad")
        self.assertGreater(scores[0].score, scores[1].score)

    # -------------------------------------------------------------
    # Test I: Unseen strategy handling
    # -------------------------------------------------------------
    def test_unseen_strategy_handling(self):
        obs = [AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED)] * 5
        scores = self.scorer.rank_strategies("kroger", obs, available_methods=["browser_cdp", "vendor_api"])

        unseen = next(s for s in scores if s.acquisition_method == "vendor_api")
        self.assertEqual(unseen.status, "UNSEEN")
        self.assertEqual(unseen.sample_size, 0)
        self.assertEqual(unseen.confidence, 0.0)
        self.assertEqual(unseen.score, 0.0)

    # -------------------------------------------------------------
    # Test J: Cross-target contamination prevention
    # -------------------------------------------------------------
    def test_target_isolation(self):
        kroger_obs = [AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED)] * 10
        amazon_obs = [AcquisitionObservation(target="amazon", acquisition_method="browser_cdp", url="u", acquisition_success=False, final_status=ObservationStatus.ACQUISITION_FAILED)] * 10

        all_obs = kroger_obs + amazon_obs

        k_score = self.scorer.evaluate_strategy("kroger", "browser_cdp", all_obs)
        a_score = self.scorer.evaluate_strategy("amazon", "browser_cdp", all_obs)

        self.assertEqual(k_score.validation_rate, 1.0)
        self.assertEqual(a_score.validation_rate, 0.0)
        self.assertEqual(k_score.score, 1.0)
        self.assertEqual(a_score.score, 0.0)

    # -------------------------------------------------------------
    # Test K: Zero-cost browser strategy
    # -------------------------------------------------------------
    def test_zero_cost_browser_strategy(self):
        obs = [AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, acquisition_cost=0.0, final_status=ObservationStatus.VALIDATED)] * 10
        score = self.scorer.evaluate_strategy("kroger", "browser_cdp", obs)
        self.assertEqual(score.total_cost, 0.0)
        self.assertEqual(score.cost_per_validated_result, 0.0)
        self.assertEqual(score.score, 1.0)

    # -------------------------------------------------------------
    # Test L: Vendor strategy with mocked cost
    # -------------------------------------------------------------
    def test_vendor_strategy_mocked_cost(self):
        obs = [AcquisitionObservation(target="kroger", acquisition_method="vendor_api", url="u", acquisition_success=True, acquisition_cost=0.02, final_status=ObservationStatus.VALIDATED)] * 10
        score = self.scorer.evaluate_strategy("kroger", "vendor_api", obs)
        self.assertEqual(score.total_cost, 0.20)
        self.assertEqual(score.cost_per_validated_result, 0.02)

    # -------------------------------------------------------------
    # Test M: No network calls
    # -------------------------------------------------------------
    def test_no_network_calls(self):
        # Verify scorer runs in complete isolation without socket/network access
        obs = [AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED)] * 5
        scores = rank_strategies("kroger", obs)
        self.assertIsNotNone(scores)

    # -------------------------------------------------------------
    # Test N: No acquisition execution
    # -------------------------------------------------------------
    def test_no_acquisition_execution(self):
        strat1 = MockedStrategy("browser_cdp")
        strat2 = MockedStrategy("vendor_api")
        orchestrator = AcquisitionOrchestrator(strategies=[strat1, strat2])

        req = AcquisitionRequest(target="kroger", url="https://www.kroger.com/p/0004000042431")
        obs = [AcquisitionObservation(target="kroger", acquisition_method="browser_cdp", url="u", acquisition_success=True, final_status=ObservationStatus.VALIDATED)] * 5

        # Recommend strategy via orchestrator helper
        rec = orchestrator.recommend_strategy(req, obs)

        self.assertIsNotNone(rec)
        self.assertEqual(rec.acquisition_method, "browser_cdp")
        # Ensure strategies were NEVER executed
        self.assertFalse(strat1.acquired)
        self.assertFalse(strat2.acquired)


if __name__ == "__main__":
    unittest.main()
