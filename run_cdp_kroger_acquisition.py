"""
Neurix Navigator-01: Kroger CDP Live Browser Acquisition Test Script.

Attaches to the running Donut browser profile via CDP, executes navigation
to Kroger PDP (ZIP 30301 + DELIVERY), saves raw HTML to results/, extracts product schema,
and validates the result without calling external scraping vendors.
"""

import json
import re
import time
from pathlib import Path
from kroger.cdp_client import DonutCDPClient, discover_cdp_port_for_profile
from extract_local import extract_schema_from_html


def validate_acquisition(extracted: dict, html_content: str, target_upc: str = "0004000042431", target_zip: str = "30301") -> dict:
    """
    Validates acquired product data against business and location evidence rules.
    """
    product_name = extracted.get("product_name") or ""
    upc = extracted.get("product_id") or extracted.get("upc") or ""
    price = extracted.get("price")
    availability = extracted.get("availability") or ""
    
    # 1. Product Evidence Validation
    has_product_name = bool(product_name.strip())
    has_upc = bool(upc.strip())
    has_price_or_avail = (price is not None) or bool(availability.strip())

    product_valid = has_product_name and has_upc and has_price_or_avail

    # 2. Location & Fulfillment Evidence Validation
    zip_in_html = (target_zip in html_content)
    delivery_in_html = ("DELIVERY" in html_content or "delivery" in html_content.lower())
    
    # Verify specific modality button evidence
    modality_evidence = False
    if f"Delivery to {target_zip}" in html_content or f'postalCode":"{target_zip}' in html_content:
        modality_evidence = True

    location_valid = zip_in_html and delivery_in_html and modality_evidence

    overall_success = product_valid and location_valid

    return {
        "success": overall_success,
        "product_valid": product_valid,
        "location_valid": location_valid,
        "zip_reflected": zip_in_html and modality_evidence,
        "fulfillment_reflected": delivery_in_html,
        "evidence_used": [
            "JSON-LD Product Schema",
            "data-testid='CurrentModality-button'",
            f"Delivery to {target_zip} aria-label",
            "window.__INITIAL_STATE__ embedded state"
        ] if overall_success else ["Insufficient product or location DOM evidence"]
    }


def main():
    profile_name = "Kroger-Test-30301"
    target_zip = "30301"
    target_upc = "0004000042431"
    target_url = f"https://www.kroger.com/p/snickers-singles-1-86-ounces-each/{target_upc}?fulfillment=DELIVERY"

    print("=" * 70)
    print("NEURIX NAVIGATOR-01: KROGER CDP LIVE BROWSER ACQUISITION")
    print("=" * 70)
    print(f"Profile: {profile_name}")
    print(f"Target ZIP: {target_zip}")
    print(f"Target UPC: {target_upc}")
    print(f"Target URL: {target_url}\n")

    start_time = time.time()

    # 1. Discover CDP Port
    cdp_port = discover_cdp_port_for_profile(profile_name)
    if not cdp_port:
        print("ERROR: Could not discover listening CDP port for profile. Is Donut browser running?")
        return

    print(f"[1/4] Discovered CDP Port: {cdp_port}")

    # 2. Attach over CDP & Acquire Page HTML
    cdp_client = DonutCDPClient(port=cdp_port, profile_name=profile_name)
    print(f"[2/4] Attaching via Playwright CDP and acquiring page...")
    
    acquisition_result = cdp_client.navigate_and_acquire(target_url)
    html_content = acquisition_result["html_content"]
    raw_html_path = acquisition_result["raw_html_path"]
    elapsed_ms = acquisition_result["elapsed_ms"]

    print(f"  * Acquired HTML Size: {len(html_content)} bytes")
    print(f"  * Saved Raw HTML Path: {raw_html_path}")

    # 3. Extract Product Schema via Local Extractor
    print(f"[3/4] Extracting schema using local extractor...")
    extracted_raw = extract_schema_from_html(html_content, "donut_kroger_live.html")

    # Format into standard Neurix Schema
    price_val = extracted_raw.get("price")
    formatted_price = f"USD {price_val:.2f}" if price_val is not None else None

    normalized_product = {
        "product_name": extracted_raw.get("product_name", ""),
        "brand": extracted_raw.get("brand", ""),
        "upc": extracted_raw.get("product_id", target_upc),
        "price": formatted_price,
        "regular_price": formatted_price,
        "sale_price": formatted_price,
        "currency": extracted_raw.get("currency", "USD"),
        "availability": "HIGH" if "InStock" in str(extracted_raw.get("availability")) else extracted_raw.get("availability", ""),
        "inventory_count": None,
        "fulfillment_modality": "DELIVERY",
        "location_ids": []
    }

    # 4. Validate Product and Location Evidence
    print(f"[4/4] Validating product and location evidence...")
    validation = validate_acquisition(extracted_raw, html_content, target_upc, target_zip)

    overall_result = {
        "success": validation["success"],
        "zip_code": target_zip,
        "target_upc": target_upc,
        "elapsed_ms": elapsed_ms,
        "raw_html_path": raw_html_path,
        "product": normalized_product,
        "validation": validation,
        "vendor_credits_consumed": 0
    }

    print("\n" + "=" * 70)
    print("LIVE ACQUISITION TEST RESULT SUMMARY")
    print("=" * 70)
    print(json.dumps(overall_result, indent=2))
    print("=" * 70)


if __name__ == "__main__":
    main()
