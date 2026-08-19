# AI Intelligence Monitor 🚀

A permanent, production-grade **AI Intelligence Monitor** subsystem designed to continuously discover, validate, semantically classify, deduplicate, and notify about AI ecosystem developments (new models, capabilities, APIs, cloud AI services, and free AI platforms).

---

## 🌟 Key Features

- **Project Intelligence Synchronization**: Automatically inspects local codebase capabilities and maintains an active capabilities map to avoid duplicate alerts.
- **Strict Free AI Platform Discovery**: Rigorous multi-tier classification (`FREE`, `FREE_TIER`, `TRIAL`, `OPEN_SOURCE`, `OPEN_WEIGHTS`, `PAID_ONLY`) with evidence verification and quota extraction.
- **Multi-Level Deduplication**:
  - URL Normalization & Tracking parameter stripping (`utm_*`, `fbclid`, etc.) with SHA-256 indexing.
  - **Event-Level Deduplication**: Clusters multiple sources/mirrors covering the exact same announcement into a single canonical event.
- **Dynamic Search Query Engine**: Learns high-yield search terms, tracks query lineage (`discovered_by_query_id`), and automatically generates new search queries.
- **Modular LLM Provider Abstraction**: Supports Groq (Llama-3.3-70B), OpenAI, Gemini, and a deterministic offline Rule-Based fallback.
- **Telegram Notification Dispatcher**: Idempotent message delivery with rich Markdown formatting, emojis, capability diffs, and verification timestamps.
- **Process-Level Isolated Worker Daemon**: Runs independently with graceful signal handling (`SIGINT`/`SIGTERM`) and health metrics.
- **Full Persistence**: Built-in SQLite engine with WAL mode, historical snapshots, and comprehensive audit logs.

---

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
```env
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
COMPARISON_PROVIDER=groq
```

### 3. CLI Usage
```bash
# Sync capabilities from codebase
python cli.py sync

# Run manual discovery cycle
python cli.py scan --limit 3

# View monitor database statistics
python cli.py stats

# View active dynamic search queries and yield scores
python cli.py queries

# View monitored AI providers
python cli.py providers

# Start the standalone background daemon
python cli.py worker
```

### 4. Running Tests
```bash
pytest tests -v
```

---

## 🏗️ Architecture

```
data_mining/
├── cli.py                        # CLI Management Tool
├── config.py                     # Configuration settings
├── project_capabilities.json     # Project Capability Mirror
├── sync/                         # Codebase intelligence synchronization
├── core/                         # Normalization, event dedup, security, audit
├── llm/                          # LLM Providers (Groq, OpenAI, Gemini, Fallback)
├── search/                       # Dynamic queries & web search adapters
├── extractors/                   # HTML, Model, and Free AI validators
├── comparison/                   # Semantic comparator & change detector
├── notifications/                # Telegram dispatcher & formatters
├── scheduler/                    # Standalone background daemon
├── db/                           # SQLite repository, schema & migrations
└── tests/                        # Comprehensive test suite (20 tests)
```
