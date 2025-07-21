from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    """
    Configuration class for MicroSaaS client.
    It loads environment variables and sets up constants for URLs, headers, and paths.
    """

    # ---------- URLs ----------
    SUPABASE_URL = "https://xvndstojqjjnwqgxibxa.supabase.co/rest/v1/micro_saas_ideas"
    GENERATOR_URL = "https://www.findmicrosaasideas.com/api/micro-saas-ideas-generator"
    PROXY_PING_URL = "https://ipv4.webshare.io/"

    # ---------- Auth ----------
    API_KEY = os.getenv("SUPABASE_APIKEY")
    USER_ID = "01b7b465-e18d-4340-9b2c-1e89cc7b1e57"

    # ---------- Timing ----------
    REQUEST_DELAY = 0.5  # seconds
    TIMEOUT = 30
    SHORT_TIMEOUT = 3

    # ---------- Paths ----------
    CACHE_DIR = Path(".cache")
    CACHE_DIR.mkdir(exist_ok=True)

    # ---------- Headers ----------
    BASE_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
        "Accept": "application/json",
        "apikey": API_KEY,
        "authorization": f"Bearer {API_KEY}",
        "accept-profile": "public",
    }
