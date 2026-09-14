"""
Generic Session Manager & Session Bundle for Neurix Navigator v0.1 Core.
Tracks in-memory session metadata, cookies, headers, proxy bindings, and health state.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class SessionBundle:
    session_id: str
    domain: str
    country: str = "US"
    target: str = "generic"
    proxy_binding: Optional[str] = None
    user_agent: Optional[str] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    status: str = "healthy"  # "healthy", "unhealthy", "expired"
    reuse_count: int = 0
    last_validation: Optional[float] = None

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if self.status == "expired":
            return True
        if self.expires_at is not None and now >= self.expires_at:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "domain": self.domain,
            "country": self.country,
            "target": self.target,
            "proxy_binding": self.proxy_binding,
            "user_agent": self.user_agent,
            "cookies": dict(self.cookies),
            "headers": dict(self.headers),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "reuse_count": self.reuse_count,
            "last_validation": self.last_validation
        }


class SessionManager:
    """
    In-memory session manager handling lifecycle, updates, expiry, and health tracking.
    """

    def __init__(self, default_ttl_seconds: float = 3600.0):
        self.default_ttl_seconds = default_ttl_seconds
        self._sessions: Dict[str, SessionBundle] = {}

    def create_session(
        self,
        domain: str,
        country: str = "US",
        target: str = "generic",
        proxy_binding: Optional[str] = None,
        user_agent: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        ttl_seconds: Optional[float] = None,
        session_id: Optional[str] = None
    ) -> SessionBundle:
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = (now + ttl) if ttl > 0 else None

        bundle = SessionBundle(
            session_id=sid,
            domain=domain,
            country=country,
            target=target,
            proxy_binding=proxy_binding,
            user_agent=user_agent or "NeurixNavigator-HTTP/1.0",
            cookies=dict(cookies) if cookies else {},
            headers=dict(headers) if headers else {},
            created_at=now,
            expires_at=expires_at,
            status="healthy",
            reuse_count=0,
            last_validation=now
        )
        self._sessions[sid] = bundle
        return bundle

    def get_session(self, session_id: str) -> Optional[SessionBundle]:
        bundle = self._sessions.get(session_id)
        if not bundle:
            return None
        if bundle.is_expired():
            bundle.status = "expired"
            return None
        return bundle

    def get_active_session(
        self, domain: str, country: Optional[str] = None
    ) -> Optional[SessionBundle]:
        now = time.time()
        for bundle in self._sessions.values():
            if bundle.domain.lower() == domain.lower():
                if country and bundle.country.upper() != country.upper():
                    continue
                if bundle.status == "healthy" and not bundle.is_expired(now):
                    return bundle
        return None

    def update_session(
        self,
        session_id: str,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        status: Optional[str] = None
    ) -> Optional[SessionBundle]:
        bundle = self.get_session(session_id)
        if not bundle:
            return None
        if cookies:
            bundle.cookies.update(cookies)
        if headers:
            bundle.headers.update(headers)
        if status:
            bundle.status = status
        return bundle

    def mark_healthy(self, session_id: str) -> bool:
        bundle = self._sessions.get(session_id)
        if bundle:
            bundle.status = "healthy"
            bundle.last_validation = time.time()
            return True
        return False

    def mark_unhealthy(self, session_id: str) -> bool:
        bundle = self._sessions.get(session_id)
        if bundle:
            bundle.status = "unhealthy"
            return True
        return False

    def increment_reuse_count(self, session_id: str) -> int:
        bundle = self.get_session(session_id)
        if bundle:
            bundle.reuse_count += 1
            return bundle.reuse_count
        return 0

    def is_expired(self, session_id: str) -> bool:
        bundle = self._sessions.get(session_id)
        if not bundle:
            return True
        return bundle.is_expired()

    def remove_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def purge_expired_sessions(self) -> int:
        now = time.time()
        expired_ids = [
            sid for sid, bundle in self._sessions.items()
            if bundle.is_expired(now)
        ]
        for sid in expired_ids:
            del self._sessions[sid]
        return len(expired_ids)

    def list_sessions(self, domain: Optional[str] = None) -> List[SessionBundle]:
        if domain:
            return [
                b for b in self._sessions.values()
                if b.domain.lower() == domain.lower()
            ]
        return list(self._sessions.values())
