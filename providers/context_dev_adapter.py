import os
import requests
from typing import Dict, Any, Tuple, Optional
from .base import BaseProvider

class ContextDevProvider(BaseProvider):
    def __init__(self):
        super().__init__(name="Context.dev", env_var="CONTEXT_DEV_API_KEY")

    def get_api_key(self) -> str:
        key = os.getenv("CONTEXT_DEV_API_KEY", "").strip()
        if not key:
            key = os.getenv("CONTEXT_API_KEY", "").strip()
        return key

    def _fetch_raw(self, target: Dict[str, Any], api_key: str) -> Tuple[Optional[int], bytes, str]:
        target_url = target.get("url", "")
        endpoint = "https://api.context.dev/v1/web/scrape/html"
        params = {
            "url": target_url
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "NAVIGATOR-01/1.0"
        }
        
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        status_code = response.status_code
        content_type = response.headers.get("Content-Type", "text/html")

        if status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and "html" in data:
                    html_content = data["html"]
                    return status_code, html_content.encode("utf-8"), "text/html"
            except Exception:
                pass

        return status_code, response.content, content_type
