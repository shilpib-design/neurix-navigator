import requests
from typing import Dict, Any, Tuple, Optional
from .base import BaseProvider

class StringProvider(BaseProvider):
    def __init__(self):
        super().__init__(name="String", env_var="STRING_API_KEY")

    def _fetch_raw(self, target: Dict[str, Any], api_key: str) -> Tuple[Optional[int], bytes, str]:
        target_url = target.get("url", "")
        endpoint = "https://request.usestring.ai/v1/fetch"
        payload = {
            "url": target_url,
            "format": "raw"
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NAVIGATOR-01/1.0"
        }
        
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        content_type = response.headers.get("Content-Type", "text/html")
        return response.status_code, response.content, content_type
