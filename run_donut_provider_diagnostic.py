"""
Donut + Proxy Provider Diagnostic Runner.

Executes 3 tests:
Test 1: GeoNode Residential -> https://example.com
Test 2: GeoNode Residential -> https://www.kroger.com
Test 3: DataImpulse Residential -> https://www.kroger.com
"""

import json
import time
import requests
import urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

TESTS = [
    {
        "test_num": 1,
        "proxy_provider": "GeoNode Residential",
        "proxy_type": "Residential",
        "sess_id": "dnut01",
        "host": "192.155.103.209",
        "port": 10000,
        "user": "geonode_nxvF2zmzrd-type-residential-country-us-lifetime-3-session-dnut01",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "target_url": "https://example.com",
        "target_name": "example.com"
    },
    {
        "test_num": 2,
        "proxy_provider": "GeoNode Residential",
        "proxy_type": "Residential",
        "sess_id": "dnut02",
        "host": "192.155.103.209",
        "port": 10000,
        "user": "geonode_nxvF2zmzrd-type-residential-country-us-lifetime-3-session-dnut02",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3",
        "target_url": "https://www.kroger.com",
        "target_name": "kroger.com"
    },
    {
        "test_num": 3,
        "proxy_provider": "DataImpulse Residential",
        "proxy_type": "Residential",
        "sess_id": "dnut03",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "user": "ba55974e3d2af4473e91__cr.us;sessid.dnut03",
        "password": "6a5fe91d07152901",
        "target_url": "https://www.kroger.com",
        "target_name": "kroger.com"
    }
]


def fetch_exit_ip(host: str, port: int, user: str, pwd: str) -> str:
    try:
        enc_u = urllib.parse.quote(user, safe="")
        enc_p = urllib.parse.quote(pwd, safe="")
        px = f"http://{enc_u}:{enc_p}@{host}:{port}"
        resp = requests.get("http://ip-api.com/json/", proxies={"http": px, "https": px}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("query", "Unknown")
    except Exception:
        pass
    return "Unknown"


def run_test(p, t_cfg: dict):
    t_num = t_cfg["test_num"]
    provider = t_cfg["proxy_provider"]
    target = t_cfg["target_url"]
    t_name = t_cfg["target_name"]
    host = t_cfg["host"]
    port = t_cfg["port"]
    user = t_cfg["user"]
    pwd = t_cfg["password"]
    sess = t_cfg["sess_id"]

    profile_id = f"donut-profile-diag-{t_num:02d}"

    print(f"\n[TEST #{t_num}] {provider} -> {target} (Session: {sess})")

    # Fetch exit IP beforehand
    exit_ip = fetch_exit_ip(host, port, user, pwd)
    print(f"  Proxy Exit IP: {exit_ip}")

    start_time = time.time()
    success = False
    http_status = None
    final_url = None
    bytes_downloaded = 0
    bytes_uploaded = 0
    error_msg = None
    cdp_events = []

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

            def on_request_failed(event):
                cdp_events.append(f"RequestFailed: {event.get('errorText')}")

            def on_loading_failed(event):
                cdp_events.append(f"LoadingFailed: {event.get('errorText')}")

            def on_response_received(event):
                resp = event.get("response", {})
                cdp_events.append(f"Response: {resp.get('status')} url={resp.get('url')[:50]}")

            cdp.on("Network.requestFailed", on_request_failed)
            cdp.on("Network.loadingFailed", on_loading_failed)
            cdp.on("Network.responseReceived", on_response_received)
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
            if target in res.url or res.url == page.url:
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
            res = page.goto(target, wait_until="domcontentloaded", timeout=45000)
            if res:
                http_status = res.status
                final_url = res.url
                if res.status < 400:
                    success = True
            else:
                final_url = page.url
        except PlaywrightTimeoutError:
            error_msg = "Page load timed out after 45s"
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

    print(f"  Result: Success={success} | Status={http_status} | Time={elapsed_ms}ms | Error={error_msg}")

    return {
        "test_num": t_num,
        "donut_profile": profile_id,
        "proxy_provider": provider,
        "session_id": sess,
        "exit_ip": exit_ip,
        "target_name": t_name,
        "target_url": target,
        "success": success,
        "http_status": http_status,
        "elapsed_ms": elapsed_ms,
        "final_url": final_url,
        "bytes": total_bytes,
        "error": error_msg,
        "cdp_events": cdp_events
    }


def main():
    print("=" * 80)
    print("DONUT PROXY PROVIDER COMPARATIVE DIAGNOSTIC")
    print("=" * 80)

    results = []
    with sync_playwright() as p:
        for t_cfg in TESTS:
            res = run_test(p, t_cfg)
            results.append(res)
            time.sleep(2)

    # Evaluate Diagnosis
    # Test 1: GeoNode -> example.com
    # Test 2: GeoNode -> kroger.com
    # Test 3: DataImpulse -> kroger.com
    succ1 = results[0]["success"]
    succ2 = results[1]["success"]
    succ3 = results[2]["success"]

    if not succ2 and not succ3:
        short_diagnosis = "Kroger-specific blocking/compatibility of proxied browser traffic is likely."
    elif not succ2 and succ3:
        short_diagnosis = "Proxy exit-network/IP reputation is likely the differentiating factor."
    elif succ2 and succ3:
        short_diagnosis = "Previous failure was transient/session-specific; proceed to a single ZIP/product validation test before the 40-test matrix."
    else:
        short_diagnosis = "Results are inconclusive: Test 1 failed or inconsistent pattern."

    # Write Markdown
    md_path = Path("results/donut_proxy_provider_diagnostic_20260910.md")
    md_path.parent.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# Donut Proxy Provider Diagnostic Report\n")
    md.append(f"*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

    md.append("## Diagnostic Summary Table\n")
    md.append("| Test | Proxy | Target | Success | HTTP | Time | Exit IP | Error |")
    md.append("|---|---|---|---|---:|---:|---|---|")

    for r in results:
        succ_s = "YES" if r["success"] else "NO"
        st_s = str(r["http_status"]) if r["http_status"] is not None else "N/A"
        t_s = f"{r['elapsed_ms']} ms"
        err_s = r["error"] or "None"
        md.append(f"| {r['test_num']} | {r['proxy_provider']} | {r['target_name']} | {succ_s} | {st_s} | {t_s} | `{r['exit_ip']}` | `{err_s}` |")

    md.append("\n---\n")
    md.append("## Test Event & Session Trace\n")

    for r in results:
        md.append(f"### Test {r['test_num']} — {r['proxy_provider']} ({r['target_name']})")
        md.append(f"- **Donut Profile Identifier**: `{r['donut_profile']}`")
        md.append(f"- **Proxy Session ID**: `{r['session_id']}`")
        md.append(f"- **Proxy Exit IP**: `{r['exit_ip']}`")
        md.append(f"- **Final URL**: `{r['final_url'] or 'N/A'}`")
        md.append(f"- **Recorded Bytes**: {r['bytes']} bytes")
        md.append(f"- **CDP Network Trace**: {'; '.join(r['cdp_events'][:5]) or 'No failures recorded'}\n")

    md.append("\n---\n")
    md.append("## Diagnosis\n")
    md.append(f"**\"{short_diagnosis}\"**\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print(f"Report: {md_path}")
    print(f"Diagnosis: {short_diagnosis}")


if __name__ == "__main__":
    main()
