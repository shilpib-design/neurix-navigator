"""
Target-Agnostic Chrome DevTools Protocol (CDP) Acquisition Engine.

Provides clean, generic attachment to running Chromium browsers over CDP using Playwright,
capturing rendered page HTML and metadata without site-specific logic.
"""

from typing import Dict, Any, List, Optional
import urllib.request
import json
import time


def verify_cdp_port(port: int, host: str = "127.0.0.1") -> bool:
    """
    Checks if a local TCP port responds to the standard CDP /json/version endpoint.
    """
    url = f"http://{host}:{port}/json/version"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                return "webSocketDebuggerUrl" in data or "Protocol-Version" in data
    except Exception:
        pass
    return False


def get_cdp_targets(port: int, host: str = "127.0.0.1") -> List[Dict[str, Any]]:
    """
    Queries http://<host>:<port>/json/list to enumerate active pages and targets.
    """
    url = f"http://{host}:{port}/json/list"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode())
    except Exception:
        pass
    return []


class GenericCDPClient:
    """
    Target-agnostic CDP Client.

    Attaches to an existing running browser over CDP, navigates to a supplied URL,
    and returns normalized page metadata and outerHTML.
    """

    def __init__(self, port: int, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.cdp_url = f"http://{self.host}:{self.port}"

    def is_available(self) -> bool:
        return verify_cdp_port(self.port, self.host)

    def inspect_targets(self) -> Dict[str, Any]:
        """
        Enumerates existing browser contexts, pages, and targets over CDP without navigating.
        """
        if not self.is_available():
            return {
                "success": False,
                "cdp_port": self.port,
                "playwright_connected": False,
                "contexts_count": 0,
                "pages_count": 0,
                "urls": [],
                "titles": [],
                "browser": "cdp"
            }

        targets = get_cdp_targets(self.port, self.host)
        urls = []
        titles = []
        playwright_connected = False
        contexts_count = 0
        pages_count = 0

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.cdp_url)
                playwright_connected = True
                contexts_count = len(browser.contexts)
                for ctx in browser.contexts:
                    pages_count += len(ctx.pages)
                    for page in ctx.pages:
                        urls.append(page.url)

                for t in targets:
                    if t.get("type") == "page":
                        t_title = t.get("title", "")
                        if t_title and t_title not in titles:
                            titles.append(t_title)
        except Exception:
            playwright_connected = False
            page_targets = [t for t in targets if t.get("type") == "page"]
            urls = [t.get("url") for t in page_targets if t.get("url")]
            titles = [t.get("title") for t in page_targets if t.get("title")]
            pages_count = len(page_targets)
            contexts_count = 1 if pages_count > 0 else 0

        return {
            "success": True,
            "cdp_port": self.port,
            "playwright_connected": playwright_connected,
            "contexts_count": contexts_count,
            "pages_count": pages_count,
            "urls": urls,
            "titles": titles,
            "browser": "cdp"
        }

    def navigate_and_acquire(self, target_url: str, timeout_ms: int = 30000) -> Dict[str, Any]:
        """
        Attaches over CDP, navigates existing page to target_url, waits for DOM readiness,
        and extracts rendered HTML and page title.

        Returns clean, target-agnostic acquisition result structure.
        """
        if not self.is_available():
            return {
                "success": False,
                "error": f"CDP endpoint unavailable at {self.cdp_url}",
                "url": target_url,
                "title": "",
                "html": "",
                "elapsed_ms": 0,
                "browser": "cdp"
            }

        start_time = time.time()
        from playwright.sync_api import sync_playwright

        html_content = ""
        title = ""
        final_url = target_url

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(self.cdp_url)
            if not browser.contexts:
                raise RuntimeError("No active browser context found in target CDP browser.")

            ctx = browser.contexts[0]
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            if page.url != target_url:
                try:
                    page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                except Exception:
                    pass

            time.sleep(2)

            # Retrieve outerHTML via CDP session reliably
            try:
                cdp_session = ctx.new_cdp_session(page)
                doc = cdp_session.send("DOM.getDocument")
                html_obj = cdp_session.send("DOM.getOuterHTML", {"nodeId": doc["root"]["nodeId"]})
                html_content = html_obj.get("outerHTML", "")
            except Exception:
                try:
                    html_content = page.content()
                except Exception:
                    pass

            try:
                title = page.title()
            except Exception:
                pass

            final_url = page.url
            # Do NOT close browser or context

        elapsed_ms = int((time.time() - start_time) * 1000)
        success = bool(html_content and len(html_content) > 100)

        return {
            "success": success,
            "url": final_url,
            "title": title,
            "html": html_content,
            "elapsed_ms": elapsed_ms,
            "browser": "cdp"
        }
