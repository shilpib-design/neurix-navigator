"""
Acquisition Strategies for Neurix Acquisition Orchestrator.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from orchestrator.models import AcquisitionRequest, AcquisitionResult


class BaseAcquisitionStrategy(ABC):
    """
    Abstract contract for acquisition strategies.
    """
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """
        Checks if this strategy can be executed currently.
        """
        pass

    @abstractmethod
    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        """
        Executes acquisition for the target request.
        """
        pass


class BrowserCDPStrategy(BaseAcquisitionStrategy):
    """
    Strategy that delegates acquisition to the generic browser/CDP engine.
    """
    name: str = "browser_cdp"

    def __init__(self, profile_name: str = "Kroger-Test-30301", port: Optional[int] = None):
        self.profile_name = profile_name
        self.port = port

    def _resolve_port(self) -> Optional[int]:
        if self.port:
            return self.port
        try:
            from kroger.cdp_client import discover_cdp_port_for_profile
            return discover_cdp_port_for_profile(self.profile_name)
        except Exception:
            return None

    def is_available(self) -> bool:
        port = self._resolve_port()
        if not port:
            return False
        try:
            from browser.cdp import verify_cdp_port
            return verify_cdp_port(port)
        except Exception:
            return False

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        port = self._resolve_port()
        if not port or not self.is_available():
            return AcquisitionResult(
                success=False,
                method=self.name,
                url=request.url,
                error=f"Browser CDP port unavailable for profile '{self.profile_name}'"
            )

        try:
            from browser.acquisition import CDPAcquisitionEngine
            engine = CDPAcquisitionEngine(port=port)
            result = engine.acquire(request.url)
            return AcquisitionResult(
                success=result.get("success", False),
                method=self.name,
                url=result.get("url", request.url),
                title=result.get("title", ""),
                html=result.get("html", ""),
                elapsed_ms=result.get("elapsed_ms", 0),
                error=result.get("error")
            )
        except Exception as e:
            return AcquisitionResult(
                success=False,
                method=self.name,
                url=request.url,
                error=f"Browser CDP acquisition error: {e}"
            )


class VendorAPIStrategy(BaseAcquisitionStrategy):
    """
    Interface/stub for future third-party vendor scraping strategies.
    Remains uncalled and stubbed for future implementation.
    """
    name: str = "vendor_api"

    def __init__(self, vendor_name: str = "generic_vendor"):
        self.vendor_name = vendor_name

    def is_available(self) -> bool:
        # Stubbed: returning False to keep uncalled
        return False

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult:
        return AcquisitionResult(
            success=False,
            method=f"{self.name}:{self.vendor_name}",
            url=request.url,
            error=f"VendorAPIStrategy for '{self.vendor_name}' is an uncalled stub"
        )
