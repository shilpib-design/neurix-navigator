"""
Kroger ZIP Delivery-Context Resolver.

Dynamically maps a US ZIP code to Kroger's delivery context via
a pluggable Acquisition Client interface.
"""

from typing import Dict, Any
from kroger.acquisition import BaseAcquisitionClient

KROGER_MODALITY_OPTIONS_URL = "https://www.kroger.com/atlas/v1/modality/options"


def resolve_delivery_context(zip_code: str, acquisition_client: BaseAcquisitionClient) -> dict:
    """
    Dynamically resolves Kroger delivery fulfillment context for a given US ZIP code.

    Delegates the raw request execution to the provided acquisition_client,
    then parses the response payload to select and normalize the DELIVERY context.

    Args:
        zip_code (str): Target US postal code (e.g. "30301").
        acquisition_client (BaseAcquisitionClient): Pluggable client implementation.

    Returns:
        dict: Normalized delivery context dictionary.
    """
    if not zip_code or not str(zip_code).strip():
        raise ValueError("ZIP code must be a non-empty string.")

    zip_code_str = str(zip_code).strip()

    url = KROGER_MODALITY_OPTIONS_URL
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json, text/plain, */*",
        "x-kroger-channel": "WEB",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
        ),
    }
    payload = {
        "address": {
            "postalCode": zip_code_str
        }
    }

    response_data = acquisition_client.post(url, payload, headers)

    if not response_data or not isinstance(response_data, (dict, list)):
        raise ValueError(
            f"Invalid response payload returned by acquisition client for ZIP {zip_code_str}"
        )

    return parse_modality_response(response_data, zip_code_str)


def parse_modality_response(data: Any, zip_code: str) -> dict:
    """
    Parses the Kroger /atlas/v1/modality/options response payload and returns
    a normalized DELIVERY context dictionary.

    Args:
        data (dict | list): Response body from /atlas/v1/modality/options.
        zip_code (str): Input postal code.

    Returns:
        dict: Normalized context object containing postal_code, latitude, longitude,
              modality_type, provider, fallback fields, fulfillment list,
              destination_validated, and raw_delivery_option.
    """
    options = []
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], dict):
            options = data["data"].get("modalityOptions", [])
        elif "modalityOptions" in data:
            options = data["modalityOptions"]
        elif isinstance(data.get("options"), list):
            options = data["options"]
    elif isinstance(data, list):
        options = data

    delivery_option = None
    for opt in options:
        if not isinstance(opt, dict):
            continue
        modality_info = opt.get("modality", {})
        m_type = modality_info.get("type") or opt.get("modalityType") or opt.get("type")
        if m_type == "DELIVERY":
            delivery_option = opt
            break

    if not delivery_option:
        raise ValueError(
            f"No DELIVERY modality option found in Kroger response for ZIP {zip_code}"
        )

    modality = delivery_option.get("modality", {})
    handoff = modality.get("handoffAddress", {})
    address = handoff.get("address", {})
    location = handoff.get("location", {})

    postal_code = address.get("postalCode") or modality.get("postalCode") or zip_code
    latitude = location.get("lat") if "lat" in location else modality.get("lat")
    longitude = location.get("lng") if "lng" in location else modality.get("lng")

    validated = handoff.get("validated")
    if validated is None:
        validated = modality.get("validated", True)

    normalized_context = {
        "postal_code": str(postal_code),
        "latitude": latitude,
        "longitude": longitude,
        "modality_type": "DELIVERY",
        "provider": delivery_option.get("provider", "kroger"),
        "fallback_fulfillment": delivery_option.get("fallbackFulfillment"),
        "fallback_destination": delivery_option.get("fallbackDestination"),
        "fulfillment": delivery_option.get("fulfillment", []),
        "destination_validated": bool(validated),
        "raw_delivery_option": delivery_option,
    }

    return normalized_context
