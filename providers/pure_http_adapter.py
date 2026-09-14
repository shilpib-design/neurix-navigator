"""
Pure HTTP Provider Adapter for Neurix Navigator v0.1 Core.
Binds PureHttpEngine and SessionManager into Navigator's BaseProvider architecture.
"""

from typing import Dict, Any, Optional, Tuple
from providers.base import BaseProvider
from core.http_engine import PureHttpEngine, HttpTransport
from core.session import SessionManager


class PureHttpProvider(BaseProvider):
    """
    Acquisition adapter using Pure HTTP engine without browser requirements.
    """

    def __init__(
        self,
        name: str = "PureHTTP",
        engine: Optional[PureHttpEngine] = None,
        session_manager: Optional[SessionManager] = None,
        transport: Optional[HttpTransport] = None
    ):
        super().__init__(name=name, env_var="PURE_HTTP_ENABLED")
        self.session_manager = session_manager or SessionManager()
        self.engine = engine or PureHttpEngine(transport=transport, session_manager=self.session_manager)

    def is_configured(self) -> bool:
        # Pure HTTP requires no external API key, so it is configured by default
        return True

    def _fetch_raw(self, target: Dict[str, Any], api_key: str) -> Tuple[Optional[int], bytes, str]:
        url = target.get("url", "")
        headers = target.get("headers")
        cookies = target.get("cookies")
        proxy = target.get("proxy")
        timeout = target.get("timeout", 10.0)
        session_id = target.get("session_id")
        domain = target.get("domain", "Generic")
        country = target.get("country", "US")

        res = self.engine.acquire(
            url=url,
            headers=headers,
            cookies=cookies,
            proxy=proxy,
            timeout=timeout,
            session_id=session_id,
            domain=domain,
            country=country
        )

        content_type = res.headers.get("content-type", "text/html")
        return res.status_code, res.content, content_type
