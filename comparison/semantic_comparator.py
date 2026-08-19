import logging
from typing import List, Optional
from data_mining.core.project_knowledge import ProjectKnowledgeBase
from data_mining.llm.base import LLMProvider
from data_mining.llm.factory import get_llm_provider
from data_mining.models.enums import DiscoveryType
from data_mining.models.schemas import ComparisonResult, FreeServiceInfo, ModelInfo

logger = logging.getLogger("data_mining.comparison")


class SemanticComparator:
    """
    Evaluates new discoveries against current project capabilities map
    using LLM reasoning and semantic equivalence clusters.
    """

    def __init__(
        self,
        knowledge_base: Optional[ProjectKnowledgeBase] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        self.kb = knowledge_base or ProjectKnowledgeBase()
        self.llm = llm_provider or get_llm_provider()

    def compare_model(self, model: ModelInfo) -> ComparisonResult:
        cap_map = self.kb.get_map()

        # Build list of discovered capability tags
        discovered_caps: List[str] = list(model.modalities)
        if model.reasoning:
            discovered_caps.append("reasoning")
        if model.tools:
            discovered_caps.append("tool_calling")
        if model.structured_output:
            discovered_caps.append("structured_outputs")
        if model.vision:
            discovered_caps.append("vision")
        if model.coding:
            discovered_caps.append("coding")
        if model.open_weights:
            discovered_caps.append("open_weights")
        if model.context_window and model.context_window >= 128000:
            discovered_caps.append(f"{model.context_window // 1024}k_context")

        return self.llm.compare_capabilities(
            item_name=model.model_name,
            provider=model.provider,
            item_type=DiscoveryType.MODEL,
            discovered_capabilities=discovered_caps,
            project_map=cap_map,
        )

    def compare_free_service(self, service: FreeServiceInfo) -> ComparisonResult:
        cap_map = self.kb.get_map()

        caps = [f"free_status_{service.free_status.value}"]
        if service.api_available:
            caps.append("free_api_access")

        return self.llm.compare_capabilities(
            item_name=service.service_name,
            provider=service.domain,
            item_type=DiscoveryType.FREE_SERVICE,
            discovered_capabilities=caps,
            project_map=cap_map,
        )
