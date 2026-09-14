"""
Pure HTTP Acquisition Engine & Pluggable Transport Layer for Neurix Navigator v0.1 Core.
Provides configurable HTTP GET requests, session integration, latency/byte tracking, and structured error handling.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

from core.session import SessionManager, SessionBundle
from core.models import FailureCategory


@dataclass
class HttpAcquisitionResponse:
    url: str
    status_code: Optional[int]
    headers: Dict[str, str]
    cookies: Dict[str, str]
    content: bytes
    text: str
    elapsed_ms: int
    byte_count: int
    success: bool
    error: Optional[str]
    failure_category: Optional[str]
    session_id: Optional[str] = None
    session_assisted: bool = False
    session_reused: bool = False
    session_invalidated: bool = False
    session_reuse_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "headers": dict(self.headers),
            "cookies": dict(self.cookies),
            "response_size": self.byte_count,
            "elapsed_ms": self.elapsed_ms,
            "success": self.success,
            "error": self.error,
            "failure_category": self.failure_category,
            "session_id": self.session_id,
            "session_assisted": self.session_assisted,
            "session_reused": self.session_reused,
            "session_invalidated": self.session_invalidated,
            "session_reuse_count": self.session_reuse_count
        }


class HttpTransport(ABC):
    """
    Abstract interface for low-level HTTP transport execution.
    Isolates third-party HTTP client libraries (requests, curl_cffi, etc.) from Navigator.
    """

    @abstractmethod
    def send_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: float = 10.0
    ) -> Tuple[Optional[int], Dict[str, str], Dict[str, str], bytes, int, Optional[str]]:
        """
        Executes HTTP request.
        Returns: (status_code, response_headers, response_cookies, content_bytes, elapsed_ms, error_message)
        """
        pass


class RequestsHttpTransport(HttpTransport):
    """
    Default HTTP transport using standard Python `requests`.
    """

    def __init__(self):
        import requests
        self._requests = requests

    def send_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: float = 10.0
    ) -> Tuple[Optional[int], Dict[str, str], Dict[str, str], bytes, int, Optional[str]]:
        req_headers = dict(headers) if headers else {}
        req_cookies = dict(cookies) if cookies else {}
        proxies = {"http": proxy, "https": proxy} if proxy else None

        start_t = time.perf_counter()
        try:
            resp = self._requests.request(
                method=method,
                url=url,
                headers=req_headers,
                cookies=req_cookies,
                proxies=proxies,
                timeout=timeout,
                allow_redirects=True
            )
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            res_headers = dict(resp.headers)
            res_cookies = dict(resp.cookies)
            content_bytes = resp.content or b""
            return resp.status_code, res_headers, res_cookies, content_bytes, elapsed_ms, None
        except self._requests.exceptions.Timeout:
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            return None, {}, {}, b"", elapsed_ms, "Request timed out"
        except self._requests.exceptions.ConnectionError as e:
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            return None, {}, {}, b"", elapsed_ms, f"Connection error: {str(e)}"
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            return None, {}, {}, b"", elapsed_ms, f"HTTP request failed: {str(e)}"


class CurlCffiHttpTransport(HttpTransport):
    """
    Alternative HTTP transport using `curl_cffi` for browser TLS fingerprint matching.
    Falls back gracefully to `RequestsHttpTransport` if `curl_cffi` module is unavailable.
    """

    def __init__(self):
        try:
            import curl_cffi.requests as curl_req
            self._curl_req = curl_req
            self._available = True
        except ImportError:
            self._available = False
            self._fallback = RequestsHttpTransport()

    def send_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: float = 10.0
    ) -> Tuple[Optional[int], Dict[str, str], Dict[str, str], bytes, int, Optional[str]]:
        if not self._available:
            return self._fallback.send_request(url, method, headers, cookies, proxy, timeout)

        req_headers = dict(headers) if headers else {}
        req_cookies = dict(cookies) if cookies else {}
        proxies = {"http": proxy, "https": proxy} if proxy else None

        start_t = time.perf_counter()
        try:
            resp = self._curl_req.request(
                method=method,
                url=url,
                headers=req_headers,
                cookies=req_cookies,
                proxies=proxies,
                timeout=timeout,
                impersonate="chrome110"
            )
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            res_headers = dict(resp.headers)
            res_cookies = dict(resp.cookies)
            content_bytes = resp.content or b""
            return resp.status_code, res_headers, res_cookies, content_bytes, elapsed_ms, None
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)
            return None, {}, {}, b"", elapsed_ms, f"curl_cffi request failed: {str(e)}"


class PureHttpEngine:
    """
    High-level Pure HTTP acquisition engine coordinating transport execution,
    session management, structured error classification, and metrics collection.
    """

    def __init__(
        self,
        transport: Optional[HttpTransport] = None,
        session_manager: Optional[SessionManager] = None
    ):
        self.transport = transport or RequestsHttpTransport()
        self.session_manager = session_manager or SessionManager()

    def acquire(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: float = 10.0,
        session_id: Optional[str] = None,
        domain: Optional[str] = None,
        country: str = "US"
    ) -> HttpAcquisitionResponse:
        req_headers = dict(headers) if headers else {}
        req_cookies = dict(cookies) if cookies else {}
        bound_session: Optional[SessionBundle] = None
        session_assisted = False
        session_reused = False
        session_invalidated = False
        session_reuse_count = 0

        # 1. Session Binding & Inheritance
        if session_id:
            bound_session = self.session_manager.get_session(session_id)
            if bound_session:
                session_assisted = True
                session_reused = bool(bound_session.reuse_count > 0)
                session_reuse_count = bound_session.reuse_count + 1
                self.session_manager.increment_reuse_count(session_id)
                # Merge session cookies and headers
                for k, v in bound_session.cookies.items():
                    if k not in req_cookies:
                        req_cookies[k] = v
                for k, v in bound_session.headers.items():
                    if k not in req_headers:
                        req_headers[k] = v
                if bound_session.user_agent and "User-Agent" not in req_headers:
                    req_headers["User-Agent"] = bound_session.user_agent
                if bound_session.proxy_binding and not proxy:
                    proxy = bound_session.proxy_binding

        # Ensure default User-Agent if not provided
        if "User-Agent" not in req_headers:
            req_headers["User-Agent"] = "NeurixNavigator-HTTP/1.0"

        # 2. Transport Execution
        status_code, res_headers, res_cookies, content_bytes, elapsed_ms, err_msg = self.transport.send_request(
            url=url,
            method=method,
            headers=req_headers,
            cookies=req_cookies,
            proxy=proxy,
            timeout=timeout
        )

        byte_count = len(content_bytes) if content_bytes else 0
        text = content_bytes.decode("utf-8", errors="ignore") if content_bytes else ""

        # 3. Success & Error Classification
        success = bool(status_code and 200 <= status_code < 400 and byte_count > 100)
        failure_category = None

        if not success:
            if err_msg and "time" in err_msg.lower():
                failure_category = FailureCategory.TIMEOUT.value
            elif status_code == 429:
                failure_category = FailureCategory.RATE_LIMIT.value
            elif status_code in (403, 401) or "block" in (err_msg or "").lower():
                failure_category = FailureCategory.BLOCK_PAGE.value
            elif status_code and status_code >= 500:
                failure_category = FailureCategory.PROVIDER_ERROR.value
            elif err_msg and "connect" in err_msg.lower():
                failure_category = FailureCategory.PROVIDER_ERROR.value
            elif not status_code:
                failure_category = FailureCategory.PROVIDER_ERROR.value
            else:
                failure_category = FailureCategory.VALIDATION_FAILED.value

        # 4. Session State Update
        active_sid = bound_session.session_id if bound_session else None
        if active_sid:
            if res_cookies:
                self.session_manager.update_session(active_sid, cookies=res_cookies)
            if success:
                self.session_manager.mark_healthy(active_sid)
                session_invalidated = False
            else:
                self.session_manager.mark_unhealthy(active_sid)
                session_invalidated = True

        return HttpAcquisitionResponse(
            url=url,
            status_code=status_code,
            headers=res_headers,
            cookies=res_cookies,
            content=content_bytes,
            text=text,
            elapsed_ms=elapsed_ms,
            byte_count=byte_count,
            success=success,
            error=err_msg or (None if success else f"HTTP status {status_code}"),
            failure_category=failure_category,
            session_id=active_sid,
            session_assisted=session_assisted,
            session_reused=session_reused,
            session_invalidated=session_invalidated,
            session_reuse_count=session_reuse_count
        )
