"""
Dynamic Candidate Generator for Neurix Navigator v0.1 Core.
Filters compatible capabilities dynamically from TargetProfile and ProviderRegistry.
"""

from typing import List, Optional, Any
from core.models import TargetProfile, CustomerPreferences, CapabilityMetadata, HealthState
from core.registry import ProviderRegistry


class CandidateGenerator:
    """
    Generates compatible acquisition candidates for a given target context without hardcoded domain chains.
    """

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def generate_candidates(
        self,
        profile: TargetProfile,
        preferences: CustomerPreferences,
        discovery_result: Optional[Any] = None
    ) -> List[CapabilityMetadata]:
        all_caps = self.registry.list_capabilities(enabled_only=True)
        candidates = []

        # Extract discovered surface types if discovery_result provided
        discovered_surface_types = set()
        if discovery_result and hasattr(discovery_result, "surfaces"):
            for s in discovery_result.surfaces:
                if hasattr(s, "surface_type"):
                    discovered_surface_types.add(s.surface_type)
        elif isinstance(discovery_result, list):
            for item in discovery_result:
                if hasattr(item, "surface_type"):
                    discovered_surface_types.add(item.surface_type)

        for cap in all_caps:
            if self.is_compatible(cap, profile, preferences):
                # Annotate capability metadata with discovery evidence if present
                if discovered_surface_types:
                    has_matching_discovery = False
                    if "json_ld" in discovered_surface_types and "api" in cap.acquisition_method:
                        has_matching_discovery = True
                    elif "graphql_endpoint" in discovered_surface_types and ("api" in cap.acquisition_method or "graphql" in cap.capability_id.lower()):
                        has_matching_discovery = True
                    elif "json_endpoint" in discovered_surface_types and "api" in cap.acquisition_method:
                        has_matching_discovery = True
                    elif "rsc_payload" in discovered_surface_types and ("api" in cap.acquisition_method or "browser" in cap.acquisition_method):
                        has_matching_discovery = True

                    # Store discovery match indicator safely in historical_metrics for decision engine awareness
                    cap.historical_metrics["discovery_matched"] = has_matching_discovery
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
