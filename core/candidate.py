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
            if self.is_compatible(cap, profile, preferences):
                candidates.append(cap)

        return candidates

    @staticmethod
    def is_compatible(
        capability: CapabilityMetadata,
        profile: TargetProfile,
        preferences: CustomerPreferences
    ) -> bool:
        if not capability.enabled or capability.current_health in [HealthState.FAILED, HealthState.DISABLED]:
            return False
        if (
            profile.inferred_country
            and profile.inferred_country != "Unknown"
            and profile.inferred_country not in capability.country_capabilities
        ):
            return False
        if profile.target_type not in capability.target_capabilities and "generic" not in capability.target_capabilities:
            return False
        if profile.location_sensitivity and not capability.location_capabilities:
            return False
        avg_lat = capability.historical_metrics.get("avg_latency_ms", 3000)
        return not preferences.max_latency_ms or avg_lat <= preferences.max_latency_ms * 1.5
