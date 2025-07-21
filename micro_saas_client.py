import os
import json
import time
import random
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging
import ast  # str to dict conversion
from config import Config


class ProxyManager:
    """
    Manages proxy rotation and health checks.
    """

    def __init__(self):
        self.proxies = {
            "http": os.getenv("PROXY_URL"),
            "https": os.getenv("PROXY_URL"),
        }
        self._current_proxy_index = 0

    def ping_proxy(self) -> bool:
        """Return True if proxy answers within 5 seconds."""
        try:
            resp = requests.head(
                Config.PROXY_PING_URL,
                proxies=self.proxies,
                timeout=Config.SHORT_TIMEOUT,
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def healthy_proxy_check(self) -> bool:
        """
        Return only proxies that pass the ping test.
        """
        print("[INFO] checking proxies …")
        healthy = self.ping_proxy()
        print(f"healthy: {healthy}")
        print(f"[INFO] The proxy is {'healthy' if healthy else 'unhealthy'}.")
        return healthy


class CacheManager:
    """
    Manages caching of keyword and ideas.
    """

    def __init__(self, cache_dir: Path = Path(".cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def cache_file(self, keyword: str) -> Path:
        safe = "".join(c if c.isalnum() else "_" for c in keyword.lower())
        return self.cache_dir / f"{safe}.json"

    def load_cached(self, keyword: str) -> Optional[str]:
        """Load cached idea-id for a keyword."""
        cache = self.cache_file(keyword)
        if cache.exists():
            print(f"[Info] Loading cached idea-id for '{keyword}'")
            return json.loads(cache.read_text()).get("id")
        return None

    def _createcache_file_names(self, keyword: str) -> tuple[str, str]:
        """
        Create standardized cache file names for keyword and ideas.
        Returns a tuple of (keyword_id_file_name, ideas_file_name).
        """
        if not keyword:
            raise ValueError("Keyword must not be empty.")
        if not isinstance(keyword, str):
            raise TypeError("Keyword must be a string.")
        std_keyword = keyword.lower().replace(" ", "_")
        kw_id_file_name = f"keyword_id_{std_keyword}"
        ideas_file_name = f"ideas_{std_keyword}"
        return kw_id_file_name, ideas_file_name

    def save_cache(self, keyword: str, data: dict) -> None:
        # std_keyword = keyword.lower().replace(" ", "_")
        kw_id_file_name, ideas_file_name = self._createcache_file_names(keyword)
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary.")
        if "id" not in data:
            raise ValueError("Data must contain an 'id' field.")
        elif len(data.keys()) == 1:
            self.cache_file(kw_id_file_name).write_text(json.dumps(data, indent=2))
        else:
            self.cache_file(ideas_file_name).write_text(json.dumps(data, indent=2))

    def list_cached_keywords(self) -> List[str]:
        return [p.stem.replace("_", " ") for p in self.cache_dir.glob("*.json")]


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

    REQUEST_DELAY = Config.REQUEST_DELAY
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
        self.cache_manager = CacheManager()

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
                timeout=30,
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

    def _fetch_ideas(self, idea_id: str) -> Dict[str, Any]:
        url = f"{self.SUPABASE_URL}?select=*&id=eq.{idea_id}"
        # proxies = self._next_proxy()
        resp = requests.get(url, headers=self.HEADERS, proxies=self.proxies, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data[0] if isinstance(data, list) and data else {}

    def _extract_ideas(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract ideas from the fetched data.
        Returns a list of ideas.
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary.")
        if "ideas" not in data:
            raise KeyError("Data must contain an 'ideas' field.")
        ideas_dict = (
            ast.literal_eval(str(data["ideas"]))
            if isinstance(data["ideas"], str)
            else {}
        )
        list_values = [value for _, value in ideas_dict.items()]
        results = []
        for idx in range(1, len(list_values), 2):
            results.append({list_values[idx - 1]: list_values[idx]})
        return results

    # --------------- public API --------------- #
    def get_ideas(self, keyword: str) -> Optional[Dict[str, Any]]:
        """
        Return the full idea dict for a keyword (cached or fresh).
        """
        idea_id = self.cache_manager.load_cached(keyword)
        if not idea_id:
            print(f"[INFO] fetching new idea-id for '{keyword}' …")
            idea_id = self._call_id_generator(keyword)
            if not idea_id:
                return None
            self.cache_manager.save_cache(keyword, {"id": idea_id})
        print(f"[INFO] Fetching ideas for keyword: '{keyword}' from the cache")
        ideas_dict = self._fetch_ideas(idea_id)
        self.cache_manager.save_cache(keyword, ideas_dict)
        return ideas_dict

    def deep_extract_ideas(self, keyword: str, limit: int = 12) -> List[Dict[str, Any]]:
        """
        Return a list of unique ideas for a keyword
        So the function will send several requests to the API
        until it reaches the limit or it reaches the limit of requests.
        """
        ideas = set()
        max_nbr_requests = 10
        idea_id = self._call_id_generator(keyword)
        while len(ideas) < limit and max_nbr_requests > 0:
            if not idea_id:
                idea_id = self._call_id_generator(keyword)
                print(
                    f"[INFO] No idea-id found for '{keyword}', generating a new one …"
                )
                continue
            ideas_dict = self._fetch_ideas(idea_id)
            # if not ideas_dict:
            #     continue
            ideas_list = self._extract_ideas(ideas_dict)
            for idea in ideas_list:
                if len(ideas) >= limit:
                    break
                ideas.add(tuple(idea.items()))
            idea_id = self._call_id_generator(keyword)
            print(f"[INFO] Found {len(ideas)} ideas so far for '{keyword}'")
            time.sleep(1.5)
            max_nbr_requests -= 1

        final_result = [dict(idea) for idea in ideas]
        results_file_name = f"ideas_{keyword.lower().replace(' ', '_')}_{limit}.json"
        self.cache_manager.cache_file(results_file_name).write_text(
            json.dumps(final_result, indent=2)
        )
        return final_result
