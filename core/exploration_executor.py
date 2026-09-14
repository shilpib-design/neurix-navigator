"""
Controlled Live Exploration Executor for Neurix Navigator v0.1 Core.
Orchestrates bounded capability exploration attempts, telemetry, learning updates, and policy checks.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.models import (
    AcquisitionRequest,
    TargetProfile,
    CapabilityMetadata,
    FailureCategory,
    CustomerPreferences
)
from core.intelligence import TargetIntelligence
from core.candidate import CandidateGenerator
from core.exploration import ExplorationPlanner, ExplorationBudget, ExplorationDecision
from core.registry import ProviderRegistry
from core.rate_card import RateCardRegistry
from core.learning import LearningEngine
from core.policy import PolicyEngine
from core.storage import LeanStorageManager
from orchestrator.models import AcquisitionRequest as ArchReq
from orchestrator.orchestrator import TargetExtractorRegistry, TargetValidator
from telemetry.recorder import AcquisitionObservationRecorder
from telemetry.models import ObservationStatus, AcquisitionObservation


@dataclass
class ExplorationAttemptResult:
    capability_id: str
    provider_id: str
    attempt_index: int
    success: bool
    validated: bool
    status_code: Optional[int]
    elapsed_ms: int
    bytes_count: int
    cost: float
    error: Optional[str]
    failure_category: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "provider_id": self.provider_id,
            "attempt_index": self.attempt_index,
            "success": self.success,
            "validated": self.validated,
            "status_code": self.status_code,
            "elapsed_ms": self.elapsed_ms,
            "bytes_count": self.bytes_count,
            "cost": self.cost,
            "error": self.error,
            "failure_category": self.failure_category
        }


@dataclass
class ControlledExplorationResult:
    request_id: str
    target_profile: Dict[str, Any]
    success: bool
    validated: bool
    data: Dict[str, Any]
    attempts: List[Dict[str, Any]]
    total_cost: float
    total_latency_ms: int
    budget_max_attempts: int
    budget_consumed: int
    budget_remaining: int
    stop_reason: str
    policy_promoted: bool
    telemetry_observations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "target_profile": self.target_profile,
            "success": self.success,
            "validated": self.validated,
            "data": self.data,
            "attempts": self.attempts,
            "total_cost": round(self.total_cost, 6),
            "total_latency_ms": self.total_latency_ms,
            "budget_max_attempts": self.budget_max_attempts,
            "budget_consumed": self.budget_consumed,
            "budget_remaining": self.budget_remaining,
            "stop_reason": self.stop_reason,
            "policy_promoted": self.policy_promoted,
            "telemetry_observations": self.telemetry_observations
        }


class ExplorationExecutor:
    """
    Executes bounded capability exploration attempts safely and records structured observations.
    """

    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        rate_card_registry: Optional[RateCardRegistry] = None,
        extractor_registry: Optional[TargetExtractorRegistry] = None,
        validator: Optional[TargetValidator] = None,
        learning_engine: Optional[LearningEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
        storage_manager: Optional[LeanStorageManager] = None,
        exploration_planner: Optional[ExplorationPlanner] = None,
        telemetry_recorder: Optional[AcquisitionObservationRecorder] = None
    ):
        self.registry = registry or ProviderRegistry()
        self.rate_card_registry = rate_card_registry or RateCardRegistry()
        self.extractor_registry = extractor_registry or TargetExtractorRegistry()
        self.validator = validator or TargetValidator()
        self.learning_engine = learning_engine or LearningEngine(self.registry)
        self.policy_engine = policy_engine or PolicyEngine()
        self.storage_manager = storage_manager or LeanStorageManager()
        self.exploration_planner = exploration_planner or ExplorationPlanner()
        self.telemetry_recorder = telemetry_recorder or AcquisitionObservationRecorder()
        self.candidate_generator = CandidateGenerator(self.registry)

    def execute_exploration(
        self,
        request: AcquisitionRequest,
        budget: Optional[ExplorationBudget] = None
    ) -> ControlledExplorationResult:
        start_time = time.time()

        # 1. Target Intelligence
        profile = TargetIntelligence.analyze(request)

        # 2. Candidate Generation
        candidates = self.candidate_generator.generate_candidates(profile, request.customer_preferences)

        # 3. Budget Initialization
        if budget is None:
            budget = ExplorationBudget(max_attempts=self.exploration_planner.default_max_attempts)

        max_attempts_allocated = budget.max_attempts

        if not candidates:
            return ControlledExplorationResult(
                request_id=request.request_id,
                target_profile=profile.to_dict(),
                success=False,
                validated=False,
                data={},
                attempts=[],
                total_cost=0.0,
                total_latency_ms=int((time.time() - start_time) * 1000),
                budget_max_attempts=max_attempts_allocated,
                budget_consumed=budget.attempts_consumed,
                budget_remaining=budget.remaining,
                stop_reason="NO_COMPATIBLE_CANDIDATES",
                policy_promoted=False
            )

        if not budget.allowed:
            return ControlledExplorationResult(
                request_id=request.request_id,
                target_profile=profile.to_dict(),
                success=False,
                validated=False,
                data={},
                attempts=[],
                total_cost=0.0,
                total_latency_ms=int((time.time() - start_time) * 1000),
                budget_max_attempts=max_attempts_allocated,
                budget_consumed=budget.attempts_consumed,
                budget_remaining=budget.remaining,
                stop_reason="BUDGET_EXHAUSTED",
                policy_promoted=False
            )

        # 4. Plan Exploration Decisions
        decisions = self.exploration_planner.plan(
            candidates, profile, request.customer_preferences, budget
        )

        if not decisions:
            return ControlledExplorationResult(
                request_id=request.request_id,
                target_profile=profile.to_dict(),
                success=False,
                validated=False,
                data={},
                attempts=[],
                total_cost=0.0,
                total_latency_ms=int((time.time() - start_time) * 1000),
                budget_max_attempts=max_attempts_allocated,
                budget_consumed=budget.attempts_consumed,
                budget_remaining=budget.remaining,
                stop_reason="NO_EXPLORATION_NEEDED",
                policy_promoted=False
            )

        # 5. Controlled Execution Loop
        attempts: List[ExplorationAttemptResult] = []
        telemetry_obs: List[Dict[str, Any]] = []
        final_validated = False
        final_data: Dict[str, Any] = {}
        final_html = ""
        total_cost = 0.0
        stop_reason = "ALL_ATTEMPTS_FAILED"
        attempt_index = 0

        for decision in decisions:
            if not budget.allowed:
                stop_reason = "BUDGET_EXHAUSTED"
                break

            capability = self.registry.get(decision.capability_id)
            if not capability or not capability.enabled:
                continue

            budget.consume(1)
            attempt_index += 1
            att_start = time.time()

            # Execute capability attempt
            acq_res = self._execute_capability(capability, request, profile)
            elapsed_ms = int((time.time() - att_start) * 1000)

            html_content = acq_res.get("html", "")
            bytes_count = len(html_content.encode("utf-8")) if html_content else 0

            # Extraction & Validation
            extracted_data = {}
            extractor_fn = self.extractor_registry.get(profile.domain)
            if extractor_fn and acq_res.get("success"):
                try:
                    arch_req = ArchReq(url=request.url, target=profile.domain.lower(), parameters=request.parameters)
                    extracted_data = extractor_fn(html_content, arch_req)
                except Exception:
                    extracted_data = {}

            # Generic fallback extraction if domain extractor returned missing required fields
            if acq_res.get("success") and html_content:
                req_fields = request.fields or ["product_name", "price"]
                if not extracted_data or any(extracted_data.get(f) is None or extracted_data.get(f) == "" for f in req_fields):
                    fallback_data = self._fallback_extract_generic_html(html_content)
                    for k, v in fallback_data.items():
                        if v and (extracted_data.get(k) is None or extracted_data.get(k) == ""):
                            extracted_data[k] = v

            val_res = self.validator.validate(
                extracted_data,
                ArchReq(url=request.url, target=profile.domain.lower(), requirements={"fields": request.fields})
            )
            is_validated = bool(acq_res.get("success") and val_res.validated)

            # Marginal Cost calculation
            cost_attempt = self.rate_card_registry.get_marginal_cost(
                capability.provider_id, capability.capability_id, domain=profile.domain
            )
            total_cost += cost_attempt
            self.rate_card_registry.record_usage(capability.provider_id, capability.capability_id)

            # Classification of failure
            fail_cat = None
            if not is_validated:
                if acq_res.get("failure_category"):
                    fail_cat = acq_res["failure_category"]
                elif "429" in str(acq_res.get("error", "")):
                    fail_cat = FailureCategory.RATE_LIMIT.value
                elif "timeout" in str(acq_res.get("error", "")).lower():
                    fail_cat = FailureCategory.TIMEOUT.value
                elif "block" in str(acq_res.get("error", "")).lower():
                    fail_cat = FailureCategory.BLOCK_PAGE.value
                else:
                    fail_cat = FailureCategory.VALIDATION_FAILED.value

            attempt_result = ExplorationAttemptResult(
                capability_id=capability.capability_id,
                provider_id=capability.provider_id,
                attempt_index=attempt_index,
                success=acq_res.get("success", False),
                validated=is_validated,
                status_code=acq_res.get("status_code"),
                elapsed_ms=elapsed_ms,
                bytes_count=bytes_count,
                cost=cost_attempt,
                error=acq_res.get("error"),
                failure_category=fail_cat
            )
            attempts.append(attempt_result)

            # Telemetry observation recording
            obs_dict = self._record_telemetry_and_learning(
                request=request,
                profile=profile,
                capability=capability,
                attempt_result=attempt_result,
                val_evidence=getattr(val_res, "evidence", []) if is_validated else []
            )
            telemetry_obs.append(obs_dict)

            # Raw Payload TTL Metadata storage
            self.storage_manager.store_raw_payload_metadata(request.request_id, capability.capability_id, html_content)

            if is_validated:
                final_validated = True
                final_data = extracted_data
                final_html = html_content
                stop_reason = "VALIDATED_RESULT_FOUND"
                break
            else:
                if budget.remaining == 0:
                    stop_reason = "BUDGET_EXHAUSTED"

        # Check Policy Promotion Status
        executed_ids = [a.capability_id for a in attempts]
        sample_size = max(
            (
                self.registry.get(cid).historical_metrics.get("sample_size", 1)
                for cid in executed_ids
                if self.registry.get(cid)
            ),
            default=1
        )
        eval_metrics = {
            "expected_validation": 1.0 if final_validated else 0.0,
            "expected_latency": sum(a.elapsed_ms for a in attempts) / max(1, len(attempts)),
            "expected_cost": total_cost,
            "cost_per_validated": total_cost if final_validated else float("inf")
        }

        # Policy promotion evaluation
        promoted, _ = self.policy_engine.evaluate_and_promote(
            profile, executed_ids, eval_metrics, sample_size=sample_size
        )

        total_latency_ms = int((time.time() - start_time) * 1000)

        return ControlledExplorationResult(
            request_id=request.request_id,
            target_profile=profile.to_dict(),
            success=final_validated,
            validated=final_validated,
            data=final_data,
            attempts=[a.to_dict() for a in attempts],
            total_cost=total_cost,
            total_latency_ms=total_latency_ms,
            budget_max_attempts=max_attempts_allocated,
            budget_consumed=budget.attempts_consumed,
            budget_remaining=budget.remaining,
            stop_reason=stop_reason,
            policy_promoted=promoted,
            telemetry_observations=telemetry_obs
        )

    def _execute_capability(
        self, cap: CapabilityMetadata, request: AcquisitionRequest, profile: TargetProfile
    ) -> Dict[str, Any]:
        adapter = self.registry.resolve_adapter(cap.capability_id)
        if adapter:
            try:
                target_payload = {
                    "name": f"{profile.domain} Product",
                    "url": request.url,
                    "country": profile.inferred_country
                }
                res = adapter.fetch(target_payload)
                raw_b = res.get("raw_content") or b""
                html_text = raw_b.decode("utf-8", errors="ignore") if raw_b else ""
                status_code = res.get("status_code", 200)
                success = bool(status_code and status_code < 400 and len(html_text) > 100)
                return {
                    "success": success,
                    "status_code": status_code,
                    "html": html_text,
                    "error": res.get("error_message"),
                    "failure_category": None if success else FailureCategory.PROVIDER_ERROR.value
                }
            except Exception as e:
                return {
                    "success": False,
                    "status_code": 500,
                    "html": "",
                    "error": str(e),
                    "failure_category": FailureCategory.PROVIDER_ERROR.value
                }

        return {
            "success": False,
            "status_code": 500,
            "html": "",
            "error": "Unbound capability: no adapter registered",
            "failure_category": FailureCategory.PROVIDER_ERROR.value
        }

    @staticmethod
    def _fallback_extract_generic_html(html: str) -> Dict[str, Any]:
        data = {}
        if "<h1>" in html and "</h1>" in html:
            data["product_name"] = html.split("<h1>")[1].split("</h1>")[0]
        elif "<title>" in html and "</title>" in html:
            data["product_name"] = html.split("<title>")[1].split("</title>")[0]

        if "id='price'>" in html:
            data["price"] = html.split("id='price'>")[1].split("</div>")[0]
        elif "class='price'>" in html:
            data["price"] = html.split("class='price'>")[1].split("</div>")[0]

        if "id='availability'>" in html:
            data["availability"] = html.split("id='availability'>")[1].split("</div>")[0]
        elif "InStock" in html:
            data["availability"] = "InStock"

        return data

    def _record_telemetry_and_learning(
        self,
        request: AcquisitionRequest,
        profile: TargetProfile,
        capability: CapabilityMetadata,
        attempt_result: ExplorationAttemptResult,
        val_evidence: List[str]
    ) -> Dict[str, Any]:
        # 1. Update Learning Engine
        self.learning_engine.record_observation(
            capability_id=capability.capability_id,
            domain=profile.domain,
            country=profile.inferred_country,
            success=attempt_result.success,
            validated=attempt_result.validated,
            latency_ms=attempt_result.elapsed_ms,
            bytes_count=attempt_result.bytes_count,
            estimated_cost=attempt_result.cost,
            failure_category=attempt_result.failure_category,
            url_pattern=profile.url_pattern,
            target_type=profile.target_type,
            customer_profile=request.customer_preferences.to_dict()
        )

        # 2. Record Telemetry Observation via AcquisitionObservationRecorder
        obs_status = (
            ObservationStatus.VALIDATED if attempt_result.validated
            else ObservationStatus.VALIDATION_FAILED if attempt_result.success
            else ObservationStatus.ACQUISITION_FAILED
        )

        obs = AcquisitionObservation(
            target=profile.domain.lower(),
            acquisition_method=capability.capability_id,
            url=request.url,
            parameters=request.parameters,
            required_fields=request.fields,
            acquisition_success=attempt_result.success,
            elapsed_ms=attempt_result.elapsed_ms,
            bytes=attempt_result.bytes_count,
            http_status=attempt_result.status_code,
            acquisition_error_code=attempt_result.failure_category,
            acquisition_error_message=attempt_result.error,
            extraction_success=attempt_result.success,
            extracted_fields=request.fields if attempt_result.validated else [],
            validated=attempt_result.validated,
            evidence=val_evidence,
            acquisition_cost=attempt_result.cost,
            final_status=obs_status
        )

        return obs.to_dict()
