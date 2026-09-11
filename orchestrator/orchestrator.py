"""
Deterministic Acquisition Orchestrator for Neurix Navigator-01.

Coordinates acquisition strategy selection, target extraction routing,
and result validation without site-specific code inside the orchestrator.
"""

from typing import Dict, Any, List, Optional, Callable
from orchestrator.models import (
    AcquisitionRequest,
    AcquisitionResult,
    ValidationResult,
    OrchestrationStatus,
    OrchestrationResult
)
from orchestrator.strategies import BaseAcquisitionStrategy, BrowserCDPStrategy


class TargetExtractorRegistry:
    """
    Registry mapping target keys (e.g. "kroger", "amazon", "flipkart") to extractor functions.
    """

    def __init__(self):
        self._extractors: Dict[str, Callable[[str, AcquisitionRequest], Dict[str, Any]]] = {}
        self._register_default_extractors()

    def register(self, target: str, extractor_fn: Callable[[str, AcquisitionRequest], Dict[str, Any]]):
        self._extractors[target.lower().strip()] = extractor_fn

    def get(self, target: str) -> Optional[Callable[[str, AcquisitionRequest], Dict[str, Any]]]:
        return self._extractors.get(target.lower().strip())

    def _register_default_extractors(self):
        # Default registration using existing domain extractors
        try:
            from extract_local import extract_schema_from_html
            self.register("kroger", lambda html, req: extract_schema_from_html(html, "kroger.html"))
        except Exception:
            pass

        try:
            from amazon.product import extract_amazon_product
            self.register("amazon", lambda html, req: extract_amazon_product(html, req.parameters.get("asin", "")))
        except Exception:
            pass

        try:
            from flipkart.product import extract_flipkart_product
            self.register("flipkart", lambda html, req: extract_flipkart_product(html, req.parameters.get("product_id", "")))
        except Exception:
            pass



class TargetValidator:
    """
    Generic validation engine enforcing business schema completeness and evidence verification.
    """

    def validate(self, data: Dict[str, Any], request: AcquisitionRequest) -> ValidationResult:
        if not data or not isinstance(data, dict):
            return ValidationResult(
                validated=False,
                confidence=0.0,
                evidence=[],
                data={},
                errors=["Extractor returned empty or invalid data format"]
            )

        errors = []
        evidence = []

        # Check required fields requested in requirements spec
        req_fields = request.requirements.get("fields", ["product_name", "price"])
        for field in req_fields:
            val = data.get(field)
            if val is None or val == "" or val == []:
                errors.append(f"Missing required field: '{field}'")
            else:
                evidence.append(f"Field '{field}' present")

        # Check product identifier (product_name or id/upc/asin)
        product_name = data.get("product_name") or data.get("name")
        product_id = data.get("product_id") or data.get("upc") or data.get("asin")
        price = data.get("price")
        availability = data.get("availability")

        if not product_name:
            errors.append("Product name is missing or empty")

        if not (price or availability):
            errors.append("Neither price nor availability evidence is present")

        validated = len(errors) == 0
        confidence = 1.0 if validated else max(0.0, 1.0 - (len(errors) * 0.3))

        return ValidationResult(
            validated=validated,
            confidence=round(confidence, 2),
            evidence=evidence,
            data=data,
            errors=errors
        )


class AcquisitionOrchestrator:
    """
    Deterministic Acquisition Orchestrator.
    
    Coordinates strategy selection, acquisition, target extraction, and validation.
    """

    def __init__(
        self,
        strategies: Optional[List[BaseAcquisitionStrategy]] = None,
        extractor_registry: Optional[TargetExtractorRegistry] = None,
        validator: Optional[TargetValidator] = None
    ):
        self.strategies = strategies if strategies is not None else [BrowserCDPStrategy()]
        self.extractor_registry = extractor_registry or TargetExtractorRegistry()
        self.validator = validator or TargetValidator()

    def select_strategy(self, request: AcquisitionRequest) -> Optional[BaseAcquisitionStrategy]:
        """
        Deterministically selects the first available acquisition strategy.
        """
        for strategy in self.strategies:
            if strategy.is_available():
                return strategy
        return None

    def execute(self, request: AcquisitionRequest) -> OrchestrationResult:
        """
        Executes the acquisition pipeline:
        Strategy Selection -> Acquisition -> Target Extraction -> Validation
        """
        # 1. Select Strategy
        strategy = self.select_strategy(request)
        if not strategy:
            return OrchestrationResult(
                success=False,
                validated=False,
                status=OrchestrationStatus.NO_STRATEGY,
                acquisition={"method": "none", "elapsed_ms": 0},
                data={},
                validation={"evidence": [], "confidence": 0.0},
                errors=["No available acquisition strategy found."]
            )

        # 2. Execute Acquisition
        acq_result = strategy.acquire(request)
        acq_info = {
            "method": acq_result.method,
            "elapsed_ms": acq_result.elapsed_ms,
            "url": acq_result.url,
            "title": acq_result.title
        }

        if not acq_result.success or not acq_result.html:
            return OrchestrationResult(
                success=False,
                validated=False,
                status=OrchestrationStatus.ACQUISITION_FAILED,
                acquisition=acq_info,
                data={},
                validation={"evidence": [], "confidence": 0.0},
                errors=[acq_result.error or "Acquisition strategy failed to retrieve page content."]
            )

        # 3. Lookup Target Extractor
        extractor_fn = self.extractor_registry.get(request.target)
        if not extractor_fn:
            return OrchestrationResult(
                success=False,
                validated=False,
                status=OrchestrationStatus.NO_EXTRACTOR,
                acquisition=acq_info,
                data={},
                validation={"evidence": [], "confidence": 0.0},
                errors=[f"No extractor registered for target '{request.target}'."]
            )

        # 4. Execute Extraction
        try:
            extracted_data = extractor_fn(acq_result.html, request)
        except Exception as e:
            return OrchestrationResult(
                success=False,
                validated=False,
                status=OrchestrationStatus.EXTRACTION_FAILED,
                acquisition=acq_info,
                data={},
                validation={"evidence": [], "confidence": 0.0},
                errors=[f"Extraction failed for target '{request.target}': {e}"]
            )

        if not extracted_data:
            return OrchestrationResult(
                success=False,
                validated=False,
                status=OrchestrationStatus.EXTRACTION_FAILED,
                acquisition=acq_info,
                data={},
                validation={"evidence": [], "confidence": 0.0},
                errors=[f"Extractor returned empty result for target '{request.target}'."]
            )

        # 5. Execute Validation
        val_result = self.validator.validate(extracted_data, request)
        if not val_result.validated:
            return OrchestrationResult(
                success=False,
                validated=False,
                status=OrchestrationStatus.VALIDATION_FAILED,
                acquisition=acq_info,
                data=extracted_data,
                validation=val_result.to_dict(),
                errors=val_result.errors
            )

        # 6. Success
        return OrchestrationResult(
            success=True,
            validated=True,
            status=OrchestrationStatus.SUCCESS,
            acquisition=acq_info,
            data=extracted_data,
            validation=val_result.to_dict(),
            errors=[]
        )

    def recommend_strategy(
        self,
        request: AcquisitionRequest,
        observations: List[Any],
        scorer: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Optional recommendation layer. Returns top recommended StrategyScore.
        Does NOT alter execution behavior or select strategy for execute().
        """
        from scoring.scorer import StrategyScorer
        available_methods = [s.name for s in self.strategies if s.is_available()]
        s_scorer = scorer or StrategyScorer()
        return s_scorer.recommend(
            target=request.target,
            observations=observations,
            available_methods=available_methods
        )

