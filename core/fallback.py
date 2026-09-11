"""
Failure-Aware Fallback Manager for Neurix Navigator v0.1 Core.
Dynamically adjusts remaining cascade steps during execution based on observed failure category.
"""

from typing import List, Optional
from core.models import CapabilityMetadata, FailureCategory
from core.registry import ProviderRegistry


class FallbackManager:
    """
    Evaluates failure feedback and re-ranks/swaps remaining candidates during runtime execution.
    """

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def adjust_cascade_on_failure(
        self,
        remaining_cascade: List[CapabilityMetadata],
        failed_capability: CapabilityMetadata,
        failure_category: str
    ) -> List[CapabilityMetadata]:
        """
        Dynamically adjusts remaining cascade capabilities based on failure type.
        """
        adjusted = [c for c in remaining_cascade if c.capability_id != failed_capability.capability_id]

        if not adjusted:
            # Fetch backup capabilities from registry if initial list depleted
            all_caps = self.registry.list_capabilities(enabled_only=True)
            adjusted = [c for c in all_caps if c.capability_id != failed_capability.capability_id]

        if failure_category == FailureCategory.RATE_LIMIT.value:
            # Prefer different provider API or browser
            adjusted.sort(key=lambda c: (c.provider_id == failed_capability.provider_id, c.historical_metrics.get("avg_latency_ms", 3000)))

        elif failure_category == FailureCategory.BLOCK_PAGE.value:
            # Prefer browser rendering with proxy over plain HTTP API
            adjusted.sort(key=lambda c: (0 if c.browser_support else 1, -c.historical_metrics.get("validation_rate", 0.8)))

        elif failure_category == FailureCategory.TIMEOUT.value:
            # Prefer lower-latency options
            adjusted.sort(key=lambda c: c.historical_metrics.get("avg_latency_ms", 3000))

        elif failure_category == FailureCategory.VALIDATION_FAILED.value:
            # Prefer capabilities with high historical validation rate
            adjusted.sort(key=lambda c: -c.historical_metrics.get("validation_rate", 0.8))

        return adjusted
