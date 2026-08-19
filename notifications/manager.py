import logging
from typing import Optional
from data_mining.config import settings
from data_mining.db.repository import Repository
from data_mining.models.enums import EventType, NotificationStatus, Priority
from data_mining.models.schemas import ChangeEvent, ComparisonResult, FreeServiceInfo, ModelInfo
from data_mining.notifications.base import NotificationProvider
from data_mining.notifications.telegram import TelegramNotificationProvider

logger = logging.getLogger("data_mining.notifications.manager")


class NotificationManager:
    """
    Manages formatting, priority filtering, deduplication, and dispatching
    of AI monitor notifications.
    """

    def __init__(
        self,
        provider: Optional[NotificationProvider] = None,
        repo: Optional[Repository] = None,
    ):
        self.provider = provider or TelegramNotificationProvider()
        self.repo = repo or Repository()

    def dispatch_model_event(
        self,
        event: ChangeEvent,
        model: ModelInfo,
        comparison: ComparisonResult,
        event_group_id: Optional[int] = None,
    ) -> NotificationStatus:
        # Priority filter check
        if event.priority == Priority.LOW and not settings.NOTIFY_LOW_PRIORITY:
            logger.info(f"Skipping low priority event: {event.title}")
            return NotificationStatus.SKIPPED

        # Atomic deduplication claim: only one caller wins the right to send
        if event_group_id and not self.repo.try_claim_event_group_notification(event_group_id):
            logger.info(f"Notification for event group {event_group_id} already sent. Suppressing duplicate.")
            return NotificationStatus.SUPPRESSED_DUPLICATE

        # Emoji Header Selection
        header_map = {
            EventType.NEW_MODEL: "🚀 NEW MODEL DISCOVERY",
            EventType.NEW_CAPABILITY: "🆕 NEW AI CAPABILITY",
            EventType.MODEL_UPDATE: "🔄 MODEL UPDATE",
            EventType.PRICE_CHANGE: "💰 PRICING CHANGE",
            EventType.DEPRECATION: "⚠️ MODEL DEPRECATION",
        }
        title = header_map.get(event.event_type, "🆕 AI ECOSYSTEM UPDATE")

        body_lines = [
            f"🏢 *Provider:* {model.provider}",
            f"🤖 *Model:* {model.model_name} (v{model.version})",
            "",
        ]

        if comparison.new_capabilities:
            body_lines.append("🧠 *New Capabilities:*")
            for cap in comparison.new_capabilities:
                body_lines.append(f"• {cap}")
            body_lines.append("")

        if comparison.existing_capabilities:
            body_lines.append("✅ *Already in your project:*")
            for cap in comparison.existing_capabilities:
                body_lines.append(f"• {cap}")
            body_lines.append("")

        free_desc = "Verified free tier" if model.free_status.value in ("free", "free_tier") else model.free_status.value
        body_lines.append(f"🆓 *Free Access:* {free_desc}")

        if model.context_window:
            body_lines.append(f"📏 *Context Window:* {model.context_window:,} tokens")

        if model.source_urls:
            body_lines.append(f"\n🔗 *Official / Source:*\n{model.source_urls[0]}")

        body_lines.append(f"\n📅 *First seen:* {event.first_seen[:10]}")

        body = "\n".join(body_lines)

        status = self.provider.send_message(
            title=title,
            body=body,
            priority=event.priority,
        )

        # Claim was taken upfront; release it if the send actually failed so a retry can occur
        if event_group_id and status != NotificationStatus.SENT:
            self.repo.release_event_group_notification_claim(event_group_id)

        self.repo.save_notification(
            event_group_id=event_group_id,
            event_type=event.event_type,
            title=title,
            body=body,
            priority=event.priority,
            recipient=settings.TELEGRAM_CHAT_ID or "default_chat",
            status=status,
        )

        return status

    def dispatch_free_service_event(
        self,
        event: ChangeEvent,
        service: FreeServiceInfo,
        event_group_id: Optional[int] = None,
    ) -> NotificationStatus:
        # Atomic deduplication claim: only one caller wins the right to send
        if event_group_id and not self.repo.try_claim_event_group_notification(event_group_id):
            logger.info(f"Free service event {event_group_id} already notified. Suppressing duplicate.")
            return NotificationStatus.SUPPRESSED_DUPLICATE

        title = "🆓 NEW FREE AI PLATFORM"
        body_lines = [
            f"🌐 *Platform / Service:* {service.service_name}",
            f"📍 *Domain:* `{service.domain}`",
            f"🎯 *Free Status:* `{service.free_status.value.upper()}`",
            f"📊 *Quotas / Limits:* {service.limits}",
            f"🔌 *API Available:* {'Yes' if service.api_available else 'Web / Playground only'}",
            f"🔑 *Registration Required:* {'Yes' if service.registration_required else 'No'}",
            f"💳 *Payment Card Required:* {'Yes' if service.payment_method_required else 'No'}",
            f"\n🔗 *Source:*\n{service.source_url}",
            f"\n📅 *Verified:* {service.last_verified[:10]}",
        ]
        body = "\n".join(body_lines)

        status = self.provider.send_message(
            title=title,
            body=body,
            priority=event.priority,
        )

        # Claim was taken upfront; release it if the send actually failed so a retry can occur
        if event_group_id and status != NotificationStatus.SENT:
            self.repo.release_event_group_notification_claim(event_group_id)

        self.repo.save_notification(
            event_group_id=event_group_id,
            event_type=event.event_type,
            title=title,
            body=body,
            priority=event.priority,
            recipient=settings.TELEGRAM_CHAT_ID or "default_chat",
            status=status,
        )

        return status
