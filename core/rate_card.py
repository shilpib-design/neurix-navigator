"""
Dynamic Rate Card Engine for Neurix Navigator v0.1 Core.
Supports provider/domain specific rates, volume pricing tiers, effective dates,
and marginal billing-period cost calculation for the Economic Optimizer.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class VolumeTier:
    min_volume: int
    max_volume: Optional[int]  # None for upper unbounded tier
    unit_cost: float


@dataclass
class ProviderRateCard:
    provider_id: str
    capability_id: str
    base_rate: float
    pricing_unit: str = "request"  # "request" or "gb"
    domain_multipliers: Dict[str, float] = field(default_factory=dict)
    volume_tiers: List[VolumeTier] = field(default_factory=list)
    version: str = "1.0"
    pricing_version: str = "1.0"
    effective_date: float = field(default_factory=time.time)
    effective_until: Optional[float] = None

    def get_marginal_rate(self, current_period_volume: int, domain: str = "Generic") -> float:
        """
        Calculates the effective marginal cost per unit given current billing period consumption.
        """
        multiplier = self.domain_multipliers.get(domain, 1.0)

        if not self.volume_tiers:
            return self.base_rate * multiplier

        # Match volume tier
        for tier in self.volume_tiers:
            if tier.min_volume <= current_period_volume:
                if tier.max_volume is None or current_period_volume < tier.max_volume:
                    return tier.unit_cost * multiplier

        # Fallback to last tier or base_rate
        return (self.volume_tiers[-1].unit_cost if self.volume_tiers else self.base_rate) * multiplier


class RateCardRegistry:
    """
    Registry for dynamic vendor rate cards and billing-period consumption trackers.
    """

    def __init__(self):
        self._rate_cards: Dict[str, ProviderRateCard] = {}
        self._consumption_counter: Dict[str, int] = {}
        self._load_default_rate_cards()

    def register(self, rate_card: ProviderRateCard):
        key = f"{rate_card.provider_id}:{rate_card.capability_id}"
        self._rate_cards[key] = rate_card
        if key not in self._consumption_counter:
            self._consumption_counter[key] = 0

    def record_usage(self, provider_id: str, capability_id: str, units: int = 1):
        key = f"{provider_id}:{capability_id}"
        self._consumption_counter[key] = self._consumption_counter.get(key, 0) + units

    def get_consumption(self, provider_id: str, capability_id: str) -> int:
        key = f"{provider_id}:{capability_id}"
        return self._consumption_counter.get(key, 0)

    def get_marginal_cost(
        self,
        provider_id: str,
        capability_id: str,
        domain: str = "Generic",
        estimated_units: float = 1.0,
        default_cost: float = 0.001
    ) -> float:
        key = f"{provider_id}:{capability_id}"
        rate_card = self._rate_cards.get(key)
        if not rate_card:
            return default_cost * estimated_units

        current_vol = self._consumption_counter.get(key, 0)
        unit_rate = rate_card.get_marginal_rate(current_vol, domain)
        return unit_rate * estimated_units

    def _load_default_rate_cards(self):
        # Configure standard rate cards
        self.register(ProviderRateCard(
            provider_id="Context.dev",
            capability_id="Context.dev",
            base_rate=0.0010,
            volume_tiers=[
                VolumeTier(min_volume=0, max_volume=10000, unit_cost=0.0010),
                VolumeTier(min_volume=10000, max_volume=None, unit_cost=0.0007)
            ]
        ))
        self.register(ProviderRateCard(
            provider_id="String",
            capability_id="String",
            base_rate=0.0015,
            volume_tiers=[
                VolumeTier(min_volume=0, max_volume=5000, unit_cost=0.0015),
                VolumeTier(min_volume=5000, max_volume=None, unit_cost=0.0010)
            ]
        ))
        self.register(ProviderRateCard(
            provider_id="Scrapfly",
            capability_id="Scrapfly",
            base_rate=0.0020
        ))
        self.register(ProviderRateCard(
            provider_id="AlterLab",
            capability_id="AlterLab",
            base_rate=0.0012
        ))
        self.register(ProviderRateCard(
            provider_id="PureHTTP",
            capability_id="pure_http",
            base_rate=0.0001
        ))
        self.register(ProviderRateCard(
            provider_id="PureHTTP",
            capability_id="PureHTTP",
            base_rate=0.0001
        ))
        self.register(ProviderRateCard(
            provider_id="SessionAssistedHTTP",
            capability_id="session_assisted_http",
            base_rate=0.00015
        ))
        self.register(ProviderRateCard(
            provider_id="SessionAssistedHTTP",
            capability_id="SessionAssistedHTTP",
            base_rate=0.00015
        ))
        self.register(ProviderRateCard(
            provider_id="Donut Browser",
            capability_id="Donut Browser",
            base_rate=0.0002
        ))

        # Proxy Rate Cards (per GB pricing estimated as 0.005 GB per request = 5MB)
        # GeoNode Res: $0.57/GB -> ~$0.000285 / 0.5MB request
        self.register(ProviderRateCard(
            provider_id="GeoNode Res",
            capability_id="GeoNode Res",
            base_rate=0.0003,
            pricing_unit="gb"
        ))
        self.register(ProviderRateCard(
            provider_id="GeoNode DC",
            capability_id="GeoNode DC",
            base_rate=0.00015,
            pricing_unit="gb"
        ))
        self.register(ProviderRateCard(
            provider_id="DI Res",
            capability_id="DI Res",
            base_rate=0.00035,
            pricing_unit="gb"
        ))
        self.register(ProviderRateCard(
            provider_id="DI Mobile",
            capability_id="DI Mobile",
            base_rate=0.00065,
            pricing_unit="gb"
        ))
