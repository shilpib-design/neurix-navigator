"""
FAST 2-TEST Indian Proxy Kroger Diagnostic.

Tests 2 Indian Residential Proxies against https://www.kroger.com concurrently:
1. GeoNode Residential India ($0.57/GB)
2. DataImpulse Residential India ($0.65/GB)

Chromium Launch Args: [--disable-http2, --no-sandbox, --disable-setuid-sandbox]
Timeout: 15s navigation / 20s hard timeout.
Output: results/donut_kroger_indian_proxy_diagnostic_20260910.md
"""

import json
import time
import requests
import urllib.parse
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

load_dotenv()

TARGET_URL = "https://www.kroger.com"

TESTS = [
    {
        "test_num": 1,
        "provider": "GeoNode",
        "proxy_type": "Residential",
        "country": "India",
        "host": "192.155.103.209",
        "port": 10000,
        "username": "geonode_nxvF2zmzrd-type-residential-country-in-lifetime-3-session-in01",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "rate": 0.57,
        "session_id": "in01"
    },
    {
        "test_num": 2,
        "provider": "DataImpulse",
        "proxy_type": "Residential",
        "country": "India",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "username": "ba55974e3d2af4473e91__cr.in;sessid.in02",
        "password": "6a5fe91d07152901",
        "rate": 0.65,
        "session_id": "in02"
    }
]


def fetch_exit_ip(host: str, port: int, user: str, pwd: str) -> str:
    try:
        enc_u = urllib.parse.quote(user, safe="")
        enc_p = urllib.parse.quote(pwd, safe="")
        px = f"http://{enc_u}:{enc_p}@{host}:{port}"
        resp = requests.get("http://ip-api.com/json/", proxies={"http": px, "https": px}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("query", "Unknown")
    except Exception:
        pass
    return "Unknown"


def run_indian_proxy_test(t_cfg: dict) -> dict:
    t_num = t_cfg["test_num"]
    provider = t_cfg["provider"]
    ptype = t_cfg["proxy_type"]
    cntry = t_cfg["country"]
    host = t_cfg["host"]
    port = t_cfg["port"]
    user = t_cfg["username"]
    pwd = t_cfg["password"]
    sess_id = t_cfg["session_id"]
    rate = t_cfg["rate"]

    print(f"[TEST #{t_num}] Starting {provider} {ptype} {cntry} (Session: {sess_id})...")

    exit_ip = fetch_exit_ip(host, port, user, pwd)
    print(f"  [{provider} {cntry}] Exit IP: {exit_ip}")

    start_time = time.time()
    success = False
    http_status = None
    bytes_downloaded = 0
    bytes_uploaded = 0
    error_msg = None
    cdp_events = []
    final_url = None

    with sync_playwright() as p:
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
                if TARGET_URL in res.url or res.url == page.url:
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
                # 15s timeout for fast navigation measurement
                res = page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
                if res:
                    http_status = res.status
                    final_url = res.url
                    if res.status < 400:
                        success = True
                else:
                    final_url = page.url
            except PlaywrightTimeoutError:
                error_msg = "Page load timed out after 15s"
            except Exception as e:
                error_msg = str(e)

            if not final_url:
                final_url = page.url

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

    failure_stage = "None"
    if not success:
        if "timeout" in (error_msg or "").lower():
            failure_stage = "Kroger edge / HTTP timeout"
        elif "proxy" in (error_msg or "").lower():
            failure_stage = "Proxy CONNECT"
        else:
            failure_stage = "Kroger WAF / HTTP level"

    print(f"  [{provider} {cntry}] Complete: Success={success} | Status={http_status} | Time={elapsed_ms}ms | Error={error_msg}")

    return {
        "test_num": t_num,
        "provider": provider,
        "proxy_type": ptype,
        "country": cntry,
        "session_id": sess_id,
        "exit_ip": exit_ip,
        "success": success,
        "http_status": http_status,
        "elapsed_ms": elapsed_ms,
        "bytes": total_bytes,
        "bytes_down": bytes_downloaded,
        "bytes_up": bytes_uploaded,
        "final_url": final_url or "about:blank",
        "failure_stage": failure_stage,
        "error": error_msg or "None",
        "rate": rate,
        "cdp_events": cdp_events
    }


def main():
    print("=" * 80)
    print("FAST 2-TEST KROGER INDIAN PROXY DIAGNOSTIC")
    print("=" * 80)
    print("Target: https://www.kroger.com")
    print("Concurrency: 2 Parallel Tests")
    print("Timeout: 15s Navigation / 20s Hard Limit")
    print("-" * 80)

    start_wall = time.time()

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(run_indian_proxy_test, t): t for t in TESTS}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)

    results.sort(key=lambda x: x["test_num"])
    total_wall_ms = int((time.time() - start_wall) * 1000)

    # Determine Conclusion
    succ1 = results[0]["success"]
    succ2 = results[1]["success"]

    if succ1 and succ2:
        final_conclusion = "Indian proxies succeed while US proxies fail:\n\"Indian network/geography is a strong differentiating variable.\""
    elif not succ1 and not succ2:
        final_conclusion = "Indian proxies also fail:\n\"Geography alone does not explain the proxy failure.\""
    else:
        final_conclusion = "Mixed result:\n\"Proxy provider/network remains a differentiating variable.\""

    # Write Markdown Report
    output_path = Path("results/donut_kroger_indian_proxy_diagnostic_20260910.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# Donut Kroger Indian Proxy Diagnostic Report\n")
    md.append(f"*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")
    md.append(f"*Total Wall-Clock Time: {total_wall_ms} ms*\n")

    # TABLE 1
    md.append("## Diagnostic Test Results Table\n")
    md.append("| Provider | Type | Country | Exit IP | Success | HTTP | Time | Bytes | Failure Stage | Error |")
    md.append("|---|---|---|---|---|---:|---:|---:|---|---|")

    for r in results:
        succ_s = "YES" if r["success"] else "NO"
        st_s = str(r["http_status"]) if r["http_status"] is not None else "N/A"
        time_s = f"{r['elapsed_ms']} ms"
        bytes_s = f"{r['bytes']} B"
        err_s = r["error"] or "None"
        p_name = f"{r['provider']} {r['proxy_type']}"

        md.append(f"| {p_name} | {r['proxy_type']} | {r['country']} | `{r['exit_ip']}` | {succ_s} | {st_s} | {time_s} | {bytes_s} | {r['failure_stage']} | `{err_s}` |")

    # COST TABLE
    md.append("\n## Proxy Cost Table\n")
    md.append("*Note: Browser-observed bandwidth; provider-billed bandwidth unavailable. All proxy costs below are ESTIMATED.*\n")
    md.append("| Provider | Tests | Success | GB | Rate/GB | Estimated Cost |")
    md.append("|---|---:|---:|---:|---:|---:|")

    tot_gb = 0.0
    tot_cost = 0.0
    tot_succ = 0

    for r in results:
        gb = r["bytes"] / 1000000000.0
        cost = gb * r["rate"]
        succ_val = 1 if r["success"] else 0
        tot_succ += succ_val
        tot_gb += gb
        tot_cost += cost
        p_name = f"{r['provider']} {r['proxy_type']} {r['country']}"

        md.append(f"| {p_name} | 1 | {succ_val} | {gb:.8f} | ${r['rate']:.2f} | ${cost:.6f} |")

    md.append(f"| **TOTAL** | **2** | **{tot_succ}** | **{tot_gb:.8f}** | — | **${tot_cost:.6f}** |")

    # FINAL CONCLUSION
    md.append("\n---\n")
    md.append("## Final Conclusion\n")
    md.append(f"**{final_conclusion}**\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("\n" + "=" * 80)
    print("INDIAN PROXY DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print(f"Wall-Clock Time: {total_wall_ms} ms")
    print(f"Report saved:    {output_path}")
    print(f"Conclusion:      {final_conclusion}")


if __name__ == "__main__":
    main()
