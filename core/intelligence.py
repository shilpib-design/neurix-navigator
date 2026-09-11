"""
Target Intelligence Engine for Neurix Navigator v0.1 Core.
Infers TargetProfile from an AcquisitionRequest without requiring explicit customer parameters.
"""

import urllib.parse
from typing import Dict, Any, Optional, Tuple
from core.models import AcquisitionRequest, TargetProfile


class TargetIntelligence:
    """
    Parses request URLs and signals to generate an internal TargetProfile.
    """

    KNOWN_DOMAINS = {
        "amazon": "Amazon",
        "flipkart": "Flipkart",
        "purplle": "Purplle",
        "kroger": "Kroger",
    }
    DOMAIN_COUNTRIES = {
        "Amazon": "US",
        "Flipkart": "IN",
        "Purplle": "IN",
        "Kroger": "US",
    }
    TLD_COUNTRIES = {
        ".in": "IN",
        ".co.uk": "GB",
        ".ca": "CA",
        ".de": "DE",
        ".fr": "FR",
        ".au": "AU",
        ".sg": "SG",
    }
    BROWSER_LIKELIHOODS = {
        "Kroger": 0.9,
        "Amazon": 0.6,
        "Flipkart": 0.4,
        "Purplle": 0.2,
    }

    @classmethod
    def analyze(cls, request: AcquisitionRequest) -> TargetProfile:
        parsed = urllib.parse.urlparse(request.url)
        hostname = cls._hostname(parsed.netloc)
        domain = cls.normalize_domain(hostname)
        inferred_country, country_confidence = cls.infer_country(
            request.country, hostname, domain
        )
        url_pattern, target_type = cls.detect_url_pattern(parsed)
        query_params = urllib.parse.parse_qs(parsed.query)
        location_sensitivity = cls.is_location_sensitive(query_params, request.parameters)
        browser_likelihood = cls.BROWSER_LIKELIHOODS.get(domain, 0.5)
        fingerprint = f"{domain}:{target_type}:{inferred_country}:{url_pattern}"

        return TargetProfile(
            domain=domain,
            url_pattern=url_pattern,
            inferred_country=inferred_country,
            country_confidence=country_confidence,
            target_type=target_type,
            location_sensitivity=location_sensitivity,
            browser_likelihood=browser_likelihood,
            required_capabilities=["pdp_extraction"],
            fingerprint=fingerprint
        )

    @classmethod
    def normalize_domain(cls, hostname: str) -> str:
        normalized = hostname.lower().strip(".")
        if normalized.startswith("www."):
            normalized = normalized[4:]
        labels = normalized.split(".")
        for label in labels:
            if label in cls.KNOWN_DOMAINS:
                return cls.KNOWN_DOMAINS[label]
        return "Generic"

    @staticmethod
    def _hostname(netloc: str) -> str:
        return netloc.rsplit("@", 1)[-1].split(":", 1)[0].lower().strip(".")

    @classmethod
    def infer_country(
        cls, explicit_country: Optional[str], hostname: str, domain: str
    ) -> Tuple[str, float]:
        if explicit_country and explicit_country.strip():
            return explicit_country.strip().upper(), 1.0
        if domain in cls.DOMAIN_COUNTRIES:
            return cls.DOMAIN_COUNTRIES[domain], 0.95
        for suffix, country in sorted(cls.TLD_COUNTRIES.items(), key=lambda item: -len(item[0])):
            if hostname.endswith(suffix):
                return country, 0.90
        return "Unknown", 0.0

    @staticmethod
    def detect_url_pattern(parsed: urllib.parse.ParseResult) -> Tuple[str, str]:
        path = parsed.path.rstrip("/")
        path_lower = path.lower()
        segments = {segment for segment in path_lower.split("/") if segment}
        query_keys = {key.lower() for key in urllib.parse.parse_qs(parsed.query)}

        if "checkout" in segments or path_lower.endswith("/checkout"):
            return "/checkout/*", "checkout"
        if "cart" in segments or path_lower.endswith("/cart"):
            return "/cart/*", "cart"
        if (
            "search" in segments
            or "search" in path_lower
            or query_keys.intersection({"q", "query", "search", "s"})
        ):
            return "/search/*", "search"
        if "/dp/" in path_lower:
            return "/dp/*", "pdp"
        if any(token in segments for token in (
            "category", "categories", "catalog", "collection", "collections",
            "browse", "listing", "list"
        )):
            return "/category/*", "category"
        if any(token in segments for token in ("p", "product", "products", "item", "detail", "details")):
            return "/p/*", "pdp"
        if not path:
            return "/", "homepage"
        return "/unknown/*", "unknown"

    @staticmethod
    def is_location_sensitive(
        query_params: Dict[str, Any], request_parameters: Dict[str, Any]
    ) -> bool:
        location_keys = {
            "zip", "zipcode", "postal", "postalcode", "pincode", "postcode", "location"
        }
        query_keys = {key.lower() for key in query_params}
        parameter_keys = {key.lower() for key in request_parameters}
        return bool(query_keys.intersection(location_keys) or parameter_keys.intersection(location_keys))
