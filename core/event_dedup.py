import hashlib
import re
from typing import Optional
from data_mining.core.normalizer import normalize_entity_name
from data_mining.models.enums import EventType


def generate_canonical_event_key(
    event_type: EventType,
    provider: str,
    entity_name: str,
    version: Optional[str] = None,
    secondary_info: Optional[str] = None,
) -> str:
    """
    Generates a deterministic canonical key for event clustering to ensure
    that multi-source coverage of the exact same announcement generates
    only one canonical event and a single Telegram notification.
    """
    p_norm = normalize_entity_name(provider) or "unknown"
    e_norm = normalize_entity_name(entity_name) or "general"
    v_norm = normalize_entity_name(version or "1.0")

    if event_type in (EventType.NEW_MODEL, EventType.MODEL_UPDATE):
        return f"model:{p_norm}:{e_norm}:{v_norm}"

    elif event_type == EventType.NEW_FREE_AI_SERVICE:
        # Free services are keyed by service/domain name
        return f"free_service:{e_norm}"

    elif event_type == EventType.NEW_CAPABILITY:
        return f"capability:{p_norm}:{e_norm}"

    elif event_type == EventType.PRICE_CHANGE:
        return f"price_change:{p_norm}:{e_norm}"

    elif event_type == EventType.DEPRECATION:
        return f"deprecation:{p_norm}:{e_norm}"

    else:
        # Fallback event key based on provider + entity + optional secondary hash
        sec_hash = ""
        if secondary_info:
            sec_hash = ":" + hashlib.sha256(secondary_info.strip().lower().encode("utf-8")).hexdigest()[:12]
        return f"event:{event_type.value}:{p_norm}:{e_norm}{sec_hash}"
