import unittest

from providers.context_dev_adapter import ContextDevProvider
from providers.scrapfly_adapter import ScrapflyProvider
from providers.string_adapter import StringProvider
from core.models import AcquisitionRequest, CapabilityMetadata, CustomerPreferences, FailureCategory
from core.pipeline import UnifiedPipeline
from core.registry import ProviderRegistry
from core.fallback import FallbackManager
from core.rate_card import RateCardRegistry
from orchestrator.orchestrator import TargetExtractorRegistry, TargetValidator


class MockProvider:
    def __init__(self, html):
        self.html = html
        self.calls = 0

    def fetch(self, target):
        self.calls += 1
        return {
            "status_code": 200,
            "success": True,
            "raw_content": self.html.encode("utf-8"),
            "error_message": None,
        }


def isolated_registry():
    registry = ProviderRegistry()
    for capability in registry.list_capabilities(enabled_only=False):
        registry.set_enabled(capability.capability_id, False)
    return registry


class TestStage2Integration(unittest.TestCase):
    def test_default_capabilities_bind_only_active_providers(self):
        registry = ProviderRegistry()
        active = {c.capability_id for c in registry.list_capabilities()}
        self.assertEqual(active, {"String", "Scrapfly", "Context.dev"})
        self.assertIsInstance(registry.resolve_adapter("String"), StringProvider)
        self.assertIsInstance(registry.resolve_adapter("Scrapfly"), ScrapflyProvider)
        self.assertIsInstance(registry.resolve_adapter("Context.dev"), ContextDevProvider)
        self.assertFalse(registry.is_executable("AlterLab"))

    def test_unbound_capability_fails_without_synthetic_success(self):
        registry = isolated_registry()
        capability = CapabilityMetadata(
            provider_id="Unbound", capability_id="Unbound", country_capabilities=["US"],
            target_capabilities=["pdp"]
        )
        registry.register(capability)
        pipeline = UnifiedPipeline(
            registry=registry,
            rate_card_registry=RateCardRegistry(),
            exploration_rate=0.0
        )

        result = pipeline.process_request(AcquisitionRequest(url="https://example.com/p/1"))

        self.assertFalse(result["success"])
        self.assertEqual(result["executed_attempts"][0]["status_code"], 500)
        self.assertEqual(result["executed_attempts"][0]["failure_category"], FailureCategory.PROVIDER_ERROR.value)
        self.assertEqual(result["executed_attempts"][0]["error"], "Unbound capability: no adapter registered")
        self.assertEqual(result["executed_attempts"][0]["bytes"], 0)

    def test_disabled_capability_is_not_executable(self):
        registry = ProviderRegistry()
        registry.set_enabled("String", False)
        self.assertIsNone(registry.resolve_adapter("String"))
        self.assertFalse(registry.is_executable("String"))

    def test_fallback_preserves_country_constraint(self):
        registry = isolated_registry()
        failed = CapabilityMetadata(
            provider_id="US API", capability_id="us", country_capabilities=["US"],
            target_capabilities=["pdp"], historical_metrics={"avg_latency_ms": 100}
        )
        wrong_country = CapabilityMetadata(
            provider_id="IN API", capability_id="in", country_capabilities=["IN"],
            target_capabilities=["pdp"], historical_metrics={"avg_latency_ms": 100}
        )
        for capability in (failed, wrong_country):
            registry.register(capability)

        fallback = FallbackManager(registry).adjust_cascade_on_failure(
            [failed], failed, FailureCategory.VALIDATION_FAILED.value,
            candidate_pool=[failed, wrong_country],
            profile=type("Profile", (), {
                "inferred_country": "US", "target_type": "pdp",
                "location_sensitivity": False
            })(),
            preferences=CustomerPreferences()
        )
        self.assertEqual(fallback, [])

    def test_fallback_preserves_target_type_constraint(self):
        registry = isolated_registry()
        failed = CapabilityMetadata(
            provider_id="US API", capability_id="us", country_capabilities=["US"],
            target_capabilities=["pdp"], historical_metrics={"avg_latency_ms": 100}
        )
        valid = CapabilityMetadata(
            provider_id="US Search", capability_id="search", country_capabilities=["US"],
            target_capabilities=["search"], historical_metrics={"avg_latency_ms": 100}
        )
        for capability in (failed, valid):
            registry.register(capability)

        fallback = FallbackManager(registry).adjust_cascade_on_failure(
            [failed], failed, FailureCategory.VALIDATION_FAILED.value,
            candidate_pool=[failed, valid],
            profile=type("Profile", (), {
                "inferred_country": "US", "target_type": "pdp",
                "location_sensitivity": False
            })(),
            preferences=CustomerPreferences()
        )
        self.assertEqual(fallback, [])

    def test_pipeline_uses_registered_adapter_and_records_learning_context(self):
        registry = isolated_registry()
        capability = CapabilityMetadata(
            provider_id="Mock", capability_id="Mock", country_capabilities=["US"],
            target_capabilities=["pdp"], estimated_cost=0.0001,
            historical_metrics={"validation_rate": 0.99, "avg_latency_ms": 1, "sample_size": 1}
        )
        adapter = MockProvider("<html>" + ("x" * 120) + "</html>")
        registry.register(capability)
        registry.bind_adapter("Mock", adapter)

        extractors = TargetExtractorRegistry()
        extractors._extractors.clear()
        extractors.register("Generic", lambda html, req: {
            "product_name": "Mock product", "price": "$1", "availability": "InStock"
        })
        pipeline = UnifiedPipeline(
            registry=registry,
            rate_card_registry=RateCardRegistry(),
            extractor_registry=extractors,
            validator=TargetValidator(),
            exploration_rate=0.0
        )

        result = pipeline.process_request(AcquisitionRequest(url="https://example.com/p/1"))

        self.assertTrue(result["validated"])
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(result["executed_attempts"][0]["attempt_index"], 1)
        observation = pipeline.learning_engine.get_observations()[0]
        self.assertEqual(observation["url_pattern"], "/p/*")
        self.assertEqual(observation["target_type"], "pdp")
        self.assertEqual(result["policy"]["selected_cascade"], ["Mock"])


if __name__ == "__main__":
    unittest.main()
