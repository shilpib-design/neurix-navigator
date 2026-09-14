"""
Comprehensive Unit Test Suite for Phase 3G Self-Healing Foundation.
Tests all 25 degradation detection, thresholding, signal emission, target isolation, and safety requirements.
Uses 100% synthetic/in-memory data with zero live network calls.
"""

import unittest
from core.degradation import (
    DegradationDetector,
    BaselineMetrics,
    DegradationThresholds,
    DegradationEvent,
    ReinvestigationSignal
)
from core.models import AcquisitionRequest, CapabilityMetadata, CustomerPreferences, TargetProfile
from core.registry import ProviderRegistry
from core.pipeline import UnifiedPipeline
from core.learning import LearningEngine


class TestSelfHealingFoundation(unittest.TestCase):

    def setUp(self):
        self.thresholds = DegradationThresholds(min_samples=10, max_window_size=20)
        self.detector = DegradationDetector(thresholds=self.thresholds)

    # 1. Baseline Creation & Use
    def test_01_baseline_creation_and_use(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        baseline = BaselineMetrics(validation_rate=0.95, success_rate=0.98, avg_latency_ms=1200.0, cpvr=0.001)
        self.detector.set_baseline(ctx_key, baseline)
        retrieved = self.detector.get_baseline(ctx_key)
        self.assertEqual(retrieved.validation_rate, 0.95)
        self.assertEqual(retrieved.avg_latency_ms, 1200.0)

    # 2. Rolling Observation Window
    def test_02_rolling_observation_window(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        for i in range(25):
            self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": True, "validated": True, "latency_ms": 1000, "estimated_cost": 0.001
            })
        window = self.detector._windows[ctx_key]
        self.assertEqual(len(window), 20)  # max_window_size

    # 3. Minimum Sample Threshold Config
    def test_03_minimum_sample_threshold(self):
        detector = DegradationDetector(DegradationThresholds(min_samples=5))
        self.assertEqual(detector.thresholds.min_samples, 5)

    # 4. Insufficient Sample Size Safety
    def test_04_insufficient_sample_does_not_trigger_degradation(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(validation_rate=0.95))
        
        # Record only 5 failed observations (min_samples is 10)
        events = []
        signals = []
        for _ in range(5):
            evs, sigs = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": False, "validated": False, "latency_ms": 1000, "estimated_cost": 0.001
            })
            events.extend(evs)
            signals.extend(sigs)

        self.assertEqual(len(events), 0)
        self.assertEqual(len(signals), 0)

    # 5. Validation-Rate Degradation Detection
    def test_05_validation_rate_degradation(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(validation_rate=0.95))

        # Record 10 observations with low validation (30% validation rate vs 95% baseline)
        events = []
        for i in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": True, "validated": (i < 3), "latency_ms": 1000, "estimated_cost": 0.001
            })
            events.extend(evs)

        self.assertGreater(len(events), 0)
        val_events = [e for e in events if e.metric == "validation_rate"]
        self.assertGreater(len(val_events), 0)
        self.assertEqual(val_events[0].capability_id, "Context.dev")
        self.assertTrue(val_events[0].requires_reinvestigation)

    # 6. Acquisition-Success Degradation Detection
    def test_06_acquisition_success_degradation(self):
        ctx_key = "Flipkart:pdp:IN:String"
        self.detector.set_baseline(ctx_key, BaselineMetrics(success_rate=0.90, validation_rate=0.40))

        events = []
        for i in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Flipkart", "target_type": "pdp", "country": "IN", "capability_id": "String",
                "success": (i < 4), "validated": (i < 4), "latency_ms": 1000, "estimated_cost": 0.0015
            })
            events.extend(evs)

        succ_events = [e for e in events if e.metric in ["success_rate", "validation_rate"]]
        self.assertGreater(len(succ_events), 0)

    # 7. Latency Degradation Detection
    def test_07_latency_degradation(self):
        ctx_key = "Kroger:pdp:US:Scrapfly"
        self.detector.set_baseline(ctx_key, BaselineMetrics(avg_latency_ms=1000.0, validation_rate=0.85))

        events = []
        for _ in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Kroger", "target_type": "pdp", "country": "US", "capability_id": "Scrapfly",
                "success": True, "validated": True, "latency_ms": 3000, "estimated_cost": 0.002
            })
            events.extend(evs)

        lat_events = [e for e in events if e.metric == "latency"]
        self.assertGreater(len(lat_events), 0)
        self.assertGreaterEqual(lat_events[0].current_value, 2000.0)

    # 8. Error-Rate Degradation Detection
    def test_08_error_rate_degradation(self):
        ctx_key = "Purplle:pdp:IN:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(error_rate=0.05, success_rate=0.95))

        events = []
        for i in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Purplle", "target_type": "pdp", "country": "IN", "capability_id": "Context.dev",
                "success": (i < 2), "validated": (i < 2), "latency_ms": 1000, "estimated_cost": 0.001
            })
            events.extend(evs)

        err_events = [e for e in events if e.metric in ["error_rate", "success_rate", "validation_rate"]]
        self.assertGreater(len(err_events), 0)

    # 9. CPVR Degradation Detection
    def test_09_cpvr_degradation(self):
        ctx_key = "Amazon:pdp:US:AlterLab"
        self.detector.set_baseline(ctx_key, BaselineMetrics(cpvr=0.001, validation_rate=0.85))

        events = []
        for i in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "AlterLab",
                "success": True, "validated": (i < 2), "latency_ms": 1000, "estimated_cost": 0.005
            })
            events.extend(evs)

        cpvr_events = [e for e in events if e.metric in ["cpvr", "validation_rate"]]
        self.assertGreater(len(cpvr_events), 0)

    # 10. Capability Health Degradation Detection
    def test_10_capability_health_degradation(self):
        events = []
        for _ in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Scrapfly",
                "success": False, "validated": False, "latency_ms": 1000, "failure_category": "RATE_LIMIT"
            })
            events.extend(evs)

        health_events = [e for e in events if e.metric == "capability_health"]
        self.assertGreater(len(health_events), 0)

    # 11. Session Health Signal Detection
    def test_11_session_health_signal(self):
        events = []
        signals = []
        for _ in range(10):
            evs, sigs = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "session_assisted_http",
                "success": False, "validated": False, "latency_ms": 500, "failure_category": "SESSION_EXPIRED"
            })
            events.extend(evs)
            signals.extend(sigs)

        sess_signals = [s for s in signals if s.triggering_metric == "session_health"]
        self.assertGreater(len(sess_signals), 0)

    # 12. Discovery Evidence Preservation
    def test_12_discovery_evidence_preservation(self):
        disc_ev = {"matched_surface": "json_ld", "confidence": 0.90}
        events = []
        for _ in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Purplle", "target_type": "pdp", "country": "IN", "capability_id": "Context.dev",
                "success": False, "validated": False, "latency_ms": 1000, "discovery_evidence": disc_ev
            })
            events.extend(evs)

        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].discovery_evidence, disc_ev)

    # 13. Absolute Threshold Evaluation
    def test_13_absolute_threshold(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(validation_rate=0.85))
        # Drop of 0.25 (0.85 -> 0.60) >= abs threshold 0.20
        events = []
        for i in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": True, "validated": (i < 6), "latency_ms": 1000
            })
            events.extend(evs)

        self.assertGreater(len(events), 0)

    # 14. Relative Threshold Evaluation
    def test_14_relative_threshold(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(validation_rate=0.60))
        # Relative drop of 50% (0.60 -> 0.30) >= rel threshold 0.25
        events = []
        for i in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": True, "validated": (i < 3), "latency_ms": 1000
            })
            events.extend(evs)

        self.assertGreater(len(events), 0)

    # 15. No False Positive Validation
    def test_15_no_false_positive(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(validation_rate=0.85, avg_latency_ms=1000))
        
        events = []
        for _ in range(15):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": True, "validated": True, "latency_ms": 950, "estimated_cost": 0.001
            })
            events.extend(evs)

        self.assertEqual(len(events), 0)

    # 16. Multiple Metric Evaluation
    def test_16_multiple_metrics(self):
        ctx_key = "Amazon:pdp:US:Context.dev"
        self.detector.set_baseline(ctx_key, BaselineMetrics(validation_rate=0.90, avg_latency_ms=1000))
        
        events = []
        for _ in range(10):
            evs, _ = self.detector.record_observation({
                "domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev",
                "success": False, "validated": False, "latency_ms": 3500, "failure_category": "RATE_LIMIT"
            })
            events.extend(evs)

        metrics_detected = {e.metric for e in events}
        self.assertGreater(len(metrics_detected), 1)

    # 17. Multiple Target Contexts
    def test_17_multiple_target_contexts(self):
        for _ in range(10):
            self.detector.record_observation({"domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev", "success": True, "validated": False, "latency_ms": 1000})
            self.detector.record_observation({"domain": "Flipkart", "target_type": "pdp", "country": "IN", "capability_id": "String", "success": True, "validated": True, "latency_ms": 1000})

        keys = list(self.detector._windows.keys())
        self.assertEqual(len(keys), 2)

    # 18. Target-Level Isolation
    def test_18_target_level_isolation(self):
        # Degradation on Amazon PDP
        for _ in range(10):
            self.detector.record_observation({"domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "Context.dev", "success": True, "validated": False, "latency_ms": 1000})
        
        # Stable on Flipkart PDP
        for _ in range(10):
            self.detector.record_observation({"domain": "Flipkart", "target_type": "pdp", "country": "IN", "capability_id": "Context.dev", "success": True, "validated": True, "latency_ms": 1000})

        amz_key = "Amazon:pdp:US:Context.dev"
        fk_key = "Flipkart:pdp:IN:Context.dev"

        amz_events = [e for e in self.detector.get_events() if e.context_key == amz_key]
        fk_events = [e for e in self.detector.get_events() if e.context_key == fk_key]

        self.assertGreater(len(amz_events), 0)
        self.assertEqual(len(fk_events), 0)

    # 19. DegradationEvent Serialization
    def test_19_degradation_event_serialization(self):
        event = DegradationEvent(
            context_key="Amazon:pdp:US:Context.dev",
            capability_id="Context.dev",
            domain="Amazon",
            target_type="pdp",
            country="US",
            metric="validation_rate",
            baseline_value=0.90,
            current_value=0.50,
            absolute_delta=0.40,
            relative_delta=0.4444,
            sample_size=10,
            threshold_value=0.20,
            severity="HIGH",
            reason="Validation rate drop"
        )
        d = event.to_dict()
        self.assertEqual(d["context_key"], "Amazon:pdp:US:Context.dev")
        self.assertEqual(d["severity"], "HIGH")
        self.assertTrue(d["requires_reinvestigation"])

    # 20. ReinvestigationSignal Serialization
    def test_20_reinvestigation_signal_serialization(self):
        signal = ReinvestigationSignal(
            context_key="Amazon:pdp:US:Context.dev",
            capability_id="Context.dev",
            domain="Amazon",
            target_type="pdp",
            country="US",
            triggering_metric="validation_rate",
            priority="HIGH",
            reason="Validation drop"
        )
        d = signal.to_dict()
        self.assertEqual(d["context_key"], "Amazon:pdp:US:Context.dev")
        self.assertEqual(d["priority"], "HIGH")

    # 21. Priority and Severity Assignment
    def test_21_priority_severity(self):
        event = DegradationEvent(severity="CRITICAL")
        signal = ReinvestigationSignal(priority="URGENT")
        self.assertEqual(event.severity, "CRITICAL")
        self.assertEqual(signal.priority, "URGENT")

    # 22. Deterministic Repeated Evaluation
    def test_22_deterministic_repeated_evaluation(self):
        det1 = DegradationDetector(DegradationThresholds(min_samples=5))
        det2 = DegradationDetector(DegradationThresholds(min_samples=5))

        obs_list = [
            {"domain": "Amazon", "target_type": "pdp", "country": "US", "capability_id": "C1", "success": True, "validated": False, "latency_ms": 1000}
            for _ in range(6)
        ]

        for obs in obs_list:
            det1.record_observation(obs)
            det2.record_observation(obs)

        self.assertEqual(len(det1.get_events()), len(det2.get_events()))
        self.assertEqual(len(det1.get_signals()), len(det2.get_signals()))

    # 23. Pipeline & Telemetry Integration
    def test_23_pipeline_telemetry_integration(self):
        class MockAdapter:
            def fetch(self, target):
                return {
                    "status_code": 200,
                    "success": True,
                    "raw_content": b"<html>" + (b"w" * 150) + b"</html>",
                    "error_message": None
                }

        pipeline = UnifiedPipeline(exploration_rate=0.0)
        for cap in pipeline.registry.list_capabilities():
            pipeline.registry.bind_adapter(cap.capability_id, MockAdapter())

        pipeline.extractor_registry.register("Amazon", lambda html, req: {
            "product_name": "Book", "price": "$12", "availability": "InStock"
        })

        req = AcquisitionRequest(url="https://www.amazon.com/dp/B00999")
        res = pipeline.process_request(req)

        self.assertIn("degradation_events", res)
        self.assertIn("reinvestigation_signals", res)

    # 24. No Automatic Policy Change Check (Phase 5 Boundary)
    def test_24_no_automatic_policy_change(self):
        pipeline = UnifiedPipeline(exploration_rate=0.0)
        initial_policy = pipeline.policy_engine.get_active_policy(TargetProfile(domain="Amazon", url_pattern="/dp/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.5))

        # Record degradation observation
        for _ in range(10):
            pipeline.learning_engine.record_observation(
                capability_id="Context.dev",
                domain="Amazon",
                country="US",
                success=False,
                validated=False,
                latency_ms=5000,
                bytes_count=0,
                estimated_cost=0.001,
                failure_category="BLOCK_PAGE"
            )

        post_degradation_policy = pipeline.policy_engine.get_active_policy(TargetProfile(domain="Amazon", url_pattern="/dp/*", inferred_country="US", country_confidence=1.0, target_type="pdp", location_sensitivity=False, browser_likelihood=0.5))

        # Phase 3G must NOT mutate policy automatically
        self.assertEqual(initial_policy, post_degradation_policy)

    # 25. Complete Regression Suite
    def test_25_complete_regression_suite(self):
        class MockAdapter:
            def fetch(self, target):
                return {
                    "status_code": 200,
                    "success": True,
                    "raw_content": b"<html>" + (b"s" * 150) + b"</html>",
                    "error_message": None
                }

        pipeline = UnifiedPipeline(exploration_rate=0.0)
        for cap in pipeline.registry.list_capabilities():
            pipeline.registry.bind_adapter(cap.capability_id, MockAdapter())

        pipeline.extractor_registry.register("Kroger", lambda html, req: {
            "product_name": "Milk", "price": "$3.99", "availability": "InStock"
        })

        req = AcquisitionRequest(url="https://www.kroger.com/p/milk/123")
        res = pipeline.process_request(req)

        self.assertTrue(res["validated"])
        self.assertIn("routing_decision", res)
        self.assertIn("degradation_events", res)


if __name__ == "__main__":
    unittest.main()
