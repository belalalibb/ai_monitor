import logging
from typing import Any, Dict, Optional
from data_mining.core.event_dedup import generate_canonical_event_key
from data_mining.models.enums import EventType, Priority
from data_mining.models.schemas import ChangeEvent, FreeServiceInfo, ModelInfo

logger = logging.getLogger("data_mining.change_detector")


class ChangeDetector:
    """
    Detects meaningful changes between newly extracted entities and previous states.
    Produces structured ChangeEvents with canonical event keys.
    """

    def detect_model_changes(
        self,
        new_model: ModelInfo,
        existing_model: Optional[Dict[str, Any]],
        is_new: bool,
    ) -> Optional[ChangeEvent]:
        canonical_key = generate_canonical_event_key(
            event_type=EventType.NEW_MODEL if is_new else EventType.MODEL_UPDATE,
            provider=new_model.provider,
            entity_name=new_model.model_name,
            version=new_model.version,
        )

        if is_new:
            # Brand new model release
            priority = Priority.CRITICAL if (new_model.reasoning or "reasoning" in new_model.modalities) else Priority.HIGH
            return ChangeEvent(
                event_type=EventType.NEW_MODEL,
                entity_type="model",
                entity_name=new_model.model_name,
                provider=new_model.provider,
                title=f"New Model Released: {new_model.provider} {new_model.model_name}",
                description=f"Discovered new model from {new_model.provider} with {new_model.context_window} context.",
                diff_summary={
                    "version": new_model.version,
                    "modalities": new_model.modalities,
                    "context_window": new_model.context_window,
                    "free_status": new_model.free_status.value,
                },
                priority=priority,
                source_url=new_model.source_urls[0] if new_model.source_urls else "",
                canonical_event_key=canonical_key,
                evidence=new_model.evidence,
            )

        if not existing_model:
            return None

        # Check for meaningful diffs
        diffs = {}
        if existing_model.get("context_window") != new_model.context_window:
            diffs["context_window"] = {"old": existing_model.get("context_window"), "new": new_model.context_window}
        if existing_model.get("free_status") != new_model.free_status.value:
            diffs["free_status"] = {"old": existing_model.get("free_status"), "new": new_model.free_status.value}

        if diffs:
            return ChangeEvent(
                event_type=EventType.MODEL_UPDATE,
                entity_type="model",
                entity_name=new_model.model_name,
                provider=new_model.provider,
                title=f"Model Updated: {new_model.provider} {new_model.model_name}",
                description=f"Meaningful specification update detected for {new_model.model_name}.",
                diff_summary=diffs,
                priority=Priority.MEDIUM,
                source_url=new_model.source_urls[0] if new_model.source_urls else "",
                canonical_event_key=canonical_key,
                evidence=new_model.evidence,
            )

        return None

    def detect_free_service_changes(
        self,
        service: FreeServiceInfo,
        is_new: bool,
    ) -> Optional[ChangeEvent]:
        canonical_key = generate_canonical_event_key(
            event_type=EventType.NEW_FREE_AI_SERVICE,
            provider=service.domain,
            entity_name=service.service_name,
        )

        if is_new:
            return ChangeEvent(
                event_type=EventType.NEW_FREE_AI_SERVICE,
                entity_type="free_service",
                entity_name=service.service_name,
                provider=service.domain,
                title=f"New Free AI Platform Discovered: {service.service_name}",
                description=f"Discovered free AI access on {service.domain} ({service.free_status.value}).",
                diff_summary={
                    "domain": service.domain,
                    "free_status": service.free_status.value,
                    "limits": service.limits,
                    "api_available": service.api_available,
                },
                priority=Priority.HIGH,
                source_url=service.source_url,
                canonical_event_key=canonical_key,
                evidence=service.evidence,
            )

        return None
