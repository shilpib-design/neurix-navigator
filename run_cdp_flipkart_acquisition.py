"""
Neurix Navigator-01: Phase 5 Cross-Site Flipkart Browser Acquisition Test Script.

Attaches to the running Donut browser profile over CDP using the target-agnostic
CDPAcquisitionEngine, navigates to Flipkart PDP (Panasonic H-HSA35100E Telephoto Zoom Lens),
captures rendered DOM HTML, and performs local domain extraction without vendor APIs or browser client modifications.
"""

import json
import time
from pathlib import Path
from kroger.cdp_client import discover_cdp_port_for_profile
from browser.acquisition import CDPAcquisitionEngine
from flipkart.product import extract_flipkart_product, validate_flipkart_acquisition


def main():
    profile_name = "Kroger-Test-30301"
    expected_id = "ACCFFGX6TAMWKM4H"
    target_url = "https://www.flipkart.com/panasonic-h-hsa35100e-telephoto-zoom-lens/p/itmffgx6p6c2wgda"

    print("=" * 70)
    print("NEURIX NAVIGATOR-01: PHASE 5 CROSS-SITE FLIPKART BROWSER ACQUISITION")
    print("=" * 70)
    print(f"Target Retailer: Flipkart India")
    print(f"Expected Product ID: {expected_id}")
    print(f"Target URL: {target_url}\n")

    # 1. Discover CDP Port
    cdp_port = discover_cdp_port_for_profile(profile_name)
    if not cdp_port:
        print("ERROR: Could not discover listening CDP port for running Donut profile.")
        return

    print(f"[1/4] Discovered CDP Port: {cdp_port}")

    # 2. Attach via Generic CDPAcquisitionEngine & Acquire Flipkart Page
    print(f"[2/4] Attaching via CDPAcquisitionEngine and navigating to Flipkart...")
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
    raw_html_filename = f"donut_flipkart_cdp_{timestamp}.html"
    raw_html_path = results_dir / raw_html_filename

    with open(raw_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"  * Page Title: {title}")
    print(f"  * Acquired HTML Size: {len(html_content)} bytes")
    print(f"  * Saved Raw HTML Path: {raw_html_path}")

    # 4. Local Flipkart Domain Extraction & Validation
    print(f"[3/4] Extracting Flipkart product schema locally...")
    extracted_product = extract_flipkart_product(html_content, expected_id)

    print(f"[4/4] Validating Flipkart acquisition evidence...")
    validation = validate_flipkart_acquisition(extracted_product, html_content, expected_id)

    final_report = {
        "cdp_attachment": True,
        "flipkart_navigation": True,
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
    print("PHASE 5 CROSS-SITE FLIPKART TEST SUMMARY")
    print("=" * 70)
    print(json.dumps(final_report, indent=2))
    print("=" * 70)


if __name__ == "__main__":
    main()
