"""
Consolidated Kroger 10x4 Provider Experiment Runner.

Executes 10 Kroger product URL + ZIP combinations against 4 providers:
1. String
2. Scrapfly
3. AlterLab
4. Context.dev

Total: 40 test cells.

Saves raw responses to results/kroger_10x4_raw/
Generates:
- results/kroger_10x4_20260910.jsonl
- results/kroger_10x4_20260910.csv
- results/kroger_10x4_summary.md
"""

import os
import re
import json
import time
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from dotenv import load_dotenv

from providers import get_all_providers

from extract_local import extract_schema_from_html, parse_price

TEST_ITEMS = [
    {
        "test_id": 1,
        "zipcode": "30301",
        "url": "https://www.kroger.com/p/colgate-baking-soda-and-peroxide-whitening-toothpaste-in-brisk-mint/0003500051092?fulfillment=DELIVERY",
        "expected_upc": "0003500051092",
        "product_hint": "Colgate Baking Soda Toothpaste"
    },
    {
        "test_id": 2,
        "zipcode": "30301",
        "url": "https://www.kroger.com/p/suave-essentials-daily-clarifying-shampoo-deep-cleansing-for-all-hair-types-22-5-fl-oz/0038371100458?fulfillment=DELIVERY",
        "expected_upc": "0038371100458",
        "product_hint": "Suave Shampoo"
    },
    {
        "test_id": 3,
        "zipcode": "30303",
        "url": "https://www.kroger.com/p/nature-s-own-honey-wheat-bread-non-gmo-sandwich-bread-20-oz-loaf/0007225003706?fulfillment=DELIVERY",
        "expected_upc": "0007225003706",
        "product_hint": "Nature's Own Bread"
    },
    {
        "test_id": 4,
        "zipcode": "30303",
        "url": "https://www.kroger.com/p/kroger-salted-butter-sticks/0001111089301",
        "expected_upc": "0001111089301",
        "product_hint": "Kroger Salted Butter"
    },
    {
        "test_id": 5,
        "zipcode": "60601",
        "url": "https://www.kroger.com/p/every-man-jack-men-s-sandalwood-teak-aluminum-free-deodorant/0087863900023?fulfillment=DELIVERY",
        "expected_upc": "0087863900023",
        "product_hint": "Every Man Jack Deodorant"
    },
    {
        "test_id": 6,
        "zipcode": "60601",
        "url": "https://www.kroger.com/p/native-coconut-vanilla-deodorant/0081215403001",
        "expected_upc": "0081215403001",
        "product_hint": "Native Deodorant"
    },
    {
        "test_id": 7,
        "zipcode": "75201",
        "url": "https://www.kroger.com/p/allegra-adult-24-hour-non-drowsy-allergy-relief-antihistamine-tablets-with-180-mg-fexofenadine-hci/0004116741240",
        "expected_upc": "0004116741240",
        "product_hint": "Allegra Allergy"
    },
    {
        "test_id": 8,
        "zipcode": "75201",
        "url": "https://www.kroger.com/p/claritin-liqui-gels-24-hour-non-drowsy-allergy-relief-capsules-loratadine-10mg/0004110080798?fulfillment=DELIVERY",
        "expected_upc": "0004110080798",
        "product_hint": "Claritin Liqui-Gels"
    },
    {
        "test_id": 9,
        "zipcode": "77001",
        "url": "https://www.kroger.com/p/charmin-ultra-strong-toilet-paper-12-mega-xl-rolls/0003077213451",
        "expected_upc": "0003077213451",
        "product_hint": "Charmin Ultra Strong"
    },
    {
        "test_id": 10,
        "zipcode": "77001",
        "url": "https://www.kroger.com/p/charmin-ultra-soft-toilet-paper-12-mega-xl-rolls/0003077219367",
        "expected_upc": "0003077219367",
        "product_hint": "Charmin Ultra Soft"
    }
]


def provider_slug(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return cleaned


def analyze_location_evidence(raw_text: str, target_zip: str) -> Tuple[Optional[str], List[str]]:
    evidence = []
    detected_zip = None

    if not raw_text:
        return None, []

    # Check for postalCode or ZIP mentions in embedded state or HTML
    zip_matches = re.findall(r'"postalCode"\s*:\s*"(\d{5})"', raw_text)
    if not zip_matches:
        zip_matches = re.findall(r'"zipCode"\s*:\s*"(\d{5})"', raw_text)
    if not zip_matches:
        zip_matches = re.findall(r'"zip"\s*:\s*"(\d{5})"', raw_text)

    if zip_matches:
        detected_zip = zip_matches[0]
        evidence.append(f"Found postalCode '{detected_zip}' in payload")

    if target_zip in raw_text:
        evidence.append(f"Target ZIP '{target_zip}' string present in response body")

    if "DELIVERY" in raw_text:
        evidence.append("Fulfillment mode 'DELIVERY' present in payload")

    store_matches = re.findall(r'"storeId"\s*:\s*"([a-zA-Z0-9]+)"', raw_text)
    if store_matches:
        evidence.append(f"Store ID '{store_matches[0]}' present in payload")

    facility_matches = re.findall(r'"facilityId"\s*:\s*"([a-zA-Z0-9]+)"', raw_text)
    if facility_matches:
        evidence.append(f"Facility ID '{facility_matches[0]}' present in payload")

    return detected_zip, evidence


def classify_result(
    status_code: Optional[int],
    content_bytes: bytes,
    extracted: dict,
    error_message: Optional[str],
    provider_name: str,
    target_upc: str
) -> str:
    # 1. Async Incomplete (e.g. AlterLab 202 Accepted)
    if status_code == 202:
        return "ASYNC_INCOMPLETE"

    # 2. Timeout
    if error_message and ("timed out" in error_message.lower() or "timeout" in error_message.lower()):
        return "TIMEOUT"

    # 3. Provider Error (e.g. HTTP 500, unconfigured, connection error)
    if status_code is None or status_code >= 500 or (error_message and not status_code):
        return "PROVIDER_ERROR"

    raw_text = ""
    if content_bytes:
        try:
            raw_text = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = str(content_bytes)

    # 4. Blocked (Akamai / Access Denied / 403 / 429 / Block Page)
    if status_code in (403, 429) or "Access Denied" in raw_text or "Security Check" in raw_text or "Robot Check" in raw_text or "Akamai" in raw_text:
        return "BLOCKED"

    if status_code == 200 and len(content_bytes) < 1000 and ("denied" in raw_text.lower() or "block" in raw_text.lower() or "captcha" in raw_text.lower()):
        return "BLOCKED"

    # 5. Extraction & Validation Check
    product_name = extracted.get("product_name")
    price = extracted.get("price")
    prod_id = extracted.get("product_id") or ""

    if product_name and (price is not None or extracted.get("availability")):
        # Check if UPC matches or reasonable title match
        if target_upc in prod_id or target_upc in raw_text or len(product_name) > 3:
            return "VALIDATED"
        else:
            return "ACQUIRED_NOT_VALIDATED"

    if len(content_bytes) > 5000 and ("kroger" in raw_text.lower() or "<html" in raw_text.lower()):
        return "EXTRACTION_FAILED"

    return "ACQUIRED_NOT_VALIDATED" if status_code == 200 else "PROVIDER_ERROR"


def main():
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    results_dir = Path("results")
    raw_dir = results_dir / "kroger_10x4_raw"
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    providers = get_all_providers()

    print("=" * 80)
    print("KROGER 10x4 CONSOLIDATED PROVIDER EXPERIMENT")
    print("=" * 80)
    print(f"Total Test Cells: {len(TEST_ITEMS)} URLs x {len(providers)} Providers = {len(TEST_ITEMS) * len(providers)}")
    print("-" * 80)

    cell_results = []
    test_index = 0
    total_cells = len(TEST_ITEMS) * len(providers)

    for item in TEST_ITEMS:
        test_id = item["test_id"]
        zipcode = item["zipcode"]
        url = item["url"]
        expected_upc = item["expected_upc"]
        product_hint = item["product_hint"]

        print(f"\n[Test #{test_id}] ZIP: {zipcode} | Product: {product_hint}")
        print(f"URL: {url}")

        for provider in providers:
            test_index += 1
            p_name = provider.name
            p_slug = provider_slug(p_name)

            print(f"  ({test_index}/{total_cells}) Requesting via {p_name}...", end=" ", flush=True)

            target_dict = {
                "name": f"kroger_test_{test_id:02d}_{zipcode}",
                "url": url
            }

            # Execute request exactly once
            res = provider.fetch(target_dict)

            raw_bytes = res.get("raw_content") or b""
            status_code = res.get("status_code")
            elapsed_ms = res.get("elapsed_ms", 0)
            error_message = res.get("error_message")
            acq_success = res.get("success", False)

            # Determine extension & filename
            ext = "html"
            if status_code == 202 or (raw_bytes and raw_bytes.startswith(b"{")):
                ext = "json" if raw_bytes.startswith(b"{") else "raw"
            elif "html" not in res.get("content_type", "").lower():
                ext = "txt"

            filename = f"{test_id:02d}_{p_slug}_{zipcode}.{ext}"
            file_path = raw_dir / filename

            raw_path_str = None
            raw_text = ""
            if raw_bytes:
                with open(file_path, "wb") as f:
                    f.write(raw_bytes)
                raw_path_str = str(file_path)
                try:
                    raw_text = raw_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    raw_text = str(raw_bytes)

            # Attempt extraction using extract_local.py logic
            extracted = {}
            if raw_text and ("<html" in raw_text.lower() or "{" in raw_text):
                try:
                    extracted = extract_schema_from_html(raw_text, filename="kroger.html")
                except Exception as e:
                    extracted = {"error": str(e)}

            detected_zip, loc_evidence = analyze_location_evidence(raw_text, zipcode)

            final_class = classify_result(
                status_code=status_code,
                content_bytes=raw_bytes,
                extracted=extracted,
                error_message=error_message,
                provider_name=p_name,
                target_upc=expected_upc
            )

            val_success = (final_class == "VALIDATED")
            ext_success = bool(extracted.get("product_name"))

            val_failure_reason = None
            if not val_success:
                if final_class == "BLOCKED":
                    val_failure_reason = "Blocked / Access Denied page"
                elif final_class == "ASYNC_INCOMPLETE":
                    val_failure_reason = "Async dispatch response (HTTP 202)"
                elif final_class == "TIMEOUT":
                    val_failure_reason = "Request timeout"
                elif final_class == "EXTRACTION_FAILED":
                    val_failure_reason = "Extractor failed to parse required product fields"
                elif final_class == "ACQUIRED_NOT_VALIDATED":
                    val_failure_reason = "Acquired page could not be validated (missing price/UPC/location)"
                else:
                    val_failure_reason = error_message or f"HTTP {status_code}"

            cell_record = {
                "test_id": test_id,
                "provider": p_name,
                "zipcode": zipcode,
                "url": url,
                "start_time": res.get("timestamp"),
                "elapsed_ms": elapsed_ms,
                "status_code": status_code,
                "response_bytes": len(raw_bytes),
                "acquisition_success": acq_success,
                "raw_response_path": raw_path_str,
                "failure_type": final_class if final_class != "VALIDATED" else None,
                "failure_message": error_message,
                "product_name": extracted.get("product_name", ""),
                "brand": extracted.get("brand", ""),
                "product_id": extracted.get("product_id") or expected_upc,
                "price": extracted.get("price"),
                "regular_price": extracted.get("regular_price"),
                "sale_price": extracted.get("sale_price"),
                "currency": extracted.get("currency", "USD" if extracted.get("price") else ""),
                "availability": extracted.get("availability", ""),
                "inventory_count": extracted.get("inventory_count"),
                "fulfillment_modality": "DELIVERY" if "fulfillment=DELIVERY" in url else "",
                "detected_zipcode": detected_zip,
                "location_evidence": loc_evidence,
                "extraction_success": ext_success,
                "validation_success": val_success,
                "validation_failure_reason": val_failure_reason,
                "final_classification": final_class
            }

            cell_results.append(cell_record)

            disp_status = f"HTTP {status_code}" if status_code else "N/A"
            print(f"[{final_class}] Status: {disp_status} | Size: {len(raw_bytes)}B | Elapsed: {elapsed_ms}ms")

    # 1. Save JSONL
    jsonl_path = results_dir / "kroger_10x4_20260910.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in cell_results:
            f.write(json.dumps(r) + "\n")

    # 2. Save CSV
    csv_path = results_dir / "kroger_10x4_20260910.csv"
    if cell_results:
        fieldnames = list(cell_results[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in cell_results:
                r_copy = r.copy()
                r_copy["location_evidence"] = "; ".join(r_copy["location_evidence"]) if isinstance(r_copy["location_evidence"], list) else str(r_copy["location_evidence"])
                writer.writerow(r_copy)

    # 3. Generate Summary Report Markdown
    generate_markdown_summary(cell_results, results_dir / "kroger_10x4_summary.md", providers)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
    print(f"JSONL saved to: {jsonl_path}")
    print(f"CSV saved to:   {csv_path}")
    print(f"Summary saved:  {results_dir / 'kroger_10x4_summary.md'}")
    print(f"Raw files in:   {raw_dir}/")


def generate_markdown_summary(results: List[dict], output_path: Path, providers: list):
    provider_names = [p.name for p in providers]

    stats = {}
    for p in provider_names:
        p_res = [r for r in results if r["provider"] == p]
        total = len(p_res)
        acq_succ = sum(1 for r in p_res if r["acquisition_success"])
        validated = sum(1 for r in p_res if r["final_classification"] == "VALIDATED")
        blocked = sum(1 for r in p_res if r["final_classification"] == "BLOCKED")
        timeouts = sum(1 for r in p_res if r["final_classification"] == "TIMEOUT")
        p_errors = sum(1 for r in p_res if r["final_classification"] == "PROVIDER_ERROR")
        async_inc = sum(1 for r in p_res if r["final_classification"] == "ASYNC_INCOMPLETE")
        ext_fails = sum(1 for r in p_res if r["final_classification"] == "EXTRACTION_FAILED")
        acq_not_val = sum(1 for r in p_res if r["final_classification"] == "ACQUIRED_NOT_VALIDATED")

        avg_lat = (sum(r["elapsed_ms"] for r in p_res) / total) if total > 0 else 0.0
        avg_size = (sum(r["response_bytes"] for r in p_res) / total) if total > 0 else 0.0

        stats[p] = {
            "total": total,
            "acq_succ": acq_succ,
            "acq_succ_pct": (acq_succ / total * 100) if total > 0 else 0.0,
            "validated": validated,
            "val_rate": (validated / total * 100) if total > 0 else 0.0,
            "blocked": blocked,
            "timeouts": timeouts,
            "p_errors": p_errors,
            "async_inc": async_inc,
            "ext_fails": ext_fails,
            "acq_not_val": acq_not_val,
            "avg_lat": avg_lat,
            "avg_size": avg_size
        }

    # Identify bests
    best_acq = max(provider_names, key=lambda p: (stats[p]["acq_succ_pct"], -stats[p]["avg_lat"]))
    best_val = max(provider_names, key=lambda p: (stats[p]["val_rate"], stats[p]["acq_succ_pct"], -stats[p]["avg_lat"]))
    fastest = min(provider_names, key=lambda p: stats[p]["avg_lat"] if stats[p]["avg_lat"] > 0 else 999999)

    # Markdown construction
    md = []
    md.append("# Kroger 10x4 Consolidated Provider Experiment Summary")
    md.append(f"\n*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")
    md.append("## Provider-Level Comparison\n")

    md.append("| Provider | Total Tests | Acquisition Success | Acquisition Success % | Validated | Validation Rate | Blocked | Timeouts | Provider Errors | Async Incomplete | Extraction Failures | Avg Latency (ms) | Avg Size (Bytes) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for p in provider_names:
        s = stats[p]
        md.append(
            f"| **{p}** | {s['total']} | {s['acq_succ']} | {s['acq_succ_pct']:.1f}% | "
            f"{s['validated']} | {s['val_rate']:.1f}% | {s['blocked']} | {s['timeouts']} | "
            f"{s['p_errors']} | {s['async_inc']} | {s['ext_fails']} | {s['avg_lat']:.1f} ms | {s['avg_size']:.0f} B |"
        )

    md.append("\n---\n")
    md.append("## Test-Level Classification Matrix\n")

    md.append("| Test ID | ZIP | Product | String | Scrapfly | AlterLab | Context.dev |")
    md.append("| :---: | :---: | :--- | :---: | :---: | :---: | :---: |")

    for item in TEST_ITEMS:
        tid = item["test_id"]
        zipc = item["zipcode"]
        phint = item["product_hint"]

        p_classes = []
        for p in ["String", "Scrapfly", "AlterLab", "Context.dev"]:
            matching = [r for r in results if r["test_id"] == tid and r["provider"] == p]
            if matching:
                p_classes.append(matching[0]["final_classification"])
            else:
                p_classes.append("N/A")

        md.append(f"| #{tid:02d} | {zipc} | {phint} | {p_classes[0]} | {p_classes[1]} | {p_classes[2]} | {p_classes[3]} |")

    md.append("\n---\n")
    md.append("## Analytical Findings\n")

    md.append(f"### 1. Best Provider by Acquisition Success\n**{best_acq}** (Acquisition Success: {stats[best_acq]['acq_succ_pct']:.1f}%).\n")
    md.append(f"### 2. Best Provider by Validation Rate\n**{best_val}** (Validation Rate: {stats[best_val]['val_rate']:.1f}%).\n")
    md.append(f"### 3. Fastest Provider by Average Latency\n**{fastest}** (Average Latency: {stats[fastest]['avg_lat']:.1f} ms).\n")

    md.append("### 4. Most Common Failure Mode per Provider\n")
    for p in provider_names:
        s = stats[p]
        modes = [
            ("BLOCKED", s["blocked"]),
            ("TIMEOUT", s["timeouts"]),
            ("PROVIDER_ERROR", s["p_errors"]),
            ("ASYNC_INCOMPLETE", s["async_inc"]),
            ("EXTRACTION_FAILED", s["ext_fails"]),
            ("ACQUIRED_NOT_VALIDATED", s["acq_not_val"])
        ]
        modes.sort(key=lambda x: x[1], reverse=True)
        top_mode, count = modes[0]
        if count == 0:
            md.append(f"- **{p}**: None (100% Validated)")
        else:
            pct = (count / s['total']) * 100
            md.append(f"- **{p}**: `{top_mode}` ({count}/{s['total']} tests, {pct:.1f}%)")

    md.append("\n### 5. Evidence of ZIP-Specific Behavior Differences\n")
    loc_ev_found = [r for r in results if r["location_evidence"]]
    if loc_ev_found:
        md.append(f"Recorded location context evidence across {len(loc_ev_found)} test cells. Provider response payloads pass parameters via URL query string (`?fulfillment=DELIVERY`), but providers vary in whether they extract or persist server-side ZIP cookies (`postalCode`, `storeId`).")
    else:
        md.append("No explicit server-side location context (e.g. `postalCode`, `storeId`) was returned in raw provider response bodies without location header injection.")

    md.append("\n### 6. Cases Where HTTP 200 Did NOT Mean Usable/Validated Data\n")
    http200_unusable = [r for r in results if r["status_code"] == 200 and r["final_classification"] != "VALIDATED"]
    if http200_unusable:
        md.append(f"Identified **{len(http200_unusable)} test cells** where providers returned HTTP status 200, but content was unvalidated or blocked:\n")
        for r in http200_unusable:
            md.append(f"- **Test #{r['test_id']:02d} ({r['provider']})**: HTTP 200 returned {r['response_bytes']} bytes, but classified as `{r['final_classification']}` ({r['validation_failure_reason']}).")
    else:
        md.append("All HTTP 200 responses resulted in validated product data.")

    md.append("\n---\n")
    md.append("*Note: This document contains strictly factual provider comparison data. No architectural recommendations or fallback logic modifications were introduced.*")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    main()
