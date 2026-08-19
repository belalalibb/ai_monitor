import tempfile
from pathlib import Path
import pytest
from data_mining.core.normalizer import compute_url_hash
from data_mining.db.repository import Repository
from data_mining.models.enums import EventType, FreeStatus, Priority
from data_mining.models.schemas import ChangeEvent, FreeServiceInfo, ModelInfo, ProviderInfo


def test_database_crud_and_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = Repository(db_path=db_path)

        # 1. Upsert Provider
        p = ProviderInfo(name="Mistral AI", domain="mistral.ai", categories=["llm"])
        p_id = repo.upsert_provider(p)
        assert p_id > 0
        prov = repo.get_provider_by_name("Mistral AI")
        assert prov is not None
        assert prov.domain == "mistral.ai"

        # 2. URL Deduplication
        url = "https://mistral.ai/news/codestral-2501"
        u_hash = compute_url_hash(url)
        u_id1, is_new1 = repo.upsert_url(url, url, u_hash, "mistral.ai")
        assert is_new1 is True

        u_id2, is_new2 = repo.upsert_url(url, url, u_hash, "mistral.ai")
        assert is_new2 is False
        assert u_id1 == u_id2

        # 3. Model Upsert
        m = ModelInfo(provider="Mistral AI", model_name="Codestral", coding=True)
        m_id, is_m_new = repo.upsert_model(m)
        assert is_m_new is True

        models = repo.get_all_models()
        assert len(models) == 1
        assert models[0]["coding"] == 1

        # 4. Event Group & Deduplication
        eg_id1, is_eg_new1 = repo.get_or_create_event_group(
            canonical_event_key="model:mistral:codestral:1.0",
            event_type=EventType.NEW_MODEL,
            provider="Mistral AI",
            entity_name="Codestral",
            title="Codestral Release",
        )
        assert is_eg_new1 is True

        eg_id2, is_eg_new2 = repo.get_or_create_event_group(
            canonical_event_key="model:mistral:codestral:1.0",
            event_type=EventType.NEW_MODEL,
            provider="Mistral AI",
            entity_name="Codestral",
            title="Codestral Release Mirror",
        )
        assert is_eg_new2 is False
        assert eg_id1 == eg_id2
