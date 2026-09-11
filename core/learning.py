"""
Recency-Weighted Telemetry Learning Engine for Neurix Navigator v0.1 Core.
Updates capability statistics in real-time after every attempt.
"""

import time
from typing import Dict, Any, List, Optional
from core.registry import ProviderRegistry


class LearningEngine:
    """
    Processes attempt observations and updates recency-weighted provider metrics.
    """

    def __init__(self, registry: ProviderRegistry, alpha: float = 0.20):
        self.registry = registry
        self.alpha = alpha  # Recency weighting factor (0.20 = 20% weight to newest observation)
        self._observations: List[Dict[str, Any]] = []

    def record_observation(
        self,
        capability_id: str,
        domain: str,
        country: str,
        success: bool,
        validated: bool,
        latency_ms: int,
        bytes_count: int,
        estimated_cost: float,
        failure_category: Optional[str] = None,
        url_pattern: Optional[str] = None,
        target_type: Optional[str] = None,
        customer_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        obs = {
            "timestamp": time.time(),
            "capability_id": capability_id,
            "domain": domain,
            "country": country,
            "success": success,
            "validated": validated,
            "latency_ms": latency_ms,
            "bytes": bytes_count,
            "estimated_cost": estimated_cost,
            "failure_category": failure_category,
            "url_pattern": url_pattern,
            "target_type": target_type,
            "customer_profile": customer_profile or {}
        }
        self._observations.append(obs)

        # Update registry capability metrics
        cap = self.registry.get(capability_id)
        if cap:
            hist = cap.historical_metrics
            sample_sz = hist.get("sample_size", 0) + 1
            hist["sample_size"] = sample_sz

            # Recency weighted update
            prev_succ = hist.get("success_rate", 0.8)
            prev_val = hist.get("validation_rate", 0.75)
            prev_lat = hist.get("avg_latency_ms", 3000)

            new_succ = (1 - self.alpha) * prev_succ + self.alpha * (1.0 if success else 0.0)
            new_val = (1 - self.alpha) * prev_val + self.alpha * (1.0 if validated else 0.0)
            new_lat = (1 - self.alpha) * prev_lat + self.alpha * float(latency_ms)

            hist["success_rate"] = round(new_succ, 4)
            hist["validation_rate"] = round(new_val, 4)
            hist["avg_latency_ms"] = round(new_lat, 1)

            # Update health state machine
            self.registry.update_health(capability_id, success, failure_category)

        return obs

    def get_observations(self) -> List[Dict[str, Any]]:
        return list(self._observations)
