"""
Confidence-Based Policy Engine for Neurix Navigator v0.1 Core.
Tracks policy states per context key and promotes superior cascades immediately.
"""

import time
import math
from typing import Dict, Any, List, Optional, Tuple
from core.models import PolicyState, TargetProfile


class PolicyEngine:
    """
    Manages persistent strategy/policy state and handles instant policy promotion.
    """

    def __init__(self, min_sample_size: int = 5, min_confidence: float = 0.65, min_improvement_margin: float = 0.05):
        self.min_sample_size = min_sample_size
        self.min_confidence = min_confidence
        self.min_improvement_margin = min_improvement_margin
        self._policy_store: Dict[str, PolicyState] = {}

    def get_active_policy(self, profile: TargetProfile) -> Optional[PolicyState]:
        key = profile.context_key()
        return self._policy_store.get(key)

    def calculate_confidence(self, sample_size: int, success_rate: float) -> float:
        """
        Calculates statistical confidence score based on sample size and variance.
        Confidence = 1 - 1 / sqrt(N + 1) * (1 + 4 * p * (1 - p))
        """
        if sample_size <= 0:
            return 0.0
        variance_penalty = 4.0 * success_rate * (1.0 - success_rate)
        conf = 1.0 - (1.0 / math.sqrt(sample_size + 1)) * (1.0 + 0.2 * variance_penalty)
        return max(0.0, min(1.0, conf))

    def evaluate_and_promote(
        self,
        profile: TargetProfile,
        evaluated_cascade: List[str],
        cascade_metrics: Dict[str, Any],
        sample_size: int
    ) -> Tuple[bool, PolicyState]:
        """
        Evaluates a candidate cascade and promotes it to active production policy if criteria are met.
        Returns: (promoted: bool, current_policy_state: PolicyState)
        """
        key = profile.context_key()
        current_policy = self._policy_store.get(key)

        exp_val = cascade_metrics.get("expected_validation", 0.8)
        exp_lat = cascade_metrics.get("expected_latency", 3000.0)
        exp_cost = cascade_metrics.get("expected_cost", 0.001)
        cost_per_val = cascade_metrics.get("cost_per_validated", 0.0012)
        conf = self.calculate_confidence(sample_size, exp_val)

        new_policy = PolicyState(
            context_key=key,
            selected_cascade=evaluated_cascade,
            expected_success=exp_val,
            expected_validation=exp_val,
            expected_latency=exp_lat,
            expected_cost=exp_cost,
            expected_cost_per_validated=cost_per_val,
            confidence=conf,
            sample_size=sample_size,
            version=(current_policy.version + 1) if current_policy else 1,
            last_updated=time.time()
        )

        if not current_policy:
            # Initialize initial policy
            self._policy_store[key] = new_policy
            return True, new_policy

        # Promotion check criteria:
        # 1. Sample size >= threshold
        # 2. Confidence >= threshold
        # 3. Cost per validated is at least min_improvement_margin lower
        if sample_size >= self.min_sample_size and conf >= self.min_confidence:
            improvement = (current_policy.expected_cost_per_validated - cost_per_val) / max(1e-6, current_policy.expected_cost_per_validated)
            if improvement >= self.min_improvement_margin:
                self._policy_store[key] = new_policy
                return True, new_policy

        return False, current_policy
