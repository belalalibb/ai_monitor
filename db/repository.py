import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from data_mining.db.database import get_db, init_db
from data_mining.models.enums import (
    EventType,
    NotificationStatus,
    Priority,
    SourceReliability,
)
from data_mining.models.schemas import (
    ChangeEvent,
    ComparisonResult,
    FreeServiceInfo,
    ModelInfo,
    MonitorRunStats,
    ProjectCapabilityMap,
    ProviderInfo,
    SearchQueryItem,
    utc_now_iso,
)


class Repository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        init_db(self.db_path)

    # -------------------------------------------------------------
    # Providers
    # -------------------------------------------------------------
    def upsert_provider(self, provider: ProviderInfo) -> int:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO providers (name, domain, description, official_urls, is_monitored, categories, last_checked, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    domain = excluded.domain,
                    description = excluded.description,
                    official_urls = excluded.official_urls,
                    is_monitored = excluded.is_monitored,
                    categories = excluded.categories,
                    last_checked = COALESCE(excluded.last_checked, providers.last_checked)
                RETURNING id;
                """,
                (
                    provider.name,
                    provider.domain,
                    provider.description,
                    json.dumps(provider.official_urls),
                    1 if provider.is_monitored else 0,
                    json.dumps(provider.categories),
                    provider.last_checked,
                    now,
                ),
            )
            row = cur.fetchone()
            return row["id"] if row else 0

    def get_providers(self, monitored_only: bool = True) -> List[ProviderInfo]:
        with get_db(self.db_path) as conn:
            query = "SELECT * FROM providers WHERE is_monitored = 1" if monitored_only else "SELECT * FROM providers"
            cur = conn.execute(query)
            rows = cur.fetchall()
            return [
                ProviderInfo(
                    name=r["name"],
                    domain=r["domain"],
                    description=r["description"] or "",
                    official_urls=json.loads(r["official_urls"] or "[]"),
                    is_monitored=bool(r["is_monitored"]),
                    categories=json.loads(r["categories"] or "[]"),
                    last_checked=r["last_checked"],
                )
                for r in rows
            ]

    def get_provider_by_name(self, name: str) -> Optional[ProviderInfo]:
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM providers WHERE LOWER(name) = LOWER(?)", (name,))
            r = cur.fetchone()
            if not r:
                return None
            return ProviderInfo(
                name=r["name"],
                domain=r["domain"],
                description=r["description"] or "",
                official_urls=json.loads(r["official_urls"] or "[]"),
                is_monitored=bool(r["is_monitored"]),
                categories=json.loads(r["categories"] or "[]"),
                last_checked=r["last_checked"],
            )

    def update_provider_last_checked(self, name: str) -> None:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            conn.execute(
                "UPDATE providers SET last_checked = ? WHERE LOWER(name) = LOWER(?)",
                (now, name),
            )

    # -------------------------------------------------------------
    # URLs & Deduplication
    # -------------------------------------------------------------
    def is_url_known(self, url_hash: str) -> bool:
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT 1 FROM urls WHERE url_hash = ?", (url_hash,))
            return cur.fetchone() is not None

    def get_url_by_hash(self, url_hash: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM urls WHERE url_hash = ?", (url_hash,))
            r = cur.fetchone()
            return dict(r) if r else None

    def upsert_url(
        self,
        raw_url: str,
        canonical_url: str,
        url_hash: str,
        domain: str,
        content_hash: Optional[str] = None,
        semantic_hash: Optional[str] = None,
        discovered_by_query_id: Optional[int] = None,
    ) -> Tuple[int, bool]:
        """Returns (url_id, is_new). Atomic via ON CONFLICT (no check-then-insert race)."""
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            # Detect novelty atomically: a pre-existing row means not new.
            cur = conn.execute("SELECT 1 FROM urls WHERE url_hash = ?", (url_hash,))
            was_existing = cur.fetchone() is not None

            cur = conn.execute(
                """
                INSERT INTO urls (raw_url, canonical_url, url_hash, domain, first_seen, last_seen, content_hash, semantic_hash, discovered_by_query_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url_hash) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    content_hash = COALESCE(excluded.content_hash, urls.content_hash),
                    semantic_hash = COALESCE(excluded.semantic_hash, urls.semantic_hash)
                RETURNING id;
                """,
                (
                    raw_url,
                    canonical_url,
                    url_hash,
                    domain,
                    now,
                    now,
                    content_hash,
                    semantic_hash,
                    discovered_by_query_id,
                ),
            )
            row = cur.fetchone()
            return row["id"], not was_existing

    def is_domain_known(self, domain: str) -> bool:
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT 1 FROM urls WHERE domain = ? LIMIT 1", (domain,))
            if cur.fetchone():
                return True
            cur = conn.execute("SELECT 1 FROM providers WHERE domain = ? LIMIT 1", (domain,))
            return cur.fetchone() is not None

    # -------------------------------------------------------------
    # Models
    # -------------------------------------------------------------
    def upsert_model(self, model: ModelInfo) -> Tuple[int, bool]:
        """Returns (model_id, is_new)."""
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                SELECT id, context_window, pricing, free_status, tools, vision, reasoning
                FROM models
                WHERE LOWER(provider_name) = LOWER(?) AND LOWER(model_name) = LOWER(?) AND version = ?
                """,
                (model.provider, model.model_name, model.version),
            )
            existing = cur.fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE models SET
                        last_seen = ?,
                        modalities = ?,
                        context_window = COALESCE(?, context_window),
                        reasoning = ?,
                        tools = ?,
                        structured_output = ?,
                        vision = ?,
                        audio = ?,
                        video = ?,
                        coding = ?,
                        agentic_capabilities = ?,
                        open_weights = ?,
                        license = COALESCE(?, license),
                        api_available = ?,
                        pricing = ?,
                        free_status = ?,
                        confidence_score = MAX(confidence_score, ?)
                    WHERE id = ?;
                    """,
                    (
                        now,
                        json.dumps(model.modalities),
                        model.context_window,
                        1 if model.reasoning else 0,
                        1 if model.tools else 0,
                        1 if model.structured_output else 0,
                        1 if model.vision else 0,
                        1 if model.audio else 0,
                        1 if model.video else 0,
                        1 if model.coding else 0,
                        1 if model.agentic_capabilities else 0,
                        1 if model.open_weights else 0,
                        model.license,
                        1 if model.api_available else 0,
                        json.dumps(model.pricing or {}),
                        model.free_status.value,
                        model.confidence_score,
                        existing["id"],
                    ),
                )
                return existing["id"], False

            cur = conn.execute(
                """
                INSERT INTO models (
                    provider_name, model_name, version, release_date, modalities, context_window,
                    reasoning, tools, structured_output, vision, audio, video, coding,
                    agentic_capabilities, open_weights, license, api_available, pricing,
                    free_status, confidence_score, discovered_by_query_id, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    model.provider,
                    model.model_name,
                    model.version,
                    model.release_date,
                    json.dumps(model.modalities),
                    model.context_window,
                    1 if model.reasoning else 0,
                    1 if model.tools else 0,
                    1 if model.structured_output else 0,
                    1 if model.vision else 0,
                    1 if model.audio else 0,
                    1 if model.video else 0,
                    1 if model.coding else 0,
                    1 if model.agentic_capabilities else 0,
                    1 if model.open_weights else 0,
                    model.license,
                    1 if model.api_available else 0,
                    json.dumps(model.pricing or {}),
                    model.free_status.value,
                    model.confidence_score,
                    model.discovered_by_query_id,
                    now,
                    now,
                ),
            )
            return cur.lastrowid, True

    def get_all_models(self) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM models ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------
    # Free Services
    # -------------------------------------------------------------
    def upsert_free_service(self, service: FreeServiceInfo) -> Tuple[int, bool]:
        """Returns (service_id, is_new)."""
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT id FROM free_services WHERE domain = ?", (service.domain,))
            existing = cur.fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE free_services SET
                        service_name = ?,
                        models = ?,
                        api_available = ?,
                        free_status = ?,
                        limits = ?,
                        quota_details = ?,
                        registration_required = ?,
                        payment_method_required = ?,
                        region_restrictions = ?,
                        official_documentation = ?,
                        terms_url = ?,
                        source_url = ?,
                        confidence_score = MAX(confidence_score, ?),
                        last_verified = ?
                    WHERE id = ?;
                    """,
                    (
                        service.service_name,
                        json.dumps(service.models),
                        1 if service.api_available else 0,
                        service.free_status.value,
                        service.limits,
                        service.quota_details,
                        1 if service.registration_required else 0,
                        1 if service.payment_method_required else 0,
                        service.region_restrictions,
                        service.official_documentation,
                        service.terms_url,
                        service.source_url,
                        service.confidence_score,
                        now,
                        existing["id"],
                    ),
                )
                return existing["id"], False

            cur = conn.execute(
                """
                INSERT INTO free_services (
                    service_name, domain, models, api_available, free_status, limits,
                    quota_details, registration_required, payment_method_required,
                    region_restrictions, official_documentation, terms_url, source_url,
                    confidence_score, last_verified, discovered_by_query_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    service.service_name,
                    service.domain,
                    json.dumps(service.models),
                    1 if service.api_available else 0,
                    service.free_status.value,
                    service.limits,
                    service.quota_details,
                    1 if service.registration_required else 0,
                    1 if service.payment_method_required else 0,
                    service.region_restrictions,
                    service.official_documentation,
                    service.terms_url,
                    service.source_url,
                    service.confidence_score,
                    now,
                    service.discovered_by_query_id,
                ),
            )
            return cur.lastrowid, True

    def get_all_free_services(self) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM free_services ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------------------------
    # Event Groups & Event Deduplication
    # -------------------------------------------------------------
    def get_or_create_event_group(
        self,
        canonical_event_key: str,
        event_type: EventType,
        provider: str,
        entity_name: str,
        title: str,
    ) -> Tuple[int, bool]:
        """Returns (event_group_id, is_new_event). Race-safe via ON CONFLICT DO NOTHING."""
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO event_groups (canonical_event_key, event_type, provider, entity_name, title, created_at, notification_sent)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(canonical_event_key) DO NOTHING
                RETURNING id;
                """,
                (canonical_event_key, event_type.value, provider, entity_name, title, now),
            )
            row = cur.fetchone()
            if row:
                return row["id"], True

            # Row already existed (or was inserted concurrently)
            cur = conn.execute(
                "SELECT id FROM event_groups WHERE canonical_event_key = ?",
                (canonical_event_key,),
            )
            existing = cur.fetchone()
            return existing["id"], False

    def try_claim_event_group_notification(self, event_group_id: int) -> bool:
        """
        Atomically claims the right to notify for an event group.
        Returns True only for the single caller that flips notification_sent 0 -> 1.
        Eliminates the check-then-send race that caused duplicate notifications.
        """
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE event_groups SET notification_sent = 1 WHERE id = ? AND notification_sent = 0",
                (event_group_id,),
            )
            return cur.rowcount == 1

    def release_event_group_notification_claim(self, event_group_id: int) -> None:
        """Releases a previously acquired claim (e.g. after a failed send) so retries remain possible."""
        with get_db(self.db_path) as conn:
            conn.execute(
                "UPDATE event_groups SET notification_sent = 0 WHERE id = ?",
                (event_group_id,),
            )

    def mark_event_group_notified(self, event_group_id: int) -> None:
        with get_db(self.db_path) as conn:
            conn.execute(
                "UPDATE event_groups SET notification_sent = 1 WHERE id = ?",
                (event_group_id,),
            )

    def is_event_group_notified(self, event_group_id: int) -> bool:
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                "SELECT notification_sent FROM event_groups WHERE id = ?",
                (event_group_id,),
            )
            r = cur.fetchone()
            return bool(r["notification_sent"]) if r else False

    def save_change_event(self, event: ChangeEvent, event_group_id: Optional[int] = None) -> int:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO change_events (
                    event_group_id, event_type, entity_type, entity_name, provider,
                    title, description, diff_summary, priority, source_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_group_id,
                    event.event_type.value,
                    event.entity_type,
                    event.entity_name,
                    event.provider,
                    event.title,
                    event.description,
                    json.dumps(event.diff_summary),
                    event.priority.value,
                    event.source_url,
                    now,
                ),
            )
            return cur.lastrowid

    # -------------------------------------------------------------
    # Evidence Records
    # -------------------------------------------------------------
    def save_evidence(
        self,
        entity_type: str,
        entity_name: str,
        source_url: str,
        source_type: SourceReliability,
        extracted_fact: str,
        validation_checks: List[str],
        reasoning: str,
        confidence_score: float,
    ) -> int:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO evidence_records (
                    entity_type, entity_name, source_url, source_type, extracted_fact,
                    validation_checks, reasoning, confidence_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    entity_type,
                    entity_name,
                    source_url,
                    source_type.value,
                    extracted_fact,
                    json.dumps(validation_checks),
                    reasoning,
                    confidence_score,
                    now,
                ),
            )
            return cur.lastrowid

    # -------------------------------------------------------------
    # Search Queries & Lineage
    # -------------------------------------------------------------
    def upsert_search_query(self, query: str, category: str = "general", discovered_by: str = "system") -> int:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT id FROM search_queries WHERE query = ?", (query,))
            existing = cur.fetchone()
            if existing:
                return existing["id"]

            cur = conn.execute(
                """
                INSERT INTO search_queries (query, category, discovered_by, usefulness_score, created_at)
                VALUES (?, ?, ?, 1.0, ?);
                """,
                (query, category, discovered_by, now),
            )
            return cur.lastrowid

    def record_query_outcome(
        self,
        query_id: int,
        results_count: int,
        new_domains: int,
        new_models: int,
        new_services: int,
        duplicates_count: int,
    ) -> None:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM search_queries WHERE id = ?", (query_id,))
            q = cur.fetchone()
            if not q:
                return

            new_yield = (new_domains * 2.0) + (new_models * 3.0) + (new_services * 3.0)
            penalty = 0.5 if (results_count > 0 and (new_domains + new_models + new_services) == 0) else 0.0

            # Adaptive usefulness score: moving average bounded between 0.1 and 10.0
            current_score = q["usefulness_score"]
            updated_score = max(0.1, min(10.0, (current_score * 0.7) + (new_yield * 0.3) - penalty))

            dup_rate = duplicates_count / max(1, results_count)

            conn.execute(
                """
                UPDATE search_queries SET
                    usefulness_score = ?,
                    results_count = results_count + ?,
                    new_domains_found = new_domains_found + ?,
                    new_models_found = new_models_found + ?,
                    new_services_found = new_services_found + ?,
                    duplicate_rate = (duplicate_rate + ?) / 2.0,
                    last_used = ?
                WHERE id = ?;
                """,
                (
                    updated_score,
                    results_count,
                    new_domains,
                    new_models,
                    new_services,
                    dup_rate,
                    now,
                    query_id,
                ),
            )

    def get_top_search_queries(self, limit: int = 15) -> List[SearchQueryItem]:
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM search_queries ORDER BY usefulness_score DESC, results_count ASC LIMIT ?",
                (limit,),
            )
            return [
                SearchQueryItem(
                    id=r["id"],
                    query=r["query"],
                    category=r["category"],
                    discovered_by=r["discovered_by"],
                    usefulness_score=r["usefulness_score"],
                    results_count=r["results_count"],
                    new_domains_found=r["new_domains_found"],
                    new_models_found=r["new_models_found"],
                    new_services_found=r["new_services_found"],
                    duplicate_rate=r["duplicate_rate"],
                    last_used=r["last_used"],
                    created_at=r["created_at"],
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------
    # Comparisons & Notifications
    # -------------------------------------------------------------
    def save_comparison(self, comp: ComparisonResult) -> int:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO comparisons (
                    item_type, item_name, provider, status, new_capabilities,
                    existing_capabilities, equivalence_reasoning, priority,
                    confidence_score, evidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    comp.item_type.value,
                    comp.item_name,
                    comp.provider,
                    comp.status.value,
                    json.dumps(comp.new_capabilities),
                    json.dumps(comp.existing_capabilities),
                    comp.equivalence_reasoning,
                    comp.priority.value,
                    comp.confidence_score,
                    comp.evidence,
                    now,
                ),
            )
            return cur.lastrowid

    def save_notification(
        self,
        event_group_id: Optional[int],
        event_type: EventType,
        title: str,
        body: str,
        priority: Priority,
        recipient: str,
        status: NotificationStatus,
        error_message: Optional[str] = None,
    ) -> int:
        now = utc_now_iso()
        sent_at = now if status == NotificationStatus.SENT else None
        with get_db(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO notifications (
                    event_group_id, event_type, title, body, priority, recipient,
                    status, sent_at, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event_group_id,
                    event_type.value,
                    title,
                    body,
                    priority.value,
                    recipient,
                    status.value,
                    sent_at,
                    error_message,
                    now,
                ),
            )
            return cur.lastrowid

    # -------------------------------------------------------------
    # Monitor Runs & Metrics
    # -------------------------------------------------------------
    def start_monitor_run(self, run_id: str) -> None:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO monitor_runs (run_id, started_at, status, created_at)
                VALUES (?, ?, 'running', ?);
                """,
                (run_id, now, now),
            )

    def finish_monitor_run(self, stats: MonitorRunStats) -> None:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            conn.execute(
                """
                UPDATE monitor_runs SET
                    finished_at = ?,
                    status = ?,
                    sources_checked = ?,
                    queries_executed = ?,
                    urls_discovered = ?,
                    urls_new = ?,
                    urls_duplicate = ?,
                    models_discovered = ?,
                    capabilities_new = ?,
                    free_services_discovered = ?,
                    notifications_sent = ?,
                    errors = ?
                WHERE run_id = ?;
                """,
                (
                    now,
                    stats.status.value,
                    stats.sources_checked,
                    stats.queries_executed,
                    stats.urls_discovered,
                    stats.urls_new,
                    stats.urls_duplicate,
                    stats.models_discovered,
                    stats.capabilities_new,
                    stats.free_services_discovered,
                    stats.notifications_sent,
                    json.dumps(stats.errors),
                    stats.run_id,
                ),
            )

    # -------------------------------------------------------------
    # Audit Logs
    # -------------------------------------------------------------
    def log_audit(
        self,
        action: str,
        actor: str,
        entity_type: str,
        entity_id: str,
        details: str,
        confidence: float = 1.0,
    ) -> None:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (action, actor, entity_type, entity_id, details, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (action, actor, entity_type, entity_id, details, confidence, now),
            )

    # -------------------------------------------------------------
    # Project Capability Mirror Synchronization
    # -------------------------------------------------------------
    def sync_project_mirror(self, cap_map: ProjectCapabilityMap) -> None:
        now = utc_now_iso()
        with get_db(self.db_path) as conn:
            # Sync providers
            for p in cap_map.providers:
                conn.execute(
                    """
                    INSERT INTO project_capabilities_mirror (category, item_name, source_file, last_synced)
                    VALUES ('provider', ?, 'project_sync', ?)
                    ON CONFLICT(category, item_name) DO UPDATE SET last_synced = excluded.last_synced;
                    """,
                    (p, now),
                )
            # Sync models
            for m in cap_map.models:
                conn.execute(
                    """
                    INSERT INTO project_capabilities_mirror (category, item_name, source_file, last_synced)
                    VALUES ('model', ?, 'project_sync', ?)
                    ON CONFLICT(category, item_name) DO UPDATE SET last_synced = excluded.last_synced;
                    """,
                    (m, now),
                )
            # Sync capabilities
            for c in cap_map.capabilities:
                conn.execute(
                    """
                    INSERT INTO project_capabilities_mirror (category, item_name, source_file, last_synced)
                    VALUES ('capability', ?, 'project_sync', ?)
                    ON CONFLICT(category, item_name) DO UPDATE SET last_synced = excluded.last_synced;
                    """,
                    (c, now),
                )
            # Sync features
            for f in cap_map.features:
                conn.execute(
                    """
                    INSERT INTO project_capabilities_mirror (category, item_name, source_file, last_synced)
                    VALUES ('feature', ?, 'project_sync', ?)
                    ON CONFLICT(category, item_name) DO UPDATE SET last_synced = excluded.last_synced;
                    """,
                    (f, now),
                )
            # Sync integrations
            for i in cap_map.integrations:
                conn.execute(
                    """
                    INSERT INTO project_capabilities_mirror (category, item_name, source_file, last_synced)
                    VALUES ('integration', ?, 'project_sync', ?)
                    ON CONFLICT(category, item_name) DO UPDATE SET last_synced = excluded.last_synced;
                    """,
                    (i, now),
                )

    def get_stats_summary(self) -> Dict[str, int]:
        with get_db(self.db_path) as conn:
            stats = {}
            for table in [
                "providers",
                "models",
                "free_services",
                "urls",
                "search_queries",
                "change_events",
                "event_groups",
                "notifications",
                "comparisons",
                "audit_logs",
                "monitor_runs",
            ]:
                cur = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
                stats[table] = cur.fetchone()["cnt"]
            return stats
