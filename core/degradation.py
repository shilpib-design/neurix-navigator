"""
Self-Healing Foundation Layer for Neurix Navigator v0.1 Core.
Detects statistically meaningful performance degradation across rolling observation windows
and emits explainable ReinvestigationSignals for Phase 5 consumption.
Strictly bounded to signal emission; does NOT execute automatic routing changes or exploration.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BaselineMetrics:
    validation_rate: float = 0.85
    success_rate: float = 0.90
    avg_latency_ms: float = 2000.0
    error_rate: float = 0.10
    cpvr: float = 0.0012
    sample_size: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_rate": round(self.validation_rate, 4),
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "error_rate": round(self.error_rate, 4),
            "cpvr": round(self.cpvr, 6),
            "sample_size": self.sample_size
        }


@dataclass
class DegradationThresholds:
    min_samples: int = 10
    max_window_size: int = 20
    validation_rate_drop_abs: float = 0.20
    validation_rate_drop_rel: float = 0.25
    success_rate_drop_abs: float = 0.20
    latency_increase_factor: float = 1.5
    cpvr_increase_factor: float = 1.5
    error_rate_max: float = 0.30

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_samples": self.min_samples,
            "max_window_size": self.max_window_size,
            "validation_rate_drop_abs": self.validation_rate_drop_abs,
            "validation_rate_drop_rel": self.validation_rate_drop_rel,
            "success_rate_drop_abs": self.success_rate_drop_abs,
            "latency_increase_factor": self.latency_increase_factor,
            "cpvr_increase_factor": self.cpvr_increase_factor,
            "error_rate_max": self.error_rate_max
        }


@dataclass
class DegradationEvent:
    event_id: str = field(default_factory=lambda: f"deg_{uuid.uuid4().hex[:8]}")
    context_key: str = ""
    capability_id: str = ""
    domain: str = ""
    target_type: str = ""
    country: str = ""
    metric: str = ""  # validation_rate, success_rate, latency, error_rate, cpvr, health, session
    baseline_value: float = 0.0
    current_value: float = 0.0
    absolute_delta: float = 0.0
    relative_delta: float = 0.0
    sample_size: int = 0
    threshold_value: float = 0.0
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    detected_at: float = field(default_factory=time.time)
    reason: str = ""
    requires_reinvestigation: bool = True
    discovery_evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "context_key": self.context_key,
            "capability_id": self.capability_id,
            "domain": self.domain,
            "target_type": self.target_type,
            "country": self.country,
            "metric": self.metric,
            "baseline_value": round(self.baseline_value, 4),
            "current_value": round(self.current_value, 4),
            "absolute_delta": round(self.absolute_delta, 4),
            "relative_delta": round(self.relative_delta, 4),
            "sample_size": self.sample_size,
            "threshold_value": round(self.threshold_value, 4),
            "severity": self.severity,
            "detected_at": self.detected_at,
            "reason": self.reason,
            "requires_reinvestigation": self.requires_reinvestigation,
            "discovery_evidence": self.discovery_evidence
        }


@dataclass
class ReinvestigationSignal:
    signal_id: str = field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:8]}")
    context_key: str = ""
    capability_id: str = ""
    domain: str = ""
    target_type: str = ""
    country: str = ""
    triggering_metric: str = ""
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, URGENT
    reason: str = ""
    degradation_event: Dict[str, Any] = field(default_factory=dict)
    discovery_evidence: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "context_key": self.context_key,
            "capability_id": self.capability_id,
            "domain": self.domain,
            "target_type": self.target_type,
            "country": self.country,
            "triggering_metric": self.triggering_metric,
            "priority": self.priority,
            "reason": self.reason,
            "degradation_event": self.degradation_event,
            "discovery_evidence": self.discovery_evidence,
            "created_at": self.created_at
        }


class DegradationDetector:
    """
    Deterministic degradation detection engine.
    Monitors rolling target observations against baselines and emits ReinvestigationSignals.
    Zero autonomous policy mutation or exploration side effects.
    """

    def __init__(self, thresholds: Optional[DegradationThresholds] = None):
        self.thresholds = thresholds or DegradationThresholds()
        self._windows: Dict[str, List[Dict[str, Any]]] = {}
        self._baselines: Dict[str, BaselineMetrics] = {}
        self._events: List[DegradationEvent] = []
        self._signals: List[ReinvestigationSignal] = []

    def set_baseline(self, context_key: str, baseline: BaselineMetrics):
        self._baselines[context_key] = baseline

    def get_baseline(self, context_key: str) -> BaselineMetrics:
        if context_key in self._baselines:
            return self._baselines[context_key]
        return BaselineMetrics()

    def make_context_key(self, domain: str, target_type: str, country: str, capability_id: str) -> str:
        return f"{domain}:{target_type}:{country}:{capability_id}"

    def record_observation(self, observation: Dict[str, Any]) -> Tuple[List[DegradationEvent], List[ReinvestigationSignal]]:
        domain = observation.get("domain", "Generic")
        target_type = observation.get("target_type", "pdp")
        country = observation.get("country", "US")
        capability_id = observation.get("capability_id", "default")

        context_key = self.make_context_key(domain, target_type, country, capability_id)

        window = self._windows.get(context_key, [])
        window.append(observation)

        if len(window) > self.thresholds.max_window_size:
            window.pop(0)
        self._windows[context_key] = window

        # Policy Safety: Require minimum sample count before evaluating degradation
        if len(window) < self.thresholds.min_samples:
            return [], []

        baseline = self.get_baseline(context_key)
        new_events: List[DegradationEvent] = []
        new_signals: List[ReinvestigationSignal] = []

        # Current window metrics calculation
        val_count = sum(1 for o in window if o.get("validated"))
        succ_count = sum(1 for o in window if o.get("success"))
        window_size = len(window)

        curr_val_rate = val_count / window_size
        curr_succ_rate = succ_count / window_size
        curr_lat = sum(float(o.get("latency_ms", 0)) for o in window) / window_size
        curr_err_rate = 1.0 - curr_succ_rate
        curr_cost = sum(float(o.get("estimated_cost", 0.001)) for o in window) / window_size
        curr_cpvr = (curr_cost / curr_val_rate) if curr_val_rate > 0 else 9999.0

        disc_ev = observation.get("discovery_evidence", {})

        # 1. Validation Rate Degradation
        abs_drop = baseline.validation_rate - curr_val_rate
        rel_drop = (abs_drop / baseline.validation_rate) if baseline.validation_rate > 0 else 0.0
        if abs_drop >= self.thresholds.validation_rate_drop_abs or rel_drop >= self.thresholds.validation_rate_drop_rel:
            event = DegradationEvent(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                metric="validation_rate",
                baseline_value=baseline.validation_rate,
                current_value=curr_val_rate,
                absolute_delta=abs_drop,
                relative_delta=rel_drop,
                sample_size=window_size,
                threshold_value=self.thresholds.validation_rate_drop_abs,
                severity="HIGH" if rel_drop >= 0.40 else "MEDIUM",
                reason=f"Validation rate dropped from {baseline.validation_rate:.2f} to {curr_val_rate:.2f} (delta: -{abs_drop:.2f})",
                discovery_evidence=disc_ev
            )
            signal = ReinvestigationSignal(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                triggering_metric="validation_rate",
                priority="HIGH" if rel_drop >= 0.40 else "MEDIUM",
                reason=event.reason,
                degradation_event=event.to_dict(),
                discovery_evidence=disc_ev
            )
            new_events.append(event)
            new_signals.append(signal)

        # 2. Acquisition Success Rate Degradation
        succ_drop = baseline.success_rate - curr_succ_rate
        if succ_drop >= self.thresholds.success_rate_drop_abs and not any(e.metric == "validation_rate" for e in new_events):
            event = DegradationEvent(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                metric="success_rate",
                baseline_value=baseline.success_rate,
                current_value=curr_succ_rate,
                absolute_delta=succ_drop,
                relative_delta=succ_drop / baseline.success_rate if baseline.success_rate > 0 else 0.0,
                sample_size=window_size,
                threshold_value=self.thresholds.success_rate_drop_abs,
                severity="MEDIUM",
                reason=f"Acquisition success rate dropped from {baseline.success_rate:.2f} to {curr_succ_rate:.2f}",
                discovery_evidence=disc_ev
            )
            signal = ReinvestigationSignal(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                triggering_metric="success_rate",
                priority="MEDIUM",
                reason=event.reason,
                degradation_event=event.to_dict(),
                discovery_evidence=disc_ev
            )
            new_events.append(event)
            new_signals.append(signal)

        # 3. Latency Degradation
        if curr_lat >= baseline.avg_latency_ms * self.thresholds.latency_increase_factor:
            lat_delta = curr_lat - baseline.avg_latency_ms
            event = DegradationEvent(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                metric="latency",
                baseline_value=baseline.avg_latency_ms,
                current_value=curr_lat,
                absolute_delta=lat_delta,
                relative_delta=lat_delta / baseline.avg_latency_ms if baseline.avg_latency_ms > 0 else 0.0,
                sample_size=window_size,
                threshold_value=baseline.avg_latency_ms * self.thresholds.latency_increase_factor,
                severity="LOW" if curr_lat < 10000 else "MEDIUM",
                reason=f"Average latency increased from {baseline.avg_latency_ms:.0f}ms to {curr_lat:.0f}ms",
                discovery_evidence=disc_ev
            )
            signal = ReinvestigationSignal(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                triggering_metric="latency",
                priority=event.severity,
                reason=event.reason,
                degradation_event=event.to_dict(),
                discovery_evidence=disc_ev
            )
            new_events.append(event)
            new_signals.append(signal)

        # 4. Error Rate Degradation
        if curr_err_rate >= self.thresholds.error_rate_max and not any(e.metric in ["validation_rate", "success_rate"] for e in new_events):
            event = DegradationEvent(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                metric="error_rate",
                baseline_value=baseline.error_rate,
                current_value=curr_err_rate,
                absolute_delta=curr_err_rate - baseline.error_rate,
                relative_delta=(curr_err_rate - baseline.error_rate) / baseline.error_rate if baseline.error_rate > 0 else 0.0,
                sample_size=window_size,
                threshold_value=self.thresholds.error_rate_max,
                severity="HIGH",
                reason=f"Error rate ({curr_err_rate:.2f}) exceeded max threshold ({self.thresholds.error_rate_max:.2f})",
                discovery_evidence=disc_ev
            )
            signal = ReinvestigationSignal(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                triggering_metric="error_rate",
                priority="HIGH",
                reason=event.reason,
                degradation_event=event.to_dict(),
                discovery_evidence=disc_ev
            )
            new_events.append(event)
            new_signals.append(signal)

        # 5. Economic / CPVR Degradation
        if curr_cpvr >= baseline.cpvr * self.thresholds.cpvr_increase_factor and baseline.cpvr > 0:
            cpvr_delta = curr_cpvr - baseline.cpvr
            event = DegradationEvent(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                metric="cpvr",
                baseline_value=baseline.cpvr,
                current_value=curr_cpvr,
                absolute_delta=cpvr_delta,
                relative_delta=cpvr_delta / baseline.cpvr,
                sample_size=window_size,
                threshold_value=baseline.cpvr * self.thresholds.cpvr_increase_factor,
                severity="MEDIUM",
                reason=f"CPVR deteriorated from ${baseline.cpvr:.6f} to ${curr_cpvr:.6f}",
                discovery_evidence=disc_ev
            )
            signal = ReinvestigationSignal(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                triggering_metric="cpvr",
                priority="MEDIUM",
                reason=event.reason,
                degradation_event=event.to_dict(),
                discovery_evidence=disc_ev
            )
            new_events.append(event)
            new_signals.append(signal)

        # 6. Capability / Session Health Signal Detection
        fail_cat = str(observation.get("failure_category", "")).upper()
        if fail_cat in ["SESSION_EXPIRED", "SESSION_INVALID", "RATE_LIMIT", "BLOCK_PAGE", "CAPTCHA"]:
            metric_type = "session_health" if "SESSION" in fail_cat else "capability_health"
            event = DegradationEvent(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                metric=metric_type,
                baseline_value=1.0,
                current_value=0.0,
                absolute_delta=1.0,
                relative_delta=1.0,
                sample_size=window_size,
                threshold_value=0.0,
                severity="HIGH" if fail_cat in ["BLOCK_PAGE", "CAPTCHA"] else "MEDIUM",
                reason=f"Health degradation signal triggered by failure category: {fail_cat}",
                discovery_evidence=disc_ev
            )
            signal = ReinvestigationSignal(
                context_key=context_key,
                capability_id=capability_id,
                domain=domain,
                target_type=target_type,
                country=country,
                triggering_metric=metric_type,
                priority=event.severity,
                reason=event.reason,
                degradation_event=event.to_dict(),
                discovery_evidence=disc_ev
            )
            new_events.append(event)
            new_signals.append(signal)

        self._events.extend(new_events)
        self._signals.extend(new_signals)
        return new_events, new_signals

    def get_events(self) -> List[DegradationEvent]:
        return list(self._events)

    def get_signals(self) -> List[ReinvestigationSignal]:
        return list(self._signals)
