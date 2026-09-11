"""
Local Offline Telemetry Observation Example.

Demonstrates recording mocked acquisition attempts across Kroger, Amazon, Flipkart,
and vendor strategies, persisting to JSONL, and calculating outcome metrics.
"""

import json
import os
from pathlib import Path
from telemetry.models import AcquisitionObservation, ObservationStatus
from telemetry.recorder import AcquisitionObservationRecorder, calculate_metrics


def main():
    print("=" * 70)
    print("NEURIX ACQUISITION TELEMETRY & OUTCOME LAYER - OFFLINE EXAMPLE")
    print("=" * 70)

    recorder = AcquisitionObservationRecorder()
    observations = []

    # 1. Kroger/browser: validated, 2676 ms, cost 0
    obs1 = AcquisitionObservation(
        target="kroger",
        acquisition_method="browser_cdp",
        url="https://www.kroger.com/p/snickers-singles-1-86-ounces-each/0004000042431?fulfillment=DELIVERY",
        parameters={"postal_code": "30301", "upc": "0004000042431"},
        required_fields=["product_name", "price", "availability"],
        acquisition_success=True,
        elapsed_ms=2676,
        bytes=975680,
        raw_html_path="results/donut_kroger_cdp_20260910_182522.html",
        http_status=200,
        extraction_success=True,
        extracted_fields=["product_name", "brand", "upc", "price", "availability"],
        validated=True,
        evidence=["JSON-LD Product Schema", "Delivery to 30301 aria-label"],
        acquisition_cost=0.0,
        vendor_credits=0.0,
        currency="USD",
        final_status=ObservationStatus.VALIDATED
    )
    observations.append(obs1)

    # 2. Amazon/browser: validated, 5387 ms, cost 0
    obs2 = AcquisitionObservation(
        target="amazon",
        acquisition_method="browser_cdp",
        url="https://www.amazon.in/dp/B078Y2PJL4",
        parameters={"asin": "B078Y2PJL4"},
        required_fields=["product_name", "price"],
        acquisition_success=True,
        elapsed_ms=5387,
        bytes=614022,
        raw_html_path="results/donut_amazon_cdp_20260910_183935.html",
        http_status=200,
        extraction_success=True,
        extracted_fields=["product_name", "brand", "asin", "price", "availability"],
        validated=True,
        evidence=["ASIN B078Y2PJL4 match in DOM", "Price: INR 8,396.00"],
        acquisition_cost=0.0,
        vendor_credits=0.0,
        currency="USD",
        final_status=ObservationStatus.VALIDATED
    )
    observations.append(obs2)

    # 3. Flipkart/browser: validated, 3969 ms, cost 0
    obs3 = AcquisitionObservation(
        target="flipkart",
        acquisition_method="browser_cdp",
        url="https://www.flipkart.com/panasonic-h-hsa35100e-telephoto-zoom-lens/p/itmffgx6p6c2wgda",
        parameters={"product_id": "ACCFFGX6TAMWKM4H"},
        required_fields=["product_name", "price"],
        acquisition_success=True,
        elapsed_ms=3969,
        bytes=344400,
        raw_html_path="results/donut_flipkart_cdp_20260910_184122.html",
        http_status=200,
        extraction_success=True,
        extracted_fields=["product_name", "brand", "product_id", "price", "availability"],
        validated=True,
        evidence=["Panasonic / H-HSA35100E evidence found in DOM"],
        acquisition_cost=0.0,
        vendor_credits=0.0,
        currency="USD",
        final_status=ObservationStatus.VALIDATED
    )
    observations.append(obs3)

    # 4. Kroger/vendor: mocked acquisition with non-zero cost and successful validation
    obs4 = AcquisitionObservation(
        target="kroger",
        acquisition_method="vendor_api:scrapfly",
        url="https://www.kroger.com/p/snickers-singles/0004000042431",
        parameters={"postal_code": "30301"},
        required_fields=["product_name", "price"],
        acquisition_success=True,
        elapsed_ms=1850,
        bytes=512000,
        raw_html_path="results/scrapfly_kroger_20260910.html",
        http_status=200,
        extraction_success=True,
        extracted_fields=["product_name", "price"],
        validated=True,
        evidence=["Scrapfly JSON payload"],
        acquisition_cost=0.005,
        vendor_credits=1.0,
        currency="USD",
        final_status=ObservationStatus.VALIDATED
    )
    observations.append(obs4)

    # 5. Kroger/failed: mocked acquisition failure
    obs5 = AcquisitionObservation(
        target="kroger",
        acquisition_method="browser_cdp",
        url="https://www.kroger.com/p/invalid-product/0000000000000",
        parameters={"postal_code": "00000"},
        required_fields=["product_name", "price"],
        acquisition_success=False,
        elapsed_ms=1200,
        bytes=0,
        raw_html_path=None,
        http_status=404,
        acquisition_error_code="ACQUISITION_FAILED",
        acquisition_error_message="HTTP 404 Product Not Found",
        extraction_success=False,
        validated=False,
        acquisition_cost=0.0,
        vendor_credits=0.0,
        currency="USD",
        final_status=ObservationStatus.ACQUISITION_FAILED
    )
    observations.append(obs5)

    # Persist to JSONL file
    test_jsonl_path = "results/test_observations_example.jsonl"
    if os.path.exists(test_jsonl_path):
        os.remove(test_jsonl_path)

    for obs in observations:
        recorder.save_to_jsonl(obs, file_path=test_jsonl_path)

    print(f"Recorded {len(observations)} observations into {test_jsonl_path}")

    # Calculate Summary Metrics
    metrics = calculate_metrics(observations)

    print("\n" + "=" * 70)
    print("TELEMETRY METRICS SUMMARY")
    print("=" * 70)
    print(f"Total Attempts:               {metrics['total_attempts']}")
    print(f"Successful Acquisitions:       {metrics['successful_acquisitions']}")
    print(f"Validated Results:             {metrics['validated_results']}")
    print(f"Success Rate:                 {metrics['success_rate'] * 100:.1f}%")
    print(f"Validation Rate:              {metrics['validation_rate'] * 100:.1f}%")
    print(f"Average Latency:              {metrics['average_latency_ms']} ms")
    print(f"Total Acquisition Cost:       ${metrics['total_acquisition_cost']:.4f}")
    print(f"Cost per Validated Result:    ${metrics['cost_per_validated_result']:.6f}")
    print("=" * 70)

    # Clean up test output file
    if os.path.exists(test_jsonl_path):
        os.remove(test_jsonl_path)


if __name__ == "__main__":
    main()
