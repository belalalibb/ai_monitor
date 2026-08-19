"""
SQL Schema and DDL for the AI Intelligence Monitor Subsystem.
"""

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    description TEXT DEFAULT '',
    official_urls TEXT DEFAULT '[]',
    is_monitored INTEGER DEFAULT 1,
    categories TEXT DEFAULT '[]',
    last_checked TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    version TEXT DEFAULT '1.0',
    release_date TEXT,
    modalities TEXT DEFAULT '["text"]',
    context_window INTEGER,
    reasoning INTEGER DEFAULT 0,
    tools INTEGER DEFAULT 0,
    structured_output INTEGER DEFAULT 0,
    vision INTEGER DEFAULT 0,
    audio INTEGER DEFAULT 0,
    video INTEGER DEFAULT 0,
    coding INTEGER DEFAULT 0,
    agentic_capabilities INTEGER DEFAULT 0,
    open_weights INTEGER DEFAULT 0,
    license TEXT,
    api_available INTEGER DEFAULT 0,
    pricing TEXT DEFAULT '{}',
    free_status TEXT DEFAULT 'unknown',
    confidence_score REAL DEFAULT 0.5,
    discovered_by_query_id INTEGER,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE(provider_name, model_name, version)
);

CREATE TABLE IF NOT EXISTS capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    aliases TEXT DEFAULT '[]',
    description TEXT DEFAULT '',
    providers TEXT DEFAULT '[]',
    models TEXT DEFAULT '[]',
    project_support TEXT DEFAULT 'PROJECT_UNKNOWN',
    evidence TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT UNIQUE NOT NULL,
    category TEXT DEFAULT 'general',
    description TEXT DEFAULT '',
    project_status TEXT DEFAULT 'PROJECT_UNKNOWN',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    reliability_score REAL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT UNIQUE NOT NULL,
    category TEXT DEFAULT 'general',
    discovered_by TEXT DEFAULT 'system',
    usefulness_score REAL DEFAULT 1.0,
    results_count INTEGER DEFAULT 0,
    new_domains_found INTEGER DEFAULT 0,
    new_models_found INTEGER DEFAULT 0,
    new_services_found INTEGER DEFAULT 0,
    duplicate_rate REAL DEFAULT 0.0,
    last_used TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_url TEXT NOT NULL,
    canonical_url TEXT UNIQUE NOT NULL,
    url_hash TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    content_hash TEXT,
    semantic_hash TEXT,
    status_code INTEGER DEFAULT 200,
    discovered_by_query_id INTEGER,
    FOREIGN KEY(discovered_by_query_id) REFERENCES search_queries(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovery_type TEXT NOT NULL,
    title TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    url_id INTEGER,
    canonical_url TEXT NOT NULL,
    summary TEXT NOT NULL,
    raw_data TEXT DEFAULT '{}',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    FOREIGN KEY(url_id) REFERENCES urls(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS discovery_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovery_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    semantic_hash TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(discovery_id) REFERENCES discoveries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS free_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    domain TEXT UNIQUE NOT NULL,
    models TEXT DEFAULT '[]',
    api_available INTEGER DEFAULT 0,
    free_status TEXT NOT NULL,
    limits TEXT DEFAULT 'Unknown limits',
    quota_details TEXT DEFAULT '',
    registration_required INTEGER DEFAULT 1,
    payment_method_required INTEGER DEFAULT 0,
    region_restrictions TEXT DEFAULT 'None specified',
    official_documentation TEXT DEFAULT '',
    terms_url TEXT DEFAULT '',
    source_url TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5,
    last_verified TEXT NOT NULL,
    discovered_by_query_id INTEGER,
    FOREIGN KEY(discovered_by_query_id) REFERENCES search_queries(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS event_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_event_key TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    notification_sent INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS change_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_group_id INTEGER,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    diff_summary TEXT DEFAULT '{}',
    priority TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(event_group_id) REFERENCES event_groups(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    extracted_fact TEXT NOT NULL,
    validation_checks TEXT DEFAULT '[]',
    reasoning TEXT DEFAULT '',
    confidence_score REAL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comparisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type TEXT NOT NULL,
    item_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    new_capabilities TEXT DEFAULT '[]',
    existing_capabilities TEXT DEFAULT '[]',
    equivalence_reasoning TEXT DEFAULT '',
    priority TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.5,
    evidence TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_group_id INTEGER,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    priority TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_at TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(event_group_id) REFERENCES event_groups(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS monitor_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    sources_checked INTEGER DEFAULT 0,
    queries_executed INTEGER DEFAULT 0,
    urls_discovered INTEGER DEFAULT 0,
    urls_new INTEGER DEFAULT 0,
    urls_duplicate INTEGER DEFAULT 0,
    models_discovered INTEGER DEFAULT 0,
    capabilities_new INTEGER DEFAULT 0,
    free_services_discovered INTEGER DEFAULT 0,
    notifications_sent INTEGER DEFAULT 0,
    errors TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_capabilities_mirror (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    item_name TEXT NOT NULL,
    source_file TEXT DEFAULT '',
    metadata TEXT DEFAULT '{}',
    last_synced TEXT NOT NULL,
    UNIQUE(category, item_name)
);

-- Indexes for high-speed lookups and deduplication
CREATE INDEX IF NOT EXISTS idx_urls_canonical ON urls(canonical_url);
CREATE INDEX IF NOT EXISTS idx_urls_hash ON urls(url_hash);
CREATE INDEX IF NOT EXISTS idx_urls_domain ON urls(domain);
CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider_name);
CREATE INDEX IF NOT EXISTS idx_models_name ON models(model_name);
CREATE INDEX IF NOT EXISTS idx_free_services_domain ON free_services(domain);
CREATE INDEX IF NOT EXISTS idx_event_groups_key ON event_groups(canonical_event_key);
CREATE INDEX IF NOT EXISTS idx_change_events_type ON change_events(event_type);
CREATE INDEX IF NOT EXISTS idx_queries_score ON search_queries(usefulness_score);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
"""
