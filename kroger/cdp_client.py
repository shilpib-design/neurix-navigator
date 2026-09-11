"""
Kroger CDP (Chrome DevTools Protocol) Client Module.

Handles Donut browser profile discovery (PID, socket lookup, CDP port resolution)
and delegates generic browser acquisition to the target-agnostic browser/cdp module.
"""

from typing import Dict, Any, List, Optional
import subprocess
import time
from pathlib import Path
from kroger.acquisition import DonutClient, BaseAcquisitionClient
from browser.cdp import GenericCDPClient, verify_cdp_port, get_cdp_targets


def discover_cdp_port_for_profile(profile_name: str = "Kroger-Test-30301") -> Optional[int]:
    """
    Discovers the listening CDP remote debugging port for a running Donut profile.

    1. Queries Donut REST API for profile metadata (process_id).
    2. Inspects local OS process sockets via lsof for process_id.
    3. Verifies that http://127.0.0.1:<port>/json/version responds with valid CDP metadata.
    """
    try:
        donut_client = DonutClient()
        profile = donut_client.find_profile_by_name(profile_name)
        pid = profile.get("process_id")
    except Exception:
        pid = None

    ports_to_check = []

    if pid:
        try:
            cmd = f"lsof -a -p {pid} -i TCP -s TCP:LISTEN -P -n"
            out = subprocess.check_output(cmd, shell=True).decode()
            for line in out.splitlines():
                if "LISTEN" in line:
                    parts = line.split()
                    for part in parts:
                        if ":" in part:
                            port_str = part.split(":")[-1]
                            if port_str.isdigit():
                                ports_to_check.append(int(port_str))
        except Exception:
            pass

    for port in ports_to_check:
        if verify_cdp_port(port):
            return port

    return None


class DonutCDPClient(BaseAcquisitionClient):
    """
    Donut CDP Acquisition Client.

    Integrates Donut profile discovery with the target-agnostic browser.cdp engine.
    """

    def __init__(self, port: Optional[int] = None, profile_name: str = "Kroger-Test-30301"):
        self.profile_name = profile_name
        self.port = port or discover_cdp_port_for_profile(profile_name)
        self.generic_client = GenericCDPClient(port=self.port) if self.port else None

    def is_cdp_available(self) -> bool:
        return self.generic_client is not None and self.generic_client.is_available()

    def inspect_pages(self) -> Dict[str, Any]:
        """
        Delegates target inspection to the generic CDP client.
        """
        if not self.generic_client:
            return {
                "cdp_discovered": False,
                "cdp_port": None,
                "playwright_connected": False,
                "contexts_count": 0,
                "pages_count": 0,
                "urls": [],
                "titles": [],
                "targets": []
            }
        
        info = self.generic_client.inspect_targets()
        info["cdp_discovered"] = info["success"]
        info["targets"] = get_cdp_targets(self.port) if self.port else []
        return info

    def navigate_and_acquire(self, target_url: str) -> Dict[str, Any]:
        """
        Delegates navigation and DOM capture to the generic CDP client,
        saves raw HTML into results/, and returns normalized metadata.
        """
        if not self.generic_client or not self.is_cdp_available():
            raise RuntimeError(f"CDP port unavailable for profile '{self.profile_name}'. Is Donut running?")

        acquisition = self.generic_client.navigate_and_acquire(target_url)

        # Save acquired raw HTML into results/
        results_dir = Path(__file__).resolve().parent.parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        raw_html_filename = f"donut_kroger_cdp_{timestamp}.html"
        raw_html_path = results_dir / raw_html_filename

        with open(raw_html_path, "w", encoding="utf-8") as f:
            f.write(acquisition.get("html", ""))

        return {
            "cdp_port": self.port,
            "url": acquisition.get("url", target_url),
            "title": acquisition.get("title", ""),
            "html_content": acquisition.get("html", ""),
            "raw_html_path": str(raw_html_path),
            "elapsed_ms": acquisition.get("elapsed_ms", 0),
            "browser": acquisition.get("browser", "donut-cdp")
        }

    def post(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Implements BaseAcquisitionClient.post by navigating over CDP.
        """
        return self.navigate_and_acquire(url)
