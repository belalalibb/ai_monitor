import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from data_mining.config import settings
from data_mining.core.security import wrap_untrusted_content
from data_mining.llm.base import LLMProvider
from data_mining.llm.rule_based_fallback import RuleBasedFallbackProvider
from data_mining.models.enums import ComparisonStatus, DiscoveryType, FreeStatus, Priority, SourceReliability
from data_mining.models.schemas import ComparisonResult, EvidenceRecord, FreeServiceInfo, ModelInfo, ProjectCapabilityMap

logger = logging.getLogger("data_mining.llm.groq")

# Sane bounds for LLM-reported context windows (tokens)
_MIN_CONTEXT_WINDOW = 256
_MAX_CONTEXT_WINDOW = 100_000_000


def _safe_confidence(value: Any, default: float = 0.85) -> float:
    """Coerces an LLM-supplied confidence into a float clamped to [0.0, 1.0]."""
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return default
    if conf != conf:  # NaN check
        return default
    return max(0.0, min(1.0, conf))


def _safe_enum(enum_cls, value: Any, default):
    """Coerces an LLM-supplied string into an Enum member, falling back safely on invalid values."""
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        logger.warning(f"LLM returned invalid {enum_cls.__name__} value {value!r}; using {default!r}")
        return default


def _safe_str_list(value: Any, max_items: int = 50, max_len: int = 500) -> List[str]:
    """Sanitizes an LLM-supplied list into a bounded list of trimmed strings."""
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value[:max_items]:
        if isinstance(item, str) and item.strip():
            out.append(item.strip()[:max_len])
        elif isinstance(item, (int, float)):
            out.append(str(item))
    return out


def _safe_context_window(value: Any, default: int = 128000) -> int:
    """Coerces an LLM-supplied context window into a sane integer range."""
    try:
        cw = int(value)
    except (TypeError, ValueError):
        return default
    if cw < _MIN_CONTEXT_WINDOW or cw > _MAX_CONTEXT_WINDOW:
        return default
    return cw


class GroqProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.fallback = RuleBasedFallbackProvider()

    def _call_groq(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> Optional[str]:
        if not self.api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
                res = client.post(self.base_url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"Groq API returned status {res.status_code}: {res.text}")
                    return None
        except Exception as e:
            logger.warning(f"Groq API call failed ({e}). Using rule-based fallback.")
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
            "You are an expert AI Capability Comparator. Compare a new AI discovery against the current project baseline.\n"
            "Output strictly valid JSON with keys:\n"
            "- status: 'PROJECT_ALREADY_HAS' | 'PROJECT_PARTIAL_SUPPORT' | 'PROJECT_DOES_NOT_HAVE' | 'PROJECT_UNKNOWN'\n"
            "- new_capabilities: list of genuinely new capability strings\n"
            "- existing_capabilities: list of capabilities already in project baseline\n"
            "- equivalence_reasoning: explanation of semantic equivalences (e.g., function calling == tool calling)\n"
            "- priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'\n"
            "- confidence_score: float between 0.0 and 1.0\n"
        )
        user_prompt = (
            f"DISCOVERY:\nName: {item_name}\nProvider: {provider}\nType: {item_type.value}\n"
            f"Capabilities: {discovered_capabilities}\n\n"
            f"PROJECT CURRENT STATE:\n"
            f"Models: {project_map.models}\n"
            f"Providers: {project_map.providers}\n"
            f"Capabilities: {project_map.capabilities}\n"
            f"Features: {project_map.features}\n"
        )

        resp = self._call_groq(system_prompt, user_prompt, json_mode=True)
        if resp:
            try:
                data = json.loads(resp)
                if not isinstance(data, dict):
                    raise ValueError("LLM response is not a JSON object")
                return ComparisonResult(
                    item_type=item_type,
                    item_name=item_name,
                    provider=provider,
                    status=_safe_enum(ComparisonStatus, data.get("status"), ComparisonStatus.PROJECT_DOES_NOT_HAVE),
                    new_capabilities=_safe_str_list(data.get("new_capabilities")),
                    existing_capabilities=_safe_str_list(data.get("existing_capabilities")),
                    equivalence_reasoning=str(data.get("equivalence_reasoning") or "LLM comparison evaluated")[:2000],
                    priority=_safe_enum(Priority, data.get("priority"), Priority.HIGH),
                    confidence_score=_safe_confidence(data.get("confidence_score"), 0.9),
                    evidence=f"Evaluated with Groq {self.model}",
                )
            except Exception as e:
                logger.error(f"Failed to parse Groq comparison JSON: {e}")

        return self.fallback.compare_capabilities(item_name, provider, item_type, discovered_capabilities, project_map)

    def extract_model_info(self, raw_text: str, source_url: str) -> Optional[ModelInfo]:
        if not self.api_key:
            return self.fallback.extract_model_info(raw_text, source_url)

        system_prompt = (
            "You are an AI Model Analyst. Extract model metadata from the provided webpage content.\n"
            "Output strictly valid JSON with keys:\n"
            "- provider: string\n"
            "- model_name: string\n"
            "- version: string\n"
            "- modalities: list of strings (e.g. ['text', 'vision'])\n"
            "- context_window: integer (number of tokens, e.g. 128000)\n"
            "- reasoning: boolean\n"
            "- tools: boolean\n"
            "- structured_output: boolean\n"
            "- vision: boolean\n"
            "- coding: boolean\n"
            "- open_weights: boolean\n"
            "- license: string or null\n"
            "- api_available: boolean\n"
            "- free_status: 'free' | 'free_tier' | 'trial' | 'open_weights' | 'paid_only' | 'unknown'\n"
            "- confidence_score: float\n"
        )
        safe_data = wrap_untrusted_content(raw_text, max_chars=6000)
        user_prompt = f"Source URL: {source_url}\n\n{safe_data}"

        resp = self._call_groq(system_prompt, user_prompt, json_mode=True)
        if resp:
            try:
                data = json.loads(resp)
                if not isinstance(data, dict):
                    raise ValueError("LLM response is not a JSON object")
                conf = _safe_confidence(data.get("confidence_score"), 0.85)
                modalities = _safe_str_list(data.get("modalities")) or ["text"]
                return ModelInfo(
                    provider=str(data.get("provider") or "Unknown")[:200],
                    model_name=str(data.get("model_name") or "AI Model")[:200],
                    version=str(data.get("version") or "1.0")[:100],
                    modalities=modalities,
                    context_window=_safe_context_window(data.get("context_window")),
                    reasoning=bool(data.get("reasoning", False)),
                    tools=bool(data.get("tools", False)),
                    structured_output=bool(data.get("structured_output", False)),
                    vision=bool(data.get("vision", False)),
                    coding=bool(data.get("coding", False)),
                    open_weights=bool(data.get("open_weights", False)),
                    license=data.get("license") if isinstance(data.get("license"), str) else None,
                    api_available=bool(data.get("api_available", True)),
                    free_status=_safe_enum(FreeStatus, data.get("free_status"), FreeStatus.UNKNOWN),
                    source_urls=[source_url],
                    confidence_score=conf,
                    evidence=EvidenceRecord(
                        source_url=source_url,
                        source_type=SourceReliability.SEARCH_RESULT,
                        extracted_fact=f"Model {data.get('model_name')} by {data.get('provider')}",
                        validation_checks=["groq_llm_extraction"],
                        reasoning="Extracted via Groq LLM parser",
                        confidence_score=conf,
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to parse Groq model extraction JSON: {e}")

        return self.fallback.extract_model_info(raw_text, source_url)

    def extract_free_service_info(self, raw_text: str, source_url: str) -> Optional[FreeServiceInfo]:
        if not self.api_key:
            return self.fallback.extract_free_service_info(raw_text, source_url)

        system_prompt = (
            "You are a Free AI Service Auditor. Analyze the webpage text for free AI offerings.\n"
            "Output strictly valid JSON with keys:\n"
            "- service_name: string\n"
            "- domain: string\n"
            "- models: list of model name strings\n"
            "- api_available: boolean\n"
            "- free_status: 'free' | 'free_tier' | 'trial' | 'open_weights' | 'paid_only' | 'unknown'\n"
            "- limits: string (exact limits or quotas)\n"
            "- quota_details: string\n"
            "- registration_required: boolean\n"
            "- payment_method_required: boolean\n"
            "- region_restrictions: string\n"
            "- confidence_score: float\n"
        )
        safe_data = wrap_untrusted_content(raw_text, max_chars=6000)
        user_prompt = f"Source URL: {source_url}\n\n{safe_data}"

        resp = self._call_groq(system_prompt, user_prompt, json_mode=True)
        if resp:
            try:
                data = json.loads(resp)
                if not isinstance(data, dict):
                    raise ValueError("LLM response is not a JSON object")
                conf = _safe_confidence(data.get("confidence_score"), 0.85)
                try:
                    fallback_domain = source_url.split("/")[2]
                except IndexError:
                    fallback_domain = "unknown"
                domain = data.get("domain")
                if not isinstance(domain, str) or not domain.strip():
                    domain = fallback_domain
                return FreeServiceInfo(
                    service_name=str(data.get("service_name") or "AI Service")[:200],
                    domain=domain.strip()[:255],
                    models=_safe_str_list(data.get("models")) or ["AI Model"],
                    api_available=bool(data.get("api_available", False)),
                    free_status=_safe_enum(FreeStatus, data.get("free_status"), FreeStatus.UNKNOWN),
                    limits=str(data.get("limits") or "Free tier quotas")[:1000],
                    quota_details=str(data.get("quota_details") or "")[:1000],
                    registration_required=bool(data.get("registration_required", True)),
                    payment_method_required=bool(data.get("payment_method_required", False)),
                    region_restrictions=str(data.get("region_restrictions") or "None")[:500],
                    official_documentation=source_url,
                    source_url=source_url,
                    confidence_score=conf,
                    evidence=EvidenceRecord(
                        source_url=source_url,
                        source_type=SourceReliability.SEARCH_RESULT,
                        extracted_fact=f"Free service {data.get('service_name')} verified status {data.get('free_status')}",
                        validation_checks=["groq_llm_free_tier_audit"],
                        reasoning="Validated with Groq LLM",
                        confidence_score=conf,
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to parse Groq free service extraction JSON: {e}")

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

        system_prompt = (
            "You are a search query generator specialized in finding newly released AI models, free AI APIs, and AI ecosystem updates.\n"
            "Output strictly valid JSON with key 'queries': list of search query strings (5 items)."
        )
        user_prompt = (
            f"Category: {category}\n"
            f"Recent Discoveries: {recent_discoveries}\n"
            f"Existing Queries to avoid: {existing_queries[:10]}\n"
            f"Generate {count} dynamic, highly specific search queries."
        )

        resp = self._call_groq(system_prompt, user_prompt, json_mode=True)
        if resp:
            try:
                data = json.loads(resp)
                queries = _safe_str_list(data.get("queries") if isinstance(data, dict) else None)
                if queries:
                    return [q for q in queries if q not in existing_queries][:count]
            except Exception as e:
                logger.error(f"Failed to parse Groq query generation JSON: {e}")

        return self.fallback.generate_search_queries(category, existing_queries, recent_discoveries, count)
