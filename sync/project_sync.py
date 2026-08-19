import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from data_mining.config import PROJECT_ROOT, settings
from data_mining.db.repository import Repository
from data_mining.models.schemas import ProjectCapabilityMap, utc_now_iso

logger = logging.getLogger("data_mining.project_sync")


class ProjectIntelligenceSync:
    """
    Scans the repository codebase dynamically to extract integrated providers,
    models, account managers, and capabilities, synchronizing them with
    the project capabilities mirror.
    """

    def __init__(self, root_dir: Path = PROJECT_ROOT, repo: Optional[Repository] = None):
        self.root_dir = root_dir
        self.repo = repo or Repository()

    def scan_codebase(self) -> ProjectCapabilityMap:
        """
        Inspects existing folders (accounts_manager, accounts_json, refrish_acc_manager)
        and code files to dynamically assemble the project capability map.
        """
        providers: Set[str] = {"OpenAI", "ChatGPT"}
        models: Set[str] = {"gpt-4", "gpt-4o", "gpt-3.5-turbo", "chatgpt-web"}
        features: Set[str] = {
            "account_lifecycle_management",
            "token_refresh_monitoring",
            "session_persistence",
            "cookie_authentication",
        }
        capabilities: Set[str] = {
            "chat",
            "text_generation",
            "session_management",
            "automated_token_refresh",
        }
        integrations: Set[str] = {
            "chatgpt_web_interface",
            "accounts_manager",
            "refrish_acc_manager",
        }
        metadata: Dict[str, Any] = {"scanned_sources": []}

        # Inspect accounts_json
        acc_json_dir = self.root_dir / "accounts_json"
        if acc_json_dir.exists():
            for f in acc_json_dir.glob("*.json"):
                stem = f.stem.lower()
                metadata["scanned_sources"].append(str(f.relative_to(self.root_dir)))
                if "chat_gpt" in stem or "openai" in stem:
                    providers.add("OpenAI")
                    providers.add("ChatGPT")
                elif "deepseek" in stem:
                    providers.add("DeepSeek")
                    models.add("deepseek-chat")
                    models.add("deepseek-reasoner")
                elif "claude" in stem or "anthropic" in stem:
                    providers.add("Anthropic")
                    models.add("claude-3.5-sonnet")

        # Inspect accounts_manager
        acc_mgr_dir = self.root_dir / "accounts_manager"
        if acc_mgr_dir.exists():
            for f in acc_mgr_dir.glob("*.py"):
                metadata["scanned_sources"].append(str(f.relative_to(self.root_dir)))
                content = f.read_text(encoding="utf-8", errors="ignore").lower()
                if "chat_gpt" in f.stem or "chatgpt" in content:
                    features.add("chatgpt_account_creation")
                if "cookies" in content:
                    capabilities.add("cookie_auth")
                if "tokens" in content:
                    capabilities.add("token_auth")

        # Inspect refrish_acc_manager
        ref_mgr_dir = self.root_dir / "refrish_acc_manager"
        if ref_mgr_dir.exists():
            for f in ref_mgr_dir.glob("*.py"):
                metadata["scanned_sources"].append(str(f.relative_to(self.root_dir)))
                content = f.read_text(encoding="utf-8", errors="ignore").lower()
                if "expires_in" in content:
                    features.add("token_expiry_monitoring")
                    capabilities.add("scheduled_token_refresh")

        # Create Map
        cap_map = ProjectCapabilityMap(
            features=sorted(list(features)),
            models=sorted(list(models)),
            providers=sorted(list(providers)),
            capabilities=sorted(list(capabilities)),
            integrations=sorted(list(integrations)),
            last_synced=utc_now_iso(),
            metadata=metadata,
        )

        return cap_map

    def sync_mirror(self, output_path: Optional[Path] = None) -> ProjectCapabilityMap:
        """
        Performs codebase inspection, updates project_capabilities.json,
        and synchronizes database project mirror.
        """
        cap_map = self.scan_codebase()
        target_path = output_path or settings.PROJECT_CAPABILITIES_PATH

        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Merge with existing file if present
        if target_path.exists():
            try:
                existing_data = json.loads(target_path.read_text(encoding="utf-8"))
                existing_map = ProjectCapabilityMap(**existing_data)
                # Merge sets
                cap_map.features = sorted(list(set(cap_map.features + existing_map.features)))
                cap_map.models = sorted(list(set(cap_map.models + existing_map.models)))
                cap_map.providers = sorted(list(set(cap_map.providers + existing_map.providers)))
                cap_map.capabilities = sorted(list(set(cap_map.capabilities + existing_map.capabilities)))
                cap_map.integrations = sorted(list(set(cap_map.integrations + existing_map.integrations)))
            except Exception as e:
                logger.warning(f"Could not merge with existing capabilities file: {e}")

        # Save to JSON
        target_path.write_text(
            json.dumps(cap_map.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Sync to DB
        self.repo.sync_project_mirror(cap_map)
        logger.info(f"Synchronized project capabilities mirror ({len(cap_map.models)} models, {len(cap_map.capabilities)} capabilities)")
        return cap_map
