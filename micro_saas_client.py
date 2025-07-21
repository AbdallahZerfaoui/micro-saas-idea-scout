import os
import json
import time
import random
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class MicroSaasClient:
    """
    Fetch Micro-SaaS ideas by keyword while:
      - caching keyword → idea-id
      - rotating proxies
      - respecting rate limits
    """

    # ------------------------ config ------------------------ #
    SUPABASE_URL = "https://xvndstojqjjnwqgxibxa.supabase.co/rest/v1/micro_saas_ideas"
    GENERATOR_URL = "https://www.findmicrosaasideas.com/api/micro-saas-ideas-generator"

    CACHE_DIR = Path(".cache")
    CACHE_DIR.mkdir(exist_ok=True)

    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 0.5))
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept": "application/json",
        "apikey": os.getenv("SUPABASE_APIKEY"),
        "authorization": f"Bearer {os.getenv('SUPABASE_APIKEY')}",
        "accept-profile": "public",
    }

    def __init__(self):
        self.proxies: dict = {
            "http": os.getenv("PROXY_URL"),
            "https": os.getenv("PROXY_URL"),
        }
        self._current_proxy_index = 0

    # ---------- proxy health-check ----------
    PING_URL = "https://httpbin.org/ip"

    def ping_proxy(self) -> bool:
        """Return True if proxy answers within 5 s."""
        try:
            resp = requests.head(
                self.PING_URL,
                proxies=self.proxies,
                timeout=5,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def healthy_proxy_check(self) -> bool:
        """Return only proxies that pass the ping test."""
        print("[INFO] checking proxies …")
        healthy = self.ping_proxy()
        print(f"[INFO] The proxy is {'healthy' if healthy else 'unhealthy'}.")
        return healthy
    # --------------- caching --------------- #
    
    def _cache_file(self, keyword: str) -> Path:
        safe = "".join(c if c.isalnum() else "_" for c in keyword.lower())
        return self.CACHE_DIR / f"{safe}.json"

    def _load_cached(self, keyword: str) -> Optional[str]:
        cache = self._cache_file(keyword)
        if cache.exists():
            return json.loads(cache.read_text()).get("id")
        return None

    def _save_cache(self, keyword: str, data: dict) -> None:
        std_keyword = keyword.lower().replace(" ", "_")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary.")
        if "id" not in data:
            raise ValueError("Data must contain an 'id' field.")
        elif len(data.keys()) == 1:
            file_name = f"keyword_id_{std_keyword}"
        else:
            file_name = f"ideas_{std_keyword}"
        self._cache_file(file_name).write_text(json.dumps(data, indent=2))

    # --------------- API calls --------------- #
    def _call_id_generator(self, keyword: str) -> Optional[str]:
        """
        Call the micro-saas idea generator API with a keyword.
        Returns the idea ID if successful, None otherwise.
        """
        payload = {"niche": keyword, "userId": "01b7b465-e18d-4340-9b2c-1e89cc7b1e57"}
        # proxies = self._next_proxy()
        try:
            resp = requests.post(
                self.GENERATOR_URL,
                json=payload,
                headers=self.HEADERS,
                proxies=self.proxies,
                timeout=15,
            )
            resp.raise_for_status()

            return resp.json().get("id")
        except requests.HTTPError as e:
            print(f"[ERROR] generator failed: {e}")
            return None
        except requests.RequestException as e:
            print(f"[WARN] generator failed: {e}")
            return None
        finally:
            time.sleep(self.REQUEST_DELAY)

    def _fetch_idea(self, idea_id: str) -> Dict[str, Any]:
        url = f"{self.SUPABASE_URL}?select=*&id=eq.{idea_id}"
        # proxies = self._next_proxy()
        resp = requests.get(
            url, headers=self.HEADERS, proxies=self.proxies, timeout=15
        ) 
        resp.raise_for_status()
        data = resp.json()
        return data[0] if isinstance(data, list) and data else {}

    # --------------- public API --------------- #
    def get_ideas(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        Return the full idea dict for a keyword (cached or fresh).
        """
        idea_id = self._load_cached(keyword)
        if not idea_id:
            print(f"[INFO] fetching new idea-id for '{keyword}' …")
            idea_id = self._call_id_generator(keyword)
            if not idea_id:
                return None
            self._save_cache(keyword, {"id": idea_id})

        ideas_dict = self._fetch_idea(idea_id)
        self._save_cache(keyword, ideas_dict)
        return ideas_dict

    def list_cached_keywords(self) -> List[str]:
        return [p.stem.replace("_", " ") for p in self.CACHE_DIR.glob("*.json")]


# ---------------- demo ---------------- #
# if __name__ == "__main__":
#     client = MicroSaasClient()
#     client.healthy_proxy_check()
#     kw = input("Keyword? ").strip()
#     ideas = client.get_ideas(kw)
#     if ideas:
#         print(json.dumps(ideas, indent=2))
#     else:
#         print("No idea found.")
