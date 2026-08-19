from abc import ABC, abstractmethod
from typing import Optional
from data_mining.models.enums import NotificationStatus, Priority


class NotificationProvider(ABC):
    @abstractmethod
    def send_message(
        self,
        title: str,
        body: str,
        priority: Priority = Priority.MEDIUM,
        recipient: Optional[str] = None,
    ) -> NotificationStatus:
        """Sends notification to target channel and returns delivery status."""
        pass
