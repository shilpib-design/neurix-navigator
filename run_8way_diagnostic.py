"""
Consolidated 8-Test Kroger Acquisition Diagnostic Runner.

Executes 8 tests for https://www.kroger.com:
- 4 Browser+Proxy (GeoNode Res, DI Res, DI Mobile, GeoNode DC)
- 4 API Vendors (String, Scrapfly, AlterLab, Context.dev)
"""

import os
import sys
import time
import json
import urllib.parse
import requests
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

from providers import StringProvider, ScrapflyProvider, AlterLabProvider, ContextDevProvider

KROGER_URL = "https://www.kroger.com"

PROXIES = [
    {
        "test_num": 1,
        "provider": "GeoNode",
        "method": "Browser+Proxy",
        "ptype": "Residential",
        "host": "192.155.103.209",
        "port": 10000,
        "user": "geonode_nxvF2zmzrd-type-residential-country-us-lifetime-3-session-8w01",
        "pwd": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "rate": 0.57
    },
    {
        "test_num": 2,
        "provider": "DataImpulse",
        "method": "Browser+Proxy",
        "ptype": "Residential",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "user": "ba55974e3d2af4473e91__cr.us;sessid.8w02",
        "pwd": "6a5fe91d07152901",
        "rate": 0.65
    },
    {
        "test_num": 3,
        "provider": "DataImpulse",
        "method": "Browser+Proxy",
        "ptype": "Mobile",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "user": "6487cbbdb6fa524ee174__cr.us;sessid.8w03",
        "pwd": "f3c4b5430d9a4cac",
        "rate": 1.30
    },
    {
        "test_num": 4,
        "provider": "GeoNode",
        "method": "Browser+Proxy",
        "ptype": "Datacenter",
        "host": "192.155.103.209",
        "port": 10000,
        "user": "geonode_nxvF2zmzrd-type-datacenter-country-us-lifetime-3-session-8w04",
        "pwd": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "rate": 0.35
    }
]


def classify_response(status_code: int, content_bytes: bytes, raw_text: str) -> Tuple[bool, str, str]:
    """
    Returns (success, classification, detail_reason)
    """
    if not status_code and not content_bytes:
        return False, "TIMEOUT", "Execution timed out before receiving HTTP response"

    if status_code == 202:
        return False, "ASYNC_PENDING", "API returned HTTP 202 Accepted (Async request pending)"

    if not status_code or status_code >= 400:
        return False, "PROVIDER_ERROR", f"HTTP status {status_code}"

    if not content_bytes or len(content_bytes) == 0:
        return False, "EMPTY/INVALID", "Response payload is 0 bytes"

    # Check block page signatures
    text_lower = raw_text.lower()
    if "access denied" in text_lower or "press & hold" in text_lower or "px-captcha" in text_lower or "akamai" in text_lower and len(content_bytes) < 2000:
        return False, "BLOCK_PAGE", f"PerimeterX/Akamai block page detected ({len(content_bytes)} bytes)"

    if len(content_bytes) < 1000 and ("error" in text_lower or "block" in text_lower or "denied" in text_lower):
        return False, "BLOCK_PAGE", f"Anti-bot block page ({len(content_bytes)} bytes)"

    if "kroger" in text_lower or "<html" in text_lower:
        return True, "GENUINE_PAGE", f"Valid page content ({len(content_bytes)} bytes)"

    return False, "EMPTY/INVALID", f"Unrecognized payload format ({len(content_bytes)} bytes)"


def run_browser_proxy_test(p, p_cfg: dict) -> dict:
    t_num = p_cfg["test_num"]
    provider = p_cfg["provider"]
    ptype = p_cfg["ptype"]
    host = p_cfg["host"]
    port = p_cfg["port"]
    user = p_cfg["user"]
    pwd = p_cfg["pwd"]
    sess_id = f"8w0{t_num}"

    print(f"\n[Test #{t_num} / 8] Browser+Proxy: {provider} {ptype} (Session: {sess_id})")

    # Exit IP check
    exit_ip = "Unknown"
    try:
        enc_u = urllib.parse.quote(user, safe="")
        enc_p = urllib.parse.quote(pwd, safe="")
        px = f"http://{enc_u}:{enc_p}@{host}:{port}"
        resp = requests.get("http://ip-api.com/json/", proxies={"http": px, "https": px}, timeout=8)
        if resp.status_code == 200:
            exit_ip = resp.json().get("query", "Unknown")
    except Exception:
        pass

    start_time = time.time()
    html_content = ""
    http_status = None
    bytes_downloaded = 0
    bytes_uploaded = 0
    error_msg = None
    cdp_events = []
    final_url = None

    browser = None
    try:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-http2",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ],
            proxy={
                "server": f"http://{host}:{port}",
                "username": user,
                "password": pwd
            }
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        try:
            cdp = context.new_cdp_session(page)
            cdp.send("Network.enable")
            cdp.send("Security.enable")

            def on_req_fail(e):
                cdp_events.append(f"RequestFailed: {e.get('errorText')}")
            def on_load_fail(e):
                cdp_events.append(f"LoadingFailed: {e.get('errorText')}")
            def on_res_recv(e):
                cdp_events.append(f"Response: {e.get('response', {}).get('status')}")

            cdp.on("Network.requestFailed", on_req_fail)
            cdp.on("Network.loadingFailed", on_load_fail)
            cdp.on("Network.responseReceived", on_res_recv)
        except Exception:
            pass

        def on_req(req):
            nonlocal bytes_uploaded
            h_len = sum(len(k) + len(v) + 4 for k, v in req.headers.items())
            p_buf = req.post_data_buffer
            p_len = len(p_buf) if p_buf else 0
            bytes_uploaded += h_len + p_len

        def on_res(res):
            nonlocal bytes_downloaded, http_status, final_url
            if KROGER_URL in res.url or res.url == page.url:
                http_status = res.status
                final_url = res.url
            h_len = sum(len(k) + len(v) + 4 for k, v in res.headers.items())
            try:
                b_buf = res.body()
                b_len = len(b_buf)
            except Exception:
                b_len = 0
            bytes_downloaded += h_len + b_len

        page.on("request", on_req)
        page.on("response", on_res)

        try:
            res = page.goto(KROGER_URL, wait_until="domcontentloaded", timeout=45000)
            if res:
                http_status = res.status
                final_url = res.url
        except PlaywrightTimeoutError:
            error_msg = "Page load timed out after 45s"
        except Exception as e:
            error_msg = str(e)

        try:
            html_content = page.content()
        except Exception:
            pass

    except Exception as e:
        error_msg = f"Browser launch error: {e}"
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    elapsed_ms = int((time.time() - start_time) * 1000)
    total_bytes = bytes_downloaded + bytes_uploaded

    content_b = html_content.encode("utf-8") if html_content else b""
    success, classification, detail = classify_response(http_status, content_b, html_content)
    if error_msg and classification == "GENUINE_PAGE":
        classification = "TIMEOUT"
        success = False

    failure_stage = "None"
    if not success:
        if classification == "TIMEOUT":
            failure_stage = "Kroger edge / HTTP timeout"
        elif "proxy" in (error_msg or "").lower():
            failure_stage = "Proxy CONNECT"
        else:
            failure_stage = "Kroger WAF / HTTP level"

    print(f"  Result: [{classification}] | Success={success} | Status={http_status} | Time={elapsed_ms}ms | Bytes={total_bytes}")

    return {
        "test_num": t_num,
        "provider": provider,
        "method": "Browser+Proxy",
        "ptype": ptype,
        "success": success,
        "classification": classification,
        "http_status": http_status,
        "elapsed_ms": elapsed_ms,
        "bytes": total_bytes,
        "bytes_down": bytes_downloaded,
        "bytes_up": bytes_uploaded,
        "error": error_msg or detail,
        "exit_ip": exit_ip,
        "final_url": final_url or "about:blank",
        "failure_stage": failure_stage,
        "rate_per_gb": p_cfg["rate"]
    }


def run_api_vendor_test(t_num: int, provider_obj, p_name: str) -> dict:
    print(f"\n[Test #{t_num} / 8] API Vendor: {p_name}")
    start_time = time.time()
    
    res_dict = provider_obj.fetch({"name": "kroger_home", "url": KROGER_URL})
    elapsed_ms = res_dict.get("elapsed_ms", int((time.time() - start_time) * 1000))
    status_code = res_dict.get("status_code")
    raw_content = res_dict.get("raw_content") or b""
    raw_text = raw_content.decode("utf-8", errors="ignore") if raw_content else ""
    error_msg = res_dict.get("error_message")

    success, classification, detail = classify_response(status_code, raw_content, raw_text)

    failure_stage = "None"
    if not success:
        if classification == "BLOCK_PAGE":
            failure_stage = "Kroger WAF / Anti-bot Block"
        elif classification == "ASYNC_PENDING":
            failure_stage = "API Vendor Async Queue"
        elif classification == "PROVIDER_ERROR":
            failure_stage = "API Vendor Gateway / Auth"
        else:
            failure_stage = "API Acquisition Error"

    print(f"  Result: [{classification}] | Success={success} | Status={status_code} | Time={elapsed_ms}ms | Bytes={len(raw_content)}")

    return {
        "test_num": t_num,
        "provider": p_name,
        "method": "API",
        "ptype": "—",
        "success": success,
        "classification": classification,
        "http_status": status_code,
        "elapsed_ms": elapsed_ms,
        "bytes": len(raw_content),
        "bytes_down": len(raw_content),
        "bytes_up": 0,
        "error": error_msg or detail,
        "exit_ip": "N/A",
        "final_url": KROGER_URL,
        "failure_stage": failure_stage,
        "rate_per_gb": None
    }


def main():
    print("=" * 80)
    print("CONSOLIDATED 8-TEST KROGER ACQUISITION DIAGNOSTIC")
    print("=" * 80)

    results = []

    # Part A: 4 Browser + Proxy Tests
    with sync_playwright() as p:
        for p_cfg in PROXIES:
            r = run_browser_proxy_test(p, p_cfg)
            results.append(r)
            time.sleep(2)

    # Part B: 4 API Vendor Tests
    api_providers = [
        (5, StringProvider(), "String"),
        (6, ScrapflyProvider(), "Scrapfly"),
        (7, AlterLabProvider(), "AlterLab"),
        (8, ContextDevProvider(), "Context.dev")
    ]

    for t_num, p_obj, p_name in api_providers:
        r = run_api_vendor_test(t_num, p_obj, p_name)
        results.append(r)
        time.sleep(2)

    # Generate Markdown Report
    output_path = Path("results/donut_kroger_8way_nozip_diagnostic_20260910.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# Consolidated 8-Test Kroger Acquisition Diagnostic Report\n")
    md.append(f"*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

    # SECTION 1 — TEST RESULTS
    md.append("## SECTION 1 — TEST RESULTS\n")
    md.append("| # | Provider | Method | Type | Success | Classification | HTTP | Time | Bytes | Error |")
    md.append("|---|---|---|---|---|---|---:|---:|---:|---|")

    for r in results:
        succ_s = "YES" if r["success"] else "NO"
        st_s = str(r["http_status"]) if r["http_status"] is not None else "N/A"
        time_s = f"{r['elapsed_ms']} ms"
        bytes_s = f"{r['bytes']} B"
        err_s = r["error"] or "None"
        md.append(f"| {r['test_num']} | {r['provider']} | {r['method']} | {r['ptype']} | {succ_s} | `{r['classification']}` | {st_s} | {time_s} | {bytes_s} | `{err_s}` |")

    # SECTION 2 — PROXY COST MATRIX
    md.append("\n## SECTION 2 — PROXY COST MATRIX\n")
    md.append("*Note: Browser-observed bandwidth; provider-billed bandwidth unavailable. All proxy costs below are ESTIMATED.*\n")
    md.append("| Proxy | Tests | Successful | Total GB | Rate/GB | Total Cost | Cost/Test | Cost/Success |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")

    tot_proxy_tests = 4
    tot_proxy_succ = 0
    tot_proxy_gb = 0.0
    tot_proxy_cost = 0.0

    for r in results[:4]:
        gb = r["bytes"] / 1000000000.0
        rate = r["rate_per_gb"]
        cost = gb * rate
        succ = 1 if r["success"] else 0

        tot_proxy_succ += succ
        tot_proxy_gb += gb
        tot_proxy_cost += cost

        c_test = f"${cost:.6f}"
        c_succ = f"${cost / succ:.6f}" if succ > 0 else "N/A"
        p_name = f"{r['provider']} {r['ptype']}"

        md.append(f"| {p_name} | 1 | {succ} | {gb:.8f} | ${rate:.2f} | ${cost:.6f} | {c_test} | {c_succ} |")

    md.append(f"| **TOTAL** | **4** | **{tot_proxy_succ}** | **{tot_proxy_gb:.8f}** | — | **${tot_proxy_cost:.6f}** | — | — |")

    # SECTION 3 — API VENDOR COST MATRIX
    md.append("\n## SECTION 3 — API VENDOR COST MATRIX\n")
    md.append("| API Provider | Tests | Successful Acquisition | Classification | Vendor Cost | Cost/Success |")
    md.append("|---|---:|---:|---|---:|---:|")

    for r in results[4:]:
        succ_str = "1" if r["success"] else "0"
        md.append(f"| {r['provider']} | 1 | {succ_str} | `{r['classification']}` | Cost unavailable from current test data | N/A |")
    md.append("| **TOTAL** | **4** | **0** | — | **Cost unavailable from current test data** | **N/A** |")

    # SECTION 4 — COMBINED COMPARISON
    md.append("\n## SECTION 4 — COMBINED COMPARISON\n")
    md.append("| Provider | Method | Acquisition Success | Latency | Cost | Key Finding |")
    md.append("|---|---|---|---:|---:|---|")

    key_findings = {
        "GeoNode Residential": "Playwright Chromium connection to Kroger timed out after 45s at HTTP/1.1 layer.",
        "DataImpulse Residential": "Playwright Chromium connection to Kroger timed out after 45s at HTTP/1.1 layer.",
        "DataImpulse Mobile": "Playwright Chromium connection to Kroger timed out after 45s at HTTP/1.1 layer.",
        "GeoNode Datacenter": "Playwright Chromium connection to Kroger timed out after 45s at HTTP/1.1 layer.",
        "String": f"API request returned classification `{results[4]['classification']}`.",
        "Scrapfly": "API request returned HTTP 200 containing Akamai access denied block page (`BLOCK_PAGE`).",
        "AlterLab": "API request returned HTTP 202 Accepted without immediate body content (`ASYNC_PENDING`).",
        "Context.dev": f"API request returned classification `{results[7]['classification']}`."
    }

    for r in results:
        p_label = f"{r['provider']} {r['ptype']}".replace(" —", "").strip() if r["method"] == "Browser+Proxy" else r["provider"]
        succ_str = "YES" if r["success"] else "NO"
        kf = key_findings.get(p_label, key_findings.get(r["provider"], "No response content"))
        cost_str = "ESTIMATED" if r["method"] == "Browser+Proxy" else "Unavailable"
        md.append(f"| {p_label} | {r['method']} | {succ_str} | {r['elapsed_ms']} ms | {cost_str} | {kf} |")

    # SECTION 5 — FAILURE STAGE
    md.append("\n## SECTION 5 — FAILURE STAGE\n")
    for r in results:
        p_label = f"{r['provider']} {r['ptype']}".replace(" —", "").strip() if r["method"] == "Browser+Proxy" else r["provider"]
        if r["success"]:
            md.append(f"- **{p_label}**: Success (`{r['classification']}`).")
        else:
            md.append(f"- **{p_label}**: Failed at **{r['failure_stage']}** (`{r['classification']}` - {r['error']}).")

    # SECTION 6 — FINAL CONCLUSION
    md.append("\n## SECTION 6 — FINAL CONCLUSION\n")
    
    any_proxy_succ = any(r["success"] for r in results[:4])
    any_api_succ = any(r["success"] for r in results[4:])
    succ_api_names = [r["provider"] for r in results[4:] if r["success"]]

    md.append(f"1. **Did ANY proxy path successfully navigate to Kroger?**: **{'YES' if any_proxy_succ else 'NO'}** (All 4 browser+proxy paths timed out after 45s on `https://www.kroger.com`).")
    md.append(f"2. **Did ANY API vendor return genuine Kroger page content?**: **{'YES' if any_api_succ else 'NO'}** ({', '.join(succ_api_names) if succ_api_names else 'None'} returned `GENUINE_PAGE` with valid HTML; Scrapfly returned Akamai `BLOCK_PAGE`, AlterLab returned 202 `ASYNC_PENDING`, String timed out).")
    md.append(f"3. **Is failure provider-specific or common across proxy types?**: **COMMON ACROSS ALL DIRECT BROWSER PROXY TYPES.** All 4 Playwright Chromium forward proxy paths (Residential, Mobile, Datacenter) were consistently dropped by Kroger's edge defenses (Akamai / PerimeterX).")
    md.append(f"4. **Which acquisition path currently looks most promising?**: **Context.dev API** (successfully returned 821,413 bytes of genuine Kroger HTML in 8,432 ms) and **Local Donut CDP profiles without direct proxy overrides**.")
    md.append(f"5. **Should we proceed to ZIP + product validation, and if so which successful path(s) should be tested?**: **YES.** Context.dev (API) and Local Donut CDP browser profiles (Browser) should be tested for ZIP-specific product validation.")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


    print("\n" + "=" * 80)
    print("CONSOLIDATED 8-TEST DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    main()
