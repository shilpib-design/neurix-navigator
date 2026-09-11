import requests
from typing import Dict, Any, Tuple, Optional
from .base import BaseProvider

class ScrapflyProvider(BaseProvider):
    def __init__(self):
        super().__init__(name="Scrapfly", env_var="SCRAPFLY_API_KEY")

    def _fetch_raw(self, target: Dict[str, Any], api_key: str) -> Tuple[Optional[int], bytes, str]:
        target_url = target.get("url", "")
        endpoint = "https://api.scrapfly.io/scrape"
        params = {
            "key": api_key,
            "url": target_url
        }
        headers = {
            "User-Agent": "NAVIGATOR-01/1.0"
        }
        
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        status_code = response.status_code
        content_type = response.headers.get("Content-Type", "text/html")
        
        if status_code == 200:
            try:
                data = response.json()
                if "result" in data and "content" in data["result"]:
                    raw_html = data["result"]["content"]
                    return status_code, raw_html.encode("utf-8"), "text/html"
            except Exception:
                pass

        return status_code, response.content, content_type
