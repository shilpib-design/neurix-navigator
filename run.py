import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

from providers import get_all_providers

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name).lower()

def main():
    # 1. Load environment variables strictly from .env
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    # Ensure results/ directory exists
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    # 2. Read targets from config/targets.json
    targets_file = Path("config/targets.json")
    if not targets_file.exists():
        print(f"Error: Target configuration file '{targets_file}' not found.")
        return

    with open(targets_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    targets = config_data.get("targets", [])
    providers = get_all_providers()

    print("=" * 70)
    print("NAVIGATOR-01 PROVIDER TEST HARNESS")
    print("=" * 70)
    
    # 3. Report which provider adapters are configured BEFORE making requests
    print("\n--- Provider Adapter Configuration Status ---")
    configured_count = 0
    for provider in providers:
        status_str = "CONFIGURED" if provider.is_configured() else "UNCONFIGURED (missing API key)"
        if provider.is_configured():
            configured_count += 1
        print(f"  * Provider: {provider.name:<12} | Env Var: {provider.env_var:<22} | Status: {status_str}")

    print(f"\nSummary: {configured_count}/{len(providers)} providers configured with API keys.")
    total_requests = len(providers) * len(targets)
    print(f"Plan: {len(providers)} providers x {len(targets)} targets = {total_requests} total requests.")
    print("=" * 70 + "\n")

    # 4. Execute requests: exactly 1 request per target/provider combination
    results_summary = []
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    request_index = 0
    for target in targets:
        target_name = target.get("name", "unknown")
        target_url = target.get("url", "")
        print(f"\n>>> Target [{target_name}]: {target_url}")

        for provider in providers:
            request_index += 1
            print(f"  [{request_index}/{total_requests}] Requesting via {provider.name}...", end=" ", flush=True)

            result = provider.fetch(target)

            # Handle saving raw response if present
            raw_content = result.pop("raw_content", None)
            raw_file_path = None

            if raw_content:
                ext = "html" if "html" in result.get("content_type", "").lower() else "raw"
                provider_slug = sanitize_filename(provider.name)
                target_slug = sanitize_filename(target_name)
                filename = f"{provider_slug}_{target_slug}_{run_timestamp}.{ext}"
                file_path = results_dir / filename
                
                with open(file_path, "wb") as f:
                    f.write(raw_content)
                raw_file_path = str(file_path)

            result["raw_response_path"] = raw_file_path

            status_disp = f"HTTP {result['status_code']}" if result['status_code'] is not None else "N/A"
            success_disp = "SUCCESS" if result['success'] else "FAILED"
            print(f"[{success_disp}] Status: {status_disp} | Size: {result['response_size']} bytes | Elapsed: {result['elapsed_ms']}ms")
            if result['error_message']:
                print(f"      Error: {result['error_message']}")

            results_summary.append(result)

    # 5. Save summary report under results/
    summary_path = results_dir / f"summary_{run_timestamp}.json"
    latest_summary_path = results_dir / "summary.json"

    summary_data = {
        "execution_time": datetime.now(timezone.utc).isoformat(),
        "total_requests": total_requests,
        "configured_providers": configured_count,
        "targets_count": len(targets),
        "results": results_summary
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    with open(latest_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # 6. Print summary table to stdout
    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY RESULTS")
    print("=" * 70)
    header = f"{'Provider':<12} | {'Target':<14} | {'Status':<8} | {'Success':<8} | {'Size(B)':<8} | {'Time(ms)':<8} | {'Raw File Path'}"
    print(header)
    print("-" * len(header))

    for r in results_summary:
        status = str(r['status_code']) if r['status_code'] is not None else "N/A"
        succ = "YES" if r['success'] else "NO"
        raw_path = r['raw_response_path'] or "None"
        print(f"{r['provider']:<12} | {r['target']:<14} | {status:<8} | {succ:<8} | {r['response_size']:<8} | {r['elapsed_ms']:<8} | {raw_path}")

    print("=" * 70)
    print(f"Summary JSON saved to: {latest_summary_path}")
    print("Done.")

if __name__ == "__main__":
    main()
