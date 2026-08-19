import logging
from typing import Optional
from data_mining.llm.base import LLMProvider
from data_mining.llm.factory import get_llm_provider
from data_mining.models.schemas import ModelInfo

logger = logging.getLogger("data_mining.extractors.model")


class ModelExtractor:
    """
    Extracts structured model metadata from webpage text.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def extract_model(self, raw_text: str, source_url: str, query_id: Optional[int] = None) -> Optional[ModelInfo]:
        if not raw_text or len(raw_text.strip()) < 50:
            return None

        model_info = self.llm.extract_model_info(raw_text, source_url)
        if model_info:
            model_info.discovered_by_query_id = query_id
            if source_url not in model_info.source_urls:
                model_info.source_urls.append(source_url)
        return model_info
