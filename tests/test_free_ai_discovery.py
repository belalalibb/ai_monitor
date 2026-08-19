from data_mining.extractors.free_ai_extractor import FreeAIExtractor
from data_mining.models.enums import FreeStatus


def test_free_ai_strict_classification_open_weights():
    extractor = FreeAIExtractor()
    text = "We are releasing open weights under Apache 2.0 on HuggingFace for research."
    service = extractor.extract_and_validate(text, "https://huggingface.co/org/model")
    assert service is not None
    assert service.free_status == FreeStatus.OPEN_WEIGHTS
    assert service.evidence is not None
    assert "open_weights_verified" in service.evidence.validation_checks


def test_free_ai_strict_classification_free_tier():
    extractor = FreeAIExtractor()
    text = "Our platform offers a free tier with 500 requests per day and rate limits of 10 RPM."
    service = extractor.extract_and_validate(text, "https://api.example.ai/pricing")
    assert service is not None
    assert service.free_status == FreeStatus.FREE_TIER
    assert "quota_rate_limits_verified" in service.evidence.validation_checks


def test_free_ai_strict_classification_paid_only():
    extractor = FreeAIExtractor()
    text = "Pricing starts at $20/month with credit card required. No free tier."
    service = extractor.extract_and_validate(text, "https://paid.example.ai")
    assert service is not None
    assert service.free_status == FreeStatus.PAID_ONLY
