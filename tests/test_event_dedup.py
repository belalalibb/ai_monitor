import pytest
from data_mining.core.event_dedup import generate_canonical_event_key
from data_mining.models.enums import EventType


def test_model_event_key_clustering():
    key1 = generate_canonical_event_key(
        event_type=EventType.NEW_MODEL,
        provider="OpenAI",
        entity_name="GPT-4o",
        version="1.0",
    )
    key2 = generate_canonical_event_key(
        event_type=EventType.NEW_MODEL,
        provider="openai",
        entity_name="gpt-4o",
        version="1.0",
    )
    assert key1 == key2
    assert key1 == "model:openai:gpt-4o:1.0"


def test_free_service_event_key_clustering():
    key1 = generate_canonical_event_key(
        event_type=EventType.NEW_FREE_AI_SERVICE,
        provider="openrouter.ai",
        entity_name="OpenRouter",
    )
    key2 = generate_canonical_event_key(
        event_type=EventType.NEW_FREE_AI_SERVICE,
        provider="https://openrouter.ai",
        entity_name="openrouter",
    )
    assert key1 == key2
    assert key1 == "free_service:openrouter"
