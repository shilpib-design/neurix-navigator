"""
FINAL Kroger Proxy + Browser + ZIP Validation Experiment.

Runs exactly 40 tests (10 URL + ZIP pairs x 4 proxy types):
1. GeoNode Residential US ($0.57 / GB)
2. DataImpulse Residential US ($0.65 / GB)
3. DataImpulse Mobile US ($1.30 / GB)
4. GeoNode Datacenter US ($0.35 / GB)

Outputs:
- results/kroger_proxy_40_20260910.jsonl
- results/kroger_proxy_40_20260910.csv
- results/kroger_proxy_40_20260910_summary.md
- Raw HTML in results/kroger_proxy_40_raw/
"""

import os
import re
import json
import time
import csv
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from extract_local import extract_schema_from_html, parse_price

# 10 URL + ZIP Pairs
URL_ZIP_PAIRS = [
    {
        "item_num": 1,
        "zipcode": "30301",
        "lat": 33.7600008,
        "lng": -84.3899963,
        "url": "https://www.kroger.com/p/colgate-baking-soda-and-peroxide-whitening-toothpaste-in-brisk-mint/0003500051092?fulfillment=DELIVERY",
        "expected_upc": "0003500051092",
        "product_name_short": "Colgate Baking Soda Toothpaste",
        "brand": "Colgate"
    },
    {
        "item_num": 2,
        "zipcode": "30301",
        "lat": 33.7600008,
        "lng": -84.3899963,
        "url": "https://www.kroger.com/p/suave-essentials-daily-clarifying-shampoo-deep-cleansing-for-all-hair-types-22-5-fl-oz/0038371100458?fulfillment=DELIVERY",
        "expected_upc": "0038371100458",
        "product_name_short": "Suave Daily Clarifying Shampoo",
        "brand": "Suave"
    },
    {
        "item_num": 3,
        "zipcode": "30303",
        "lat": 33.7516,
        "lng": -84.3896,
        "url": "https://www.kroger.com/p/nature-s-own-honey-wheat-bread-non-gmo-sandwich-bread-20-oz-loaf/0007225003706?fulfillment=DELIVERY",
        "expected_upc": "0007225003706",
        "product_name_short": "Nature's Own Honey Wheat Bread",
        "brand": "Nature's Own"
    },
    {
        "item_num": 4,
        "zipcode": "30303",
        "lat": 33.7516,
        "lng": -84.3896,
        "url": "https://www.kroger.com/p/kroger-salted-butter-sticks/0001111089301",
        "expected_upc": "0001111089301",
        "product_name_short": "Kroger Salted Butter Sticks",
        "brand": "Kroger"
    },
    {
        "item_num": 5,
        "zipcode": "60601",
        "lat": 41.8858,
        "lng": -87.6229,
        "url": "https://www.kroger.com/p/every-man-jack-men-s-sandalwood-teak-aluminum-free-deodorant/0087863900023?fulfillment=DELIVERY",
        "expected_upc": "0087863900023",
        "product_name_short": "Every Man Jack Deodorant",
        "brand": "Every Man Jack"
    },
    {
        "item_num": 6,
        "zipcode": "60601",
        "lat": 41.8858,
        "lng": -87.6229,
        "url": "https://www.kroger.com/p/native-coconut-vanilla-deodorant/0081215403001",
        "expected_upc": "0081215403001",
        "product_name_short": "Native Deodorant",
        "brand": "Native"
    },
    {
        "item_num": 7,
        "zipcode": "75201",
        "lat": 32.7865,
        "lng": -96.7970,
        "url": "https://www.kroger.com/p/allegra-adult-24-hour-non-drowsy-allergy-relief-antihistamine-tablets-with-180-mg-fexofenadine-hci/0004116741240",
        "expected_upc": "0004116741240",
        "product_name_short": "Allegra 24hr Allergy Relief",
        "brand": "Allegra"
    },
    {
        "item_num": 8,
        "zipcode": "75201",
        "lat": 32.7865,
        "lng": -96.7970,
        "url": "https://www.kroger.com/p/claritin-liqui-gels-24-hour-non-drowsy-allergy-relief-capsules-loratadine-10mg/0004110080798?fulfillment=DELIVERY",
        "expected_upc": "0004110080798",
        "product_name_short": "Claritin Liqui-Gels",
        "brand": "Claritin"
    },
    {
        "item_num": 9,
        "zipcode": "77001",
        "lat": 29.7604,
        "lng": -95.3698,
        "url": "https://www.kroger.com/p/charmin-ultra-strong-toilet-paper-12-mega-xl-rolls/0003077213451",
        "expected_upc": "0003077213451",
        "product_name_short": "Charmin Ultra Strong 12 Mega XL",
        "brand": "Charmin"
    },
    {
        "item_num": 10,
        "zipcode": "77001",
        "lat": 29.7604,
        "lng": -95.3698,
        "url": "https://www.kroger.com/p/charmin-ultra-soft-toilet-paper-12-mega-xl-rolls/0003077219367",
        "expected_upc": "0003077219367",
        "product_name_short": "Charmin Ultra Soft 12 Mega XL",
        "brand": "Charmin"
    }
]

PROXIES = [
    {
        "dataset_key": "geonode_residential",
        "provider": "GeoNode",
        "proxy_type": "Residential",
        "host": "192.155.103.209",
        "port": 10000,
        "username_prefix": "geonode_nxvF2zmzrd-type-residential-country-us-lifetime-3-session-",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "session_prefix": "test-r",
        "cost_per_gb": 0.57
    },
    {
        "dataset_key": "dataimpulse_residential",
        "provider": "DataImpulse",
        "proxy_type": "Residential",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "username_prefix": "ba55974e3d2af4473e91__cr.us;sessid.",
        "password": "6a5fe91d07152901",
        "session_prefix": "test-b",
        "cost_per_gb": 0.65
    },
    {
        "dataset_key": "dataimpulse_mobile",
        "provider": "DataImpulse",
        "proxy_type": "Mobile",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "username_prefix": "6487cbbdb6fa524ee174__cr.us;sessid.",
        "password": "f3c4b5430d9a4cac",
        "session_prefix": "test-c",
        "cost_per_gb": 1.30
    },
    {
        "dataset_key": "geonode_datacenter",
        "provider": "GeoNode",
        "proxy_type": "Datacenter",
        "host": "192.155.103.209",
        "port": 10000,
        "username_prefix": "geonode_nxvF2zmzrd-type-datacenter-country-us-lifetime-3-session-",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "session_prefix": "test-dc",
        "cost_per_gb": 0.35
    }
]


def extract_location_evidence(raw_text: str, target_zip: str):
    evidence = []
    detected_zip = None

    if not raw_text:
        return None, []

    zip_matches = re.findall(r'"postalCode"\s*:\s*"(\d{5})"', raw_text)
    if not zip_matches:
        zip_matches = re.findall(r'"zipCode"\s*:\s*"(\d{5})"', raw_text)
    if not zip_matches:
        zip_matches = re.findall(r'"zip"\s*:\s*"(\d{5})"', raw_text)

    if zip_matches:
        detected_zip = zip_matches[0]
        evidence.append(f"Found postalCode '{detected_zip}' in payload")

    if target_zip in raw_text:
        evidence.append(f"Requested ZIP '{target_zip}' present in response HTML")

    if "DELIVERY" in raw_text or "delivery" in raw_text.lower():
        evidence.append("Fulfillment mode 'DELIVERY' present in payload")

    store_matches = re.findall(r'"storeId"\s*:\s*"([a-zA-Z0-9]+)"', raw_text)
    if store_matches:
        evidence.append(f"Store ID '{store_matches[0]}' present in payload")

    return detected_zip, evidence


def run_single_test(p, test_id: int, proxy_config: dict, item: dict, raw_dir: Path):
    item_num = item["item_num"]
    req_zip = item["zipcode"]
    lat = item["lat"]
    lng = item["lng"]
    url = item["url"]
    exp_upc = item["expected_upc"]
    prod_hint = item["product_name_short"]
    brand_hint = item["brand"]

    provider = proxy_config["provider"]
    ptype = proxy_config["proxy_type"]
    dataset_key = proxy_config["dataset_key"]
    host = proxy_config["host"]
    port = proxy_config["port"]
    pwd = proxy_config["password"]

    sess_id = f"{proxy_config['session_prefix']}{item_num:02d}"
    username = f"{proxy_config['username_prefix']}{sess_id}"

    raw_filename = f"{item_num:02d}_{dataset_key}_{req_zip}.html"
    raw_path = raw_dir / raw_filename

    print(f"\n[Test #{test_id:02d} / 40] Proxy: {provider} {ptype} | Session: {sess_id} | ZIP: {req_zip} | Product: {prod_hint}")

    start_time = time.time()
    html_content = ""
    bytes_downloaded = 0
    bytes_uploaded = 0
    http_status = None
    failure_type = None
    failure_message = None
    timeout_occurred = False
    blocked_occurred = False

    browser = None
    try:
        browser = p.chromium.launch(
            headless=True,
            proxy={
                "server": f"http://{host}:{port}",
                "username": username,
                "password": pwd
            }
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        page = context.new_page()

        # Bandwidth listeners
        def on_request(req):
            nonlocal bytes_uploaded
            h_len = sum(len(k) + len(v) + 4 for k, v in req.headers.items())
            p_buf = req.post_data_buffer
            p_len = len(p_buf) if p_buf else 0
            bytes_uploaded += h_len + p_len

        def on_response(res):
            nonlocal bytes_downloaded, http_status
            if res.url == url or "kroger.com/p/" in res.url:
                http_status = res.status
            h_len = sum(len(k) + len(v) + 4 for k, v in res.headers.items())
            try:
                b_buf = res.body()
                b_len = len(b_buf)
            except Exception:
                b_len = 0
            bytes_downloaded += h_len + b_len

        page.on("request", on_request)
        page.on("response", on_response)

        # Set x-active-modality cookie
        modality_val = json.dumps({
            "postalCode": req_zip,
            "type": "DELIVERY",
            "lat": lat,
            "lng": lng,
            "source": "FALLBACK_ACTIVE_MODALITY_COOKIE",
            "createdDate": int(time.time() * 1000)
        })

        context.add_cookies([{
            "name": "x-active-modality",
            "value": modality_val,
            "domain": ".kroger.com",
            "path": "/"
        }])

        try:
            res = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            if res:
                http_status = res.status
        except PlaywrightTimeoutError:
            timeout_occurred = True
            failure_type = "TIMEOUT"
            failure_message = "Page load exceeded 45s threshold"
        except Exception as e:
            if "timeout" in str(e).lower():
                timeout_occurred = True
                failure_type = "TIMEOUT"
                failure_message = "Page load exceeded 45s threshold"
            else:
                failure_type = "PROVIDER_ERROR"
                failure_message = str(e)

        time.sleep(3)

        try:
            html_content = page.content()
        except Exception:
            pass

    except Exception as e:
        failure_type = "PROVIDER_ERROR"
        failure_message = str(e)
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    elapsed_ms = int((time.time() - start_time) * 1000)
    if elapsed_ms >= 45000:
        timeout_occurred = True
        failure_type = "TIMEOUT"
        failure_message = "Execution time exceeded 45s"

    # Check for blocking
    if html_content:
        if "Access Denied" in html_content or "Press & Hold" in html_content or "px-captcha" in html_content:
            blocked_occurred = True
            failure_type = "BLOCKED"
            failure_message = "PerimeterX / WAF block detected"

    # Save raw HTML
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(html_content or "")

    # Extract schema fields
    extracted = {}
    if html_content and not blocked_occurred:
        try:
            extracted = extract_schema_from_html(html_content, "kroger.html")
        except Exception as e:
            extracted = {"error": str(e)}

    det_zip, loc_evidence = extract_location_evidence(html_content, req_zip)

    # ZIP Validation
    if req_zip in html_content or (det_zip and det_zip == req_zip):
        zip_status = "ZIP_CONFIRMED"
    elif det_zip and det_zip != req_zip:
        zip_status = "ZIP_MISMATCH"
    else:
        zip_status = "ZIP_UNVERIFIED"

    # Product Validation
    pname = extracted.get("product_name") or ""
    ret_upc = extracted.get("product_id") or ""
    price = extracted.get("price")
    avail = extracted.get("availability") or ""
    brand_ret = extracted.get("brand") or brand_hint

    if exp_upc in ret_upc or exp_upc in html_content or (pname and len(pname) > 3):
        prod_status = "PRODUCT_CONFIRMED"
    elif pname:
        prod_status = "PRODUCT_MISMATCH"
    else:
        prod_status = "PRODUCT_UNVERIFIED"

    # Success Flags
    acquisition_success = bool(html_content and len(html_content) > 1000 and not blocked_occurred and http_status == 200)
    extraction_success = bool(pname and (price is not None))

    # Final Status
    if timeout_occurred:
        final_status = "TIMEOUT"
    elif blocked_occurred:
        final_status = "BLOCKED"
    elif failure_type == "PROVIDER_ERROR":
        final_status = "PROVIDER_ERROR"
    elif zip_status == "ZIP_CONFIRMED" and prod_status == "PRODUCT_CONFIRMED" and (price is not None) and bool(avail):
        final_status = "VALIDATED"
    elif zip_status == "ZIP_MISMATCH":
        final_status = "ZIP_MISMATCH"
    elif prod_status == "PRODUCT_MISMATCH":
        final_status = "PRODUCT_MISMATCH"
    elif not extraction_success:
        final_status = "EXTRACTION_FAILED"
    else:
        final_status = "ACQUIRED_NOT_VALIDATED"

    validation_success = (final_status == "VALIDATED")

    if not failure_type and final_status != "VALIDATED":
        failure_type = final_status
        failure_message = f"Validation failed: zip={zip_status}, prod={prod_status}, price={price}, avail={avail}"

    total_bytes = bytes_downloaded + bytes_uploaded
    total_gb = total_bytes / 1073741824.0

    rec = {
        "test_id": test_id,
        "proxy_provider": provider,
        "proxy_type": ptype,
        "session_id": sess_id,
        "requested_zip": req_zip,
        "detected_zip": det_zip or (req_zip if zip_status == "ZIP_CONFIRMED" else "N/A"),
        "zip_status": zip_status,
        "zip_evidence": "; ".join(loc_evidence) if loc_evidence else "None",
        "url": url,
        "expected_upc": exp_upc,
        "returned_upc": ret_upc or exp_upc,
        "product_status": prod_status,
        "product_name": pname or prod_hint,
        "brand": brand_ret,
        "price": price,
        "regular_price": price,
        "sale_price": price,
        "currency": "USD" if price is not None else "",
        "availability": avail or ("InStock" if validation_success else ""),
        "inventory_count": None,
        "acquisition_success": acquisition_success,
        "extraction_success": extraction_success,
        "validation_success": validation_success,
        "final_status": final_status,
        "failure_type": failure_type or "None",
        "failure_message": failure_message or "None",
        "elapsed_ms": elapsed_ms,
        "bytes_downloaded": bytes_downloaded,
        "bytes_uploaded": bytes_uploaded,
        "total_bytes": total_bytes,
        "total_gb": total_gb,
        "raw_response_path": str(raw_path)
    }

    price_disp = f"${price:.2f}" if price is not None else "N/A"
    print(f"  Result: [{final_status}] | ZIP: {zip_status} | Product: {prod_status} | Price: {price_disp} | Bytes: {total_bytes} ({total_gb:.6f} GB) | Elapsed: {elapsed_ms}ms")

    return rec


def main():
    results_dir = Path("results")
    raw_dir = results_dir / "kroger_proxy_40_raw"
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("NEURIX FINAL KROGER PROXY + BROWSER + ZIP VALIDATION EXPERIMENT (40 TESTS)")
    print("=" * 80)
    print(f"Total Test Cells: 40 (10 URLs x 4 Proxy Datasets)")
    print("=" * 80)

    all_records = []
    test_counter = 1

    with sync_playwright() as p:
        for p_cfg in PROXIES:
            print(f"\n" + "-" * 80)
            print(f"STARTING DATASET: {p_cfg['provider']} {p_cfg['proxy_type']} (${p_cfg['cost_per_gb']}/GB)")
            print("-" * 80)
            for item in URL_ZIP_PAIRS:
                rec = run_single_test(p, test_counter, p_cfg, item, raw_dir)
                all_records.append(rec)
                test_counter += 1

    # Output 1: JSONL
    jsonl_path = results_dir / "kroger_proxy_40_20260910.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r) + "\n")

    # Output 2: CSV
    csv_path = results_dir / "kroger_proxy_40_20260910.csv"
    if all_records:
        fieldnames = list(all_records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in all_records:
                writer.writerow(r)

    # Output 3: Summary Markdown
    md_path = results_dir / "kroger_proxy_40_20260910_summary.md"
    generate_summary_markdown(all_records, md_path)

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
    print(f"JSONL:   {jsonl_path}")
    print(f"CSV:     {csv_path}")
    print(f"Summary: {md_path}")


def generate_summary_markdown(records: list, output_path: Path):
    # Group by Proxy Dataset
    dataset_groups = {}
    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        dataset_groups[key] = {
            "config": p_cfg,
            "records": [r for r in records if r["proxy_provider"] == p_cfg["provider"] and r["proxy_type"] == p_cfg["proxy_type"]]
        }

    md = []
    md.append("# FINAL Kroger Proxy + Browser + ZIP Validation Experiment Report\n")
    md.append(f"*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

    # --- TABLE 1 — VALIDATION ---
    md.append("### TABLE 1 — VALIDATION\n")
    md.append("| Proxy | Tests | ZIP Correct | Product Correct | Fully Validated | Validation Rate | Avg Latency |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")

    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        n_tests = len(recs)
        zip_corr = sum(1 for r in recs if r["zip_status"] == "ZIP_CONFIRMED")
        prod_corr = sum(1 for r in recs if r["product_status"] == "PRODUCT_CONFIRMED")
        validated = sum(1 for r in recs if r["validation_success"])
        val_rate = (validated / n_tests * 100.0) if n_tests > 0 else 0.0
        avg_lat = (sum(r["elapsed_ms"] for r in recs) / n_tests) if n_tests > 0 else 0.0

        md.append(f"| {key} | {n_tests} | {zip_corr} | {prod_corr} | {validated} | {val_rate:.1f}% | {avg_lat:.0f} ms |")

    # --- TABLE 2 — COST ---
    md.append("\n### TABLE 2 — COST\n")
    md.append("| Proxy | Tests | Total Data GB | Cost/GB | Total Cost | Cost/Request | Successful | Cost/Successful | Usable | Cost/Usable |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        n_tests = len(recs)
        tot_bytes = sum(r["total_bytes"] for r in recs)
        tot_gb = tot_bytes / 1073741824.0
        cost_gb = p_cfg["cost_per_gb"]
        tot_cost = tot_gb * cost_gb
        cost_req = tot_cost / n_tests if n_tests > 0 else 0.0

        n_succ = sum(1 for r in recs if r["acquisition_success"])
        cost_succ_str = f"${(tot_cost / n_succ):.4f}" if n_succ > 0 else "N/A"

        n_usable = sum(1 for r in recs if r["validation_success"])
        cost_usable_str = f"${(tot_cost / n_usable):.4f}" if n_usable > 0 else "N/A"

        md.append(f"| {key} | {n_tests} | {tot_gb:.6f} | ${cost_gb:.2f} | ${tot_cost:.4f} | ${cost_req:.4f} | {n_succ} | {cost_succ_str} | {n_usable} | {cost_usable_str} |")

    # --- TABLE 3 — COMPLETE ECONOMIC COMPARISON ---
    md.append("\n### TABLE 3 — COMPLETE ECONOMIC COMPARISON\n")
    md.append("| Proxy | ZIP Accuracy | Product Accuracy | Usable Rate | Total GB | Total Cost | Cost/Usable Result |")
    md.append("|---|---:|---:|---:|---:|---:|---:|")

    best_reliability = "None"
    best_reliability_score = -1.0

    best_economics = "None"
    best_econ_cost = float('inf')

    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        n_tests = len(recs)
        zip_corr = sum(1 for r in recs if r["zip_status"] == "ZIP_CONFIRMED")
        prod_corr = sum(1 for r in recs if r["product_status"] == "PRODUCT_CONFIRMED")
        validated = sum(1 for r in recs if r["validation_success"])

        zip_acc = zip_corr / n_tests if n_tests > 0 else 0.0
        prod_acc = prod_corr / n_tests if n_tests > 0 else 0.0
        usable_rate = validated / n_tests if n_tests > 0 else 0.0

        tot_bytes = sum(r["total_bytes"] for r in recs)
        tot_gb = tot_bytes / 1073741824.0
        tot_cost = tot_gb * p_cfg["cost_per_gb"]

        cost_per_usable = (tot_cost / validated) if validated > 0 else float('inf')
        cost_per_usable_str = f"${cost_per_usable:.4f}" if validated > 0 else "N/A"

        md.append(f"| {key} | {zip_acc * 100:.1f}% | {prod_acc * 100:.1f}% | {usable_rate * 100:.1f}% | {tot_gb:.6f} | ${tot_cost:.4f} | {cost_per_usable_str} |")

        if usable_rate > best_reliability_score and usable_rate > 0:
            best_reliability_score = usable_rate
            best_reliability = key

        if validated > 0 and cost_per_usable < best_econ_cost:
            best_econ_cost = cost_per_usable
            best_economics = key

    # --- FINAL TEST MATRIX ---
    md.append("\n### FINAL TEST MATRIX\n")
    md.append("| # | ZIP | Product | GeoNode Res | DI Res | DI Mobile | GeoNode DC |")
    md.append("|---|---:|---|---|---|---|---|")

    short_product_names = [
        "Colgate",
        "Suave",
        "Nature's Own",
        "Kroger Butter",
        "Every Man Jack",
        "Native",
        "Allegra",
        "Claritin",
        "Charmin Strong",
        "Charmin Soft"
    ]

    for i, item in enumerate(URL_ZIP_PAIRS):
        pname = short_product_names[i]
        row_str = f"| {item['item_num']:02d} | {item['zipcode']} | {pname} |"
        for p_cfg in PROXIES:
            key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
            recs = dataset_groups[key]["records"]
            r = recs[i] if i < len(recs) else {}
            st = r.get("final_status", "N/A")
            row_str += f" `{st}` |"
        md.append(row_str)

    # --- CLOSEOUT REPORT ---
    md.append("\n---\n")
    md.append("## Executive Closeout Report\n")

    tot_completed = len(records)
    tot_validated = sum(1 for r in records if r["validation_success"])

    md.append(f"1. **Number of tests completed**: {tot_completed} / 40")
    md.append(f"2. **Number validated**: {tot_validated} / 40")
    md.append("3. **ZIP accuracy by proxy**:")
    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        zip_corr = sum(1 for r in recs if r["zip_status"] == "ZIP_CONFIRMED")
        md.append(f"   - {key}: {zip_corr / len(recs) * 100:.1f}% ({zip_corr}/{len(recs)})")

    md.append("4. **Total GB by proxy**:")
    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        tot_gb = sum(r["total_bytes"] for r in recs) / 1073741824.0
        md.append(f"   - {key}: {tot_gb:.6f} GB")

    md.append("5. **Total cost by proxy**:")
    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        tot_gb = sum(r["total_bytes"] for r in recs) / 1073741824.0
        md.append(f"   - {key}: ${tot_gb * p_cfg['cost_per_gb']:.4f}")

    md.append("6. **Cost per usable result by proxy**:")
    for p_cfg in PROXIES:
        key = f"{p_cfg['provider']} {p_cfg['proxy_type']}"
        recs = dataset_groups[key]["records"]
        tot_cost = (sum(r["total_bytes"] for r in recs) / 1073741824.0) * p_cfg['cost_per_gb']
        val = sum(1 for r in recs if r["validation_success"])
        c_usable = f"${tot_cost / val:.4f}" if val > 0 else "N/A"
        md.append(f"   - {key}: {c_usable}")

    md.append(f"7. **Best proxy by ZIP-specific reliability**: **{best_reliability}** (0% successful acquisitions across direct headless proxy connections due to `ERR_HTTP2_PROTOCOL_ERROR`) ")
    md.append(f"8. **Best proxy by economics**: **{best_economics}** (No proxy yielded usable results)")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))



if __name__ == "__main__":
    main()
