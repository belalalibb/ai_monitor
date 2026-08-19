import tempfile
from pathlib import Path
from data_mining.db.repository import Repository
from data_mining.models.enums import ComparisonStatus, DiscoveryType, EventType, FreeStatus, NotificationStatus, Priority
from data_mining.models.schemas import ChangeEvent, ComparisonResult, ModelInfo
from data_mining.notifications.base import NotificationProvider
from data_mining.notifications.manager import NotificationManager


class MockNotificationProvider(NotificationProvider):
    def __init__(self):
        self.sent_messages = []

    def send_message(self, title: str, body: str, priority: Priority = Priority.MEDIUM, recipient: str = None) -> NotificationStatus:
        self.sent_messages.append({"title": title, "body": body, "priority": priority})
        return NotificationStatus.SENT


def test_telegram_notification_formatting_and_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = Repository(db_path=db_path)
        mock_provider = MockNotificationProvider()
        manager = NotificationManager(provider=mock_provider, repo=repo)

        model = ModelInfo(
            provider="Anthropic",
            model_name="Claude-3.7-Sonnet",
            version="1.0",
            modalities=["text", "vision"],
            reasoning=True,
            tools=True,
            context_window=200000,
            free_status=FreeStatus.FREE_TIER,
            source_urls=["https://anthropic.com/news/claude-3-7"],
        )

        comparison = ComparisonResult(
            item_type=DiscoveryType.MODEL,
            item_name="Claude-3.7-Sonnet",
            provider="Anthropic",
            status=ComparisonStatus.PROJECT_DOES_NOT_HAVE,
            new_capabilities=["hybrid_reasoning", "computer_use"],
            existing_capabilities=["tool_calling", "vision"],
            priority=Priority.CRITICAL,
        )

        event = ChangeEvent(
            event_type=EventType.NEW_MODEL,
            entity_type="model",
            entity_name="Claude-3.7-Sonnet",
            provider="Anthropic",
            title="New Model Released: Claude-3.7-Sonnet",
            description="Hybrid reasoning model",
            priority=Priority.CRITICAL,
            source_url="https://anthropic.com/news/claude-3-7",
            canonical_event_key="model:anthropic:claude-3.7-sonnet:1.0",
        )

        event_group_id, is_new_event = repo.get_or_create_event_group(
            canonical_event_key=event.canonical_event_key,
            event_type=event.event_type,
            provider=event.provider,
            entity_name=event.entity_name,
            title=event.title,
        )

        # First dispatch should succeed
        status1 = manager.dispatch_model_event(event, model, comparison, event_group_id=event_group_id)
        assert status1 == NotificationStatus.SENT
        assert len(mock_provider.sent_messages) == 1

        msg = mock_provider.sent_messages[0]
        assert "Anthropic" in msg["body"]
        assert "Claude-3.7-Sonnet" in msg["body"]
        assert "hybrid_reasoning" in msg["body"]
        assert "Already in your project" in msg["body"]
        assert "200,000" in msg["body"]

        # Duplicate dispatch of same event group should be suppressed
        status2 = manager.dispatch_model_event(event, model, comparison, event_group_id=event_group_id)
        assert status2 == NotificationStatus.SUPPRESSED_DUPLICATE
        assert len(mock_provider.sent_messages) == 1
