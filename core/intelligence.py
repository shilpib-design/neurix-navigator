"""
Target Intelligence Engine for Neurix Navigator v0.1 Core.
Infers TargetProfile from an AcquisitionRequest without requiring explicit customer parameters.
"""

import re
import urllib.parse
from typing import Dict, Any
from core.models import AcquisitionRequest, TargetProfile


class TargetIntelligence:
    """
    Parses request URLs and signals to generate an internal TargetProfile.
    """

    @staticmethod
    def analyze(request: AcquisitionRequest) -> TargetProfile:
        url = request.url
        parsed = urllib.parse.urlparse(url)
        domain_raw = parsed.netloc.lower()

        # Domain normalization
        domain = "Generic"
        if "amazon" in domain_raw:
            domain = "Amazon"
        elif "flipkart" in domain_raw:
            domain = "Flipkart"
        elif "purplle" in domain_raw:
            domain = "Purplle"
        elif "kroger" in domain_raw:
            domain = "Kroger"

        # Inferred Country
        inferred_country = "US"
        country_confidence = 0.70

        if request.country:
            inferred_country = request.country.upper()
            country_confidence = 1.0
        elif ".in" in domain_raw or domain in ["Flipkart", "Purplle"]:
            inferred_country = "IN"
            country_confidence = 0.95
        elif ".com" in domain_raw or domain in ["Kroger", "Amazon"]:
            inferred_country = "US"
            country_confidence = 0.95

        # URL Pattern & Target Type
        url_pattern = "/p/*"
        target_type = "pdp"

        if "/dp/" in parsed.path:
            url_pattern = "/dp/*"
            target_type = "pdp"
        elif "/p/" in parsed.path or "/product/" in parsed.path:
            url_pattern = "/p/*"
            target_type = "pdp"
        elif "search" in parsed.path or "s=" in parsed.query or "q=" in parsed.query:
            url_pattern = "/search/*"
            target_type = "search"

        # Location Sensitivity
        location_sensitivity = False
        query_params = urllib.parse.parse_qs(parsed.query)
        if "zip" in query_params or "postalCode" in query_params or request.parameters.get("zipcode"):
            location_sensitivity = True

        # Browser Likelihood
        browser_likelihood = 0.5
        if domain == "Kroger":
            browser_likelihood = 0.9
        elif domain == "Amazon":
            browser_likelihood = 0.6
        elif domain == "Flipkart":
            browser_likelihood = 0.4
        elif domain == "Purplle":
            browser_likelihood = 0.2

        fingerprint = f"{domain}:{target_type}:{inferred_country}:{parsed.path[:15]}"

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
