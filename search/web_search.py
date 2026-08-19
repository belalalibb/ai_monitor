import logging
import re
from typing import List, Optional
from urllib.parse import parse_qs, unquote, urlparse
from bs4 import BeautifulSoup
import httpx
from data_mining.config import settings
from data_mining.core.normalizer import canonicalize_url
from data_mining.search.base import SearchProvider, SearchResult

logger = logging.getLogger("data_mining.search")


class WebSearchProvider(SearchProvider):
    """
    Web search provider that performs queries and extracts organic search results.
    """

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def search(self, query: str, max_results: int = 5, query_id: Optional[int] = None) -> List[SearchResult]:
        results: List[SearchResult] = []
        try:
            # DuckDuckGo HTML search endpoint
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}

            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=self.headers) as client:
                res = client.post(url, data=data)
                if res.status_code != 200:
                    logger.warning(f"Search request returned status {res.status_code}")
                    return results

                soup = BeautifulSoup(res.text, "html.parser")
                for result_div in soup.find_all("div", class_=re.compile(r"result\b")):
                    title_elem = result_div.find("a", class_="result__a")
                    snippet_elem = result_div.find("a", class_="result__snippet")

                    if not title_elem:
                        continue

                    raw_href = title_elem.get("href", "")
                    # Extract target URL if routed through DDG redirect
                    target_url = raw_href
                    if "duckduckgo.com/l/?" in raw_href or "uddg=" in raw_href:
                        parsed = urlparse(raw_href)
                        qs = parse_qs(parsed.query)
                        if "uddg" in qs:
                            target_url = unquote(qs["uddg"][0])

                    canonical = canonicalize_url(target_url)
                    if not canonical.startswith("http"):
                        continue

                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(
                        SearchResult(
                            title=title,
                            url=canonical,
                            snippet=snippet,
                            source="duckduckgo",
                            query_id=query_id,
                        )
                    )

                    if len(results) >= max_results:
                        break

        except Exception as e:
            logger.error(f"Search error for query '{query}': {e}")

        return results
