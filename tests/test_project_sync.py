import tempfile
from pathlib import Path
from data_mining.core.project_knowledge import ProjectKnowledgeBase
from data_mining.db.repository import Repository
from data_mining.sync.project_sync import ProjectIntelligenceSync


def test_codebase_sync_detects_existing_providers_and_models():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        json_path = Path(tmpdir) / "project_capabilities.json"
        repo = Repository(db_path=db_path)

        sync_engine = ProjectIntelligenceSync(repo=repo)
        cap_map = sync_engine.sync_mirror(output_path=json_path)

        assert "OpenAI" in cap_map.providers or "ChatGPT" in cap_map.providers
        assert any("gpt" in m.lower() for m in cap_map.models)
        assert json_path.exists()

        kb = ProjectKnowledgeBase(json_path=json_path)
        assert kb.has_provider("OpenAI") or kb.has_provider("ChatGPT")
        assert kb.has_model("gpt-4")
