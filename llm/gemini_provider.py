import logging
from typing import List, Optional
from data_mining.config import settings
from data_mining.llm.base import LLMProvider
from data_mining.llm.rule_based_fallback import RuleBasedFallbackProvider
from data_mining.models.enums import DiscoveryType
from data_mining.models.schemas import ComparisonResult, FreeServiceInfo, ModelInfo, ProjectCapabilityMap

logger = logging.getLogger("data_mining.llm.gemini")


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self.fallback = RuleBasedFallbackProvider()

    def compare_capabilities(
        self,
        item_name: str,
        provider: str,
        item_type: DiscoveryType,
        discovered_capabilities: List[str],
        project_map: ProjectCapabilityMap,
    ) -> ComparisonResult:
        return self.fallback.compare_capabilities(item_name, provider, item_type, discovered_capabilities, project_map)

    def extract_model_info(self, raw_text: str, source_url: str) -> Optional[ModelInfo]:
        return self.fallback.extract_model_info(raw_text, source_url)

    def extract_free_service_info(self, raw_text: str, source_url: str) -> Optional[FreeServiceInfo]:
        return self.fallback.extract_free_service_info(raw_text, source_url)

    def generate_search_queries(
        self,
        category: str,
        existing_queries: List[str],
        recent_discoveries: List[str],
        count: int = 5,
    ) -> List[str]:
        return self.fallback.generate_search_queries(category, existing_queries, recent_discoveries, count)
