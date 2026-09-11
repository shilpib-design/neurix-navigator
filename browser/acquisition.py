"""
Target-Agnostic Browser Acquisition Layer for Neurix Navigator-01.

Provides a clean abstract acquisition contract and implementation wrappers for
browser engines (CDP, Playwright, etc.) detached from specific retailer target schemas.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from browser.cdp import GenericCDPClient


class BaseBrowserAcquisitionEngine(ABC):
    """
    Abstract interface for generic browser acquisition engines.
    """

    @abstractmethod
    def acquire(self, url: str) -> Dict[str, Any]:
        """
        Navigates browser to target URL and captures rendered HTML and metadata.

        Args:
            url (str): Target web URL.

        Returns:
            dict: Standardized acquisition result payload:
                  {
                      "success": bool,
                      "url": str,
                      "title": str,
                      "html": str,
                      "elapsed_ms": int,
                      "browser": str
                  }
        """
        pass


class CDPAcquisitionEngine(BaseBrowserAcquisitionEngine):
    """
    Generic acquisition engine backed by CDP (Chrome DevTools Protocol).
    """

    def __init__(self, port: int, host: str = "127.0.0.1"):
        self.client = GenericCDPClient(port=port, host=host)

    def acquire(self, url: str) -> Dict[str, Any]:
        return self.client.navigate_and_acquire(url)
