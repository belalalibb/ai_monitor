import logging
import random
import time
from typing import Dict, Optional, Tuple
import httpx
from data_mining.config import settings
from data_mining.core.normalizer import extract_domain
from data_mining.core.security import is_url_safe_to_fetch

logger = logging.getLogger("data_mining.fetcher")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
]


class HttpFetcher:
    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self._last_domain_request: Dict[str, float] = {}

    def _respect_rate_limit(self, domain: str) -> None:
        last = self._last_domain_request.get(domain, 0.0)
        elapsed = time.time() - last
        delay = settings.RATE_LIMIT_DOMAIN_DELAY
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_domain_request[domain] = time.time()

    def fetch_url(self, url: str, max_retries: int = 2) -> Optional[Tuple[str, int]]:
        """
        Fetches web page content with rate limiting, user agent rotation,
        and exponential retry backoff. Returns (html_content, status_code).
        """
        # SSRF guard: refuse to fetch internal / private / metadata addresses
        if not is_url_safe_to_fetch(url):
            logger.warning(f"Blocked unsafe URL (SSRF guard): {url}")
            return None

        domain = extract_domain(url)
        self._respect_rate_limit(domain)

        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=headers,
                    verify=True,
                ) as client:
                    response = client.get(url)
                    if response.status_code == 200:
                        return response.text, response.status_code
                    elif response.status_code in (403, 404, 410, 429):
                        logger.warning(f"Fetch {url} returned HTTP {response.status_code}")
                        return None
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries:
                    time.sleep(1.5 * (attempt + 1))

        return None
