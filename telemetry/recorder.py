"""
Acquisition Observation Recorder and Telemetry Aggregator for Neurix Navigator-01.

Maps orchestration execution results into normalized observations, persists them
to local JSONL logs, and aggregates cost and performance metrics.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from orchestrator.models import OrchestrationResult, AcquisitionRequest, OrchestrationStatus
from telemetry.models import AcquisitionObservation, ObservationStatus


class AcquisitionObservationRecorder:
    """
    Normalizes OrchestrationResult objects into AcquisitionObservation telemetry logs.
    """

    def record_orchestration_result(
        self,
        result: OrchestrationResult,
        request: AcquisitionRequest,
        cost_info: Optional[Dict[str, Any]] = None,
        bytes_count: int = 0,
        raw_html_path: Optional[str] = None
    ) -> AcquisitionObservation:
        """
        Transforms an OrchestrationResult into a normalized AcquisitionObservation.
        """
        cost_info = cost_info or {}
        acq_data = result.acquisition or {}
        val_data = result.validation or {}

        # Determine final status
        if result.validated and result.success:
            final_status = ObservationStatus.VALIDATED
        elif result.status in (OrchestrationStatus.ACQUISITION_FAILED, OrchestrationStatus.NO_STRATEGY):
            final_status = ObservationStatus.ACQUISITION_FAILED
        elif result.status in (OrchestrationStatus.EXTRACTION_FAILED, OrchestrationStatus.NO_EXTRACTOR):
            final_status = ObservationStatus.EXTRACTION_FAILED
        elif result.status == OrchestrationStatus.VALIDATION_FAILED:
            final_status = ObservationStatus.VALIDATION_FAILED
        else:
            final_status = ObservationStatus.ACQUISITION_FAILED

        # Determine acquisition success
        acq_success = result.status not in (OrchestrationStatus.ACQUISITION_FAILED, OrchestrationStatus.NO_STRATEGY)
        ext_success = result.status not in (
            OrchestrationStatus.ACQUISITION_FAILED,
            OrchestrationStatus.NO_STRATEGY,
            OrchestrationStatus.EXTRACTION_FAILED,
            OrchestrationStatus.NO_EXTRACTOR
        )

        extracted_fields = [k for k, v in result.data.items() if v not in (None, "", [])]

        observation = AcquisitionObservation(
            target=request.target,
            acquisition_method=acq_data.get("method", "unknown"),
            url=request.url,
            parameters=request.parameters,
            required_fields=request.requirements.get("fields", []),
            acquisition_success=acq_success,
            elapsed_ms=acq_data.get("elapsed_ms", 0),
            bytes=bytes_count or acq_data.get("bytes", 0),
            raw_html_path=raw_html_path or acq_data.get("raw_html_path"),
            http_status=acq_data.get("http_status", 200 if acq_success else None),
            acquisition_error_code=None if acq_success else str(result.status.value if hasattr(result.status, "value") else result.status),
            acquisition_error_message="; ".join(result.errors) if not acq_success else None,
            extraction_success=ext_success,
            extracted_fields=extracted_fields,
            extraction_error="; ".join(result.errors) if not ext_success and acq_success else None,
            validated=result.validated,
            evidence=val_data.get("evidence", []),
            validation_error="; ".join(result.errors) if not result.validated and ext_success else None,
            acquisition_cost=float(cost_info.get("acquisition_cost", 0.0)),
            vendor_credits=float(cost_info.get("vendor_credits", 0.0)),
            currency=str(cost_info.get("currency", "USD")),
            final_status=final_status
        )

        return observation

    def save_to_jsonl(self, observation: AcquisitionObservation, file_path: str = "results/observations.jsonl") -> str:
        """
        Appends a single JSON representation of an observation to a JSONL file.
        Ensures raw HTML content is never embedded into the log file.
        """
        target_path = Path(file_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        d = observation.to_dict()
        # Guarantee no large html field exists
        d.pop("html", None)
        d.pop("html_content", None)

        with open(target_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(d) + "\n")

        return str(target_path)

    def load_observations(self, file_path: str = "results/observations.jsonl") -> List[AcquisitionObservation]:
        """
        Loads all recorded observations from a JSONL file.
        """
        target_path = Path(file_path)
        if not target_path.exists():
            return []

        observations = []
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        d = json.loads(line_str)
                        observations.append(AcquisitionObservation.from_dict(d))
                    except Exception:
                        pass
        return observations


# --- Metric Helper Functions ---

def get_success_rate(observations: List[AcquisitionObservation]) -> float:
    """Calculates acquisition success rate."""
    if not observations:
        return 0.0
    successful = sum(1 for o in observations if o.acquisition_success)
    return round(successful / len(observations), 4)


def get_validation_rate(observations: List[AcquisitionObservation]) -> float:
    """Calculates validation rate over total attempts."""
    if not observations:
        return 0.0
    validated = sum(1 for o in observations if o.final_status == ObservationStatus.VALIDATED)
    return round(validated / len(observations), 4)


def get_average_latency(observations: List[AcquisitionObservation]) -> float:
    """Calculates average latency (elapsed_ms) across all attempts."""
    if not observations:
        return 0.0
    total_ms = sum(o.elapsed_ms for o in observations)
    return round(total_ms / len(observations), 2)


def get_cost_per_validated_result(observations: List[AcquisitionObservation]) -> float:
    """
    Calculates acquisition cost per validated result.
    Total acquisition cost across all attempts divided by the count of VALIDATED observations.
    Excludes failed validation attempts from the validated denominator.
    """
    validated_count = sum(1 for o in observations if o.final_status == ObservationStatus.VALIDATED)
    if validated_count == 0:
        return 0.0
    total_cost = sum(o.acquisition_cost for o in observations)
    return round(total_cost / validated_count, 6)


def calculate_metrics(observations: List[AcquisitionObservation]) -> Dict[str, Any]:
    """
    Aggregates comprehensive outcome metrics across a set of observations.
    """
    total_attempts = len(observations)
    successful_acquisitions = sum(1 for o in observations if o.acquisition_success)
    validated_results = sum(1 for o in observations if o.final_status == ObservationStatus.VALIDATED)
    total_cost = sum(o.acquisition_cost for o in observations)

    return {
        "total_attempts": total_attempts,
        "successful_acquisitions": successful_acquisitions,
        "validated_results": validated_results,
        "success_rate": get_success_rate(observations),
        "validation_rate": get_validation_rate(observations),
        "average_latency_ms": get_average_latency(observations),
        "total_acquisition_cost": round(total_cost, 6),
        "cost_per_validated_result": get_cost_per_validated_result(observations)
    }
