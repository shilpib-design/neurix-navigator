"""
Economic Routing Engine for Neurix Navigator v0.1 Core.
Optimizes acquisition strategy selection by minimizing Cost Per Validated Result (CPVR)
subject to customer SLA, capability compatibility, discovery evidence, session availability, and historical metrics.
"""

import itertools
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.models import CapabilityMetadata, CustomerPreferences, HealthState, TargetProfile
from core.rate_card import RateCardRegistry


@dataclass
class CandidateEconomicProfile:
    capability_id: str
    provider_id: str
    base_cost: float
    estimated_success_probability: float
    estimated_validation_probability: float
    estimated_validated_probability: float
    expected_latency_ms: float
    expected_cost: float
    cpvr: float
    confidence: float
    historical_sample_size: int
    discovery_evidence: Dict[str, Any] = field(default_factory=dict)
    compatible: bool = True
    eligible: bool = True
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "provider_id": self.provider_id,
            "base_cost": round(self.base_cost, 6),
            "estimated_success_probability": round(self.estimated_success_probability, 4),
            "estimated_validation_probability": round(self.estimated_validation_probability, 4),
            "estimated_validated_probability": round(self.estimated_validated_probability, 4),
            "expected_latency_ms": round(self.expected_latency_ms, 1),
            "expected_cost": round(self.expected_cost, 6),
            "cpvr": round(self.cpvr, 6) if not math.isinf(self.cpvr) else 9999.0,
            "confidence": round(self.confidence, 4),
            "historical_sample_size": self.historical_sample_size,
            "discovery_evidence": self.discovery_evidence,
            "compatible": self.compatible,
            "eligible": self.eligible,
            "reason": self.reason
        }


@dataclass
class EconomicRoutingDecision:
    selected_capability: str
    ordered_candidates: List[str]
    selected_cascade: List[str]
    expected_cost: float
    expected_cpvr: float
    expected_success_probability: float
    expected_validation_probability: float
    expected_latency_ms: float
    sla_met: bool = True
    routing_reason: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_capability": self.selected_capability,
            "ordered_candidates": self.ordered_candidates,
            "selected_cascade": self.selected_cascade,
            "expected_cost": round(self.expected_cost, 6),
            "expected_cpvr": round(self.expected_cpvr, 6) if not math.isinf(self.expected_cpvr) else 9999.0,
            "expected_success_probability": round(self.expected_success_probability, 4),
            "expected_validation_probability": round(self.expected_validation_probability, 4),
            "expected_latency_ms": round(self.expected_latency_ms, 1),
            "sla_met": self.sla_met,
            "routing_reason": self.routing_reason,
            "evidence": self.evidence,
            "confidence": round(self.confidence, 4)
        }


class EconomicRouter:
    """
    Economic routing engine for strategy and cascade evaluation.
    Minimizes Cost Per Validated Result (CPVR) while enforcing SLA constraints.
    """

    def __init__(self, rate_card_registry: Optional[RateCardRegistry] = None):
        self.rate_card_registry = rate_card_registry or RateCardRegistry()

    def evaluate_candidate(
        self,
        candidate: CapabilityMetadata,
        profile: TargetProfile,
        preferences: CustomerPreferences,
        discovery_result: Optional[Any] = None,
        session_available: bool = False
    ) -> CandidateEconomicProfile:
        metrics = candidate.historical_metrics or {}
        sample_size = max(0, int(metrics.get("sample_size", 0)))
        
        # Base cost from RateCardRegistry with fallback to cap.estimated_cost
        cost = self.rate_card_registry.get_marginal_cost(
            candidate.provider_id, candidate.capability_id, domain=profile.domain, default_cost=candidate.estimated_cost
        )

        # Baseline probabilities
        raw_succ = float(metrics.get("success_rate", 0.80 if sample_size == 0 else 0.70))
        raw_val = float(metrics.get("validation_rate", 0.75 if sample_size == 0 else 0.65))
        avg_lat = float(metrics.get("avg_latency_ms", 3000))

        # Overall validated probability
        val_prob = raw_succ * raw_val if "success_rate" in metrics and "validation_rate" in metrics else raw_val
        
        if raw_succ == 0.0 or raw_val == 0.0:
            val_prob = 0.0
            cpvr = float("inf")
        else:
            val_prob = max(0.001, min(0.99, val_prob))
            cpvr = (cost / val_prob) if val_prob > 0 else float("inf")

        # Confidence calculation
        if sample_size == 0:
            confidence = 0.50
        else:
            confidence = min(1.0, sample_size / 10.0)

        # Discovery evidence processing
        discovery_info = {}
        has_strong_discovery = False
        if discovery_result:
            surfaces = getattr(discovery_result, "surfaces", [])
            for s in surfaces:
                stype = getattr(s, "surface_type", "")
                conf = getattr(s, "confidence", 0.0)
                if stype in ["json_ld", "embedded_json", "graphql_endpoint", "rsc_payload", "structured_payload"]:
                    if conf >= 0.80:
                        has_strong_discovery = True
                        discovery_info["matched_surface"] = stype
                        discovery_info["confidence"] = conf
                        break
                elif stype == "json_endpoint" and conf >= 0.50:
                    discovery_info["matched_surface"] = stype
                    discovery_info["confidence"] = conf

        # Adjust validation probability if strong discovery evidence matches API/HTTP acquisition
        if has_strong_discovery and candidate.acquisition_method in ["api", "http"]:
            val_prob = min(0.98, val_prob + 0.05)
            confidence = min(1.0, confidence + 0.10)

        # Check compatibility
        compatible = True
        eligible = True
        reason = "Compatible and meets SLA"

        if not candidate.enabled or candidate.current_health in [HealthState.FAILED, HealthState.DISABLED]:
            compatible = False
            eligible = False
            reason = f"Capability disabled or unhealthy ({candidate.current_health.value if hasattr(candidate.current_health, 'value') else candidate.current_health})"

        if session_available and candidate.capability_id.lower() in ["session_assisted_http", "sessionassistedhttp"]:
            # Session-assisted HTTP is eligible when session is available
            pass
        elif not session_available and candidate.capability_id.lower() in ["session_assisted_http", "sessionassistedhttp"]:
            eligible = False
            reason = "No active warmed session available"

        # Calculate CPVR: Cost Per Validated Result
        cpvr = (cost / val_prob) if val_prob > 0 else float("inf")

        # SLA Filter Checks
        if eligible:
            if preferences.max_latency_ms and avg_lat > (preferences.max_latency_ms * 1.5):
                eligible = False
                reason = f"Expected latency ({avg_lat:.0f}ms) exceeds SLA limit ({preferences.max_latency_ms}ms)"
            elif preferences.min_success_rate and val_prob < (preferences.min_success_rate * 0.85):
                eligible = False
                reason = f"Validated probability ({val_prob:.2f}) below min SLA requirement ({preferences.min_success_rate:.2f})"

        return CandidateEconomicProfile(
            capability_id=candidate.capability_id,
            provider_id=candidate.provider_id,
            base_cost=cost,
            estimated_success_probability=raw_succ,
            estimated_validation_probability=raw_val,
            estimated_validated_probability=val_prob,
            expected_latency_ms=avg_lat,
            expected_cost=cost,
            cpvr=cpvr,
            confidence=confidence,
            historical_sample_size=sample_size,
            discovery_evidence=discovery_info,
            compatible=compatible,
            eligible=eligible,
            reason=reason
        )

    def evaluate_cascade(self, cascade: List[CapabilityMetadata], profile: TargetProfile) -> Dict[str, Any]:
        """
        Evaluates cumulative probability, cost, latency, and CPVR for an ordered cascade A -> B -> C.
        """
        if not cascade:
            return {
                "cascade": [],
                "cascade_ids": [],
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
            val_rate = cap.historical_metrics.get("validation_rate", 0.75)
            avg_lat = cap.historical_metrics.get("avg_latency_ms", 3000)
            cost = self.rate_card_registry.get_marginal_cost(
                cap.provider_id, cap.capability_id, domain=profile.domain, default_cost=cap.estimated_cost
            )

            p_val_step = p_cum_fail * val_rate
            p_val_total += p_val_step

            expected_cost += p_cum_fail * cost
            expected_latency += p_cum_fail * avg_lat

            p_cum_fail *= (1.0 - val_rate)

        cpvr = (expected_cost / p_val_total) if p_val_total > 0 else float("inf")

        return {
            "cascade": cascade,
            "cascade_ids": [c.capability_id for c in cascade],
            "expected_validation": p_val_total,
            "expected_latency": expected_latency,
            "expected_cost": expected_cost,
            "cost_per_validated": cpvr
        }

    def route(
        self,
        candidates: List[CapabilityMetadata],
        profile: TargetProfile,
        preferences: CustomerPreferences,
        discovery_result: Optional[Any] = None,
        session_available: bool = False
    ) -> EconomicRoutingDecision:
        if not candidates:
            return EconomicRoutingDecision(
                selected_capability="None",
                ordered_candidates=[],
                selected_cascade=[],
                expected_cost=0.0,
                expected_cpvr=float("inf"),
                expected_success_probability=0.0,
                expected_validation_probability=0.0,
                expected_latency_ms=0.0,
                sla_met=False,
                routing_reason="No compatible acquisition candidates available"
            )

        # Evaluate candidate economics
        profiles: List[CandidateEconomicProfile] = [
            self.evaluate_candidate(c, profile, preferences, discovery_result, session_available)
            for c in candidates
        ]

        # Filter eligible profiles
        eligible_profiles = [p for p in profiles if p.eligible]
        sla_met = True

        if not eligible_profiles:
            # Best-effort fallback when strict SLA filters eliminate all candidates
            sla_met = False
            eligible_profiles = [p for p in profiles if p.compatible]
            if not eligible_profiles:
                eligible_profiles = profiles

        # Sort eligible profiles by CPVR ascending
        eligible_profiles.sort(key=lambda p: p.cpvr)
        best = eligible_profiles[0]

        # Generate ordered candidate list
        ordered_ids = [p.capability_id for p in eligible_profiles]

        # Build fallback cascade (up to 3 best capabilities)
        cascade_caps = []
        for cid in ordered_ids[:3]:
            match = next((c for c in candidates if c.capability_id == cid), None)
            if match:
                cascade_caps.append(match)

        eval_cascade = self.evaluate_cascade(cascade_caps, profile)
        cascade_ids = eval_cascade["cascade_ids"]

        # Dynamic human-readable explanation
        disc_text = ""
        if best.discovery_evidence and "matched_surface" in best.discovery_evidence:
            disc_text = f", supported by discovered {best.discovery_evidence['matched_surface']} surface"

        sla_text = "meets SLA constraints" if sla_met else "selected as best-effort fallback (SLA not fully met)"
        
        explanation = (
            f"Selected '{best.capability_id}' (CPVR: ${best.cpvr:.6f}) because it provides the lowest expected cost per validated result, "
            f"with validation rate {best.estimated_validated_probability*100:.1f}%, latency {best.expected_latency_ms:.0f}ms, and {sla_text}{disc_text}."
        )

        return EconomicRoutingDecision(
            selected_capability=best.capability_id,
            ordered_candidates=ordered_ids,
            selected_cascade=cascade_ids,
            expected_cost=best.expected_cost,
            expected_cpvr=best.cpvr,
            expected_success_probability=best.estimated_success_probability,
            expected_validation_probability=best.estimated_validated_probability,
            expected_latency_ms=best.expected_latency_ms,
            sla_met=sla_met,
            routing_reason=explanation,
            evidence={
                "candidate_profiles": [p.to_dict() for p in profiles],
                "selected_candidate_profile": best.to_dict(),
                "cascade_eval": {
                    "expected_validation": round(eval_cascade["expected_validation"], 4),
                    "expected_cost": round(eval_cascade["expected_cost"], 6),
                    "cpvr": round(eval_cascade["cost_per_validated"], 6) if not math.isinf(eval_cascade["cost_per_validated"]) else 9999.0
                }
            },
            confidence=best.confidence
        )
