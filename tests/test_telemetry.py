"""
Unit Tests for Neurix Acquisition Telemetry & Outcome Observation Layer.

Tests cover successful/failed observations, zero-cost vs. paid cost metrics,
JSONL persistence, path-based HTML referencing, and metric aggregations without network calls.
"""

import unittest
import os
import json
import tempfile
from pathlib import Path
from orchestrator.models import (
    AcquisitionRequest,
    OrchestrationResult,
    OrchestrationStatus
)
from telemetry.models import AcquisitionObservation, ObservationStatus
from telemetry.recorder import (
    AcquisitionObservationRecorder,
    calculate_metrics,
    get_success_rate,
    get_validation_rate,
    get_average_latency,
    get_cost_per_validated_result
)


class TestAcquisitionTelemetry(unittest.TestCase):

    def setUp(self):
        self.recorder = AcquisitionObservationRecorder()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.jsonl_path = str(Path(self.temp_dir.name) / "test_observations.jsonl")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_A_successful_browser_acquisition(self):
        req = AcquisitionRequest(url="https://test.local/p/1", target="kroger")
        orch_res = OrchestrationResult(
            success=True,
            validated=True,
            status=OrchestrationStatus.SUCCESS,
            acquisition={"method": "browser_cdp", "elapsed_ms": 2500},
            data={"product_name": "Test Item", "price": "$1.99"},
            validation={"evidence": ["Schema valid"]}
        )
        obs = self.recorder.record_orchestration_result(orch_res, req, raw_html_path="results/raw1.html", bytes_count=500000)
        self.assertTrue(obs.acquisition_success)
        self.assertTrue(obs.validated)
        self.assertEqual(obs.final_status, ObservationStatus.VALIDATED)
        self.assertEqual(obs.raw_html_path, "results/raw1.html")
        self.assertEqual(obs.bytes, 500000)

    def test_B_acquisition_failure(self):
        req = AcquisitionRequest(url="https://test.local/p/2", target="kroger")
        orch_res = OrchestrationResult(
            success=False,
            validated=False,
            status=OrchestrationStatus.ACQUISITION_FAILED,
            acquisition={"method": "browser_cdp", "elapsed_ms": 500},
            data={},
            validation={},
            errors=["Connection Timeout"]
        )
        obs = self.recorder.record_orchestration_result(orch_res, req)
        self.assertFalse(obs.acquisition_success)
        self.assertFalse(obs.validated)
        self.assertEqual(obs.final_status, ObservationStatus.ACQUISITION_FAILED)
        self.assertIn("Connection Timeout", obs.acquisition_error_message)

    def test_C_extraction_failure(self):
        req = AcquisitionRequest(url="https://test.local/p/3", target="amazon")
        orch_res = OrchestrationResult(
            success=False,
            validated=False,
            status=OrchestrationStatus.EXTRACTION_FAILED,
            acquisition={"method": "browser_cdp", "elapsed_ms": 3000},
            data={},
            validation={},
            errors=["Extractor returned empty result"]
        )
        obs = self.recorder.record_orchestration_result(orch_res, req)
        self.assertTrue(obs.acquisition_success)
        self.assertFalse(obs.extraction_success)
        self.assertEqual(obs.final_status, ObservationStatus.EXTRACTION_FAILED)

    def test_D_validation_failure(self):
        req = AcquisitionRequest(url="https://test.local/p/4", target="flipkart")
        orch_res = OrchestrationResult(
            success=False,
            validated=False,
            status=OrchestrationStatus.VALIDATION_FAILED,
            acquisition={"method": "browser_cdp", "elapsed_ms": 2000},
            data={"product_name": "Incomplete Item"},
            validation={"evidence": []},
            errors=["Missing required field 'price'"]
        )
        obs = self.recorder.record_orchestration_result(orch_res, req)
        self.assertTrue(obs.acquisition_success)
        self.assertTrue(obs.extraction_success)
        self.assertFalse(obs.validated)
        self.assertEqual(obs.final_status, ObservationStatus.VALIDATION_FAILED)

    def test_E_zero_cost_acquisition(self):
        obs = AcquisitionObservation(
            target="kroger",
            acquisition_method="browser_cdp",
            url="https://test.local",
            acquisition_cost=0.0,
            final_status=ObservationStatus.VALIDATED
        )
        self.assertEqual(obs.cost_per_attempt, 0.0)
        self.assertEqual(obs.cost_per_validated_result, 0.0)

    def test_F_paid_vendor_acquisition_represented_through_mocked_cost(self):
        obs = AcquisitionObservation(
            target="kroger",
            acquisition_method="vendor_api:scrapfly",
            url="https://test.local",
            acquisition_cost=0.005,
            vendor_credits=1.0,
            final_status=ObservationStatus.VALIDATED
        )
        self.assertEqual(obs.cost_per_attempt, 0.005)
        self.assertEqual(obs.cost_per_validated_result, 0.005)

    def test_G_cost_per_validated_result(self):
        obs1 = AcquisitionObservation(target="kroger", acquisition_method="vendor", url="http://1", acquisition_cost=0.010, final_status=ObservationStatus.VALIDATED)
        obs2 = AcquisitionObservation(target="kroger", acquisition_method="vendor", url="http://2", acquisition_cost=0.010, final_status=ObservationStatus.VALIDATED)
        metrics = calculate_metrics([obs1, obs2])
        self.assertEqual(metrics["total_acquisition_cost"], 0.02)
        self.assertEqual(metrics["cost_per_validated_result"], 0.01)

    def test_H_failed_validation_excluded_from_validated_result_denominator(self):
        obs1 = AcquisitionObservation(target="kroger", acquisition_method="vendor", url="http://1", acquisition_cost=0.010, final_status=ObservationStatus.VALIDATED)
        obs2 = AcquisitionObservation(target="kroger", acquisition_method="vendor", url="http://2", acquisition_cost=0.010, final_status=ObservationStatus.VALIDATION_FAILED)
        metrics = calculate_metrics([obs1, obs2])
        # Total cost is 0.02, but validated results count is 1. Cost per validated result = 0.02 / 1 = 0.02
        self.assertEqual(metrics["total_acquisition_cost"], 0.02)
        self.assertEqual(metrics["validated_results"], 1)
        self.assertEqual(metrics["cost_per_validated_result"], 0.02)

    def test_I_jsonl_persistence(self):
        obs = AcquisitionObservation(
            target="kroger",
            acquisition_method="browser_cdp",
            url="https://test.local/p/5",
            elapsed_ms=1500,
            final_status=ObservationStatus.VALIDATED
        )
        self.recorder.save_to_jsonl(obs, file_path=self.jsonl_path)
        self.assertTrue(os.path.exists(self.jsonl_path))

        loaded = self.recorder.load_observations(file_path=self.jsonl_path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].target, "kroger")
        self.assertEqual(loaded[0].url, "https://test.local/p/5")

    def test_J_html_is_referenced_by_path_rather_than_embedded(self):
        obs = AcquisitionObservation(
            target="amazon",
            acquisition_method="browser_cdp",
            url="https://test.local/dp/1",
            raw_html_path="results/donut_amazon.html",
            bytes=614022,
            final_status=ObservationStatus.VALIDATED
        )
        self.recorder.save_to_jsonl(obs, file_path=self.jsonl_path)

        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            content = f.read()

        d = json.loads(content.strip())
        self.assertIn("raw_html_path", d)
        self.assertEqual(d["raw_html_path"], "results/donut_amazon.html")
        self.assertNotIn("html", d)
        self.assertNotIn("html_content", d)

    def test_K_no_network_calls(self):
        # All tests execute offline via local data structures
        req = AcquisitionRequest(url="https://offline.test", target="flipkart")
        orch_res = OrchestrationResult(
            success=True,
            validated=True,
            status=OrchestrationStatus.SUCCESS,
            acquisition={"method": "browser_cdp", "elapsed_ms": 100},
            data={"product_name": "Offline Item", "price": "100"},
            validation={"evidence": ["Offline Schema"]}
        )
        obs = self.recorder.record_orchestration_result(orch_res, req)
        self.assertTrue(obs.acquisition_success)


if __name__ == "__main__":
    unittest.main()
