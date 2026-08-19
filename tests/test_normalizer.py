import pytest
from data_mining.core.normalizer import (
    canonicalize_url,
    compute_content_hash,
    compute_url_hash,
    extract_domain,
    normalize_entity_name,
)


def test_url_canonicalization_strips_tracking():
    raw = "https://example.com/blog/ai-release?utm_source=twitter&utm_medium=social&fbclid=12345&ref=tech_news"
    canonical = canonicalize_url(raw)
    assert "utm_source" not in canonical
    assert "fbclid" not in canonical
    assert "ref" not in canonical
    assert canonical == "https://example.com/blog/ai-release"


def test_url_canonicalization_normalizes_case_and_trailing_slash():
    url1 = "HTTP://EXAMPLE.COM:80/Models/GPT-4/"
    url2 = "https://example.com:443/Models/GPT-4"
    assert canonicalize_url(url1) == "http://example.com/models/gpt-4"
    assert canonicalize_url(url2) == "https://example.com/models/gpt-4"


def test_content_hashing_consistency():
    text1 = "New AI Model Released on 2026-08-18 with 128k context!"
    text2 = "new ai model   released on 2026-08-19 with  128k context!"
    # Dates are normalized out
    hash1 = compute_content_hash(text1)
    hash2 = compute_content_hash(text2)
    assert hash1 == hash2


def test_domain_extraction():
    assert extract_domain("https://www.anthropic.com/news/claude-3-7") == "anthropic.com"
    assert extract_domain("https://api-docs.deepseek.com:443/models") == "api-docs.deepseek.com"


def test_entity_name_normalization():
    assert normalize_entity_name(" DeepSeek-R1 (Reasoner) ") == "deepseek-r1 reasoner"
    assert normalize_entity_name("GPT-4o / Omni") == "gpt-4o omni"
