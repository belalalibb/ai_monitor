from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from data_mining.models.enums import (
    ComparisonStatus,
    DiscoveryType,
    EventType,
    FreeStatus,
    NotificationStatus,
    Priority,
    RunStatus,
    SourceReliability,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvidenceRecord(BaseModel):
    source_url: str = Field(description="URL where fact was observed")
    source_type: SourceReliability = Field(default=SourceReliability.UNKNOWN)
    extracted_fact: str = Field(description="Raw extracted fact summary")
    validation_checks: List[str] = Field(default_factory=list, description="Validation steps performed")
    reasoning: str = Field(default="", description="Logical/semantic reasoning for decision")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    verified_at: str = Field(default_factory=utc_now_iso)


class ProviderInfo(BaseModel):
    name: str
    domain: str
    description: str = ""
    official_urls: List[str] = Field(default_factory=list)
    is_monitored: bool = True
    categories: List[str] = Field(default_factory=list)
    last_checked: Optional[str] = None


class ModelInfo(BaseModel):
    provider: str
    model_name: str
    version: str = "1.0"
    release_date: Optional[str] = None
    modalities: List[str] = Field(default_factory=lambda: ["text"])
    context_window: Optional[int] = None
    reasoning: bool = False
    tools: bool = False
    structured_output: bool = False
    vision: bool = False
    audio: bool = False
    video: bool = False
    coding: bool = False
    agentic_capabilities: bool = False
    open_weights: bool = False
    license: Optional[str] = None
    api_available: bool = False
    pricing: Optional[Dict[str, Any]] = None
    free_status: FreeStatus = FreeStatus.UNKNOWN
    source_urls: List[str] = Field(default_factory=list)
    confidence_score: float = 0.5
    discovered_by_query_id: Optional[int] = None
    evidence: Optional[EvidenceRecord] = None


class CapabilityInfo(BaseModel):
    name: str
    aliases: List[str] = Field(default_factory=list)
    description: str = ""
    providers: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    project_support: ComparisonStatus = ComparisonStatus.PROJECT_UNKNOWN
    evidence: str = ""


class FreeServiceInfo(BaseModel):
    service_name: str
    domain: str
    models: List[str] = Field(default_factory=list)
    api_available: bool = False
    free_status: FreeStatus = FreeStatus.UNKNOWN
    limits: str = "Unknown limits"
    quota_details: str = ""
    registration_required: bool = True
    payment_method_required: bool = False
    region_restrictions: str = "None specified"
    official_documentation: str = ""
    terms_url: str = ""
    source_url: str = ""
    confidence_score: float = 0.5
    last_verified: str = Field(default_factory=utc_now_iso)
    discovered_by_query_id: Optional[int] = None
    evidence: Optional[EvidenceRecord] = None


class ProjectCapabilityMap(BaseModel):
    features: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    last_synced: str = Field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComparisonResult(BaseModel):
    item_type: DiscoveryType
    item_name: str
    provider: str
    status: ComparisonStatus
    new_capabilities: List[str] = Field(default_factory=list)
    existing_capabilities: List[str] = Field(default_factory=list)
    equivalence_reasoning: str = ""
    priority: Priority = Priority.MEDIUM
    confidence_score: float = 0.5
    evidence: str = ""


class ChangeEvent(BaseModel):
    event_type: EventType
    entity_type: str
    entity_name: str
    provider: str
    title: str
    description: str
    diff_summary: Dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.MEDIUM
    source_url: str = ""
    canonical_event_key: str = ""  # For event-level deduplication
    first_seen: str = Field(default_factory=utc_now_iso)
    evidence: Optional[EvidenceRecord] = None


class SearchQueryItem(BaseModel):
    id: Optional[int] = None
    query: str
    category: str = "general"
    discovered_by: str = "system"
    usefulness_score: float = 1.0
    results_count: int = 0
    new_domains_found: int = 0
    new_models_found: int = 0
    new_services_found: int = 0
    duplicate_rate: float = 0.0
    last_used: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)


class MonitorRunStats(BaseModel):
    run_id: str
    started_at: str = Field(default_factory=utc_now_iso)
    finished_at: Optional[str] = None
    status: RunStatus = RunStatus.RUNNING
    sources_checked: int = 0
    queries_executed: int = 0
    urls_discovered: int = 0
    urls_new: int = 0
    urls_duplicate: int = 0
    models_discovered: int = 0
    capabilities_new: int = 0
    free_services_discovered: int = 0
    notifications_sent: int = 0
    errors: List[str] = Field(default_factory=list)
