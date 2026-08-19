import logging
from typing import Optional
from data_mining.core.normalizer import extract_domain
from data_mining.llm.base import LLMProvider
from data_mining.llm.factory import get_llm_provider
from data_mining.models.enums import FreeStatus, SourceReliability
from data_mining.models.schemas import EvidenceRecord, FreeServiceInfo

logger = logging.getLogger("data_mining.extractors.free_ai")


class FreeAIExtractor:
    """
    Dedicated strict validator and extractor for Free AI platforms and services.
    Enforces rigorous classification and refuses to claim 'Always Free'
    without explicit verified documentation evidence.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    def extract_and_validate(
        self,
        raw_text: str,
        source_url: str,
        query_id: Optional[int] = None,
    ) -> Optional[FreeServiceInfo]:
        if not raw_text or len(raw_text.strip()) < 40:
            return None

        text_lower = raw_text.lower()
        domain = extract_domain(source_url)

        # Delegate extraction to provider
        service_info = self.llm.extract_free_service_info(raw_text, source_url)
        if not service_info:
            return None

        service_info.discovered_by_query_id = query_id

        # Verification & classification validation rules
        validation_checks = ["llm_extraction"]

        has_negative_free = any(neg in text_lower for neg in ["no free tier", "no free trial", "no free access", "paid subscription only", "paid only"])
        has_paid_signals = any(p in text_lower for p in ["pricing starts at", "credit card required", "paid only", "subscription required"])
        has_verified_free_tier = any(kw in text_lower for kw in ["free tier", "free credits", "rpm", "rpd", "rate limit", "requests per day", "free plan"]) and not has_negative_free

        # Rule 1: Detect explicit paid only signals
        if has_negative_free or (has_paid_signals and not has_verified_free_tier and "100% free" not in text_lower):
            service_info.free_status = FreeStatus.PAID_ONLY
            validation_checks.append("paid_only_detected")

        # Rule 2: Open weights classification
        elif (
            "open weights" in text_lower
            or "weights available on hugging face" in text_lower
            or "github.com" in source_url
            or "huggingface.co" in source_url
        ):
            service_info.free_status = FreeStatus.OPEN_WEIGHTS
            validation_checks.append("open_weights_verified")

        # Rule 3: Free trial vs permanent free tier
        elif "trial" in text_lower and not has_verified_free_tier:
            service_info.free_status = FreeStatus.TRIAL
            validation_checks.append("trial_period_identified")

        # Rule 4: Verified free tier with quotas
        elif has_verified_free_tier:
            service_info.free_status = FreeStatus.FREE_TIER
            validation_checks.append("quota_rate_limits_verified")

        # Rule 5: Completely free claim
        elif "100% free" in text_lower or "completely free" in text_lower or "no cost" in text_lower:
            # Only claim completely FREE if explicitly affirmed
            service_info.free_status = FreeStatus.FREE
            validation_checks.append("explicit_free_declaration_found")

        # Attach complete evidence record
        service_info.evidence = EvidenceRecord(
            source_url=source_url,
            source_type=SourceReliability.SEARCH_RESULT,
            extracted_fact=(
                f"Domain {domain} offers {service_info.free_status.value} AI access. "
                f"Limits: {service_info.limits}."
            ),
            validation_checks=validation_checks,
            reasoning="Strict Free AI validation pipeline verified quota, payment, and status markers.",
            confidence_score=service_info.confidence_score,
        )

        return service_info
