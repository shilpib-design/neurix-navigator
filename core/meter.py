"""
Customer Usage Meter for Neurix Navigator v0.1 Core.
Tracks billable customer transactions independently of provider billing.
"""

from typing import List, Dict, Any
from core.models import AcquisitionRequest, BillingRecord


class CustomerUsageMeter:
    """
    Computes customer billable units, pricing, internal vendor cost, infra cost, and gross margin.
    """

    def __init__(self, base_customer_price: float = 0.05, infra_cost_per_req: float = 0.0001):
        self.base_customer_price = base_customer_price
        self.infra_cost_per_req = infra_cost_per_req
        self._records: List[BillingRecord] = []

    def record_transaction(
        self,
        request: AcquisitionRequest,
        target_domain: str,
        validated_result: bool,
        response_size_bytes: int,
        processing_time_ms: int,
        provider_cost: float
    ) -> BillingRecord:
        billable_unit = 1 if validated_result else 0
        customer_price = self.base_customer_price if validated_result else 0.0
        infra_cost = self.infra_cost_per_req
        gross_margin = customer_price - (provider_cost + infra_cost)

        record = BillingRecord(
            customer_id=request.customer_id,
            request_id=request.request_id,
            target=target_domain,
            status="SUCCESS" if validated_result else "VALIDATION_FAILED",
            validated_result=validated_result,
            billable_unit=billable_unit,
            response_size_bytes=response_size_bytes,
            processing_time_ms=processing_time_ms,
            customer_price=round(customer_price, 4),
            provider_cost=round(provider_cost, 6),
            infra_cost=round(infra_cost, 6),
            gross_margin=round(gross_margin, 6)
        )
        self._records.append(record)
        return record

    def get_records(self) -> List[BillingRecord]:
        return list(self._records)
