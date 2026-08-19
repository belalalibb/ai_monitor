import re
from typing import Any, Dict, List, Optional
from data_mining.core.normalizer import extract_domain, normalize_entity_name
from data_mining.llm.base import LLMProvider
from data_mining.models.enums import ComparisonStatus, DiscoveryType, FreeStatus, Priority, SourceReliability
from data_mining.models.schemas import (
    ComparisonResult,
    EvidenceRecord,
    FreeServiceInfo,
    ModelInfo,
    ProjectCapabilityMap,
)

# Known semantic equivalence clusters
EQUIVALENCE_CLUSTERS = {
    "tool_calling": {"tool calling", "tool use", "function calling", "tools", "actions", "function call"},
    "structured_outputs": {"structured outputs", "json mode", "json schema", "strict mode", "grammar constrained"},
    "vision": {"vision", "image understanding", "visual qa", "multimodal vision", "image input", "pixtral"},
    "reasoning": {"reasoning", "chain of thought", "cot", "thinking", "r1", "o1", "o3", "deepseek-r1"},
    "coding": {"coding", "code generation", "code completion", "codestral", "qwen-coder", "programming"},
    "long_context": {"long context", "128k", "200k", "1m context", "million token context", "large context"},
    "open_weights": {"open weights", "open source weights", "huggingface weights", "gguf", "safetensors"},
    "voice_audio": {"audio", "voice", "speech to text", "text to speech", "whisper", "realtime audio"},
}


class RuleBasedFallbackProvider(LLMProvider):
    """
    Deterministic rule-based LLM provider fallback.
    Performs feature comparison, entity extraction, and query generation
    without external API dependencies.
    """

    def compare_capabilities(
        self,
        item_name: str,
        provider: str,
        item_type: DiscoveryType,
        discovered_capabilities: List[str],
        project_map: ProjectCapabilityMap,
    ) -> ComparisonResult:
        new_caps: List[str] = []
        existing_caps: List[str] = []
        reasoning_parts: List[str] = []

        # Check if model/item is already present
        norm_item = normalize_entity_name(item_name)
        model_exists = any(normalize_entity_name(m) == norm_item for m in project_map.models)

        # Normalize project capabilities into semantic tokens with spaces instead of underscores
        project_tokens = {c.replace("_", " ").strip().lower() for c in project_map.capabilities + project_map.features}

        for cap in discovered_capabilities:
            cap_clean = cap.replace("_", " ").strip().lower()
            is_matched = False

            # Check direct match
            if cap_clean in project_tokens or any(cap_clean in pt or pt in cap_clean for pt in project_tokens):
                is_matched = True

            # Check semantic cluster equivalence
            if not is_matched:
                for cluster_name, aliases in EQUIVALENCE_CLUSTERS.items():
                    cluster_clean = cluster_name.replace("_", " ")
                    cluster_aliases = {a.replace("_", " ") for a in aliases} | {cluster_clean}
                    if any(a in cap_clean for a in cluster_aliases):
                        # Check if project already has this cluster
                        if any(any(a in pt for a in cluster_aliases) for pt in project_tokens):
                            is_matched = True
                            reasoning_parts.append(f"'{cap}' is semantically equivalent to existing '{cluster_name}' capability.")
                        break

            if is_matched:
                existing_caps.append(cap)
            else:
                new_caps.append(cap)

        # Determine overall comparison status
        if model_exists and not new_caps:
            status = ComparisonStatus.PROJECT_ALREADY_HAS
            priority = Priority.INFO
        elif model_exists and new_caps:
            status = ComparisonStatus.PROJECT_PARTIAL_SUPPORT
            priority = Priority.HIGH
        elif not model_exists and not new_caps:
            status = ComparisonStatus.PROJECT_PARTIAL_SUPPORT
            priority = Priority.MEDIUM
        else:
            status = ComparisonStatus.PROJECT_DOES_NOT_HAVE
            priority = Priority.CRITICAL if ("reasoning" in new_caps or "structured_outputs" in new_caps) else Priority.HIGH

        reasoning = " ".join(reasoning_parts) if reasoning_parts else "Rule-based cluster comparison completed."

        return ComparisonResult(
            item_type=item_type,
            item_name=item_name,
            provider=provider,
            status=status,
            new_capabilities=new_caps,
            existing_capabilities=existing_caps,
            equivalence_reasoning=reasoning,
            priority=priority,
            confidence_score=0.85,
            evidence=f"Discovered: {discovered_capabilities} | Project Baseline: {project_map.capabilities[:5]}",
        )

    def extract_model_info(self, raw_text: str, source_url: str) -> Optional[ModelInfo]:
        text_lower = raw_text.lower()

        # Try to identify provider
        provider = "Unknown"
        for p in ["OpenAI", "Anthropic", "Google", "DeepSeek", "Mistral", "Meta", "xAI", "Alibaba", "NVIDIA", "Cohere", "Groq"]:
            if p.lower() in text_lower:
                provider = p
                break

        # Try to extract model name
        model_name_match = re.search(
            r"\b(gpt-4o|gpt-4\.5|o1|o3-mini|claude-3\.7-[a-z]+|claude-3\.5-[a-z]+|gemini-2\.0-[a-z]+|deepseek-r1|deepseek-v3|llama-3\.[123]-[0-9]+b|mistral-[a-z]+|codestral|qwen-2\.5-[a-z0-9\-]+)\b",
            text_lower,
        )
        model_name = model_name_match.group(1) if model_name_match else f"{provider} New Model"

        # Extract capabilities
        has_reasoning = bool(re.search(r"\b(reasoning|chain-of-thought|deepseek-r1|o1|o3)\b", text_lower))
        has_vision = bool(re.search(r"\b(vision|image understanding|multimodal|pixtral)\b", text_lower))
        has_tools = bool(re.search(r"\b(tool calling|function calling|tools)\b", text_lower))
        has_coding = bool(re.search(r"\b(coding|code generation|codestral)\b", text_lower))
        has_structured = bool(re.search(r"\b(structured outputs|json schema|json mode)\b", text_lower))
        has_open_weights = bool(re.search(r"\b(open weights|open-source weights|apache 2\.0|mit license)\b", text_lower))

        # Extract context window
        context_match = re.search(r"\b(\d+)[kK]\s*(?:context|token)", text_lower)
        context_window = int(context_match.group(1)) * 1024 if context_match else 128000

        # Determine free status
        free_status = FreeStatus.UNKNOWN
        if "open weights" in text_lower or "open-weights" in text_lower:
            free_status = FreeStatus.OPEN_WEIGHTS
        elif "free tier" in text_lower or "free credits" in text_lower:
            free_status = FreeStatus.FREE_TIER
        elif "100% free" in text_lower or "free api" in text_lower:
            free_status = FreeStatus.FREE

        modalities = ["text"]
        if has_vision:
            modalities.append("vision")

        return ModelInfo(
            provider=provider,
            model_name=model_name,
            version="1.0",
            modalities=modalities,
            context_window=context_window,
            reasoning=has_reasoning,
            tools=has_tools,
            structured_output=has_structured,
            vision=has_vision,
            coding=has_coding,
            open_weights=has_open_weights,
            api_available=True,
            free_status=free_status,
            source_urls=[source_url],
            confidence_score=0.80,
            evidence=EvidenceRecord(
                source_url=source_url,
                source_type=SourceReliability.SEARCH_RESULT,
                extracted_fact=f"Model {model_name} from {provider} with context {context_window}",
                validation_checks=["regex_keyword_extraction", "domain_verification"],
                reasoning="Extracted via rule-based fallback tokenizer.",
                confidence_score=0.80,
            ),
        )

    def extract_free_service_info(self, raw_text: str, source_url: str) -> Optional[FreeServiceInfo]:
        text_lower = raw_text.lower()
        domain = extract_domain(source_url)
        service_name = domain.split(".")[0].capitalize()

        # Strict classification
        if "open weights" in text_lower:
            status = FreeStatus.OPEN_WEIGHTS
            limits = "Self-hosted / open weights"
        elif "free tier" in text_lower or "free credits" in text_lower or "rate limit" in text_lower:
            status = FreeStatus.FREE_TIER
            limits = "Verified free tier with rate limits/quotas"
        elif "trial" in text_lower or "free trial" in text_lower:
            status = FreeStatus.TRIAL
            limits = "Trial credits only"
        elif "free api" in text_lower or "free inference" in text_lower:
            status = FreeStatus.FREE
            limits = "Free inference available"
        else:
            status = FreeStatus.UNKNOWN
            limits = "Unverified limits"

        api_available = "api" in text_lower or "endpoint" in text_lower or "curl" in text_lower
        reg_required = "register" in text_lower or "sign up" in text_lower or "api key" in text_lower

        return FreeServiceInfo(
            service_name=service_name,
            domain=domain,
            models=["LLM Inference"],
            api_available=api_available,
            free_status=status,
            limits=limits,
            quota_details="Extracted from public site description",
            registration_required=reg_required,
            payment_method_required=False,
            region_restrictions="Global (unless blocked)",
            official_documentation=source_url,
            source_url=source_url,
            confidence_score=0.75,
            evidence=EvidenceRecord(
                source_url=source_url,
                source_type=SourceReliability.SEARCH_RESULT,
                extracted_fact=f"Service {service_name} on {domain} providing {status.value} inference",
                validation_checks=["domain_check", "keyword_free_tier_audit"],
                reasoning="Rule-based Free AI analysis performed.",
                confidence_score=0.75,
            ),
        )

    def generate_search_queries(
        self,
        category: str,
        existing_queries: List[str],
        recent_discoveries: List[str],
        count: int = 5,
    ) -> List[str]:
        base_templates = [
            '"{discovery}" official release blog',
            '"{discovery}" API documentation pricing',
            'free AI inference API "{discovery}"',
            'new AI models "{discovery}" open weights',
            'free LLM API provider "{category}" 2026',
        ]
        results = []
        seed = recent_discoveries[0] if recent_discoveries else "LLM"
        for t in base_templates:
            q = t.format(discovery=seed, category=category)
            if q not in existing_queries and q not in results:
                results.append(q)
            if len(results) >= count:
                break
        return results
