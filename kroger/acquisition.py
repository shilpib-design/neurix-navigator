"""
Kroger Acquisition Client Interface & Stubs.

Provides an abstract interface for acquiring Kroger API responses (such as modality options)
allowing pluggable execution engines (e.g. BrowserAcquisitionClient, DirectHttpClient, MockAcquisitionClient).
"""

from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

# Automatically load .env from project root
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()


class BaseAcquisitionClient(ABC):
    """
    Abstract base interface for Kroger HTTP/Browser data acquisition.
    """

    @abstractmethod
    def post(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Executes a POST request to the target URL with the given JSON payload and headers.

        Args:
            url (str): Target URL.
            payload (dict): JSON body dictionary.
            headers (dict): HTTP headers dictionary.

        Returns:
            dict: Parsed JSON response payload.
        """
        pass


class MockAcquisitionClient(BaseAcquisitionClient):
    """
    Mock acquisition client for testing and verification without live network requests.
    """

    def __init__(self, mock_response: Dict[str, Any]):
        self.mock_response = mock_response
        self.last_request = None

    def post(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        self.last_request = {
            "url": url,
            "payload": payload,
            "headers": headers
        }
        return self.mock_response


class DonutClient:
    """
    Client for interacting with the local Donut browser REST API.
    Used strictly for local browser context management and profile resolution.
    Does NOT send requests directly to Kroger or external targets.
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        raw_url = base_url or os.getenv("DONUT_API_BASE_URL") or "http://127.0.0.1:10108"
        self.base_url = raw_url.rstrip("/")
        self.token = token or os.getenv("DONUT_API_TOKEN")

    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            raise ValueError("DONUT_API_TOKEN environment variable is missing or empty.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        GET /v1/profiles
        Fetches browser profiles from the local Donut REST API endpoint.
        """
        endpoint = f"{self.base_url}/v1/profiles"
        try:
            resp = requests.get(endpoint, headers=self._get_headers(), timeout=10)
            if resp.status_code in (401, 403):
                raise PermissionError("Authentication failure accessing Donut API (401/403). Check DONUT_API_TOKEN.")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("profiles") or data.get("data") or []
            return []
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Donut API unavailable at {self.base_url}. Is Donut browser running?")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Donut API error fetching profiles: {e}")

    def find_profile_by_name(self, profile_name: str) -> Dict[str, Any]:
        """
        Searches available profiles from /v1/profiles and returns the profile object matching `name`.
        """
        profiles = self.list_profiles()
        for p in profiles:
            if isinstance(p, dict) and p.get("name") == profile_name:
                return p
        raise KeyError(f"Donut profile '{profile_name}' not found.")

    def get_profile_status(self, profile_name: str) -> Dict[str, Any]:
        """
        Discovers a profile by name and reports its running status.
        Does NOT open a URL or make external requests.
        """
        profile = self.find_profile_by_name(profile_name)
        is_running = bool(profile.get("is_running")) or (profile.get("status") in ["RUNNING", "ACTIVE"]) or bool(profile.get("process_id"))
        return {
            "profile_name": profile_name,
            "profile_id": profile.get("id"),
            "is_running": is_running,
            "status": "RUNNING" if is_running else (profile.get("status") or "STOPPED"),
            "profile_data": profile
        }

    def open_url(self, profile_id: str, target_url: str) -> Dict[str, Any]:
        """
        POST /v1/profiles/{profile_id}/open-url
        Instructs the specified Donut profile to navigate to target_url.
        Sends {"url": target_url} in the JSON body per Donut OpenAPI schema.
        """
        if not profile_id:
            raise ValueError("profile_id must be provided to open_url.")
        endpoint = f"{self.base_url}/v1/profiles/{profile_id}/open-url"
        payload = {"url": target_url}
        try:
            resp = requests.post(endpoint, json=payload, headers=self._get_headers(), timeout=15)
            if resp.status_code in (401, 403):
                raise PermissionError("Authentication failure accessing Donut API (401/403). Check DONUT_API_TOKEN.")
            if resp.status_code == 402:
                raise PermissionError("Donut API endpoint /open-url returned 402 Payment Required. The open-url REST API feature requires a paid Donut tier.")
            resp.raise_for_status()

            res_json = resp.json() if resp.content else {"status": "success"}
            return res_json
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Donut API unavailable at {self.base_url}. Is Donut browser running?")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Donut API error opening URL for profile '{profile_id}': {e}")


class BrowserAcquisitionClient(BaseAcquisitionClient):
    """
    Acquisition client implementation backed by the Donut browser REST API.
    Implements the BaseAcquisitionClient interface.
    """

    def __init__(self, profile_name: str = "Kroger-Test-30301", donut_client: Optional[DonutClient] = None):
        self.profile_name = profile_name
        self.client = donut_client or DonutClient()

    def discover_profile(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Discovers profile ID and verifies existence by profile_name dynamically.
        Does NOT open any URL or contact external targets.
        """
        p_name = profile_name or self.profile_name
        return self.client.get_profile_status(p_name)

    def open_url(self, target_url: str, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Navigates the Donut browser profile to target_url via POST /v1/profiles/{id}/open-url.
        
        1. Discovers the profile dynamically by name.
        2. Verifies the profile exists.
        3. Verifies the profile is running; if not, returns an error instead of launching a new browser.
        4. Calls /v1/profiles/{profile_id}/open-url with {"url": target_url}.
        5. Returns normalized navigation result.
        """
        p_name = profile_name or self.profile_name
        
        # 1 & 2. Discover profile dynamically & verify existence
        profile_info = self.discover_profile(p_name)
        profile_id = profile_info["profile_id"]

        # 3. Verify running status
        if not profile_info.get("is_running"):
            raise RuntimeError(
                f"Donut profile '{p_name}' (ID: {profile_id}) is not currently running. "
                "Please start the profile in Donut browser before executing navigation."
            )

        # 4 & 5. Instruct Donut to open URL
        response = self.client.open_url(profile_id, target_url)

        return {
            "profile_name": p_name,
            "profile_id": profile_id,
            "url": target_url,
            "success": True,
            "status": "OPENED",
            "response": response
        }

    def post(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Executes acquisition request using Donut browser profile.
        Implements BaseAcquisitionClient.post.
        """
        return self.open_url(url)

    def get_cdp_endpoint(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Helper method preparing for future CDP/Playwright connection to the running profile.
        Returns profile details and CDP port metadata if available.
        """
        profile_info = self.discover_profile(profile_name)
        p_data = profile_info.get("profile_data", {})
        return {
            "profile_name": profile_info["profile_name"],
            "profile_id": profile_info["profile_id"],
            "is_running": profile_info["is_running"],
            "cdp_port": p_data.get("remote_debugging_port") or p_data.get("cdp_port"),
            "process_id": p_data.get("process_id")
        }
