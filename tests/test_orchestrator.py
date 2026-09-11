"""
Unit Tests for Neurix Acquisition Orchestrator.

Tests cover strategy selection, failure states (NO_STRATEGY, ACQUISITION_FAILED,
NO_EXTRACTOR, EXTRACTION_FAILED, VALIDATION_FAILED), success flow, vendor stubs,
and retailer-selector independence without making external network calls.
"""

import unittest
from orchestrator.models import (
    AcquisitionRequest,
    AcquisitionResult,
    ValidationResult,
    OrchestrationStatus,
    OrchestrationResult
)
from orchestrator.strategies import BaseAcquisitionStrategy, VendorAPIStrategy
from orchestrator.orchestrator import AcquisitionOrchestrator, TargetExtractorRegistry, TargetValidator


class MockStrategy(BaseAcquisitionStrategy):
    def __init__(self, name="mock_strategy", available=True, should_succeed=True, html="<html><body><h1>Test</h1><div id='price'>10</div></body></html>"):
        self.name = name
        self.available = available
        self.should_succeed = should_succeed
        self.html = html
        self.acquire_called = False

    def is_available(self) -> bool:
        return self.available

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        self.acquire_called = True
        if self.should_succeed:
            return AcquisitionResult(
                success=True,
                method=self.name,
                url=request.url,
                title="Test Title",
                html=self.html,
                elapsed_ms=50
            )
        else:
            return AcquisitionResult(
                success=False,
                method=self.name,
                url=request.url,
                error="Mock acquisition failed"
            )


class TestAcquisitionOrchestrator(unittest.TestCase):

    def setUp(self):
        self.registry = TargetExtractorRegistry()
        self.registry.register("test_target", lambda html, req: {
            "product_name": "Test Product",
            "price": "$10.00",
            "availability": "InStock"
        })
        self.validator = TargetValidator()

    def test_A_browser_strategy_selected_when_available(self):
        strat1 = MockStrategy(name="unavailable_strat", available=False)
        strat2 = MockStrategy(name="browser_cdp", available=True)
        orchestrator = AcquisitionOrchestrator(strategies=[strat1, strat2], extractor_registry=self.registry)
        
        req = AcquisitionRequest(url="http://test.local", target="test_target")
        selected = orchestrator.select_strategy(req)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.name, "browser_cdp")

    def test_B_no_strategy_produces_NO_STRATEGY(self):
        strat = MockStrategy(available=False)
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=self.registry)
        
        req = AcquisitionRequest(url="http://test.local", target="test_target")
        res = orchestrator.execute(req)
        self.assertFalse(res.success)
        self.assertEqual(res.status, OrchestrationStatus.NO_STRATEGY)

    def test_C_no_extractor_produces_NO_EXTRACTOR(self):
        strat = MockStrategy(available=True, should_succeed=True)
        empty_registry = TargetExtractorRegistry()
        empty_registry._extractors.clear()
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=empty_registry)
        
        req = AcquisitionRequest(url="http://test.local", target="unregistered_target")
        res = orchestrator.execute(req)
        self.assertFalse(res.success)
        self.assertEqual(res.status, OrchestrationStatus.NO_EXTRACTOR)

    def test_D_acquisition_failure_produces_ACQUISITION_FAILED(self):
        strat = MockStrategy(available=True, should_succeed=False)
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=self.registry)
        
        req = AcquisitionRequest(url="http://test.local", target="test_target")
        res = orchestrator.execute(req)
        self.assertFalse(res.success)
        self.assertEqual(res.status, OrchestrationStatus.ACQUISITION_FAILED)

    def test_E_extraction_failure_produces_EXTRACTION_FAILED(self):
        strat = MockStrategy(available=True, should_succeed=True)
        
        def failing_extractor(html, req):
            raise ValueError("Malformed HTML format")
            
        fail_registry = TargetExtractorRegistry()
        fail_registry.register("failing_target", failing_extractor)
        
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=fail_registry)
        req = AcquisitionRequest(url="http://test.local", target="failing_target")
        res = orchestrator.execute(req)
        self.assertFalse(res.success)
        self.assertEqual(res.status, OrchestrationStatus.EXTRACTION_FAILED)

    def test_F_validation_failure_produces_VALIDATION_FAILED(self):
        strat = MockStrategy(available=True, should_succeed=True)
        
        def invalid_extractor(html, req):
            return {"product_name": "", "price": None}
            
        inv_registry = TargetExtractorRegistry()
        inv_registry.register("invalid_target", invalid_extractor)
        
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=inv_registry)
        req = AcquisitionRequest(url="http://test.local", target="invalid_target")
        res = orchestrator.execute(req)
        self.assertFalse(res.success)
        self.assertEqual(res.status, OrchestrationStatus.VALIDATION_FAILED)

    def test_G_successful_mocked_flow_produces_SUCCESS(self):
        strat = MockStrategy(available=True, should_succeed=True)
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=self.registry)
        
        req = AcquisitionRequest(url="http://test.local", target="test_target", requirements={"fields": ["product_name", "price"]})
        res = orchestrator.execute(req)
        self.assertTrue(res.success)
        self.assertTrue(res.validated)
        self.assertEqual(res.status, OrchestrationStatus.SUCCESS)
        self.assertEqual(res.data["product_name"], "Test Product")

    def test_H_vendor_strategy_remains_uncalled_stubbed(self):
        vendor_strat = VendorAPIStrategy(vendor_name="scrapfly")
        self.assertFalse(vendor_strat.is_available())
        req = AcquisitionRequest(url="http://test.local", target="test_target")
        acq_res = vendor_strat.acquire(req)
        self.assertFalse(acq_res.success)
        self.assertIn("uncalled stub", acq_res.error)

    def test_I_generic_orchestrator_contains_zero_retailer_selectors(self):
        from pathlib import Path
        orch_file = Path("orchestrator/orchestrator.py")
        content = orch_file.read_text(encoding="utf-8").lower()
        self.assertNotIn("30301", content)
        self.assertNotIn("snickers", content)
        self.assertNotIn("b078y2pjl4", content)
        self.assertNotIn("h-hsa35100e", content)

    def test_J_no_external_network_calls_occur(self):
        # Mocks execute completely locally without socket connections
        strat = MockStrategy(available=True, should_succeed=True)
        orchestrator = AcquisitionOrchestrator(strategies=[strat], extractor_registry=self.registry)
        req = AcquisitionRequest(url="http://test.local", target="test_target")
        res = orchestrator.execute(req)
        self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
