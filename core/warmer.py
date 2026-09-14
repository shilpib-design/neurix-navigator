"""
Generic Session Warmer Abstraction & Reference Mock Warmer for Neurix Navigator v0.1 Core.
Provides a pluggable interface for browser-assisted or synthetic session warming.
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from core.models import AcquisitionRequest
from core.session import SessionBundle, SessionPool
from core.intelligence import TargetIntelligence


class SessionWarmer(ABC):
    """
    Abstract interface for session warming workers.
    Concrete implementations can plug in Playwright, CDP, Puppeteer, or synthetic session warmers.
    """

    @abstractmethod
    def warm(
        self,
        request: AcquisitionRequest,
        session_pool: Optional[SessionPool] = None,
        ttl_seconds: Optional[float] = 3600.0
    ) -> SessionBundle:
        """
        Warms a session for the target request and returns a populated SessionBundle.
        If a session_pool is provided, the session is automatically added to the pool.
        """
        pass


class MockSessionWarmer(SessionWarmer):
    """
    In-memory mock session warmer for deterministic testing without external browser or network calls.
    """

    def __init__(
        self,
        warmer_id: str = "mock_warmer",
        default_cookies: Optional[Dict[str, str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        default_user_agent: Optional[str] = None
    ):
        self.warmer_id = warmer_id
        self.default_cookies = default_cookies or {"session_token": "warmed_mock_token_123", "user_auth": "valid"}
        self.default_headers = default_headers or {"X-Warmed-By": "MockSessionWarmer"}
        self.default_user_agent = default_user_agent or "Mozilla/5.0 (MockWarmer; Linux x86_64) AppleWebKit/537.36"
        self.warm_count = 0

    def warm(
        self,
        request: AcquisitionRequest,
        session_pool: Optional[SessionPool] = None,
        ttl_seconds: Optional[float] = 3600.0
    ) -> SessionBundle:
        self.warm_count += 1
        profile = TargetIntelligence.analyze(request)
        sid = f"warmed_{self.warmer_id}_{uuid.uuid4().hex[:8]}"
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else 3600.0
        expires_at = (now + ttl) if ttl > 0 else None

        bundle = SessionBundle(
            session_id=sid,
            domain=profile.domain,
            country=profile.inferred_country,
            target=profile.target_type,
            proxy_binding=request.parameters.get("proxy"),
            user_agent=self.default_user_agent,
            cookies=dict(self.default_cookies),
            headers=dict(self.default_headers),
            created_at=now,
            expires_at=expires_at,
            status="healthy",
            reuse_count=0,
            last_validation=now,
            metadata={"warmer_id": self.warmer_id, "warm_index": self.warm_count}
        )

        if session_pool:
            session_pool.add_session(bundle)

        return bundle
