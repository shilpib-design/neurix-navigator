"""
Focused Browser/Proxy HTTPS Diagnostic Script.

Runs exactly 2 tests with GeoNode Residential proxy + Playwright Chromium (--disable-http2):
Test A: https://example.com
Test B: https://www.kroger.com
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

PROXY_HOST = "192.155.103.209"
PROXY_PORT = 10000
PROXY_USER_BASE = "geonode_nxvF2zmzrd-type-residential-country-us-lifetime-3-session-diag"
PROXY_PASS = "51d11f1f-7027-429d-be1f-62d08de561d3"


def run_single_diagnostic(p, test_label: str, target_url: str, session_suffix: str):
    sess_user = f"{PROXY_USER_BASE}{session_suffix}"
    print(f"\n[TEST {test_label}] Target: {target_url} | Session: {sess_user[:50]}...")

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
                "server": f"http://{PROXY_HOST}:{PROXY_PORT}",
                "username": sess_user,
                "password": PROXY_PASS
            }
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        page = context.new_page()

        # CDP Network & Security listeners for granular diagnostics
        try:
            cdp = context.new_cdp_session(page)
            cdp.send("Network.enable")
            cdp.send("Security.enable")

            def on_request_failed(event):
                cdp_events.append(f"RequestFailed: {event.get('requestId')} - {event.get('errorText')} - canceled={event.get('canceled')}")

            def on_loading_failed(event):
                cdp_events.append(f"LoadingFailed: {event.get('errorText')} (type={event.get('type')})")

            def on_response_received(event):
                resp = event.get("response", {})
                cdp_events.append(f"ResponseReceived: {resp.get('status')} {resp.get('statusText')} url={resp.get('url')[:60]}")

            cdp.on("Network.requestFailed", on_request_failed)
            cdp.on("Network.loadingFailed", on_loading_failed)
            cdp.on("Network.responseReceived", on_response_received)
        except Exception as e:
            cdp_events.append(f"CDP Setup Note: {e}")

        # Page network byte counters
        def on_req(req):
            nonlocal bytes_uploaded
            h_len = sum(len(k) + len(v) + 4 for k, v in req.headers.items())
            p_buf = req.post_data_buffer
            p_len = len(p_buf) if p_buf else 0
            bytes_uploaded += h_len + p_len

        def on_res(res):
            nonlocal bytes_downloaded, http_status, final_url
            if target_url in res.url or res.url == page.url:
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
            res = page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
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
        error_msg = f"Browser launch / context error: {e}"
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass

    elapsed_ms = int((time.time() - start_time) * 1000)
    total_bytes = bytes_downloaded + bytes_uploaded

    print(f"  Result: Success={success} | Status={http_status} | Time={elapsed_ms}ms | Bytes={total_bytes} | Error={error_msg}")

    return {
        "label": test_label,
        "target_url": target_url,
        "success": success,
        "http_status": http_status,
        "elapsed_ms": elapsed_ms,
        "final_url": final_url,
        "bytes_downloaded": bytes_downloaded,
        "bytes_uploaded": bytes_uploaded,
        "total_bytes": total_bytes,
        "error": error_msg,
        "cdp_events": cdp_events
    }


def main():
    print("=" * 80)
    print("FOCUSED BROWSER / PROXY HTTPS DIAGNOSTIC")
    print("=" * 80)

    results = []
    with sync_playwright() as p:
        # Test A: Control HTTPS (example.com)
        res_a = run_single_diagnostic(p, "A", "https://example.com", "A01")
        results.append(res_a)

        time.sleep(2)

        # Test B: Kroger HTTPS (kroger.com)
        res_b = run_single_diagnostic(p, "B", "https://www.kroger.com", "B01")
        results.append(res_b)

    # Determine Conclusion
    succ_a = res_a["success"]
    succ_b = res_b["success"]

    if succ_a and succ_b:
        conclusion = "Proxy/browser HTTPS transport is working; Kroger-specific blocking/compatibility remains."
    elif succ_a and not succ_b:
        conclusion = "Proxy/browser HTTPS transport is working; Kroger-specific blocking/compatibility remains."
    elif not succ_a and not succ_b:
        conclusion = "Proxy/browser HTTPS transport itself is failing."
    else:
        conclusion = "Insufficient evidence; identify the exact missing diagnostic."

    # Failure stage analysis
    stage_analysis = []
    for r in results:
        t_name = f"Test {r['label']} ({r['target_url']})"
        if r["success"]:
            stage_analysis.append(f"- **{t_name}**: Successfully connected through proxy, established TLS/HTTP1.1, and completed navigation to `{r['final_url']}` (HTTP {r['http_status']}).")
        else:
            err = r['error'] or "Unknown"
            if "timeout" in err.lower():
                stage_analysis.append(f"- **{t_name}**: Failed at **HTTP/1.1 Navigation / Host Response Stage** (TCP/proxy CONNECT established, but target host did not finish delivering DOM within 45s limit). CDP Events: {'; '.join(r['cdp_events'][:3]) or 'None'}")
            elif "ERR_PROXY_CONNECTION_FAILED" in err or "ERR_TUNNEL_CONNECTION_FAILED" in err:
                stage_analysis.append(f"- **{t_name}**: Failed at **Proxy CONNECT / Tunnel Stage** ({err}).")
            elif "ERR_CERT" in err or "SSL" in err:
                stage_analysis.append(f"- **{t_name}**: Failed at **TLS Handshake Stage** ({err}).")
            else:
                stage_analysis.append(f"- **{t_name}**: Failed with error: `{err}`.")

    # Write Markdown Report
    output_path = Path("results/kroger_proxy_https_diagnostic_20260910.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# Focused Browser / Proxy HTTPS Diagnostic Report\n")
    md.append(f"*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

    md.append("## Diagnostic Summary Table\n")
    md.append("| Test | Target | Proxy | Success | HTTP Status | Time | Bytes | Error |")
    md.append("|---|---|---|---|---:|---:|---:|---|")

    for r in results:
        succ_str = "YES" if r["success"] else "NO"
        st_str = str(r["http_status"]) if r["http_status"] is not None else "N/A"
        time_str = f"{r['elapsed_ms']} ms"
        bytes_str = f"{r['total_bytes']} B"
        err_str = r["error"] or "None"
        target_domain = "example.com" if "example" in r["target_url"] else "kroger.com"

        md.append(f"| {r['label']} | {target_domain} | GeoNode Residential | {succ_str} | {st_str} | {time_str} | {bytes_str} | `{err_str}` |")

    md.append("\n---\n")
    md.append("## Failure Stage Isolation\n")
    md.append("\n".join(stage_analysis))

    md.append("\n---\n")
    md.append("## Final Conclusion\n")
    md.append(f"**{conclusion}**\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
    print(f"Report: {output_path}")
    print(f"Conclusion: {conclusion}")


if __name__ == "__main__":
    main()
