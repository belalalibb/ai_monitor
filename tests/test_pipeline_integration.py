import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from data_mining.core.project_knowledge import ProjectKnowledgeBase
from data_mining.db.repository import Repository
from data_mining.models.enums import NotificationStatus, RunStatus
from data_mining.notifications.base import NotificationProvider
from data_mining.notifications.manager import NotificationManager
from data_mining.scheduler.task_runner import PipelineTaskRunner
from data_mining.search.base import SearchProvider, SearchResult


class MockSearchProvider(SearchProvider):
    def search(self, query: str, max_results: int = 5, query_id: int = None):
        return [
            SearchResult(
                title="DeepSeek-R1 Open Reasoning Model Released",
                url="https://api-docs.deepseek.com/news/deepseek-r1-release",
                snippet="DeepSeek releases DeepSeek-R1 with open weights and reasoning tokens.",
                query_id=query_id,
            )
        ]


class MockHttpFetcher:
    def fetch_url(self, url: str):
        return (
            "<html><head><title>DeepSeek-R1 Model Release</title></head>"
            "<body><article><h1>DeepSeek-R1 Reasoning Model</h1>"
            "<p>We are releasing DeepSeek-R1 reasoning model with open weights, 128k context window, "
            "and free tier access on API.</p></article></body></html>",
            200,
        )


def test_full_pipeline_discovery_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        json_path = Path(tmpdir) / "project_capabilities.json"
        repo = Repository(db_path=db_path)
        kb = ProjectKnowledgeBase(json_path=json_path)

        runner = PipelineTaskRunner(repo=repo, knowledge_base=kb)
        runner.search_provider = MockSearchProvider()
        runner.fetcher = MockHttpFetcher()

        mock_notifier = MagicMock()
        mock_notifier.send_message.return_value = NotificationStatus.SENT
        runner.notifier.provider = mock_notifier

        stats = runner.run_full_discovery_cycle(max_queries=1)

        assert stats.status == RunStatus.COMPLETED
        assert stats.urls_discovered >= 1
        assert stats.urls_new >= 1
        assert stats.models_discovered >= 1

        # Check DB
        models = repo.get_all_models()
        assert len(models) == 1
        assert "deepseek" in models[0]["model_name"].lower() or "deepseek" in models[0]["provider_name"].lower()
