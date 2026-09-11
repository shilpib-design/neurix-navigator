"""
Lean Data Storage Manager for Neurix Navigator v0.1 Core.
Separates billing records, structured learning telemetry, and temporary raw payload TTL metadata.
"""

import time
from typing import Dict, Any, List, Optional
from core.models import BillingRecord


class LeanStorageManager:
    """
    Manages structured billing, telemetry, and temporary raw data payload TTL metadata.
    """

    def __init__(self, raw_ttl_seconds: int = 300, retain_raw_html: bool = False):
        self.raw_ttl_seconds = raw_ttl_seconds
        self.retain_raw_html = retain_raw_html
        self._billing_store: List[Dict[str, Any]] = []
        self._telemetry_store: List[Dict[str, Any]] = []
        self._raw_metadata_store: List[Dict[str, Any]] = []

    def store_billing_record(self, record: BillingRecord):
        self._billing_store.append(record.to_dict())

    def store_telemetry_observation(self, obs: Dict[str, Any]):
        # Store compact structured summary only
        compact_obs = {
            "timestamp": obs.get("timestamp", time.time()),
            "capability_id": obs.get("capability_id"),
            "domain": obs.get("domain"),
            "country": obs.get("country"),
            "success": obs.get("success"),
            "validated": obs.get("validated"),
            "latency_ms": obs.get("latency_ms"),
            "bytes": obs.get("bytes"),
            "estimated_cost": obs.get("estimated_cost"),
            "failure_category": obs.get("failure_category")
        }
        self._telemetry_store.append(compact_obs)

    def store_raw_payload_metadata(self, request_id: str, capability_id: str, html_payload: str) -> Dict[str, Any]:
        """
        Stores metadata with TTL for raw acquisition content without permanently retaining full HTML strings.
        """
        size_bytes = len(html_payload.encode("utf-8")) if html_payload else 0
        now = time.time()
        meta = {
            "request_id": request_id,
            "capability_id": capability_id,
            "size_bytes": size_bytes,
            "created_at": now,
            "expires_at": now + self.raw_ttl_seconds,
            "retained": self.retain_raw_html,
            "content_preview": html_payload[:100] if (self.retain_raw_html and html_payload) else "SUPPRESSED_PER_LEAN_STORAGE_POLICY"
        }
        self._raw_metadata_store.append(meta)
        return meta

    def purge_expired_raw_metadata(self):
        now = time.time()
        self._raw_metadata_store = [m for m in self._raw_metadata_store if m["expires_at"] > now]

    def get_billing_store(self) -> List[Dict[str, Any]]:
        return list(self._billing_store)

    def get_telemetry_store(self) -> List[Dict[str, Any]]:
        return list(self._telemetry_store)

    def get_raw_metadata_store(self) -> List[Dict[str, Any]]:
        return list(self._raw_metadata_store)
