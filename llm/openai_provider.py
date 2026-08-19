import json
import logging
from typing import List, Optional
import httpx
from data_mining.config import settings
from data_mining.llm.base import LLMProvider
from data_mining.llm.rule_based_fallback import RuleBasedFallbackProvider
from data_mining.models.enums import ComparisonStatus, DiscoveryType, Priority
from data_mining.models.schemas import ComparisonResult, FreeServiceInfo, ModelInfo, ProjectCapabilityMap

logger = logging.getLogger("data_mining.llm.openai")


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.base_url = f"{base_url.rstrip('/')}/chat/completions"
        self.fallback = RuleBasedFallbackProvider()

    def _call(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self.api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
                res = client.post(self.base_url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")
        return None

    def compare_capabilities(
        self,
        item_name: str,
        provider: str,
        item_type: DiscoveryType,
        discovered_capabilities: List[str],
        project_map: ProjectCapabilityMap,
    ) -> ComparisonResult:
        if not self.api_key:
            return self.fallback.compare_capabilities(item_name, provider, item_type, discovered_capabilities, project_map)

        system_prompt = (
            "Compare new AI discovery against current project capabilities. Return JSON with keys: "
            "status ('PROJECT_ALREADY_HAS' | 'PROJECT_PARTIAL_SUPPORT' | 'PROJECT_DOES_NOT_HAVE'), "
            "new_capabilities, existing_capabilities, equivalence_reasoning, priority, confidence_score."
        )
        user_prompt = (
            f"Discovery: {item_name} by {provider}\nCapabilities: {discovered_capabilities}\n"
            f"Project Models: {project_map.models}\nProject Capabilities: {project_map.capabilities}"
        )
        resp = self._call(system_prompt, user_prompt)
        if resp:
            try:
                data = json.loads(resp)
                return ComparisonResult(
                    item_type=item_type,
                    item_name=item_name,
                    provider=provider,
                    status=ComparisonStatus(data.get("status", "PROJECT_DOES_NOT_HAVE")),
                    new_capabilities=data.get("new_capabilities", []),
                    existing_capabilities=data.get("existing_capabilities", []),
                    equivalence_reasoning=data.get("equivalence_reasoning", ""),
                    priority=Priority(data.get("priority", "HIGH")),
                    confidence_score=float(data.get("confidence_score", 0.9)),
                    evidence="Evaluated with OpenAI LLM",
                )
            except Exception as e:
                logger.error(f"Error parsing OpenAI response: {e}")

        return self.fallback.compare_capabilities(item_name, provider, item_type, discovered_capabilities, project_map)

    def extract_model_info(self, raw_text: str, source_url: str) -> Optional[ModelInfo]:
        if not self.api_key:
            return self.fallback.extract_model_info(raw_text, source_url)
        # Similar delegation with fallback
        return self.fallback.extract_model_info(raw_text, source_url)

    def extract_free_service_info(self, raw_text: str, source_url: str) -> Optional[FreeServiceInfo]:
        if not self.api_key:
            return self.fallback.extract_free_service_info(raw_text, source_url)
        return self.fallback.extract_free_service_info(raw_text, source_url)

    def generate_search_queries(
        self,
        category: str,
        existing_queries: List[str],
        recent_discoveries: List[str],
        count: int = 5,
    ) -> List[str]:
        if not self.api_key:
            return self.fallback.generate_search_queries(category, existing_queries, recent_discoveries, count)
        return self.fallback.generate_search_queries(category, existing_queries, recent_discoveries, count)
