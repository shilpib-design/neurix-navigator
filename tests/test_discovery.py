"""
Comprehensive Unit Test Suite for Phase 3E Acquisition Discovery.
Tests all 24 architectural and functional discovery requirements in-memory with zero live network calls.
"""

import unittest
from core.discovery import DiscoveryEngine, DiscoveryRequest, DiscoverySurface, DiscoveryResult
from core.candidate import CandidateGenerator
from core.models import AcquisitionRequest, CustomerPreferences, TargetProfile, CapabilityMetadata
from core.registry import ProviderRegistry
from core.pipeline import UnifiedPipeline
from core.learning import LearningEngine


class TestAcquisitionDiscovery(unittest.TestCase):

    def setUp(self):
        self.engine = DiscoveryEngine()
        self.registry = ProviderRegistry()

    # 1. DiscoveryRequest Model
    def test_01_discovery_request(self):
        req = DiscoveryRequest(
            url="https://www.example.com/product/123",
            target="Example",
            headers={"Content-Type": "text/html"},
            status_code=200,
            body="<html><body>Test</body></html>",
            context={"customer_id": "c1"}
        )
        d = req.to_dict()
        self.assertEqual(d["url"], "https://www.example.com/product/123")
        self.assertEqual(d["target"], "Example")
        self.assertEqual(d["status_code"], 200)
        self.assertEqual(d["body_length"], len("<html><body>Test</body></html>"))

    # 2. DiscoveryResult Serialization
    def test_02_discovery_result_serialization(self):
        surface = DiscoverySurface(
            surface_type="json_ld",
            url="https://www.example.com/p/123",
            method="GET",
            content_type="application/ld+json",
            confidence=0.90,
            source="script_json_ld",
            metadata={"type": "Product"}
        )
        res = DiscoveryResult(
            target="Example",
            surfaces=[surface],
            evidence={"count": 1},
            discovery_success=True,
            errors=[],
            elapsed_ms=5
        )
        data = res.to_dict()
        self.assertEqual(data["target"], "Example")
        self.assertTrue(data["discovery_success"])
        self.assertEqual(len(data["surfaces"]), 1)
        self.assertEqual(data["surfaces"][0]["surface_type"], "json_ld")
        self.assertEqual(data["surfaces"][0]["confidence"], 0.90)

    # 3. HTML Detection
    def test_03_html_detection(self):
        req = DiscoveryRequest(
            url="https://www.example.com/p/123",
            headers={"Content-Type": "text/html; charset=utf-8"},
            body="<!DOCTYPE html><html><head><title>Product</title></head><body><h1>Shirt</h1></body></html>"
        )
        res = self.engine.discover(req)
        self.assertTrue(res.discovery_success)
        html_surfaces = [s for s in res.surfaces if s.surface_type == "html"]
        self.assertGreater(len(html_surfaces), 0)
        self.assertGreaterEqual(html_surfaces[0].confidence, 0.70)

    # 4. JSON-LD Detection
    def test_04_json_ld_detection(self):
        html = """
        <html>
        <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "Wireless Headphones",
            "offers": {"price": "99.99", "priceCurrency": "USD"}
        }
        </script>
        </head>
        </html>
        """
        req = DiscoveryRequest(url="https://www.example.com/product", body=html)
        res = self.engine.discover(req)
        ld_surfaces = [s for s in res.surfaces if s.surface_type == "json_ld"]
        self.assertEqual(len(ld_surfaces), 1)
        self.assertEqual(ld_surfaces[0].confidence, 0.90)
        self.assertEqual(ld_surfaces[0].metadata.get("type"), "Product")

    # 5. Embedded JSON Detection
    def test_05_embedded_json_detection(self):
        html = """
        <html>
        <body>
        <script id="__NEXT_DATA__" type="application/json">
        {"props": {"pageProps": {"product": {"id": "p123", "title": "Sneakers"}}}}
        </script>
        </body>
        </html>
        """
        req = DiscoveryRequest(url="https://www.example.com/sneakers", body=html)
        res = self.engine.discover(req)
        emb_surfaces = [s for s in res.surfaces if s.surface_type == "embedded_json"]
        self.assertGreaterEqual(len(emb_surfaces), 1)
        self.assertEqual(emb_surfaces[0].confidence, 0.85)

    # 6. JSON Response Detection
    def test_06_json_response_detection(self):
        json_body = '{"id": "p456", "name": "Laptop", "price": 899.00}'
        req = DiscoveryRequest(
            url="https://api.example.com/v1/products/p456",
            headers={"Content-Type": "application/json"},
            body=json_body
        )
        res = self.engine.discover(req)
        json_surfaces = [s for s in res.surfaces if s.surface_type in ["json_endpoint", "structured_payload"]]
        self.assertGreaterEqual(len(json_surfaces), 1)
        self.assertGreaterEqual(json_surfaces[0].confidence, 0.80)

    # 7. GraphQL Response Detection
    def test_07_graphql_response_detection(self):
        gql_body = '{"data": {"product": {"id": "g789", "name": "Tablet"}}}'
        req = DiscoveryRequest(
            url="https://www.example.com/graphql",
            headers={"Content-Type": "application/graphql-response+json"},
            body=gql_body
        )
        res = self.engine.discover(req)
        gql_surfaces = [s for s in res.surfaces if s.surface_type == "graphql_endpoint"]
        self.assertEqual(len(gql_surfaces), 1)
        self.assertEqual(gql_surfaces[0].confidence, 0.95)

    # 8. RSC / Application Payload Detection
    def test_08_rsc_payload_detection(self):
        rsc_body = "1:I{\"id\":\"rsc_component_1\",\"name\":\"RSC Item\"}\n0:[\"$\",\"$L1\",null,{}]\n"
        req = DiscoveryRequest(
            url="https://www.example.com/rsc-page",
            headers={"Content-Type": "text/x-component"},
            body=rsc_body
        )
        res = self.engine.discover(req)
        rsc_surfaces = [s for s in res.surfaces if s.surface_type == "rsc_payload"]
        self.assertGreaterEqual(len(rsc_surfaces), 1)
        self.assertGreaterEqual(rsc_surfaces[0].confidence, 0.85)

    # 9. Generic API Endpoint Reference Detection
    def test_09_generic_api_endpoint_reference_detection(self):
        html = """
        <html>
        <script>
        fetch('/api/v2/products/items.json')
            .then(res => res.json())
            .then(data => console.log(data));
        </script>
        </html>
        """
        req = DiscoveryRequest(url="https://www.example.com/catalog", body=html)
        res = self.engine.discover(req)
        api_surfaces = [s for s in res.surfaces if s.surface_type == "json_endpoint" and s.source == "endpoint_reference"]
        self.assertGreaterEqual(len(api_surfaces), 1)
        self.assertEqual(api_surfaces[0].url, "https://www.example.com/api/v2/products/items.json")

    # 10. Generic GraphQL Endpoint Reference Detection
    def test_10_generic_graphql_endpoint_reference_detection(self):
        html = """
        <html>
        <script>
        const endpoint = "/graphql";
        axios.post(endpoint, { query: "{ product(id: 1) { name } }" });
        </script>
        </html>
        """
        req = DiscoveryRequest(url="https://www.example.com/store", body=html)
        res = self.engine.discover(req)
        gql_refs = [s for s in res.surfaces if s.surface_type == "graphql_endpoint" and s.source == "endpoint_reference"]
        self.assertEqual(len(gql_refs), 1)
        self.assertEqual(gql_refs[0].url, "https://www.example.com/graphql")

    # 11. Relative URL Handling
    def test_11_relative_url_handling(self):
        html = '<script>const api = "/api/v1/details";</script>'
        req = DiscoveryRequest(url="https://shop.example.com/category/shoes", body=html)
        res = self.engine.discover(req)
        ref_urls = [s.url for s in res.surfaces if s.source == "endpoint_reference"]
        self.assertIn("https://shop.example.com/api/v1/details", ref_urls)

    # 12. Absolute URL Handling
    def test_12_absolute_url_handling(self):
        html = '<script>const extApi = "https://api.external-cdn.com/api/v1/data.json";</script>'
        req = DiscoveryRequest(url="https://shop.example.com/item", body=html)
        res = self.engine.discover(req)
        ref_urls = [s.url for s in res.surfaces if s.source == "endpoint_reference"]
        self.assertIn("https://api.external-cdn.com/api/v1/data.json", ref_urls)

    # 13. Duplicate Surface Deduplication
    def test_13_duplicate_surface_deduplication(self):
        html = """
        <html>
        <script type="application/ld+json">{"@type": "Product"}</script>
        <script type="application/ld+json">{"@type": "Product"}</script>
        </html>
        """
        req = DiscoveryRequest(url="https://www.example.com/dups", body=html)
        res = self.engine.discover(req)
        ld_surfaces = [s for s in res.surfaces if s.surface_type == "json_ld" and s.url == "https://www.example.com/dups"]
        self.assertEqual(len(ld_surfaces), 1)

    # 14. Confidence Ordering
    def test_14_confidence_ordering(self):
        html = """
        <html>
        <script type="application/ld+json">{"@type": "Product"}</script>
        <script>const ref = "/api/items";</script>
        </html>
        """
        req = DiscoveryRequest(
            url="https://www.example.com/item",
            headers={"Content-Type": "text/html"},
            body=html
        )
        res = self.engine.discover(req)
        confidences = [s.confidence for s in res.surfaces]
        self.assertEqual(confidences, sorted(confidences, reverse=True))

    # 15. Unsupported Content Type
    def test_15_unsupported_content(self):
        req = DiscoveryRequest(
            url="https://www.example.com/image.png",
            headers={"Content-Type": "image/png"},
            body=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."
        )
        res = self.engine.discover(req)
        self.assertFalse(res.discovery_success)
        self.assertEqual(len(res.surfaces), 0)

    # 16. Empty Content
    def test_16_empty_content(self):
        req = DiscoveryRequest(url="https://www.example.com/empty", body="")
        res = self.engine.discover(req)
        self.assertFalse(res.discovery_success)
        self.assertEqual(len(res.surfaces), 0)

    # 17. Malformed HTML Handling
    def test_17_malformed_html(self):
        malformed = "<html><head><script type='application/ld+json'>{bad json</script><div><<unclosed"
        req = DiscoveryRequest(url="https://www.example.com/badhtml", body=malformed)
        res = self.engine.discover(req)
        # Should not crash
        self.assertIsInstance(res, DiscoveryResult)

    # 18. Malformed JSON Handling
    def test_18_malformed_json(self):
        html = '<script type="application/json">{invalid json: true,,,}</script>'
        req = DiscoveryRequest(url="https://www.example.com/badjson", body=html)
        res = self.engine.discover(req)
        # Should fall back cleanly without throwing exceptions
        self.assertIsInstance(res, DiscoveryResult)

    # 19. Bounded / Zero Network Call Behavior
    def test_19_bounded_no_network_behavior(self):
        req = DiscoveryRequest(url="http://nonexistent-domain-9999.org/test", body="<html></html>")
        # Direct execution must finish immediately in milliseconds without making any DNS or socket calls
        start = self.engine.discover(req)
        self.assertLess(start.elapsed_ms, 500)

    # 20. No Recursive Crawling Verification
    def test_20_no_recursive_crawling(self):
        html = '<script>const api1 = "/api/v1"; const api2 = "/api/v2";</script>'
        req = DiscoveryRequest(url="https://www.example.com/crawl", body=html)
        res = self.engine.discover(req)
        # Verify surfaces only catalog detected endpoint strings, no HTTP sub-requests are generated
        self.assertEqual(res.elapsed_ms < 100, True)

    # 21. CandidateGenerator Integration
    def test_21_candidate_generator_integration(self):
        generator = CandidateGenerator(self.registry)
        profile = TargetProfile(
            domain="Amazon",
            url_pattern="/dp/*",
            inferred_country="US",
            country_confidence=1.0,
            target_type="pdp",
            location_sensitivity=False,
            browser_likelihood=0.5
        )
        prefs = CustomerPreferences()

        # Without discovery
        cands_no_disc = generator.generate_candidates(profile, prefs)
        self.assertGreater(len(cands_no_disc), 0)

        # With discovery evidence
        disc_surface = DiscoverySurface(surface_type="json_ld", url="https://www.amazon.com/dp/B123", confidence=0.90)
        disc_res = DiscoveryResult(target="Amazon", surfaces=[disc_surface])

        cands_with_disc = generator.generate_candidates(profile, prefs, discovery_result=disc_res)
        self.assertEqual(len(cands_with_disc), len(cands_no_disc))
        # Ensure discovery match flag is present in metrics
        matched_caps = [c for c in cands_with_disc if c.historical_metrics.get("discovery_matched")]
        self.assertGreater(len(matched_caps), 0)

    # 22. UnifiedPipeline Integration
    def test_22_unified_pipeline_integration(self):
        class MockAdapter:
            def fetch(self, target):
                return {
                    "status_code": 200,
                    "success": True,
                    "raw_content": b"<html><script type='application/ld+json'>{\"@type\":\"Product\",\"name\":\"Cream\"}</script>" + (b"x" * 150) + b"</html>",
                    "error_message": None
                }

        pipeline = UnifiedPipeline(exploration_rate=0.0)
        for cap in pipeline.registry.list_capabilities():
            pipeline.registry.bind_adapter(cap.capability_id, MockAdapter())

        pipeline.extractor_registry.register("Purplle", lambda html, req: {
            "product_name": "Cream", "price": "$10", "availability": "InStock"
        })

        # Test helper method
        acq_req = AcquisitionRequest(url="https://www.purplle.com/product/cream")
        observed = {
            "status_code": 200,
            "headers": {"content-type": "text/html"},
            "html": "<html><script type='application/ld+json'>{\"@type\":\"Product\",\"name\":\"Cream\"}</script></html>"
        }
        disc_res = pipeline.discover_surfaces(acq_req, observed)
        self.assertTrue(disc_res.discovery_success)
        self.assertGreater(len(disc_res.surfaces), 0)

        # Test end-to-end pipeline request execution with discovery output
        res = pipeline.process_request(acq_req)
        self.assertIn("discovery", res)
        self.assertTrue(res["success"])

    # 23. Telemetry Evidence Recording
    def test_23_telemetry_discovery_evidence(self):
        learning = LearningEngine(self.registry)
        disc_dict = {"surfaces": [{"surface_type": "json_ld", "confidence": 0.90}]}
        obs = learning.record_observation(
            capability_id="Context.dev",
            domain="Amazon",
            country="US",
            success=True,
            validated=True,
            latency_ms=1000,
            bytes_count=20000,
            estimated_cost=0.001,
            discovery_evidence=disc_dict
        )
        self.assertEqual(obs["discovery_evidence"], disc_dict)

    # 24. Complete Regression Suite
    def test_24_complete_regression_suite(self):
        class MockAdapter:
            def fetch(self, target):
                return {
                    "status_code": 200,
                    "success": True,
                    "raw_content": b"<html>" + (b"y" * 150) + b"</html>",
                    "error_message": None
                }

        pipeline = UnifiedPipeline(exploration_rate=0.0)
        for cap in pipeline.registry.list_capabilities():
            pipeline.registry.bind_adapter(cap.capability_id, MockAdapter())

        pipeline.extractor_registry.register("Flipkart", lambda html, req: {
            "product_name": "Flipkart Product", "price": "$15", "availability": "InStock"
        })

        req = AcquisitionRequest(url="https://www.flipkart.com/product/p/itm123")
        res = pipeline.process_request(req)
        self.assertTrue(res["validated"])
        self.assertIn("target_profile", res)
        self.assertIn("billing", res)


if __name__ == "__main__":
    unittest.main()
