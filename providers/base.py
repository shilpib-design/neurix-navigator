import os
import time
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

class BaseProvider(ABC):
    def __init__(self, name: str, env_var: str):
        self.name = name
        self.env_var = env_var

    def get_api_key(self) -> str:
        return os.getenv(self.env_var, "").strip()

    def is_configured(self) -> bool:
        return bool(self.get_api_key())

    @abstractmethod
    def _fetch_raw(self, target: Dict[str, Any], api_key: str) -> Tuple[Optional[int], bytes, str]:
        """
        Abstract method to fetch raw content from the provider.
        Must return a tuple of (status_code, content_bytes, content_type).
        """
        pass

    def fetch(self, target: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single raw content request for the given target,
        recording execution metrics and handling errors safely.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        target_name = target.get("name", "unknown")
        target_url = target.get("url", "")
        
        if not self.is_configured():
            return {
                "provider": self.name,
                "target": target_name,
                "url": target_url,
                "timestamp": timestamp,
                "elapsed_ms": 0,
                "status_code": None,
                "success": False,
                "content_type": "none",
                "response_size": 0,
                "error_message": f"Unconfigured: missing environment variable '{self.env_var}' in .env",
                "raw_content": None,
                "raw_response_path": None
            }

        api_key = self.get_api_key()
        start_time = time.perf_counter()
        
        status_code = None
        content_bytes = b""
        content_type = "unknown"
        error_message = None
        success = False

        try:
            status_code, content_bytes, content_type = self._fetch_raw(target, api_key)
            if status_code and 200 <= status_code < 300:
                success = True
            else:
                error_message = f"HTTP status {status_code}" if status_code else "Request failed without status code"
        except Exception as e:
            error_message = str(e)
            success = False

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "provider": self.name,
            "target": target_name,
            "url": target_url,
            "timestamp": timestamp,
            "elapsed_ms": elapsed_ms,
            "status_code": status_code,
            "success": success,
            "content_type": content_type,
            "response_size": len(content_bytes) if content_bytes else 0,
            "error_message": error_message,
            "raw_content": content_bytes if success and content_bytes else (content_bytes or None),
            "raw_response_path": None  # Will be set by run.py when saving to results/
        }
