"""Deterministic, bounded capability exploration planning."""

from dataclasses import dataclass
from typing import List

from core.candidate import CandidateGenerator
from core.models import CapabilityMetadata, CustomerPreferences, TargetProfile


@dataclass
class ExplorationBudget:
    max_attempts: int
    attempts_consumed: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_attempts - self.attempts_consumed)

    @property
    def allowed(self) -> bool:
        return self.remaining > 0

    def consume(self, attempts: int = 1) -> int:
        consumed = min(max(0, attempts), self.remaining)
        self.attempts_consumed += consumed
        return consumed


@dataclass(frozen=True)
class ExplorationDecision:
    capability_id: str
    priority: float
    reason: str
    context_key: str
    remaining_budget: int


class ExplorationPlanner:
    """Selects a small deterministic set of compatible capabilities to learn."""

    def __init__(self, default_max_attempts: int = 2):
        if default_max_attempts < 0:
            raise ValueError("default_max_attempts must be non-negative")
        self.default_max_attempts = default_max_attempts

    def should_explore(
        self,
        candidates: List[CapabilityMetadata],
        profile: TargetProfile,
        preferences: CustomerPreferences,
        budget: ExplorationBudget,
    ) -> bool:
        return bool(
            budget.allowed
            and any(
                CandidateGenerator.is_compatible(cap, profile, preferences)
                and self._priority(cap) > 0
                for cap in candidates
            )
        )

    def plan(
        self,
        candidates: List[CapabilityMetadata],
        profile: TargetProfile,
        preferences: CustomerPreferences,
        budget: ExplorationBudget,
    ) -> List[ExplorationDecision]:
        if not budget.allowed:
            return []

        ranked = []
        for capability in candidates:
            if not CandidateGenerator.is_compatible(capability, profile, preferences):
                continue
            priority, reason = self._priority_and_reason(capability)
            if priority > 0:
                ranked.append((priority, capability.capability_id, reason))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        selected = ranked[:budget.remaining]
        decisions = [
            ExplorationDecision(
                capability_id=capability_id,
                priority=priority,
                reason=reason,
                context_key=profile.context_key(),
                remaining_budget=budget.remaining - index,
            )
            for index, (priority, capability_id, reason) in enumerate(selected)
        ]
        budget.consume(len(decisions))
        return decisions

    def select_capabilities(
        self,
        candidates: List[CapabilityMetadata],
        profile: TargetProfile,
        preferences: CustomerPreferences,
        budget: ExplorationBudget,
    ) -> List[CapabilityMetadata]:
        decisions = self.plan(candidates, profile, preferences, budget)
        selected = {decision.capability_id for decision in decisions}
        return [capability for capability in candidates if capability.capability_id in selected]

    def _priority(self, capability: CapabilityMetadata) -> float:
        return self._priority_and_reason(capability)[0]

    @staticmethod
    def _priority_and_reason(capability: CapabilityMetadata):
        metrics = capability.historical_metrics
        sample_size = max(0, int(metrics.get("sample_size", 0)))
        failure_count = max(
            0,
            int(metrics.get("failure_count", metrics.get("consecutive_failures", 0))),
        )
        validation_rate = float(metrics.get("validation_rate", 0.0))

        if sample_size >= 10 and failure_count >= 3 and validation_rate < 0.5:
            return 0.0, "suppressed_by_repeated_failures"
        if sample_size == 0:
            return 100.0, "no_evidence"
        if sample_size < 3:
            return 80.0 / sample_size, "insufficient_evidence"
        if sample_size < 10:
            return 40.0 / sample_size, "limited_evidence"
        return 10.0 / sample_size, "established_evidence"
