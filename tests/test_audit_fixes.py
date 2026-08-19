"""Tests for the security & correctness audit fixes (P1-P3)."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_mining.core.security import is_url_safe_to_fetch
from data_mining.db.repository import Repository
from data_mining.llm.groq_provider import (
    _safe_confidence,
    _safe_context_window,
    _safe_enum,
    _safe_str_list,
)
from data_mining.models.enums import (
    ComparisonStatus,
    EventType,
    FreeStatus,
    NotificationStatus,
    Priority,
)
from data_mining.notifications.telegram import (
    TELEGRAM_MAX_MESSAGE_LENGTH,
    escape_markdown,
    truncate_message,
)


@pytest.fixture()
def repo():
    with tempfile.TemporaryDirectory() as tmp:
        yield Repository(db_path=Path(tmp) / "test.db")


# -----------------------------------------------------------------
# SSRF Guard
# -----------------------------------------------------------------
class TestSsrfGuard:
    def test_blocks_non_http_schemes(self):
        assert not is_url_safe_to_fetch("file:///etc/passwd")
        assert not is_url_safe_to_fetch("ftp://example.com/x")
        assert not is_url_safe_to_fetch("gopher://example.com")

    def test_blocks_localhost_and_internal_hosts(self):
        assert not is_url_safe_to_fetch("http://localhost/admin")
        assert not is_url_safe_to_fetch("http://localhost:8080/x")
        assert not is_url_safe_to_fetch("http://foo.internal/x", resolve_dns=False)
        assert not is_url_safe_to_fetch("http://printer.local/x", resolve_dns=False)

    def test_blocks_private_and_loopback_ips(self):
        assert not is_url_safe_to_fetch("http://127.0.0.1/")
        assert not is_url_safe_to_fetch("http://10.0.0.5/")
        assert not is_url_safe_to_fetch("http://192.168.1.1/")
        assert not is_url_safe_to_fetch("http://172.16.0.1/")
        assert not is_url_safe_to_fetch("http://0.0.0.0/")
        assert not is_url_safe_to_fetch("http://[::1]/")

    def test_blocks_cloud_metadata(self):
        assert not is_url_safe_to_fetch("http://169.254.169.254/latest/meta-data/")
        assert not is_url_safe_to_fetch("http://metadata.google.internal/computeMetadata/v1/")

    def test_allows_public_hosts(self):
        assert is_url_safe_to_fetch("https://openai.com/blog", resolve_dns=False)
        assert is_url_safe_to_fetch("https://8.8.8.8/", resolve_dns=False)

    def test_rejects_empty_and_garbage(self):
        assert not is_url_safe_to_fetch("")
        assert not is_url_safe_to_fetch(None)  # type: ignore[arg-type]
        assert not is_url_safe_to_fetch("not a url")

    def test_fetcher_refuses_unsafe_url(self):
        from data_mining.search.fetcher import HttpFetcher

        fetcher = HttpFetcher(timeout=2)
        with patch("data_mining.search.fetcher.httpx.Client") as mock_client:
            assert fetcher.fetch_url("http://127.0.0.1/secret") is None
            mock_client.assert_not_called()


# -----------------------------------------------------------------
# Telegram hardening
# -----------------------------------------------------------------
class TestTelegramHardening:
    def test_escape_markdown_specials(self):
        assert escape_markdown("a*b_c`d[e") == "a\\*b\\_c\\`d\\[e"
        assert escape_markdown("") == ""

    def test_truncate_long_message(self):
        msg = "x" * (TELEGRAM_MAX_MESSAGE_LENGTH + 500)
        out = truncate_message(msg)
        assert len(out) <= TELEGRAM_MAX_MESSAGE_LENGTH
        assert out.endswith("[truncated]")

    def test_truncate_keeps_short_message(self):
        assert truncate_message("hello") == "hello"

    def test_plain_text_fallback_on_400(self):
        from data_mining.notifications.telegram import TelegramNotificationProvider

        provider = TelegramNotificationProvider(bot_token="123:abc", chat_id="42")
        bad = MagicMock(status_code=400, text="Bad Request: can't parse entities")
        good = MagicMock(status_code=200)
        client = MagicMock()
        client.post.side_effect = [bad, good]
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        with patch("data_mining.notifications.telegram.httpx.Client", return_value=client):
            status = provider.send_message("Title_with*markdown", "body")
        assert status == NotificationStatus.SENT
        assert client.post.call_count == 2
        # second call must be plain text (no parse_mode)
        assert "parse_mode" not in client.post.call_args_list[1].kwargs["json"]


# -----------------------------------------------------------------
# Atomic notification claim
# -----------------------------------------------------------------
class TestNotificationClaim:
    def test_claim_only_wins_once(self, repo):
        gid, is_new = repo.get_or_create_event_group(
            "key1", EventType.NEW_MODEL, "OpenAI", "gpt-x", "New model gpt-x"
        )
        assert is_new
        assert repo.try_claim_event_group_notification(gid) is True
        assert repo.try_claim_event_group_notification(gid) is False

    def test_release_allows_retry(self, repo):
        gid, _ = repo.get_or_create_event_group(
            "key2", EventType.NEW_MODEL, "OpenAI", "gpt-y", "t"
        )
        assert repo.try_claim_event_group_notification(gid)
        repo.release_event_group_notification_claim(gid)
        assert repo.try_claim_event_group_notification(gid) is True

    def test_manager_releases_claim_on_failed_send(self, repo):
        from data_mining.models.schemas import ChangeEvent, ComparisonResult, ModelInfo
        from data_mining.notifications.manager import NotificationManager

        gid, _ = repo.get_or_create_event_group(
            "key3", EventType.NEW_MODEL, "P", "m", "t"
        )
        provider = MagicMock()
        provider.send_message.return_value = NotificationStatus.FAILED
        mgr = NotificationManager(provider=provider, repo=repo)

        event = ChangeEvent(
            event_type=EventType.NEW_MODEL,
            entity_type="model",
            entity_name="m",
            provider="P",
            title="t",
            description="d",
            priority=Priority.HIGH,
        )
        model = ModelInfo(provider="P", model_name="m", version="1")
        comp = ComparisonResult(
            item_type=model_item_type(),
            item_name="m",
            provider="P",
            status=ComparisonStatus.PROJECT_DOES_NOT_HAVE,
        )
        status = mgr.dispatch_model_event(event, model, comp, event_group_id=gid)
        assert status == NotificationStatus.FAILED
        # claim must be released so retry is possible
        assert repo.try_claim_event_group_notification(gid) is True

    def test_manager_suppresses_duplicate(self, repo):
        from data_mining.models.schemas import ChangeEvent, ComparisonResult, ModelInfo
        from data_mining.notifications.manager import NotificationManager

        gid, _ = repo.get_or_create_event_group(
            "key4", EventType.NEW_MODEL, "P", "m", "t"
        )
        provider = MagicMock()
        provider.send_message.return_value = NotificationStatus.SENT
        mgr = NotificationManager(provider=provider, repo=repo)

        event = ChangeEvent(
            event_type=EventType.NEW_MODEL,
            entity_type="model",
            entity_name="m",
            provider="P",
            title="t",
            description="d",
            priority=Priority.HIGH,
        )
        model = ModelInfo(provider="P", model_name="m", version="1")
        comp = ComparisonResult(
            item_type=model_item_type(),
            item_name="m",
            provider="P",
            status=ComparisonStatus.PROJECT_DOES_NOT_HAVE,
        )
        first = mgr.dispatch_model_event(event, model, comp, event_group_id=gid)
        second = mgr.dispatch_model_event(event, model, comp, event_group_id=gid)
        assert first == NotificationStatus.SENT
        assert second == NotificationStatus.SUPPRESSED_DUPLICATE
        assert provider.send_message.call_count == 1


def model_item_type():
    from data_mining.models.enums import DiscoveryType

    return DiscoveryType.MODEL


# -----------------------------------------------------------------
# Atomic upsert_url / get_or_create_event_group
# -----------------------------------------------------------------
class TestAtomicUpserts:
    def test_upsert_url_new_then_existing(self, repo):
        uid1, new1 = repo.upsert_url("https://a.com/x", "https://a.com/x", "h1", "a.com")
        uid2, new2 = repo.upsert_url("https://a.com/x", "https://a.com/x", "h1", "a.com", content_hash="c1")
        assert new1 is True
        assert new2 is False
        assert uid1 == uid2
        row = repo.get_url_by_hash("h1")
        assert row["content_hash"] == "c1"

    def test_upsert_url_coalesce_keeps_hash(self, repo):
        repo.upsert_url("u", "u", "h2", "d", content_hash="orig")
        repo.upsert_url("u", "u", "h2", "d", content_hash=None)
        assert repo.get_url_by_hash("h2")["content_hash"] == "orig"

    def test_event_group_dedup(self, repo):
        gid1, new1 = repo.get_or_create_event_group("k", EventType.NEW_MODEL, "P", "e", "t")
        gid2, new2 = repo.get_or_create_event_group("k", EventType.NEW_MODEL, "P", "e", "t")
        assert new1 is True
        assert new2 is False
        assert gid1 == gid2


# -----------------------------------------------------------------
# LLM output validation
# -----------------------------------------------------------------
class TestLlmOutputValidation:
    def test_confidence_clamped(self):
        assert _safe_confidence(5.0) == 1.0
        assert _safe_confidence(-3) == 0.0
        assert _safe_confidence(0.7) == 0.7
        assert _safe_confidence("not a number", default=0.5) == 0.5
        assert _safe_confidence(None, default=0.5) == 0.5
        assert _safe_confidence(float("nan"), default=0.5) == 0.5

    def test_safe_enum_falls_back(self):
        assert _safe_enum(FreeStatus, "free", FreeStatus.UNKNOWN) == FreeStatus.FREE
        assert _safe_enum(FreeStatus, "TOTALLY_BOGUS", FreeStatus.UNKNOWN) == FreeStatus.UNKNOWN
        assert _safe_enum(Priority, None, Priority.HIGH) == Priority.HIGH
        assert _safe_enum(ComparisonStatus, 123, ComparisonStatus.PROJECT_UNKNOWN) == ComparisonStatus.PROJECT_UNKNOWN

    def test_safe_str_list(self):
        assert _safe_str_list(["a", "", "  b  ", 3, {"x": 1}, None]) == ["a", "b", "3"]
        assert _safe_str_list("not a list") == []
        assert _safe_str_list(None) == []
        assert len(_safe_str_list(["x"] * 100, max_items=50)) == 50
        assert _safe_str_list(["y" * 600])[0] == "y" * 500

    def test_safe_context_window(self):
        assert _safe_context_window(128000) == 128000
        assert _safe_context_window(-5, default=128000) == 128000
        assert _safe_context_window(10**12, default=128000) == 128000
        assert _safe_context_window("128000") == 128000
        assert _safe_context_window("junk", default=99) == 99

    def test_invalid_llm_json_does_not_crash_compare(self):
        from data_mining.llm.groq_provider import GroqProvider
        from data_mining.models.enums import DiscoveryType
        from data_mining.models.schemas import ProjectCapabilityMap

        provider = GroqProvider(api_key="fake")
        garbage = '{"status": "NOT_A_STATUS", "priority": "SUPER", "confidence_score": "high", "new_capabilities": "oops"}'
        with patch.object(provider, "_call_groq", return_value=garbage):
            result = provider.compare_capabilities(
                "m", "P", DiscoveryType.MODEL, ["cap"], ProjectCapabilityMap()
            )
        assert result.status == ComparisonStatus.PROJECT_DOES_NOT_HAVE
        assert result.priority == Priority.HIGH
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.new_capabilities == []

    def test_invalid_llm_json_does_not_crash_model_extract(self):
        from data_mining.llm.groq_provider import GroqProvider

        provider = GroqProvider(api_key="fake")
        garbage = '{"free_status": "everything_is_free", "context_window": "huge", "confidence_score": 99}'
        with patch.object(provider, "_call_groq", return_value=garbage):
            model = provider.extract_model_info("some page text", "https://ex.com/p")
        assert model is not None
        assert model.free_status == FreeStatus.UNKNOWN
        assert model.context_window == 128000
        assert model.confidence_score == 1.0
