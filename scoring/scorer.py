"""
Deterministic Acquisition Strategy Scorer.

Evaluates historical observations per target and acquisition method,
normalizes performance metrics, and calculates weighted strategy confidence scores.
"""

from typing import Dict, Any, List, Optional
from telemetry.models import AcquisitionObservation, ObservationStatus
from scoring.models import StrategyScore


class StrategyScorer:
    """
    Evaluates and ranks acquisition strategies deterministically based on historical telemetry.
    """

    # Weighting Formula Constants
    WEIGHT_VALIDATION: float = 0.50
    WEIGHT_SUCCESS: float = 0.20
    WEIGHT_LATENCY: float = 0.15
    WEIGHT_COST: float = 0.15

    CONFIDENCE_SAMPLE_THRESHOLD: float = 10.0

    def evaluate_strategy(
        self,
        target: str,
        method: str,
        observations: List[AcquisitionObservation],
        max_latency: float = 0.0,
        max_cost: float = 0.0
    ) -> StrategyScore:
        """
        Evaluates a single (target, method) pair over its subset of observations.
        """
        method_obs = [o for o in observations if o.target.lower() == target.lower() and o.acquisition_method == method]
        sample_size = len(method_obs)

        if sample_size == 0:
            return StrategyScore(
                target=target,
                acquisition_method=method,
                sample_size=0,
                successful_acquisitions=0,
                validated_results=0,
                success_rate=0.0,
                validation_rate=0.0,
                average_latency_ms=0.0,
                total_cost=0.0,
                cost_per_validated_result=0.0,
                raw_score=0.0,
                confidence=0.0,
                final_score=0.0,
                status="UNSEEN"
            )

        successful_acquisitions = sum(1 for o in method_obs if o.acquisition_success)
        validated_results = sum(1 for o in method_obs if o.final_status == ObservationStatus.VALIDATED)

        success_rate = successful_acquisitions / sample_size
        validation_rate = validated_results / sample_size
        average_latency = sum(o.elapsed_ms for o in method_obs) / sample_size
        total_cost = sum(o.acquisition_cost for o in method_obs)

        cost_per_validated = (total_cost / validated_results) if validated_results > 0 else 0.0

        # Sub-score Normalization
        val_score = validation_rate
        succ_score = success_rate

        if success_rate == 0.0:
            latency_score = 0.0
            cost_score = 0.0
        else:
            # Latency Sub-score (lower latency is better)
            if max_latency > 0:
                latency_score = max(0.0, 1.0 - (average_latency / (max_latency * 1.5)))
            elif average_latency <= 3000:
                latency_score = 1.0
            else:
                latency_score = max(0.0, 1.0 - (average_latency / 10000.0))

            # Cost Sub-score (lower cost is better)
            if cost_per_validated == 0.0:
                cost_score = 1.0
            elif max_cost > 0:
                cost_score = max(0.0, 1.0 - (cost_per_validated / (max_cost * 1.5)))
            else:
                cost_score = max(0.0, 1.0 - (cost_per_validated / 0.05))

        # Raw Score Calculation
        raw_score = (
            (self.WEIGHT_VALIDATION * val_score) +
            (self.WEIGHT_SUCCESS * succ_score) +
            (self.WEIGHT_LATENCY * latency_score) +
            (self.WEIGHT_COST * cost_score)
        )

        # Confidence & Final Score Calculation
        confidence = min(1.0, sample_size / self.CONFIDENCE_SAMPLE_THRESHOLD)
        final_score = raw_score * confidence

        return StrategyScore(
            target=target,
            acquisition_method=method,
            sample_size=sample_size,
            successful_acquisitions=successful_acquisitions,
            validated_results=validated_results,
            success_rate=round(success_rate, 4),
            validation_rate=round(validation_rate, 4),
            average_latency_ms=round(average_latency, 2),
            total_cost=round(total_cost, 6),
            cost_per_validated_result=round(cost_per_validated, 6),
            raw_score=round(raw_score, 4),
            confidence=round(confidence, 4),
            final_score=round(final_score, 4),
            status="RANKED"
        )


    def rank_strategies(
        self,
        target: str,
        observations: List[AcquisitionObservation],
        available_methods: Optional[List[str]] = None
    ) -> List[StrategyScore]:
        """
        Groups observations by (target, method), calculates strategy scores,
        and returns strategies ranked by final_score descending.
        """
        target_obs = [o for o in observations if o.target.lower() == target.lower()]

        # Discover methods present in observations or provided list
        methods_in_obs = set(o.acquisition_method for o in target_obs)
        if available_methods:
            methods_in_obs.update(available_methods)
        
        if not methods_in_obs:
            methods_in_obs = {"browser_cdp"}

        # Calculate max latency and cost across methods for normalization
        method_stats = {}
        for m in methods_in_obs:
            m_obs = [o for o in target_obs if o.acquisition_method == m]
            if m_obs:
                m_lat = sum(o.elapsed_ms for o in m_obs) / len(m_obs)
                m_val_count = sum(1 for o in m_obs if o.final_status == ObservationStatus.VALIDATED)
                m_cost = (sum(o.acquisition_cost for o in m_obs) / m_val_count) if m_val_count > 0 else 0.0
                method_stats[m] = {"latency": m_lat, "cost": m_cost}

        max_latency = max((s["latency"] for s in method_stats.values()), default=0.0)
        max_cost = max((s["cost"] for s in method_stats.values()), default=0.0)

        scores = []
        for method in methods_in_obs:
            score = self.evaluate_strategy(target, method, target_obs, max_latency=max_latency, max_cost=max_cost)
            scores.append(score)

        # Sort by final_score descending; RANKED before UNSEEN
        scores.sort(key=lambda s: (s.status == "RANKED", s.final_score, s.sample_size), reverse=True)
        return scores

    def recommend(
        self,
        target: str,
        observations: List[AcquisitionObservation],
        available_methods: Optional[List[str]] = None
    ) -> Optional[StrategyScore]:
        """
        Returns the top-ranked StrategyScore for a target based on observations.
        """
        ranked = self.rank_strategies(target, observations, available_methods)
        return ranked[0] if ranked else None

    def recommend_strategy(
        self,
        target: str,
        observations: List[AcquisitionObservation],
        available_methods: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Returns the top-ranked acquisition method name for a target based on observations.
        """
        rec = self.recommend(target, observations, available_methods)
        return rec.acquisition_method if rec else None


def rank_strategies(
    target: str,
    observations: List[AcquisitionObservation],
    available_methods: Optional[List[str]] = None
) -> List[StrategyScore]:
    """
    Top-level helper function to rank strategies using StrategyScorer.
    """
    scorer = StrategyScorer()
    return scorer.rank_strategies(target, observations, available_methods)

