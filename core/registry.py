"""
Dynamic Provider Registry & Health State Machine for Neurix Navigator v0.1 Core.
Handles dynamic addition, removal, enabling/disabling of providers, and sliding-window health management.
"""

import time
from typing import Dict, Any, List, Optional
from core.models import CapabilityMetadata, HealthState


class ProviderRegistry:
    """
    Central registry for acquisition capabilities and health state transitions.
    Decoupled from decision logic.
    """

    def __init__(self):
        self._capabilities: Dict[str, CapabilityMetadata] = {}
        self._health_history: Dict[str, List[Dict[str, Any]]] = {}
        self._register_default_capabilities()

    def register(self, capability: CapabilityMetadata):
        key = capability.capability_id
        self._capabilities[key] = capability
        if key not in self._health_history:
            self._health_history[key] = []

    def bind_adapter(self, capability_id: str, adapter: Any) -> None:
        """Bind an executable provider adapter to a registered capability."""
        capability = self._capabilities.get(capability_id)
        if capability is None:
            raise KeyError(f"Unknown capability: {capability_id}")
        capability.adapter = adapter

    def resolve_adapter(self, capability_id: str) -> Optional[Any]:
        """Return an adapter only for an enabled registered capability."""
        capability = self._capabilities.get(capability_id)
        if not capability or not capability.enabled:
            return None
        return capability.adapter

    def is_executable(self, capability_id: str) -> bool:
        return self.resolve_adapter(capability_id) is not None

    def unregister(self, capability_id: str):
        if capability_id in self._capabilities:
            del self._capabilities[capability_id]

    def set_enabled(self, capability_id: str, enabled: bool):
        if capability_id in self._capabilities:
            self._capabilities[capability_id].enabled = enabled
            if not enabled:
                self._capabilities[capability_id].current_health = HealthState.DISABLED
            else:
                self._capabilities[capability_id].current_health = HealthState.AVAILABLE

    def get(self, capability_id: str) -> Optional[CapabilityMetadata]:
        return self._capabilities.get(capability_id)

    def list_capabilities(self, enabled_only: bool = True) -> List[CapabilityMetadata]:
        if enabled_only:
            return [c for c in self._capabilities.values() if c.enabled]
        return list(self._capabilities.values())

    def update_health(self, capability_id: str, success: bool, failure_category: Optional[str] = None):
        cap = self._capabilities.get(capability_id)
        if not cap or not cap.enabled:
            return

        history = self._health_history.get(capability_id, [])
        history.append({
            "timestamp": time.time(),
            "success": success,
            "failure_category": failure_category
        })
        # Keep sliding window of last 20 attempts
        if len(history) > 20:
            history.pop(0)
        self._health_history[capability_id] = history

        # Calculate health state based on sliding window
        recent = history[-10:] if len(history) >= 10 else history
        recent_fails = sum(1 for h in recent if not h["success"])
        fail_rate = recent_fails / len(recent) if recent else 0.0

        if failure_category == "RATE_LIMIT":
            cap.current_health = HealthState.RATE_LIMITED
        elif fail_rate >= 0.7:
            cap.current_health = HealthState.FAILED
        elif fail_rate >= 0.3:
            cap.current_health = HealthState.DEGRADED
        else:
            cap.current_health = HealthState.AVAILABLE

    def _register_default_capabilities(self):
        # 1. Context.dev API
        self.register(CapabilityMetadata(
            provider_id="Context.dev",
            capability_id="Context.dev",
            enabled=True,
            acquisition_method="api",
            country_capabilities=["US", "IN"],
            estimated_cost=0.001,
            historical_metrics={"success_rate": 0.85, "validation_rate": 0.80, "avg_latency_ms": 1500, "sample_size": 30}
        ))

        # 2. String API
        self.register(CapabilityMetadata(
            provider_id="String",
            capability_id="String",
            enabled=True,
            acquisition_method="api",
            country_capabilities=["US", "IN"],
            estimated_cost=0.0015,
            historical_metrics={"success_rate": 0.88, "validation_rate": 0.82, "avg_latency_ms": 2500, "sample_size": 30}
        ))

        # 3. Scrapfly API
        self.register(CapabilityMetadata(
            provider_id="Scrapfly",
            capability_id="Scrapfly",
            enabled=True,
            acquisition_method="api",
            country_capabilities=["US", "IN"],
            estimated_cost=0.002,
            historical_metrics={"success_rate": 0.70, "validation_rate": 0.65, "avg_latency_ms": 3500, "sample_size": 20}
        ))

        # 4. AlterLab API (Disabled by default per Stage 1 active provider specification)
        self.register(CapabilityMetadata(
            provider_id="AlterLab",
            capability_id="AlterLab",
            enabled=False,
            current_health=HealthState.DISABLED,
            acquisition_method="api",
            country_capabilities=["US", "IN"],
            estimated_cost=0.0012,
            historical_metrics={"success_rate": 0.75, "validation_rate": 0.70, "avg_latency_ms": 3000, "sample_size": 15}
        ))

        # 5. GeoNode Residential (Browser Proxy)
        self.register(CapabilityMetadata(
            provider_id="GeoNode Res",
            capability_id="GeoNode Res",
            enabled=True,
            acquisition_method="browser",
            proxy_type="Residential",
            country_capabilities=["US", "IN"],
            browser_support=True,
            estimated_cost=0.0003,
            historical_metrics={"success_rate": 0.90, "validation_rate": 0.85, "avg_latency_ms": 12000, "sample_size": 30}
        ))

        # 6. GeoNode Datacenter (Browser Proxy)
        self.register(CapabilityMetadata(
            provider_id="GeoNode DC",
            capability_id="GeoNode DC",
            enabled=True,
            acquisition_method="browser",
            proxy_type="Datacenter",
            country_capabilities=["US"],
            browser_support=True,
            estimated_cost=0.00015,
            historical_metrics={"success_rate": 0.80, "validation_rate": 0.75, "avg_latency_ms": 10000, "sample_size": 25}
        ))

        # 7. DataImpulse Residential
        self.register(CapabilityMetadata(
            provider_id="DI Res",
            capability_id="DI Res",
            enabled=True,
            acquisition_method="browser",
            proxy_type="Residential",
            country_capabilities=["US", "IN"],
            browser_support=True,
            estimated_cost=0.00035,
            historical_metrics={"success_rate": 0.85, "validation_rate": 0.80, "avg_latency_ms": 11000, "sample_size": 20}
        ))

        # 8. DataImpulse Mobile
        self.register(CapabilityMetadata(
            provider_id="DI Mobile",
            capability_id="DI Mobile",
            enabled=True,
            acquisition_method="browser",
            proxy_type="Mobile",
            country_capabilities=["US"],
            browser_support=True,
            estimated_cost=0.00065,
            historical_metrics={"success_rate": 0.92, "validation_rate": 0.88, "avg_latency_ms": 14000, "sample_size": 15}
        ))

        # 9. Donut / Local CDP Browser
        self.register(CapabilityMetadata(
            provider_id="Donut Browser",
            capability_id="Donut Browser",
            enabled=True,
            acquisition_method="browser",
            proxy_type="None",
            country_capabilities=["US", "IN"],
            browser_support=True,
            estimated_cost=0.0002,
            historical_metrics={"success_rate": 0.95, "validation_rate": 0.90, "avg_latency_ms": 8000, "sample_size": 40}
        ))

        # 10. Pure HTTP Acquisition
        self.register(CapabilityMetadata(
            provider_id="PureHTTP",
            capability_id="pure_http",
            enabled=True,
            acquisition_method="http",
            country_capabilities=["US", "IN", "GB", "CA", "DE", "FR", "AU", "SG"],
            target_capabilities=["pdp", "search", "category", "cart", "checkout", "homepage", "generic"],
            estimated_cost=0.0001,
            historical_metrics={"success_rate": 0.90, "validation_rate": 0.85, "avg_latency_ms": 500, "sample_size": 20}
        ))

        self.bind_adapter("Context.dev", self._load_adapter("Context.dev"))
        self.bind_adapter("String", self._load_adapter("String"))
        self.bind_adapter("Scrapfly", self._load_adapter("Scrapfly"))
        self.bind_adapter("pure_http", self._load_adapter("pure_http"))

        # Browser/proxy capabilities and pure_http remain registered for lifecycle and future
        # integration, but are disabled by default per Stage 2A active provider specification.
        for capability_id in (
            "GeoNode Res", "GeoNode DC", "DI Res", "DI Mobile", "Donut Browser", "pure_http"
        ):
            self.set_enabled(capability_id, False)

    @staticmethod
    def _load_adapter(provider_id: str) -> Any:
        adapter_types = {
            "Context.dev": ("providers.context_dev_adapter", "ContextDevProvider"),
            "String": ("providers.string_adapter", "StringProvider"),
            "Scrapfly": ("providers.scrapfly_adapter", "ScrapflyProvider"),
            "pure_http": ("providers.pure_http_adapter", "PureHttpProvider"),
            "PureHTTP": ("providers.pure_http_adapter", "PureHttpProvider"),
        }
        module_name, class_name = adapter_types[provider_id]
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)()
