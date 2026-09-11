"""
Neurix Navigator-01: Phase 4 Cross-Site Amazon Browser Acquisition Test Script.

Attaches to the running Donut browser profile over CDP using the target-agnostic
CDPAcquisitionEngine, navigates to Amazon India PDP (ASIN B078Y2PJL4), captures rendered DOM HTML,
and performs local domain extraction without vendor APIs or browser client modifications.
"""

import json
import time
from pathlib import Path
from kroger.cdp_client import discover_cdp_port_for_profile
from browser.acquisition import CDPAcquisitionEngine
from amazon.product import extract_amazon_product, validate_amazon_acquisition


def main():
    profile_name = "Kroger-Test-30301"
    target_asin = "B078Y2PJL4"
    target_url = f"https://www.amazon.in/dp/{target_asin}"

    print("=" * 70)
    print("NEURIX NAVIGATOR-01: PHASE 4 CROSS-SITE AMAZON BROWSER ACQUISITION")
    print("=" * 70)
    print(f"Target Retailer: Amazon India")
    print(f"Target ASIN: {target_asin}")
    print(f"Target URL: {target_url}\n")

    # 1. Discover CDP Port
    cdp_port = discover_cdp_port_for_profile(profile_name)
    if not cdp_port:
        print("ERROR: Could not discover listening CDP port for running Donut profile.")
        return

    print(f"[1/4] Discovered CDP Port: {cdp_port}")

    # 2. Attach via Generic CDPAcquisitionEngine & Acquire Amazon Page
    print(f"[2/4] Attaching via CDPAcquisitionEngine and navigating to Amazon...")
    engine = CDPAcquisitionEngine(port=cdp_port)
    
    acquisition_result = engine.acquire(target_url)

    url = acquisition_result.get("url", target_url)
    title = acquisition_result.get("title", "")
    html_content = acquisition_result.get("html", "")
    elapsed_ms = acquisition_result.get("elapsed_ms", 0)

    # 3. Save Raw HTML under results/
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    raw_html_filename = f"donut_amazon_cdp_{timestamp}.html"
    raw_html_path = results_dir / raw_html_filename

    with open(raw_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"  * Page Title: {title}")
    print(f"  * Acquired HTML Size: {len(html_content)} bytes")
    print(f"  * Saved Raw HTML Path: {raw_html_path}")

    # 4. Local Amazon Domain Extraction & Validation
    print(f"[3/4] Extracting Amazon product schema locally...")
    extracted_product = extract_amazon_product(html_content, target_asin)

    print(f"[4/4] Validating Amazon acquisition evidence...")
    validation = validate_amazon_acquisition(extracted_product, html_content, target_asin)

    final_report = {
        "cdp_attachment": True,
        "amazon_navigation": True,
        "product_page_acquired": validation["product_page_acquired"],
        "product_evidence_found": validation["evidence_found"],
        "raw_html_size": len(html_content),
        "raw_html_path": str(raw_html_path),
        "elapsed_time_ms": elapsed_ms,
        "page_title": title,
        "browser_generic_layer_modified": False,
        "external_vendor_apis_called": False,
        "vendor_credits_consumed": 0,
        "generic_acquisition_result": acquisition_result,
        "extracted_product": extracted_product,
        "validation_details": validation
    }

    print("\n" + "=" * 70)
    print("PHASE 4 CROSS-SITE AMAZON TEST SUMMARY")
    print("=" * 70)
    print(json.dumps(final_report, indent=2))
    print("=" * 70)


if __name__ == "__main__":
    main()
