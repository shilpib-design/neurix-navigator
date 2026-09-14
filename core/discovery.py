"""
Generic Acquisition Discovery Layer for Neurix Navigator v0.1.
Inspects observed HTTP response artifacts (headers, HTML, scripts, JSON body, endpoint references)
and identifies structured acquisition surfaces with deterministic confidence scoring.
"""

import json
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class DiscoveryRequest:
    url: str
    target: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    status_code: Optional[int] = None
    body: Union[str, bytes] = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "target": self.target,
            "headers": dict(self.headers),
            "status_code": self.status_code,
            "body_length": len(self.body) if self.body else 0,
            "context": self.context
        }


@dataclass
class DiscoverySurface:
    surface_type: str  # html, json_ld, embedded_json, json_endpoint, graphql_endpoint, rsc_payload, structured_payload
    url: str
    method: str = "GET"
    content_type: Optional[str] = None
    confidence: float = 0.0
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "surface_type": self.surface_type,
            "url": self.url,
            "method": self.method,
            "content_type": self.content_type,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "metadata": self.metadata
        }


@dataclass
class DiscoveryResult:
    target: str
    surfaces: List[DiscoverySurface] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    discovery_success: bool = True
    errors: List[str] = field(default_factory=list)
    elapsed_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "surfaces": [s.to_dict() for s in self.surfaces],
            "evidence": self.evidence,
            "discovery_success": self.discovery_success,
            "errors": self.errors,
            "elapsed_ms": self.elapsed_ms
        }


class DiscoveryEngine:
    """
    Generic, site-agnostic acquisition discovery engine.
    Analyzes observed HTTP response artifacts to discover potential acquisition surfaces.
    Operates strictly in-memory without making network, browser, or vendor calls.
    """

    MAX_SURFACES = 50

    def __init__(self):
        pass

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        start_time = time.time()
        surfaces: List[DiscoverySurface] = []
        errors: List[str] = []
        evidence: Dict[str, Any] = {
            "headers_checked": False,
            "body_checked": False,
            "html_analyzed": False,
            "json_ld_count": 0,
            "embedded_json_count": 0,
            "endpoint_ref_count": 0,
        }

        target_name = request.target or self._infer_target(request.url)

        # Safely convert body to text string
        body_text = ""
        if isinstance(request.body, bytes):
            try:
                body_text = request.body.decode("utf-8", errors="ignore")
            except Exception as e:
                errors.append(f"Body decoding error: {str(e)}")
        elif isinstance(request.body, str):
            body_text = request.body

        headers_lower = {k.lower(): str(v) for k, v in request.headers.items()}
        content_type = headers_lower.get("content-type", "").lower()

        # 1. Header / Content-Type Evidence
        if content_type:
            evidence["headers_checked"] = True
            header_surfaces = self._detect_header_surfaces(request.url, content_type, headers_lower)
            surfaces.extend(header_surfaces)

        if not body_text or not body_text.strip():
            elapsed_ms = int((time.time() - start_time) * 1000)
            deduped = self._deduplicate_and_sort(surfaces)
            return DiscoveryResult(
                target=target_name,
                surfaces=deduped,
                evidence=evidence,
                discovery_success=len(deduped) > 0,
                errors=errors,
                elapsed_ms=elapsed_ms
            )

        evidence["body_checked"] = True

        # 2. Response Body (JSON / Structured Payload / GraphQL / RSC) Analysis
        body_surfaces, is_pure_json = self._detect_body_surfaces(request.url, body_text, content_type)
        surfaces.extend(body_surfaces)

        # 3. HTML Content Analysis (if HTML content or not pure JSON)
        if not is_pure_json:
            evidence["html_analyzed"] = True
            html_surfaces, html_evidence = self._detect_html_surfaces(request.url, body_text)
            surfaces.extend(html_surfaces)
            evidence.update(html_evidence)

        # Deduplicate and sort surfaces by confidence descending
        final_surfaces = self._deduplicate_and_sort(surfaces)
        elapsed_ms = int((time.time() - start_time) * 1000)

        return DiscoveryResult(
            target=target_name,
            surfaces=final_surfaces,
            evidence=evidence,
            discovery_success=len(final_surfaces) > 0,
            errors=errors,
            elapsed_ms=elapsed_ms
        )

    @staticmethod
    def _infer_target(url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc.split(":")[0]
            parts = netloc.split(".")
            if len(parts) >= 2:
                return parts[-2].capitalize()
            return netloc or "generic"
        except Exception:
            return "generic"

    @staticmethod
    def _detect_header_surfaces(url: str, content_type: str, headers: Dict[str, str]) -> List[DiscoverySurface]:
        surfaces = []
        if "text/html" in content_type:
            surfaces.append(DiscoverySurface(
                surface_type="html",
                url=url,
                method="GET",
                content_type=content_type,
                confidence=0.70,
                source="header",
                metadata={"header_type": "text/html"}
            ))
        elif "application/graphql-response+json" in content_type or "application/graphql" in content_type:
            surfaces.append(DiscoverySurface(
                surface_type="graphql_endpoint",
                url=url,
                method="POST",
                content_type=content_type,
                confidence=0.95,
                source="header",
                metadata={"header_type": content_type}
            ))
        elif "text/x-component" in content_type or "x-nextjs-postponed" in headers or "x-action" in headers:
            surfaces.append(DiscoverySurface(
                surface_type="rsc_payload",
                url=url,
                method="GET",
                content_type=content_type,
                confidence=0.90,
                source="header",
                metadata={"header_type": content_type}
            ))
        elif "application/json" in content_type or "application/hal+json" in content_type:
            surfaces.append(DiscoverySurface(
                surface_type="json_endpoint",
                url=url,
                method="GET",
                content_type=content_type,
                confidence=0.95,
                source="header",
                metadata={"header_type": content_type}
            ))
        elif "application/ld+json" in content_type:
            surfaces.append(DiscoverySurface(
                surface_type="json_ld",
                url=url,
                method="GET",
                content_type=content_type,
                confidence=0.95,
                source="header",
                metadata={"header_type": content_type}
            ))
        elif "application/" in content_type:
            surfaces.append(DiscoverySurface(
                surface_type="structured_payload",
                url=url,
                method="GET",
                content_type=content_type,
                confidence=0.85,
                source="header",
                metadata={"header_type": content_type}
            ))
        return surfaces

    @staticmethod
    def _detect_body_surfaces(url: str, body_text: str, content_type: str) -> tuple:
        surfaces = []
        is_pure_json = False

        stripped = body_text.strip()

        # Check for RSC payload stream markers
        if "text/x-component" in content_type or stripped.startswith("1:I") or "__next_f" in body_text:
            surfaces.append(DiscoverySurface(
                surface_type="rsc_payload",
                url=url,
                method="GET",
                content_type="text/x-component",
                confidence=0.85,
                source="response_body",
                metadata={"rsc_stream_detected": True}
            ))

        # Check if entire body is JSON
        if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
            try:
                data = json.loads(stripped)
                is_pure_json = True
                if isinstance(data, dict):
                    # Check for GraphQL response structure
                    if "data" in data or "errors" in data:
                        surfaces.append(DiscoverySurface(
                            surface_type="graphql_endpoint",
                            url=url,
                            method="POST",
                            content_type="application/json",
                            confidence=0.90,
                            source="response_body",
                            metadata={"has_data_key": "data" in data, "has_errors_key": "errors" in data}
                        ))
                    
                    surfaces.append(DiscoverySurface(
                        surface_type="structured_payload",
                        url=url,
                        method="GET",
                        content_type="application/json",
                        confidence=0.80,
                        source="response_body",
                        metadata={"root_type": "object", "top_keys": list(data.keys())[:10]}
                    ))
                elif isinstance(data, list):
                    surfaces.append(DiscoverySurface(
                        surface_type="structured_payload",
                        url=url,
                        method="GET",
                        content_type="application/json",
                        confidence=0.80,
                        source="response_body",
                        metadata={"root_type": "array", "length": len(data)}
                    ))
            except Exception:
                is_pure_json = False

        return surfaces, is_pure_json

    def _detect_html_surfaces(self, url: str, html_text: str) -> tuple:
        surfaces = []
        evidence = {
            "json_ld_count": 0,
            "embedded_json_count": 0,
            "endpoint_ref_count": 0,
        }

        # Check basic HTML document signal
        if "<html" in html_text.lower() or "<body" in html_text.lower() or "<!doctype" in html_text.lower():
            surfaces.append(DiscoverySurface(
                surface_type="html",
                url=url,
                method="GET",
                content_type="text/html",
                confidence=0.70,
                source="html_tag",
                metadata={"document_structure": "html"}
            ))

        # A. JSON-LD script blocks: <script type="application/ld+json">...</script>
        json_ld_blocks = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_text,
            re.IGNORECASE | re.DOTALL
        )
        for block in json_ld_blocks:
            evidence["json_ld_count"] += 1
            cleaned = block.strip()
            ld_meta = {}
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    ld_meta["type"] = parsed.get("@type", "unknown")
                    ld_meta["context"] = parsed.get("@context", "")
                elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                    ld_meta["type"] = parsed[0].get("@type", "unknown")
            except Exception:
                ld_meta["raw_preview"] = cleaned[:100]

            surfaces.append(DiscoverySurface(
                surface_type="json_ld",
                url=url,
                method="GET",
                content_type="application/ld+json",
                confidence=0.90,
                source="script_json_ld",
                metadata=ld_meta
            ))

        # B. Embedded JSON blocks: <script type="application/json">...</script> or Next.js / state scripts
        embedded_json_blocks = re.findall(
            r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
            html_text,
            re.IGNORECASE | re.DOTALL
        )
        for block in embedded_json_blocks:
            evidence["embedded_json_count"] += 1
            cleaned = block.strip()
            script_meta = {}
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    script_meta["keys"] = list(parsed.keys())[:10]
            except Exception:
                script_meta["raw_preview"] = cleaned[:100]

            surfaces.append(DiscoverySurface(
                surface_type="embedded_json",
                url=url,
                method="GET",
                content_type="application/json",
                confidence=0.85,
                source="script_embedded_json",
                metadata=script_meta
            ))

        # Also search for standard state object script patterns (e.g. __NEXT_DATA__, window.__INITIAL_STATE__)
        state_patterns = [
            r'id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
            r'window\.__NUXT__\s*=\s*({.*?});'
        ]
        for pattern in state_patterns:
            matches = re.findall(pattern, html_text, re.DOTALL)
            for m in matches:
                evidence["embedded_json_count"] += 1
                state_meta = {"state_var": pattern.split("=")[0].strip()}
                try:
                    parsed = json.loads(m.strip())
                    if isinstance(parsed, dict):
                        state_meta["keys"] = list(parsed.keys())[:10]
                except Exception:
                    state_meta["preview"] = m.strip()[:100]

                surfaces.append(DiscoverySurface(
                    surface_type="embedded_json",
                    url=url,
                    method="GET",
                    content_type="application/json",
                    confidence=0.85,
                    source="script_embedded_json",
                    metadata=state_meta
                ))

        # C. Generic Endpoint References Detection (/api/..., /graphql, .json, etc.)
        endpoint_surfaces = self._detect_endpoint_references(url, html_text)
        evidence["endpoint_ref_count"] = len(endpoint_surfaces)
        surfaces.extend(endpoint_surfaces)

        return surfaces, evidence

    def _detect_endpoint_references(self, base_url: str, html_text: str) -> List[DiscoverySurface]:
        surfaces = []
        found_urls = set()

        # Generic pattern matching for API endpoints and GraphQL endpoints
        graphql_regex = r'["\'](/graphql(?:/[^"\'\s>]*)?|https?://[^"\'\s>]+/graphql(?:/[^"\'\s>]*)?)["\']'
        api_regex = r'["\'](/api/[^"\'\s>]+|https?://[^"\'\s>]+/api/[^"\'\s>]+|/[a-zA-Z0-9_-]+/v[0-9]+/[^"\'\s>]+\.json|[^"\'\s>]+\.json)["\']'

        # Match GraphQL endpoint references
        for match in re.findall(graphql_regex, html_text, re.IGNORECASE):
            resolved_url = self._normalize_url(base_url, match)
            if resolved_url and resolved_url not in found_urls:
                found_urls.add(resolved_url)
                surfaces.append(DiscoverySurface(
                    surface_type="graphql_endpoint",
                    url=resolved_url,
                    method="POST",
                    content_type="application/json",
                    confidence=0.60,
                    source="endpoint_reference",
                    metadata={"detected_ref": match}
                ))

        # Match API / JSON endpoint references
        for match in re.findall(api_regex, html_text, re.IGNORECASE):
            resolved_url = self._normalize_url(base_url, match)
            if resolved_url and resolved_url not in found_urls:
                found_urls.add(resolved_url)
                surfaces.append(DiscoverySurface(
                    surface_type="json_endpoint",
                    url=resolved_url,
                    method="GET",
                    content_type="application/json",
                    confidence=0.50,
                    source="endpoint_reference",
                    metadata={"detected_ref": match}
                ))

        return surfaces[:self.MAX_SURFACES]

    @staticmethod
    def _normalize_url(base_url: str, raw_path: str) -> Optional[str]:
        if not raw_path or not raw_path.strip():
            return None
        cleaned = raw_path.strip()
        # Avoid non-HTTP references
        if cleaned.startswith("data:") or cleaned.startswith("javascript:") or cleaned.startswith("mailto:"):
            return None
        try:
            resolved = urllib.parse.urljoin(base_url, cleaned)
            parsed = urllib.parse.urlparse(resolved)
            if parsed.scheme in ["http", "https"] and parsed.netloc:
                return resolved
        except Exception:
            return None
        return None

    def _deduplicate_and_sort(self, surfaces: List[DiscoverySurface]) -> List[DiscoverySurface]:
        seen = {}
        for s in surfaces:
            key = (s.surface_type, s.url, s.method)
            if key not in seen:
                seen[key] = s
            else:
                # Keep highest confidence and merge metadata
                if s.confidence > seen[key].confidence:
                    merged_meta = {**seen[key].metadata, **s.metadata}
                    s.metadata = merged_meta
                    seen[key] = s
                else:
                    seen[key].metadata.update(s.metadata)

        # Sort by confidence descending, then by surface_type, then by url
        sorted_surfaces = sorted(
            seen.values(),
            key=lambda item: (-item.confidence, item.surface_type, item.url)
        )
        return sorted_surfaces[:self.MAX_SURFACES]
