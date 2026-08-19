import json
import logging
from typing import Any, Dict, Optional
from data_mining.core.security import sanitize_secrets
from data_mining.db.repository import Repository

logger = logging.getLogger("data_mining.audit")


class AuditLogger:
    def __init__(self, repo: Optional[Repository] = None):
        self.repo = repo or Repository()

    def log_decision(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Dict[str, Any],
        actor: str = "ai_monitor",
        confidence: float = 1.0,
    ) -> None:
        """
        Persists structured audit trail and writes to sanitized logger.
        """
        details_str = json.dumps(details, default=str)
        clean_details = sanitize_secrets(details_str)

        try:
            self.repo.log_audit(
                action=action,
                actor=actor,
                entity_type=entity_type,
                entity_id=entity_id,
                details=clean_details,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")

        logger.info(f"[AUDIT] {action} | {entity_type}:{entity_id} | confidence={confidence:.2f}")
