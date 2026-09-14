"""
Unit Tests for Phase 3A (Pure HTTP Engine) + Phase 3B (Generic Session Manager).

All HTTP requests use in-memory mocked transports; no live network or external API calls are made.
"""

import time
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, Optional, Tuple

from core.session import SessionManager, SessionBundle
from core.http_engine import (
    PureHttpEngine,
    HttpTransport,
    RequestsHttpTransport,
    CurlCffiHttpTransport,
    HttpAcquisitionResponse
)
from core.models import (
    AcquisitionRequest,
    CustomerPreferences,
    TargetProfile,
    FailureCategory
)
from core.registry import ProviderRegistry
from core.rate_card import RateCardRegistry
from core.pipeline import UnifiedPipeline
from providers.pure_http_adapter import PureHttpProvider


class MockHttpTransport(HttpTransport):
    """
    In-memory mock HTTP transport for deterministic testing without external network calls.
    """

    def __init__(self):
        self.last_url: Optional[str] = None
        self.last_method: Optional[str] = None
        self.last_headers: Optional[Dict[str, str]] = None
        self.last_cookies: Optional[Dict[str, str]] = None
        self.last_proxy: Optional[str] = None
        self.last_timeout: Optional[float] = None

        # Configurable response overrides
        self.response_status: int = 200
        self.response_headers: Dict[str, str] = {"content-type": "text/html"}
        self.response_cookies: Dict[str, str] = {"session_cookie": "abc123val"}
        self.response_content: bytes = b"<html><body><h1>Pure HTTP Product</h1><div id='price'>$19.99</div><div id='availability'>InStock</div><p>Detailed product description for testing HTTP acquisition.</p></body></html>"
        self.response_elapsed_ms: int = 150
        self.response_error: Optional[str] = None

    def send_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: float = 10.0
    ) -> Tuple[Optional[int], Dict[str, str], Dict[str, str], bytes, int, Optional[str]]:
        self.last_url = url
        self.last_method = method
        self.last_headers = dict(headers) if headers else {}
        self.last_cookies = dict(cookies) if cookies else {}
        self.last_proxy = proxy
        self.last_timeout = timeout

        status = None if self.response_error else self.response_status
        return (
            status,
            dict(self.response_headers),
            dict(self.response_cookies),
            self.response_content if not self.response_error else b"",
            self.response_elapsed_ms,
            self.response_error
        )


class TestPhase3PureHttpSession(unittest.TestCase):

    def setUp(self):
        self.session_manager = SessionManager(default_ttl_seconds=3600.0)
        self.transport = MockHttpTransport()
        self.engine = PureHttpEngine(transport=self.transport, session_manager=self.session_manager)
        self.provider = PureHttpProvider(engine=self.engine, session_manager=self.session_manager)
        self.registry = ProviderRegistry()
        self.rate_card_registry = RateCardRegistry()

    # --- Phase 3A: Pure HTTP Engine Tests ---

    def test_01_successful_http_acquisition(self):
        res = self.engine.acquire("https://www.example.com/product/123")
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.byte_count, len(self.transport.response_content))
        self.assertIn("Pure HTTP Product", res.text)
        self.assertIsNone(res.error)
        self.assertIsNone(res.failure_category)

    def test_02_http_timeout_handling(self):
        self.transport.response_error = "Request timed out"
        res = self.engine.acquire("https://www.example.com/timeout")
        self.assertFalse(res.success)
        self.assertIsNone(res.status_code)
        self.assertEqual(res.failure_category, FailureCategory.TIMEOUT.value)
        self.assertEqual(res.error, "Request timed out")

    def test_03_http_429_rate_limit_handling(self):
        self.transport.response_status = 429
        self.transport.response_content = b"Rate limit exceeded"
        res = self.engine.acquire("https://www.example.com/ratelimit")
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 429)
        self.assertEqual(res.failure_category, FailureCategory.RATE_LIMIT.value)

    def test_04_http_403_block_page_handling(self):
        self.transport.response_status = 403
        self.transport.response_content = b"Access Denied"
        res = self.engine.acquire("https://www.example.com/blocked")
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.failure_category, FailureCategory.BLOCK_PAGE.value)

    def test_05_http_500_provider_error_handling(self):
        self.transport.response_status = 500
        self.transport.response_content = b"Internal Server Error"
        res = self.engine.acquire("https://www.example.com/error500")
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.failure_category, FailureCategory.PROVIDER_ERROR.value)

    def test_06_connection_error_handling(self):
        self.transport.response_error = "Connection error: Failed to connect"
        res = self.engine.acquire("https://www.example.com/connfail")
        self.assertFalse(res.success)
        self.assertEqual(res.failure_category, FailureCategory.PROVIDER_ERROR.value)

    def test_07_custom_headers_propagation(self):
        custom_headers = {"X-Custom-Header": "TestVal", "Accept-Language": "en-US"}
        self.engine.acquire("https://www.example.com/headers", headers=custom_headers)
        self.assertEqual(self.transport.last_headers.get("X-Custom-Header"), "TestVal")
        self.assertEqual(self.transport.last_headers.get("Accept-Language"), "en-US")
        self.assertIn("User-Agent", self.transport.last_headers)

    def test_08_cookies_propagation_and_update(self):
        session = self.session_manager.create_session(domain="Example", cookies={"init_cookie": "123"})
        self.transport.response_cookies = {"new_cookie": "456"}
        res = self.engine.acquire(
            "https://www.example.com/cookies",
            cookies={"req_cookie": "789"},
            session_id=session.session_id
        )
        self.assertEqual(self.transport.last_cookies.get("init_cookie"), "123")
        self.assertEqual(self.transport.last_cookies.get("req_cookie"), "789")
        # Session should be updated with response cookies
        updated = self.session_manager.get_session(session.session_id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.cookies.get("new_cookie"), "456")

    def test_09_proxy_configuration_passed_to_transport(self):
        proxy_url = "http://user:pass@proxy.example.com:8080"
        self.engine.acquire("https://www.example.com/proxy", proxy=proxy_url)
        self.assertEqual(self.transport.last_proxy, proxy_url)

    def test_10_response_body_and_byte_count(self):
        self.transport.response_content = b"Hello Pure HTTP Body"
        res = self.engine.acquire("https://www.example.com/body")
        self.assertEqual(res.byte_count, len(b"Hello Pure HTTP Body"))
        self.assertEqual(res.text, "Hello Pure HTTP Body")

    # --- Phase 3B: Session Manager Tests ---

    def test_11_session_creation_and_defaults(self):
        session = self.session_manager.create_session(
            domain="Amazon",
            country="US",
            target="pdp",
            proxy_binding="http://proxy:8080",
            cookies={"sid": "xyz"}
        )
        self.assertTrue(session.session_id.startswith("sess_"))
        self.assertEqual(session.domain, "Amazon")
        self.assertEqual(session.country, "US")
        self.assertEqual(session.status, "healthy")
        self.assertEqual(session.reuse_count, 0)
        self.assertEqual(session.cookies.get("sid"), "xyz")
        self.assertIsNotNone(session.expires_at)

    def test_12_session_retrieval_and_expiry(self):
        session = self.session_manager.create_session(domain="Flipkart", ttl_seconds=0.1)
        self.assertIsNotNone(self.session_manager.get_session(session.session_id))
        time.sleep(0.15)
        self.assertIsNone(self.session_manager.get_session(session.session_id))

    def test_13_session_update_and_health(self):
        session = self.session_manager.create_session(domain="Purplle")
        self.session_manager.update_session(session.session_id, cookies={"token": "abc"})
        self.assertEqual(session.cookies.get("token"), "abc")

        self.session_manager.mark_unhealthy(session.session_id)
        self.assertEqual(session.status, "unhealthy")

        self.session_manager.mark_healthy(session.session_id)
        self.assertEqual(session.status, "healthy")

    def test_14_session_reuse_count_increment(self):
        session = self.session_manager.create_session(domain="Kroger")
        c1 = self.session_manager.increment_reuse_count(session.session_id)
        c2 = self.session_manager.increment_reuse_count(session.session_id)
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 2)
        self.assertEqual(session.reuse_count, 2)

    def test_15_session_purge_expired(self):
        s1 = self.session_manager.create_session(domain="D1", ttl_seconds=3600)
        s2 = self.session_manager.create_session(domain="D2", ttl_seconds=0.05)
        time.sleep(0.1)
        purged = self.session_manager.purge_expired_sessions()
        self.assertEqual(purged, 1)
        self.assertIsNotNone(self.session_manager.get_session(s1.session_id))
        self.assertIsNone(self.session_manager.get_session(s2.session_id))

    def test_16_get_active_session_lookup(self):
        s1 = self.session_manager.create_session(domain="Amazon", country="US")
        active = self.session_manager.get_active_session(domain="Amazon", country="US")
        self.assertIsNotNone(active)
        self.assertEqual(active.session_id, s1.session_id)

    def test_17_missing_or_expired_session_handling(self):
        self.assertIsNone(self.session_manager.get_session("non_existent_sid"))
        self.assertFalse(self.session_manager.remove_session("non_existent_sid"))
        self.assertEqual(self.session_manager.increment_reuse_count("non_existent_sid"), 0)

    # --- Integration Tests ---

    def test_18_pure_http_provider_registry_integration(self):
        cap = self.registry.get("pure_http")
        self.assertIsNotNone(cap)
        self.assertEqual(cap.provider_id, "PureHTTP")
        adapter = self.registry.resolve_adapter("pure_http")
        # Registry resolves adapter when enabled
        self.registry.set_enabled("pure_http", True)
        adapter = self.registry.resolve_adapter("pure_http")
        self.assertIsNotNone(adapter)
        self.assertIsInstance(adapter, PureHttpProvider)

    def test_19_pure_http_pipeline_execution_integration(self):
        # Enable pure_http in registry and bind mock provider
        self.registry.set_enabled("pure_http", True)
        mock_provider = PureHttpProvider(engine=self.engine)
        self.registry.bind_adapter("pure_http", mock_provider)
        self.registry.get("pure_http").historical_metrics["sample_size"] = 0

        pipeline = UnifiedPipeline(registry=self.registry, rate_card_registry=self.rate_card_registry)
        req = AcquisitionRequest(url="https://www.amazon.com/dp/B001234567")
        res = pipeline.execute_exploration(req)

        self.assertTrue(res.success)
        self.assertTrue(res.validated)
        self.assertGreater(len(res.attempts), 0)

    @patch("requests.request")
    def test_20_requests_transport_isolation_with_mock(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.cookies = {"sess": "123"}
        mock_resp.content = b"<html>Mocked Content</html>"
        mock_req.return_value = mock_resp

        transport = RequestsHttpTransport()
        status, headers, cookies, content, elapsed, err = transport.send_request("https://mocked.com")

        self.assertEqual(status, 200)
        self.assertEqual(content, b"<html>Mocked Content</html>")
        self.assertIsNone(err)

    def test_21_curl_cffi_transport_fallback_when_uninstalled(self):
        with patch.dict("sys.modules", {"curl_cffi.requests": None}):
            transport = CurlCffiHttpTransport()
            # Transport falls back to RequestsHttpTransport
            self.assertFalse(transport._available)


if __name__ == "__main__":
    unittest.main()
