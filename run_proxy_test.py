"""
One-time Proxy Connectivity Test Script for Neurix Navigator-01.

Tests 4 configured proxies against http://ip-api.com/json/ exactly once each:
1. GeoNode Residential US
2. DataImpulse Residential US
3. DataImpulse Mobile US
4. GeoNode Datacenter US

Generates:
- results/proxy_ip_test_20260910.json
- results/proxy_ip_test_20260910.csv
- results/proxy_ip_test_20260910.md
"""

import json
import time
import csv
import urllib.parse
import requests
from datetime import datetime, timezone
from pathlib import Path

PROXIES_TO_TEST = [
    {
        "test_id": 1,
        "provider": "GeoNode",
        "proxy_type": "Residential",
        "session_id": "gn-res-test-01",
        "host": "192.155.103.209",
        "port": 10000,
        "username": "geonode_nxvF2zmzrd-type-residential-country-us-lifetime-3-session-gn-res-test-01",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3"
    },

    {
        "test_id": 2,
        "provider": "DataImpulse",
        "proxy_type": "Residential",
        "session_id": "di-res-test-01",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "username": "ba55974e3d2af4473e91__cr.us;sessid.di-res-test-01",
        "password": "6a5fe91d07152901"
    },
    {
        "test_id": 3,
        "provider": "DataImpulse",
        "proxy_type": "Mobile",
        "session_id": "di-mob-test-01",
        "host": "gw.dataimpulse.com",
        "port": 823,
        "username": "6487cbbdb6fa524ee174__cr.us;sessid.di-mob-test-01",
        "password": "f3c4b5430d9a4cac"
    },
    {
        "test_id": 4,
        "provider": "GeoNode",
        "proxy_type": "Datacenter",
        "session_id": "gn-dc-test-01",
        "host": "192.155.103.209",
        "port": 10000,
        "username": "geonode_nxvF2zmzrd-type-datacenter-country-us-lifetime-3-session-gn-dc-test-01",
        "password": "51d11f1f-7027-429d-be1f-62d08de561d3"
    }
]

TARGET_URL = "http://ip-api.com/json/"


def run_tests():
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("NEURIX PROXY CONNECTIVITY TEST (4 PROXIES)")
    print("=" * 80)
    print(f"Target URL: {TARGET_URL}")
    print(f"Total Requests: {len(PROXIES_TO_TEST)} (1 per proxy)")
    print("-" * 80)

    test_results = []

    for item in PROXIES_TO_TEST:
        tid = item["test_id"]
        provider = item["provider"]
        ptype = item["proxy_type"]
        sess = item["session_id"]
        host = item["host"]
        port = item["port"]
        username = item["username"]
        password = item["password"]

        print(f"\n[Test #{tid}] Testing {provider} {ptype} (Session: {sess})...", end=" ", flush=True)

        # Encode username and password safely for URL
        enc_user = urllib.parse.quote(username, safe="")
        enc_pass = urllib.parse.quote(password, safe="")

        proxy_str = f"http://{enc_user}:{enc_pass}@{host}:{port}"
        proxies_dict = {
            "http": proxy_str,
            "https": proxy_str
        }

        start_time = time.time()
        success = False
        exit_ip = None
        country = None
        region = None
        city = None
        isp = None
        org = None
        http_status = None
        error_type = None
        error_message = None

        try:
            resp = requests.get(TARGET_URL, proxies=proxies_dict, timeout=15)
            elapsed_ms = int((time.time() - start_time) * 1000)
            http_status = resp.status_code

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if data.get("status") == "success":
                        success = True
                        exit_ip = data.get("query")
                        country = data.get("country")
                        region = data.get("regionName") or data.get("region")
                        city = data.get("city")
                        isp = data.get("isp")
                        org = data.get("org")
                    else:
                        error_type = "IP_API_FAIL"
                        error_message = data.get("message", "ip-api returned non-success status")
                except Exception as e:
                    error_type = "JSON_PARSE_ERROR"
                    error_message = str(e)
            else:
                error_type = f"HTTP_{resp.status_code}"
                error_message = f"Proxy returned status code {resp.status_code}"

        except requests.exceptions.Timeout:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_type = "TIMEOUT"
            error_message = "Proxy request timed out after 15s"
        except requests.exceptions.ProxyError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_type = "PROXY_ERROR"
            error_message = "Failed to connect to proxy server or proxy authentication failed"
        except requests.exceptions.ConnectionError as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_type = "CONNECTION_ERROR"
            error_message = "Connection error while reaching target via proxy"
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_type = "UNKNOWN_ERROR"
            error_message = str(e)

        ready_status = "READY" if success else "FAILED"
        status_disp = f"HTTP {http_status}" if http_status else "N/A"
        ip_disp = exit_ip or "None"

        print(f"[{ready_status}] Status: {status_disp} | Exit IP: {ip_disp} | City: {city or 'N/A'} | Elapsed: {elapsed_ms}ms")
        if error_message:
            print(f"    Error: {error_type} - {error_message}")

        record = {
            "test_id": tid,
            "provider": provider,
            "proxy_type": ptype,
            "session_id": sess,
            "success": success,
            "ready_status": ready_status,
            "exit_ip": exit_ip,
            "country": country,
            "region": region,
            "city": city,
            "isp": isp,
            "org": org,
            "http_status": http_status,
            "latency_ms": elapsed_ms,
            "error_type": error_type,
            "error_message": error_message
        }
        test_results.append(record)

    # Output 1: JSON
    json_path = results_dir / "proxy_ip_test_20260910.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)

    # Output 2: CSV
    csv_path = results_dir / "proxy_ip_test_20260910.csv"
    fieldnames = [
        "test_id", "provider", "proxy_type", "session_id", "success", "ready_status",
        "exit_ip", "country", "region", "city", "isp", "org", "http_status",
        "latency_ms", "error_type", "error_message"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in test_results:
            writer.writerow(r)

    # Output 3: Markdown
    md_path = results_dir / "proxy_ip_test_20260910.md"
    generate_markdown(test_results, md_path)

    print("\n" + "=" * 80)
    print("PROXY TEST COMPLETE")
    print("=" * 80)
    print(f"JSON saved: {json_path}")
    print(f"CSV saved:  {csv_path}")
    print(f"Summary:    {md_path}")


def generate_markdown(results: list, output_path: Path):
    md = []
    md.append("# Neurix Proxy Connectivity Test Summary\n")
    md.append(f"*Executed on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

    md.append("## Summary Matrix\n")
    md.append("| Provider | Type | Session | Success | Exit IP | Country | Region | City | ISP | Latency |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")

    for r in results:
        succ_str = "YES" if r["success"] else "NO"
        ip_str = r["exit_ip"] or "N/A"
        cntry = r["country"] or "N/A"
        reg = r["region"] or "N/A"
        city = r["city"] or "N/A"
        isp = r["isp"] or "N/A"
        lat = f"{r['latency_ms']} ms"

        md.append(f"| **{r['provider']}** | {r['proxy_type']} | `{r['session_id']}` | {succ_str} | `{ip_str}` | {cntry} | {reg} | {city} | {isp} | {lat} |")

    md.append("\n---\n")
    md.append("## Proxy Readiness Classifications\n")

    for r in results:
        name = f"{r['provider']} {r['proxy_type']}"
        st = r["ready_status"]
        if r["success"]:
            md.append(f"- **{name}**: **{st}** (Exit IP: `{r['exit_ip']}`, Location: {r['city']}, {r['region']}, {r['country']})")
        else:
            md.append(f"- **{name}**: **{st}** (Error: {r['error_type']} - {r['error_message']})")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    run_tests()
