"""
Unified Data Models for Neurix Navigator v0.1 Core.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PriorityPreference(str, Enum):
    COST = "cost"
    LATENCY = "latency"
    SUCCESS = "success"


class HealthState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    RATE_LIMITED = "RATE_LIMITED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class FailureCategory(str, Enum):
    TIMEOUT = "TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    BLOCK_PAGE = "BLOCK_PAGE"
    CAPTCHA = "CAPTCHA"
    RATE_LIMIT = "RATE_LIMIT"
    WRONG_LOCATION = "WRONG_LOCATION"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    ASYNC_PENDING = "ASYNC_PENDING"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    BROWSER_ERROR = "BROWSER_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    OTHER = "OTHER"


@dataclass
class CustomerPreferences:
    min_success_rate: float = 0.80
    max_latency_ms: int = 25000
    priority: PriorityPreference = PriorityPreference.COST

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_success_rate": self.min_success_rate,
            "max_latency_ms": self.max_latency_ms,
            "priority": self.priority.value if isinstance(self.priority, Enum) else str(self.priority)
        }


@dataclass
class AcquisitionRequest:
    url: str
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
    customer_id: str = "default_customer"
    fields: List[str] = field(default_factory=lambda: ["product_name", "price", "availability"])
    parameters: Dict[str, Any] = field(default_factory=dict)
    customer_preferences: CustomerPreferences = field(default_factory=CustomerPreferences)
    country: Optional[str] = None  # Optional customer country parameter

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "customer_id": self.customer_id,
            "url": self.url,
            "fields": self.fields,
            "parameters": self.parameters,
            "customer_preferences": self.customer_preferences.to_dict(),
            "country": self.country
        }


@dataclass
class TargetProfile:
    domain: str
    url_pattern: str
    inferred_country: str
    country_confidence: float
    target_type: str  # e.g. "pdp", "search", "category"
    location_sensitivity: bool
    browser_likelihood: float
    required_capabilities: List[str] = field(default_factory=list)
    fingerprint: str = ""

    def context_key(self) -> str:
        return f"{self.domain}:{self.target_type}:{self.inferred_country}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "url_pattern": self.url_pattern,
            "inferred_country": self.inferred_country,
            "country_confidence": self.country_confidence,
            "target_type": self.target_type,
            "location_sensitivity": self.location_sensitivity,
            "browser_likelihood": self.browser_likelihood,
            "required_capabilities": self.required_capabilities,
            "fingerprint": self.fingerprint
        }


@dataclass
class CapabilityMetadata:
    provider_id: str
    capability_id: str
    enabled: bool = True
    acquisition_method: str = "api"  # "api", "browser", "proxy"
    country_capabilities: List[str] = field(default_factory=lambda: ["US", "IN"])
    location_capabilities: List[str] = field(default_factory=list)
    target_capabilities: List[str] = field(default_factory=lambda: ["pdp", "generic"])
    estimated_cost: float = 0.001
    pricing_unit: str = "request"  # "request", "gb"
    browser_support: bool = False
    proxy_type: str = "None"  # "None", "Residential", "Datacenter", "Mobile"
    current_health: HealthState = HealthState.AVAILABLE
    historical_metrics: Dict[str, Any] = field(default_factory=lambda: {
        "success_rate": 0.85,
        "validation_rate": 0.80,
        "avg_latency_ms": 3000,
        "sample_size": 10
    })
    failure_categories: List[str] = field(default_factory=list)
    adapter: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "capability_id": self.capability_id,
            "enabled": self.enabled,
            "acquisition_method": self.acquisition_method,
            "country_capabilities": self.country_capabilities,
            "location_capabilities": self.location_capabilities,
            "target_capabilities": self.target_capabilities,
            "estimated_cost": self.estimated_cost,
            "pricing_unit": self.pricing_unit,
            "browser_support": self.browser_support,
            "proxy_type": self.proxy_type,
            "current_health": self.current_health.value if isinstance(self.current_health, Enum) else str(self.current_health),
            "historical_metrics": self.historical_metrics,
            "failure_categories": self.failure_categories
        }


@dataclass
class BillingRecord:
    customer_id: str
    request_id: str
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    target: str = ""
    status: str = "SUCCESS"
    validated_result: bool = True
    billable_unit: int = 1
    response_size_bytes: int = 0
    processing_time_ms: int = 0
    customer_price: float = 0.05
    provider_cost: float = 0.001
    infra_cost: float = 0.0001
    gross_margin: float = 0.0489

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "target": self.target,
            "status": self.status,
            "validated_result": self.validated_result,
            "billable_unit": self.billable_unit,
            "response_size_bytes": self.response_size_bytes,
            "processing_time_ms": self.processing_time_ms,
            "customer_price": self.customer_price,
            "provider_cost": self.provider_cost,
            "infra_cost": self.infra_cost,
            "gross_margin": self.gross_margin
        }


@dataclass
class PolicyState:
    context_key: str
    selected_cascade: List[str]
    expected_success: float
    expected_validation: float
    expected_latency: float
    expected_cost: float
    expected_cost_per_validated: float
    confidence: float
    sample_size: int
    version: int = 1
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_key": self.context_key,
            "selected_cascade": self.selected_cascade,
            "expected_success": round(self.expected_success, 4),
            "expected_validation": round(self.expected_validation, 4),
            "expected_latency": round(self.expected_latency, 1),
            "expected_cost": round(self.expected_cost, 6),
            "expected_cost_per_validated": round(self.expected_cost_per_validated, 6),
            "confidence": round(self.confidence, 4),
            "sample_size": self.sample_size,
            "version": self.version,
            "last_updated": self.last_updated
        }
