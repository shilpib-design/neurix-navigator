"""
Unified Execution Pipeline Orchestrator for Neurix Navigator v0.1 Core.
Connects Request -> Intelligence -> Candidates -> Optimizer -> Orchestrator -> Extraction -> Validation -> Metering -> Learning -> Storage.
"""

import time
from typing import Dict, Any, List, Optional
from core.models import (
    AcquisitionRequest,
    TargetProfile,
    CapabilityMetadata,
    BillingRecord,
    PolicyState,
    HealthState,
    FailureCategory
)
from core.intelligence import TargetIntelligence
from core.rate_card import RateCardRegistry
from core.registry import ProviderRegistry
from core.candidate import CandidateGenerator
from core.optimizer import EconomicOptimizer
from core.fallback import FallbackManager
from core.learning import LearningEngine
from core.policy import PolicyEngine
from core.meter import CustomerUsageMeter
from core.storage import LeanStorageManager

from orchestrator.models import AcquisitionRequest as ArchReq, AcquisitionResult
from orchestrator.orchestrator import TargetExtractorRegistry, TargetValidator


class UnifiedPipeline:
    """
    Unified end-to-end execution pipeline for Neurix Navigator v0.1.
    """

    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        rate_card_registry: Optional[RateCardRegistry] = None,
        extractor_registry: Optional[TargetExtractorRegistry] = None,
        validator: Optional[TargetValidator] = None,
        exploration_rate: float = 0.10
    ):
        self.registry = registry or ProviderRegistry()
        self.rate_card_registry = rate_card_registry or RateCardRegistry()
        self.candidate_generator = CandidateGenerator(self.registry)
        self.optimizer = EconomicOptimizer(self.rate_card_registry, exploration_rate=exploration_rate)
        self.fallback_manager = FallbackManager(self.registry)
        self.learning_engine = LearningEngine(self.registry)
        self.policy_engine = PolicyEngine()
        self.usage_meter = CustomerUsageMeter()
        self.storage_manager = LeanStorageManager()

        self.extractor_registry = extractor_registry or TargetExtractorRegistry()
        self.validator = validator or TargetValidator()

    def process_request(self, request: AcquisitionRequest) -> Dict[str, Any]:
        pipeline_start = time.time()

        # 1. Target Intelligence
        profile = TargetIntelligence.analyze(request)

        # 2. Candidate Generation
        candidates = self.candidate_generator.generate_candidates(profile, request.customer_preferences)

        # 3. Decision Engine & Cascade Evaluation
        active_policy = self.policy_engine.get_active_policy(profile)
        if active_policy and not request.parameters.get("force_reoptimize"):
            # Use active policy cascade
            selected_cascade_ids = active_policy.selected_cascade
            selected_cascade = [self.registry.get(cid) for cid in selected_cascade_ids if self.registry.get(cid)]
            eval_metrics = {
                "expected_validation": active_policy.expected_validation,
                "expected_latency": active_policy.expected_latency,
                "expected_cost": active_policy.expected_cost,
                "cost_per_validated": active_policy.expected_cost_per_validated
            }
            is_exploration = False
        else:
            selected_cascade, eval_metrics, is_exploration = self.optimizer.select_optimal_strategy(
                candidates, profile, request.customer_preferences
            )

        # 4. Acquisition & Fallback Execution Loop
        attempts = []
        final_validated = False
        final_data = {}
        final_html = ""
        total_cost = 0.0
        remaining_cascade = list(selected_cascade)

        while remaining_cascade and not final_validated:
            current_cap = remaining_cascade[0]
            att_start = time.time()

            # Execute attempt via provider adapter or mock strategy
            acq_res = self._execute_capability(current_cap, request, profile)
            elapsed_ms = int((time.time() - att_start) * 1000)

            # Extract & Validate
            html_content = acq_res.get("html", "")
            bytes_count = len(html_content.encode("utf-8")) if html_content else 0

            extracted_data = {}
            extractor_fn = self.extractor_registry.get(profile.domain)
            if extractor_fn and acq_res.get("success"):
                try:
                    arch_req = ArchReq(url=request.url, target=profile.domain.lower(), parameters=request.parameters)
                    extracted_data = extractor_fn(html_content, arch_req)
                except Exception:
                    extracted_data = {}

            val_res = self.validator.validate(extracted_data, ArchReq(url=request.url, target=profile.domain.lower(), requirements={"fields": request.fields}))
            is_validated = bool(acq_res.get("success") and val_res.validated)

            # Calculate Marginal Cost for attempt
            cost_attempt = self.rate_card_registry.get_marginal_cost(current_cap.provider_id, current_cap.capability_id, domain=profile.domain)
            total_cost += cost_attempt

            # Record Rate Card usage
            self.rate_card_registry.record_usage(current_cap.provider_id, current_cap.capability_id)

            # Failure Category Classification
            fail_cat = None
            if not is_validated:
                if "429" in str(acq_res.get("error", "")):
                    fail_cat = FailureCategory.RATE_LIMIT.value
                elif "timeout" in str(acq_res.get("error", "")).lower():
                    fail_cat = FailureCategory.TIMEOUT.value
                elif "block" in str(acq_res.get("error", "")).lower():
                    fail_cat = FailureCategory.BLOCK_PAGE.value
                else:
                    fail_cat = FailureCategory.VALIDATION_FAILED.value

            # Record attempt log
            att_record = {
                "capability_id": current_cap.capability_id,
                "provider_id": current_cap.provider_id,
                "success": acq_res.get("success", False),
                "validated": is_validated,
                "elapsed_ms": elapsed_ms,
                "bytes": bytes_count,
                "cost": cost_attempt,
                "failure_category": fail_cat
            }
            attempts.append(att_record)

            # 5. Real-Time Learning Update
            self.learning_engine.record_observation(
                capability_id=current_cap.capability_id,
                domain=profile.domain,
                country=profile.inferred_country,
                success=acq_res.get("success", False),
                validated=is_validated,
                latency_ms=elapsed_ms,
                bytes_count=bytes_count,
                estimated_cost=cost_attempt,
                failure_category=fail_cat
            )

            # 6. Raw Data TTL Metadata Storage (Suppresses permanent raw HTML by default)
            self.storage_manager.store_raw_payload_metadata(request.request_id, current_cap.capability_id, html_content)

            if is_validated:
                final_validated = True
                final_data = extracted_data
                final_html = html_content
                break
            else:
                # 7. Failure-Aware Fallback Cascade Adjustment
                remaining_cascade = self.fallback_manager.adjust_cascade_on_failure(
                    remaining_cascade, current_cap, fail_cat or "VALIDATION_FAILED"
                )

        # 8. Policy Evaluation & Instant Real-Time Promotion Check
        executed_cascade_ids = [a["capability_id"] for a in attempts]
        sample_size = current_cap.historical_metrics.get("sample_size", 1) if selected_cascade else 1
        promoted, current_policy_state = self.policy_engine.evaluate_and_promote(
            profile, executed_cascade_ids, eval_metrics, sample_size=sample_size
        )

        pipeline_latency_ms = int((time.time() - pipeline_start) * 1000)

        # 9. Usage & Billing Metering
        billing_record = self.usage_meter.record_transaction(
            request=request,
            target_domain=profile.domain,
            validated_result=final_validated,
            response_size_bytes=len(final_html.encode("utf-8")) if final_html else 0,
            processing_time_ms=pipeline_latency_ms,
            provider_cost=total_cost
        )
        self.storage_manager.store_billing_record(billing_record)

        return {
            "request_id": request.request_id,
            "target_profile": profile.to_dict(),
            "success": final_validated,
            "validated": final_validated,
            "data": final_data,
            "selected_cascade": [c.capability_id for c in selected_cascade],
            "executed_attempts": attempts,
            "total_provider_cost": round(total_cost, 6),
            "total_latency_ms": pipeline_latency_ms,
            "billing": billing_record.to_dict(),
            "policy": current_policy_state.to_dict(),
            "policy_promoted": promoted,
            "is_exploration": is_exploration
        }

    def _execute_capability(self, cap: CapabilityMetadata, request: AcquisitionRequest, profile: TargetProfile) -> Dict[str, Any]:
        """
        Executes capability using registered adapter or internal stub.
        """
        if cap.adapter:
            try:
                res = cap.adapter.fetch({"name": f"{profile.domain} Product", "url": request.url})
                raw_b = res.get("raw_content") or b""
                html_text = raw_b.decode("utf-8", errors="ignore") if raw_b else ""
                status_code = res.get("status_code", 200)
                success = bool(status_code and status_code < 400 and len(html_text) > 100)
                return {
                    "success": success,
                    "status_code": status_code,
                    "html": html_text,
                    "error": res.get("error_message")
                }
            except Exception as e:
                return {"success": False, "status_code": 500, "html": "", "error": str(e)}

        # Default fallback stub if cap.adapter is None
        return {
            "success": True,
            "status_code": 200,
            "html": f"<html><body><h1>{profile.domain} Product</h1><div id='price'>$19.99</div><div id='availability'>InStock</div></body></html>",
            "error": None
        }
