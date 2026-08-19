import logging
from typing import Optional
import httpx
from data_mining.config import settings
from data_mining.core.security import sanitize_secrets
from data_mining.models.enums import NotificationStatus, Priority
from data_mining.notifications.base import NotificationProvider

logger = logging.getLogger("data_mining.notifications.telegram")

# Telegram hard limit for message text
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

_MARKDOWN_SPECIALS = ("_", "*", "`", "[")


def escape_markdown(text: str) -> str:
    """Escapes Telegram (legacy) Markdown special characters to prevent broken formatting / injection."""
    if not text:
        return ""
    for ch in _MARKDOWN_SPECIALS:
        text = text.replace(ch, f"\\{ch}")
    return text


def truncate_message(text: str, limit: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> str:
    """Truncates message to Telegram's API limit, appending an ellipsis marker."""
    if len(text) <= limit:
        return text
    suffix = "\n…[truncated]"
    return text[: limit - len(suffix)] + suffix


class TelegramNotificationProvider(NotificationProvider):
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: int = 10,
    ):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self.timeout = timeout

    def send_message(
        self,
        title: str,
        body: str,
        priority: Priority = Priority.MEDIUM,
        recipient: Optional[str] = None,
    ) -> NotificationStatus:
        target_chat = recipient or self.chat_id
        if not self.bot_token or not target_chat:
            logger.info("[TELEGRAM_DRY_RUN] Token or Chat ID not configured. Message suppressed safely.")
            return NotificationStatus.SKIPPED

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        # Escape Markdown specials in the (potentially external-data-derived) title
        safe_title = escape_markdown(title)
        formatted_text = f"*{safe_title}*\n\n{body}"
        clean_text = truncate_message(sanitize_secrets(formatted_text))

        payload = {
            "chat_id": target_chat,
            "text": clean_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    logger.info(f"Telegram notification sent successfully to {target_chat}")
                    return NotificationStatus.SENT

                # HTTP 400 usually means broken Markdown entities -> retry once as plain text
                if res.status_code == 400:
                    logger.warning("Telegram rejected Markdown payload (400). Retrying as plain text.")
                    plain_payload = {
                        "chat_id": target_chat,
                        "text": truncate_message(sanitize_secrets(f"{title}\n\n{body}")),
                        "disable_web_page_preview": False,
                    }
                    res2 = client.post(url, json=plain_payload)
                    if res2.status_code == 200:
                        logger.info(f"Telegram plain-text fallback sent successfully to {target_chat}")
                        return NotificationStatus.SENT
                    logger.error(f"Telegram plain-text fallback failed {res2.status_code}: {res2.text}")
                    return NotificationStatus.FAILED

                logger.error(f"Telegram send failed with status {res.status_code}: {res.text}")
                return NotificationStatus.FAILED
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return NotificationStatus.FAILED
