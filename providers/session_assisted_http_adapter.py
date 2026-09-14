"""
Session-Assisted HTTP Provider Adapter for Neurix Navigator v0.1 Core.
Binds SessionPool, SessionWarmer, and PureHttpEngine into Navigator's BaseProvider architecture.
"""

from typing import Dict, Any, Optional, Tuple
from providers.base import BaseProvider
from core.http_engine import PureHttpEngine, HttpTransport, HttpAcquisitionResponse
from core.session import SessionPool, SessionBundle


class SessionAssistedHttpProvider(BaseProvider):
    """
    Acquisition adapter that attempts HTTP acquisition using a compatible warmed SessionBundle if available.
    Falls back gracefully to unassisted Pure HTTP acquisition if no valid session exists.
    """

    def __init__(
        self,
        name: str = "SessionAssistedHTTP",
        engine: Optional[PureHttpEngine] = None,
        session_pool: Optional[SessionPool] = None,
        transport: Optional[HttpTransport] = None
    ):
        super().__init__(name=name, env_var="SESSION_ASSISTED_HTTP_ENABLED")
        self.session_pool = session_pool or SessionPool()
        self.engine = engine or PureHttpEngine(transport=transport, session_manager=self.session_pool)

    def is_configured(self) -> bool:
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
        target_type = target.get("target_type", "generic")

        # 1. Compatible session lookup if session_id is not explicitly provided
        if not session_id:
            active_session = self.session_pool.get_compatible_session(
                domain=domain, country=country, target=target_type
            )
            if active_session:
                session_id = active_session.session_id

        # 2. Execute HTTP acquisition using engine
        res: HttpAcquisitionResponse = self.engine.acquire(
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

    def fetch(self, target: Dict[str, Any]) -> Dict[str, Any]:
        session_id = target.get("session_id")
        domain = target.get("domain", "Generic")
        country = target.get("country", "US")
        target_type = target.get("target_type", "generic")

        if not session_id:
            session_before = self.session_pool.get_compatible_session(
                domain=domain, country=country, target=target_type
            )
        else:
            session_before = self.session_pool.get_session(session_id)

        result = super().fetch(target)

        session_after = self.session_pool.get_session(session_before.session_id) if session_before else None

        result["session_id"] = session_before.session_id if session_before else None
        result["session_assisted"] = bool(session_before)
        result["session_reused"] = bool(session_before and session_before.reuse_count > 1)
        result["session_invalidated"] = bool(session_after and session_after.status == "unhealthy")
        result["session_reuse_count"] = session_after.reuse_count if session_after else (session_before.reuse_count if session_before else 0)

        return result
