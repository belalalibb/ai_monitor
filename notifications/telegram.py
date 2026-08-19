import logging
from typing import Optional
import httpx
from data_mining.config import settings
from data_mining.core.security import sanitize_secrets
from data_mining.models.enums import NotificationStatus, Priority
from data_mining.notifications.base import NotificationProvider

logger = logging.getLogger("data_mining.notifications.telegram")


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
        formatted_text = f"*{title}*\n\n{body}"
        clean_text = sanitize_secrets(formatted_text)

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
                else:
                    logger.error(f"Telegram send failed with status {res.status_code}: {res.text}")
                    return NotificationStatus.FAILED
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return NotificationStatus.FAILED
