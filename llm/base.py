from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from data_mining.models.enums import DiscoveryType, FreeStatus
from data_mining.models.schemas import ComparisonResult, FreeServiceInfo, ModelInfo, ProjectCapabilityMap


class LLMProvider(ABC):
    """
    Abstract interface for LLM operations:
    - Semantic capability comparison
    - Model metadata extraction
    - Free AI platform extraction & validation
    - Dynamic search query generation
    - Relevance classification
    """

    @abstractmethod
    def compare_capabilities(
        self,
        item_name: str,
        provider: str,
        item_type: DiscoveryType,
        discovered_capabilities: List[str],
        project_map: ProjectCapabilityMap,
    ) -> ComparisonResult:
        """
        Compares discovered capabilities against the project's capability map.
        """
        pass

    @abstractmethod
    def extract_model_info(self, raw_text: str, source_url: str) -> Optional[ModelInfo]:
        """
        Extracts structured ModelInfo from raw scraped text.
        """
        pass

    @abstractmethod
    def extract_free_service_info(self, raw_text: str, source_url: str) -> Optional[FreeServiceInfo]:
        """
        Extracts FreeServiceInfo and verifies free tier limits/quotas.
        """
        pass

    @abstractmethod
    def generate_search_queries(
        self,
        category: str,
        existing_queries: List[str],
        recent_discoveries: List[str],
        count: int = 5,
    ) -> List[str]:
        """
        Generates dynamic, high-yield search queries.
        """
        pass
