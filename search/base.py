from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    source: str = "web_search"
    query_id: Optional[int] = None


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5, query_id: Optional[int] = None) -> List[SearchResult]:
        """Performs search and returns search results."""
        pass
