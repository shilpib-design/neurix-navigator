"""
Economic Optimizer & Multi-step Cascade Evaluator for Neurix Navigator v0.1 Core.
Evaluates single strategies and multi-tier cascades (A -> B -> C) to find the lowest
expected cost per validated result that satisfies customer SLA preferences.
"""

import itertools
import random
from typing import List, Dict, Any, Tuple
from core.models import TargetProfile, CustomerPreferences, CapabilityMetadata
from core.rate_card import RateCardRegistry


class EconomicOptimizer:
    """
    Evaluates strategy candidates and multi-step cascades using marginal pricing and probability math.
    """

    def __init__(self, rate_card_registry: RateCardRegistry, exploration_rate: float = 0.10):
        self.rate_card_registry = rate_card_registry
        self.exploration_rate = exploration_rate

    def evaluate_cascade(self, cascade: List[CapabilityMetadata], profile: TargetProfile) -> Dict[str, Any]:
        """
        Calculates expected validation probability, expected latency, expected cost,
        and cost per validated result for a multi-step fallback cascade.
        """
        if not cascade:
            return {
                "cascade": [],
                "expected_validation": 0.0,
                "expected_latency": 0.0,
                "expected_cost": 0.0,
                "cost_per_validated": float("inf")
            }

        p_cum_fail = 1.0
        p_val_total = 0.0
        expected_cost = 0.0
        expected_latency = 0.0

        for cap in cascade:
            val_rate = cap.historical_metrics.get("validation_rate", 0.80)
            avg_lat = cap.historical_metrics.get("avg_latency_ms", 3000)
            # Marginal cost from rate card (falling back to cap.estimated_cost if no rate card registered)
            cost = self.rate_card_registry.get_marginal_cost(
                cap.provider_id, cap.capability_id, domain=profile.domain, default_cost=cap.estimated_cost
            )

            # Probability of reaching this step * success/cost/lat of this step
            p_val_step = p_cum_fail * val_rate
            p_val_total += p_val_step

            expected_cost += p_cum_fail * cost
            expected_latency += p_cum_fail * avg_lat

            p_cum_fail *= (1.0 - val_rate)

        cost_per_validated = (expected_cost / p_val_total) if p_val_total > 0 else float("inf")

        return {
            "cascade": cascade,
            "cascade_ids": [c.capability_id for c in cascade],
            "expected_validation": p_val_total,
            "expected_latency": expected_latency,
            "expected_cost": expected_cost,
            "cost_per_validated": cost_per_validated
        }

    def select_optimal_strategy(
        self,
        candidates: List[CapabilityMetadata],
        profile: TargetProfile,
        preferences: CustomerPreferences
    ) -> Tuple[List[CapabilityMetadata], Dict[str, Any], bool]:
        """
        Selects the optimal strategy or cascade.
        Returns: (selected_cascade, evaluation_metrics, is_exploration)
        """
        if not candidates:
            return [], {"cost_per_validated": float("inf")}, False

        # Controlled Exploration (budget-controlled percentage)
        is_exploration = (random.random() < self.exploration_rate)
        if is_exploration and len(candidates) > 1:
            explored_cand = random.choice(candidates)
            eval_res = self.evaluate_cascade([explored_cand], profile)
            return [explored_cand], eval_res, True

        # Generate candidate cascades (lengths 1, 2, 3)
        possible_cascades = []
        # Single candidates
        for c in candidates:
            possible_cascades.append([c])

        # Dual cascades
        if len(candidates) >= 2:
            for c1, c2 in itertools.permutations(candidates, 2):
                possible_cascades.append([c1, c2])

        # Triple cascades
        if len(candidates) >= 3:
            for c1, c2, c3 in itertools.permutations(candidates, 3):
                possible_cascades.append([c1, c2, c3])

        valid_evaluations = []
        for casc in possible_cascades:
            ev = self.evaluate_cascade(casc, profile)

            # SLA Validation filter
            if preferences.min_success_rate and ev["expected_validation"] < (preferences.min_success_rate * 0.85):
                continue
            if preferences.max_latency_ms and ev["expected_latency"] > (preferences.max_latency_ms * 1.5):
                continue

            valid_evaluations.append(ev)

        if not valid_evaluations:
            # Fallback to evaluating all single candidates without hard SLA filter
            for c in candidates:
                valid_evaluations.append(self.evaluate_cascade([c], profile))

        # Sort by primary optimization metric (cost_per_validated)
        valid_evaluations.sort(key=lambda x: x["cost_per_validated"])
        best_eval = valid_evaluations[0]

        return best_eval["cascade"], best_eval, False
