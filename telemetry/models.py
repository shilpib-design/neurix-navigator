"""
Data Models for Acquisition Observations and Outcome Telemetry.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


class ObservationStatus(str):
    VALIDATED = "VALIDATED"
    ACQUISITION_FAILED = "ACQUISITION_FAILED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


@dataclass
class AcquisitionObservation:
    """
    Records a single acquisition attempt and its business outcome.
    """

    # Identity
    target: str
    acquisition_method: str
    url: str
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Request
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)

    # Acquisition
    acquisition_success: bool = False
    elapsed_ms: int = 0
    bytes: int = 0
    raw_html_path: Optional[str] = None
    http_status: Optional[int] = None
    acquisition_error_code: Optional[str] = None
    acquisition_error_message: Optional[str] = None

    # Extraction
    extraction_success: bool = False
    extracted_fields: List[str] = field(default_factory=list)
    extraction_error: Optional[str] = None

    # Validation
    validated: bool = False
    evidence: List[str] = field(default_factory=list)
    validation_error: Optional[str] = None

    # Cost
    acquisition_cost: float = 0.0
    vendor_credits: float = 0.0
    currency: str = "USD"

    # Outcome
    final_status: str = ObservationStatus.ACQUISITION_FAILED

    @property
    def cost_per_attempt(self) -> float:
        """Returns the cost incurred for this attempt."""
        return self.acquisition_cost

    @property
    def cost_per_validated_result(self) -> Optional[float]:
        """
        Returns the cost incurred if and only if the attempt resulted in a VALIDATED status.
        Returns None if validation failed.
        """
        if self.final_status == ObservationStatus.VALIDATED:
            return self.acquisition_cost
        return None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["cost_per_attempt"] = self.cost_per_attempt
        d["cost_per_validated_result"] = self.cost_per_validated_result
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AcquisitionObservation":
        d_copy = d.copy()
        d_copy.pop("cost_per_attempt", None)
        d_copy.pop("cost_per_validated_result", None)
        return cls(**d_copy)
