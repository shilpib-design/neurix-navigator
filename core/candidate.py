"""
Dynamic Candidate Generator for Neurix Navigator v0.1 Core.
Filters compatible capabilities dynamically from TargetProfile and ProviderRegistry.
"""

from typing import List
from core.models import TargetProfile, CustomerPreferences, CapabilityMetadata, HealthState
from core.registry import ProviderRegistry


class CandidateGenerator:
    """
    Generates compatible acquisition candidates for a given target context without hardcoded domain chains.
    """

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def generate_candidates(self, profile: TargetProfile, preferences: CustomerPreferences) -> List[CapabilityMetadata]:
        all_caps = self.registry.list_capabilities(enabled_only=True)
        candidates = []

        for cap in all_caps:
            # 1. Health state filter
            if cap.current_health in [HealthState.FAILED, HealthState.DISABLED]:
                continue

            # 2. Country capability filter
            if profile.inferred_country and profile.inferred_country not in cap.country_capabilities:
                continue

            # 3. Target type capability filter
            if profile.target_type not in cap.target_capabilities and "generic" not in cap.target_capabilities:
                continue

            # 4. Latency preference filter (soft constraint)
            avg_lat = cap.historical_metrics.get("avg_latency_ms", 3000)
            if preferences.max_latency_ms and avg_lat > preferences.max_latency_ms * 1.5:
                continue

            candidates.append(cap)

        return candidates
