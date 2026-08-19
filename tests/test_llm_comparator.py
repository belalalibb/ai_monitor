import pytest
from data_mining.llm.rule_based_fallback import RuleBasedFallbackProvider
from data_mining.models.enums import ComparisonStatus, DiscoveryType
from data_mining.models.schemas import ProjectCapabilityMap


def test_rule_based_comparator_understands_semantic_equivalence():
    comparator = RuleBasedFallbackProvider()
    project_map = ProjectCapabilityMap(
        models=["gpt-4o"],
        providers=["OpenAI"],
        capabilities=["tool_calling", "vision"],
        features=["chat"],
    )

    # Discovered model has "function calling" (equivalent to "tool_calling") and "structured outputs" (new)
    res = comparator.compare_capabilities(
        item_name="GPT-4o-mini",
        provider="OpenAI",
        item_type=DiscoveryType.MODEL,
        discovered_capabilities=["function calling", "structured outputs"],
        project_map=project_map,
    )

    assert "function calling" in res.existing_capabilities
    assert "structured outputs" in res.new_capabilities
    assert res.status in (ComparisonStatus.PROJECT_PARTIAL_SUPPORT, ComparisonStatus.PROJECT_DOES_NOT_HAVE)
    assert res.confidence_score >= 0.8
