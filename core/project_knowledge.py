import json
import logging
from pathlib import Path
from typing import List, Optional, Set
from data_mining.config import settings
from data_mining.core.normalizer import normalize_entity_name
from data_mining.models.schemas import ProjectCapabilityMap, utc_now_iso
from data_mining.sync.project_sync import ProjectIntelligenceSync

logger = logging.getLogger("data_mining.knowledge")


class ProjectKnowledgeBase:
    """
    Manages and exposes the project's current AI knowledge base / capability mirror.
    Supports empty-file initial baseline discovery and dynamic syncing.
    """

    def __init__(self, json_path: Optional[Path] = None):
        self.json_path = json_path or settings.PROJECT_CAPABILITIES_PATH
        self.cap_map: Optional[ProjectCapabilityMap] = None
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        if self.json_path.exists():
            try:
                data = json.loads(self.json_path.read_text(encoding="utf-8"))
                self.cap_map = ProjectCapabilityMap(**data)
                # Check if file has meaningful content
                if not (self.cap_map.models or self.cap_map.providers or self.cap_map.capabilities):
                    logger.info("Project capabilities file exists but is empty. Triggering sync baseline.")
                    self.initialize_baseline()
            except Exception as e:
                logger.warning(f"Error reading capabilities map from {self.json_path}: {e}")
                self.initialize_baseline()
        else:
            logger.info(f"Capabilities map not found at {self.json_path}. Initializing baseline.")
            self.initialize_baseline()

    def initialize_baseline(self) -> ProjectCapabilityMap:
        """
        Runs project intelligence sync to establish the initial baseline.
        """
        sync_engine = ProjectIntelligenceSync()
        self.cap_map = sync_engine.sync_mirror(self.json_path)
        return self.cap_map

    def reload(self) -> ProjectCapabilityMap:
        self._load_or_initialize()
        return self.cap_map or ProjectCapabilityMap()

    def get_map(self) -> ProjectCapabilityMap:
        if self.cap_map is None:
            self._load_or_initialize()
        return self.cap_map or ProjectCapabilityMap()

    def has_provider(self, provider_name: str) -> bool:
        norm = normalize_entity_name(provider_name)
        if not norm or not self.cap_map:
            return False
        return any(normalize_entity_name(p) == norm for p in self.cap_map.providers)

    def has_model(self, model_name: str) -> bool:
        norm = normalize_entity_name(model_name)
        if not norm or not self.cap_map:
            return False
        # Exact match or substring containment (e.g. gpt-4 in gpt-4-turbo)
        for m in self.cap_map.models:
            m_norm = normalize_entity_name(m)
            if m_norm == norm or (len(norm) > 4 and norm in m_norm):
                return True
        return False

    def has_capability(self, capability_name: str) -> bool:
        norm = normalize_entity_name(capability_name)
        if not norm or not self.cap_map:
            return False
        return any(normalize_entity_name(c) == norm for c in self.cap_map.capabilities)

    def add_model(self, model_name: str, provider: Optional[str] = None) -> None:
        cap_map = self.get_map()
        if model_name not in cap_map.models:
            cap_map.models.append(model_name)
            if provider and provider not in cap_map.providers:
                cap_map.providers.append(provider)
            self._save()

    def add_capability(self, capability_name: str) -> None:
        cap_map = self.get_map()
        if capability_name not in cap_map.capabilities:
            cap_map.capabilities.append(capability_name)
            self._save()

    def _save(self) -> None:
        if self.cap_map:
            self.cap_map.last_synced = utc_now_iso()
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            self.json_path.write_text(
                json.dumps(self.cap_map.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
