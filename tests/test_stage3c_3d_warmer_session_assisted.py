"""
Comprehensive Unit Tests for Phase 3C (Session Warmer & Session Pool) and Phase 3D (Session-Assisted HTTP).

All tests use in-memory mocks; no live network, browser, vendor API, or external calls are made.
"""

import time
import unittest
from typing import Dict, Any, Optional

from core.session import SessionBundle, SessionManager, SessionPool
from core.warmer import SessionWarmer, MockSessionWarmer
from core.http_engine import PureHttpEngine, HttpTransport, HttpAcquisitionResponse
from core.models import AcquisitionRequest, CustomerPreferences, TargetProfile
from core.registry import ProviderRegistry
from core.rate_card import RateCardRegistry
from core.pipeline import UnifiedPipeline
from providers.pure_http_adapter import PureHttpProvider
from providers.session_assisted_http_adapter import SessionAssistedHttpProvider
from tests.test_stage3_pure_http_session import MockHttpTransport


class TestPhase3CSessionWarmerAndPool(unittest.TestCase):

    def setUp(self):
        self.pool = SessionPool()
        self.warmer = MockSessionWarmer(warmer_id="test_warmer")

    def test_01_session_warmer_interface_and_mock(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        self.assertIsInstance(bundle, SessionBundle)
        self.assertEqual(bundle.domain, "Amazon")
        self.assertEqual(bundle.country, "US")
        self.assertEqual(bundle.status, "healthy")
        self.assertIn("session_token", bundle.cookies)
        self.assertEqual(bundle.metadata.get("warmer_id"), "test_warmer")

    def test_02_session_pool_insertion_and_retrieval(self):
        req = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm123")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        retrieved = self.pool.get_session(bundle.session_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.domain, "Flipkart")

    def test_03_compatible_session_retrieval(self):
        req = AcquisitionRequest(url="https://www.purplle.com/product/cream")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        compatible = self.pool.get_compatible_session(domain="Purplle", country="IN", target="pdp")
        self.assertIsNotNone(compatible)
        self.assertEqual(compatible.session_id, bundle.session_id)

    def test_04_incompatible_domain_filtering(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        self.warmer.warm(req, session_pool=self.pool)

        compatible = self.pool.get_compatible_session(domain="Flipkart", country="US")
        self.assertIsNone(compatible)

    def test_05_incompatible_country_filtering(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        self.warmer.warm(req, session_pool=self.pool)  # Inferred US

        compatible = self.pool.get_compatible_session(domain="Amazon", country="DE")
        self.assertIsNone(compatible)

    def test_06_expired_session_filtering(self):
        req = AcquisitionRequest(url="https://www.kroger.com/p/milk")
        bundle = self.warmer.warm(req, session_pool=self.pool, ttl_seconds=0.05)

        self.assertIsNotNone(self.pool.get_compatible_session(domain="Kroger"))
        time.sleep(0.08)
        self.assertIsNone(self.pool.get_compatible_session(domain="Kroger"))

    def test_07_unhealthy_session_filtering(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        self.pool.mark_unhealthy(bundle.session_id)
        self.assertIsNone(self.pool.get_compatible_session(domain="Amazon"))

    def test_08_reuse_counter_tracking(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        c1 = self.pool.increment_reuse_count(bundle.session_id)
        c2 = self.pool.increment_reuse_count(bundle.session_id)
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 2)

    def test_09_multiple_sessions_correct_selection(self):
        req1 = AcquisitionRequest(url="https://www.amazon.com/dp/B001111111")
        req2 = AcquisitionRequest(url="https://www.amazon.com/dp/B002222222")

        b1 = self.warmer.warm(req1, session_pool=self.pool)
        time.sleep(0.01)
        b2 = self.warmer.warm(req2, session_pool=self.pool)

        # Most recently validated session selected first
        selected = self.pool.get_compatible_session(domain="Amazon", country="US")
        self.assertIsNotNone(selected)
        self.assertEqual(selected.session_id, b2.session_id)


class TestPhase3DSessionAssistedHTTP(unittest.TestCase):

    def setUp(self):
        self.pool = SessionPool()
        self.warmer = MockSessionWarmer(warmer_id="test_warmer")
        self.transport = MockHttpTransport()
        self.engine = PureHttpEngine(transport=self.transport, session_manager=self.pool)
        self.provider = SessionAssistedHttpProvider(engine=self.engine, session_pool=self.pool)
        self.registry = ProviderRegistry()
        self.rate_card_registry = RateCardRegistry()

    def test_10_session_assisted_http_success(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        target = {
            "name": "Amazon Product",
            "url": req.url,
            "domain": "Amazon",
            "country": "US",
            "target_type": "pdp"
        }
        res = self.provider.fetch(target)

        self.assertTrue(res["success"])
        self.assertEqual(res["session_id"], bundle.session_id)
        self.assertTrue(res["session_assisted"])
        self.assertFalse(res["session_invalidated"])
        self.assertEqual(self.transport.last_cookies.get("session_token"), "warmed_mock_token_123")

    def test_11_session_assisted_http_with_no_session(self):
        target = {
            "name": "Unwarmed Target",
            "url": "https://www.unwarmed.com/dp/123",
            "domain": "Unwarmed",
            "country": "US"
        }
        res = self.provider.fetch(target)

        self.assertTrue(res["success"])
        self.assertIsNone(res["session_id"])
        self.assertFalse(res["session_assisted"])

    def test_12_failed_validation_causes_session_invalidation(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        # Simulate 403 Forbidden HTTP error
        self.transport.response_status = 403
        self.transport.response_content = b"Access Denied"

        target = {
            "name": "Blocked Product",
            "url": req.url,
            "domain": "Amazon",
            "country": "US",
            "session_id": bundle.session_id
        }
        res = self.provider.fetch(target)

        self.assertFalse(res["success"])
        self.assertTrue(res["session_invalidated"])

        # Session should now be marked unhealthy and ignored for future compatible requests
        self.assertEqual(self.pool.get_session(bundle.session_id).status, "unhealthy")
        self.assertIsNone(self.pool.get_compatible_session(domain="Amazon"))

    def test_13_session_expiry_during_acquisition(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool, ttl_seconds=0.05)

        time.sleep(0.08)
        target = {
            "name": "Expired Product",
            "url": req.url,
            "domain": "Amazon",
            "country": "US",
            "session_id": bundle.session_id
        }
        res = self.provider.fetch(target)

        # Expired session is not bound
        self.assertFalse(res["session_assisted"])

    def test_14_backward_compatibility_pure_http(self):
        pure_provider = PureHttpProvider(engine=self.engine)
        target = {
            "name": "Pure HTTP Product",
            "url": "https://www.amazon.com/dp/B001234567",
            "domain": "Amazon",
            "country": "US"
        }
        res = pure_provider.fetch(target)
        self.assertTrue(res["success"])

    def test_15_provider_registry_integration(self):
        cap = self.registry.get("session_assisted_http")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.provider_id, "SessionAssistedHTTP")

        self.registry.set_enabled("session_assisted_http", True)
        adapter = self.registry.resolve_adapter("session_assisted_http")
        self.assertIsNotNone(adapter)
        self.assertIsInstance(adapter, SessionAssistedHttpProvider)

    def test_16_pipeline_integration(self):
        self.registry.set_enabled("session_assisted_http", True)
        mock_provider = SessionAssistedHttpProvider(engine=self.engine, session_pool=self.pool)
        self.registry.bind_adapter("session_assisted_http", mock_provider)
        self.registry.get("session_assisted_http").historical_metrics["sample_size"] = 0

        # Warm a session into pool
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        self.warmer.warm(req, session_pool=self.pool)

        pipeline = UnifiedPipeline(registry=self.registry, rate_card_registry=self.rate_card_registry)
        res = pipeline.execute_exploration(req)

        self.assertTrue(res.success)
        self.assertTrue(res.validated)
        self.assertGreater(len(res.attempts), 0)

    def test_17_telemetry_fields(self):
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        bundle = self.warmer.warm(req, session_pool=self.pool)

        target = {
            "name": "Telemetry Product",
            "url": req.url,
            "domain": "Amazon",
            "country": "US",
            "session_id": bundle.session_id
        }
        res = self.provider.fetch(target)

        self.assertIn("session_id", res)
        self.assertIn("session_assisted", res)
        self.assertIn("session_reused", res)
        self.assertIn("session_invalidated", res)
        self.assertIn("session_reuse_count", res)
        self.assertEqual(res["session_id"], bundle.session_id)
        self.assertTrue(res["session_assisted"])


if __name__ == "__main__":
    unittest.main()
