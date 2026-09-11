"""
Data Models for Neurix Acquisition Orchestrator.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class OrchestrationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ACQUISITION_FAILED = "ACQUISITION_FAILED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NO_STRATEGY = "NO_STRATEGY"
    NO_EXTRACTOR = "NO_EXTRACTOR"


@dataclass
class AcquisitionRequest:
    """
    Normalized, retailer-agnostic acquisition request model.
    """
    url: str
    target: str  # e.g., "kroger", "amazon", "flipkart"
    parameters: Dict[str, Any] = field(default_factory=dict)
    requirements: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "target": self.target,
            "parameters": self.parameters,
            "requirements": self.requirements
        }


@dataclass
class AcquisitionResult:
    """
    Raw payload result produced by an acquisition strategy.
    """
    success: bool
    method: str  # e.g., "browser_cdp", "vendor_api"
    url: str
    title: str = ""
    html: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "method": self.method,
            "url": self.url,
            "title": self.title,
            "html_length": len(self.html),
            "elapsed_ms": self.elapsed_ms,
            "error": self.error
        }


@dataclass
class ValidationResult:
    """
    Validation output produced by TargetValidator.
    """
    validated: bool
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validated": self.validated,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "data": self.data,
            "errors": self.errors
        }


@dataclass
class OrchestrationResult:
    """
    Final normalized output returned by AcquisitionOrchestrator.
    """
    success: bool
    validated: bool
    status: OrchestrationStatus
    acquisition: Dict[str, Any]
    data: Dict[str, Any]
    validation: Dict[str, Any]
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "validated": self.validated,
            "status": self.status.value if isinstance(self.status, OrchestrationStatus) else str(self.status),
            "acquisition": self.acquisition,
            "data": self.data,
            "validation": self.validation,
            "errors": self.errors
        }
