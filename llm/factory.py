import logging
from typing import Optional
from data_mining.config import settings
from data_mining.llm.base import LLMProvider
from data_mining.llm.gemini_provider import GeminiProvider
from data_mining.llm.groq_provider import GroqProvider
from data_mining.llm.openai_provider import OpenAIProvider
from data_mining.llm.rule_based_fallback import RuleBasedFallbackProvider

logger = logging.getLogger("data_mining.llm.factory")


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    name = (provider_name or settings.COMPARISON_PROVIDER).lower()

    if name == "groq":
        return GroqProvider()
    elif name in ("openai", "chatgpt"):
        return OpenAIProvider()
    elif name in ("gemini", "google"):
        return GeminiProvider()
    elif name in ("rule_based", "fallback", "offline"):
        return RuleBasedFallbackProvider()
    else:
        logger.info(f"Unrecognized provider '{name}'. Defaulting to Groq with fallback.")
        return GroqProvider()
