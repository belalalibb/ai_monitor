# MISSION: BUILD A PERMANENT AI INTELLIGENCE MONITOR

You are a Senior Staff Engineer, Systems Architect, Data Engineer, AI Engineer, Security Engineer, and QA Auditor.

Your task is to design and implement a production-grade **AI Intelligence Monitor** integrated with the existing project.

Do NOT build a simple scraper or news feed.

The system must continuously discover, validate, classify, compare, deduplicate, store, and notify about new AI companies, AI models, AI capabilities, APIs, datasets, cloud AI services, free AI platforms, and relevant AI ecosystem updates.

The system must understand the capabilities and models that already exist in the current project and must NOT repeatedly report things that are already present.

---

## 1. PRIMARY OBJECTIVE

Build a permanent monitoring subsystem that:

1. Monitors major AI companies and model providers.
2. Discovers newly released AI models and capabilities.
3. Detects new AI APIs, cloud AI services, datasets, platforms, and tools.
4. Searches continuously for websites/platforms that provide AI models or AI inference for free.
5. Dynamically generates and improves search keywords.
6. Reads the project's existing features/models file.
7. Compares every discovery against the project's current capabilities.
8. Reports only materially new capabilities, models, providers, or useful resources.
9. Prevents duplicate URLs and duplicate discoveries.
10. Sends every important new discovery/update to Telegram.
11. Runs in a dedicated independent monitoring worker/process.
12. Survives application restarts and continues from persisted state.
13. Maintains historical snapshots so changes can be detected precisely.
14. Uses LLM reasoning for semantic comparison rather than simple string matching.
15. Keeps all monitoring, comparison, and notification logic modular and provider-agnostic.

---

# 2. NON-NEGOTIABLE PRINCIPLES

### Do NOT:

* Build a one-off scraper.
* Hard-code a fixed list of keywords and stop there.
* Assume search-engine snippets are trustworthy.
* Treat every search result as a valid AI service.
* send the same URL twice.
* send repeated notifications for unchanged content.
* report an existing project capability as "new".
* make Groq a hard dependency of the architecture.
* run monitoring inside the main web/API process.
* overwrite historical discoveries.
* silently discard failed validations.
* trust LLM output without validation.
* invent model capabilities, pricing, free tiers, or URLs.
* auto-register accounts on external services.
* expose API keys or Telegram credentials in logs.
* aggressively crawl domains in a way that violates robots.txt, rate limits, or terms of service.

---

# 3. EXISTING PROJECT CAPABILITY SOURCE

Locate the project file that contains the currently implemented:

* features
* models
* providers
* integrations
* capabilities
* AI-related functionality

Do NOT assume the filename.

Inspect the repository and determine the correct source of truth.

The system must support an existing file if one already exists.

If necessary, introduce a normalized internal representation without destroying the original format.

Example conceptual structure:

```json
{
  "features": [],
  "models": [],
  "providers": [],
  "capabilities": [],
  "integrations": []
}
```

The actual implementation must adapt to the project's existing architecture.

---

# 4. EMPTY-FILE INITIAL DISCOVERY MODE

If the project's capability/model file is empty:

Enter:

INITIAL_DISCOVERY_MODE

In this mode:

* discover major AI providers
* discover currently available models
* discover APIs
* discover free AI services
* discover open-weight models
* discover cloud AI services
* discover relevant datasets
* discover AI developer platforms
* discover important AI capabilities

Store all validated discoveries as the initial baseline.

Do NOT report the complete baseline as repeated "new" discoveries indefinitely.

After initialization:

NORMAL_DELTA_MODE

must become the default.

---

# 5. MONITORED COMPANIES

Create a configurable provider registry.

Initial providers should include, where relevant:

* OpenAI
* Anthropic
* Google / Google DeepMind / Google Cloud
* Microsoft / Azure AI
* Meta AI
* Amazon AWS
* NVIDIA
* xAI
* Mistral
* DeepSeek
* Alibaba / Qwen
* Cohere
* AI21
* Hugging Face
* Stability AI
* Z.ai
* other major AI model providers

This list MUST NOT be hard-coded as the only sources.

The system must support adding/removing providers through configuration/database.

---

# 6. SOURCE HIERARCHY

Use source reliability levels.

Priority order:

1. Official provider websites
2. Official documentation
3. Official release notes
4. Official model cards
5. Official GitHub repositories
6. Official research papers
7. Hugging Face/model repositories
8. Cloud provider documentation
9. Trusted technical/news sources
10. Search-engine discovery results

Search engines are primarily a DISCOVERY mechanism.

Whenever possible, validate discovered information against the actual source page.

For each fact, retain source URL and source type.

---

# 7. DISCOVERY ENGINE

Build a discovery pipeline:

```text
Scheduler
   ↓
Search Query Generator
   ↓
Search Engine Layer
   ↓
Candidate URLs
   ↓
URL Normalization
   ↓
Deduplication
   ↓
Fetch
   ↓
Content Extraction
   ↓
AI Relevance Classification
   ↓
Entity Extraction
   ↓
Validation
   ↓
Semantic Comparison
   ↓
Change Detection
   ↓
Database
   ↓
Notification
```

The system must support multiple search providers through an abstraction.

---

# 8. DYNAMIC SEARCH KEYWORD ENGINE

Do NOT rely only on a static keyword list.

Implement a dynamic keyword/query generation system.

Maintain:

```text
Search Vocabulary
Search Queries
Query Categories
Query History
Query Performance
Discovery Sources
Last Seen
First Seen
```

The query generator should generate new queries based on:

* newly discovered terminology
* new model names
* new provider names
* new AI capabilities
* recent release language
* newly discovered websites
* current project gaps
* AI ecosystem trends

Examples:

```text
"new AI model" API
"free inference" LLM
"free AI API" model
"open weights" reasoning model
"free vision model"
"free coding model"
"free multimodal model"
"free API access"
"new model release"
"AI inference platform free"
```

These are examples only.

The system must generate new queries dynamically.

---

# 9. GROQ USAGE

Initially use a Groq API key for:

1. semantic comparison
2. feature extraction
3. query generation
4. classification
5. summarization where appropriate

Credentials MUST come from environment/secrets management.

Example:

```env
GROQ_API_KEY=
```

Never commit credentials.

Never log credentials.

---

# 10. LLM PROVIDER ABSTRACTION

Do NOT couple the system directly to Groq.

Create an interface such as:

```text
LLMProvider
```

Support conceptually:

```text
Groq
OpenAI
Anthropic
Gemini
Ollama/Local
Other providers
```

Configuration:

```env
COMPARISON_PROVIDER=groq
QUERY_GENERATION_PROVIDER=groq
```

The system must allow changing providers without changing business logic.

Implement fallback behavior where appropriate.

---

# 11. SEMANTIC FEATURE COMPARISON

This is a core subsystem.

Given:

CURRENT PROJECT:

```text
features
models
providers
capabilities
integrations
```

and:

NEW DISCOVERY:

```text
model/provider/platform
capabilities
modalities
API features
context window
tools
reasoning
structured outputs
vision
audio
video
agents
RAG
fine-tuning
etc.
```

Ask the LLM to determine:

```text
EXISTING
NEW
UPDATED
UNKNOWN
NOT_RELEVANT
```

Example:

```text
Current:
- Tool calling
- Multimodal
- Long context

Discovery:
- Tool calling
- Multimodal
- Long context
- Structured outputs

Result:

Existing:
- Tool calling
- Multimodal
- Long context

New:
- Structured outputs
```

The comparator must understand semantic equivalence.

For example:

```text
"function calling"
≈
"tool calling"
```

but:

```text
"structured output"
!=
"function calling"
```

unless evidence supports equivalence.

Do NOT trust LLM-only output blindly.

Store evidence supporting each classification.

---

# 12. CHANGE DETECTION

Every source/model/provider must support snapshots.

Store:

```text
first_seen
last_seen
content_hash
semantic_hash
version
previous_version
source_url
```

Detect changes such as:

* new model
* model update
* new capability
* pricing change
* free-tier change
* API change
* context-window change
* deprecation
* availability change
* licensing change

The system must report meaningful changes, not trivial page edits.

---

# 13. URL DEDUPLICATION

This is mandatory.

The same URL MUST NEVER generate duplicate notifications.

Implement:

```text
Raw URL
   ↓
Normalize
   ↓
Remove tracking parameters
   ↓
Canonicalize
   ↓
Hash
   ↓
Database lookup
```

Store:

```text
canonical_url
url_hash
first_seen
last_seen
content_hash
```

The same resource appearing in:

* Google
* Bing
* another search engine
* repeated searches
* different query variations

must resolve to the same canonical resource.

Also support redirect resolution.

---

# 14. CONTENT DEDUPLICATION

URL deduplication is not enough.

Two different URLs may contain the same announcement.

Therefore calculate:

```text
content_hash
semantic_hash
```

and detect duplicate announcements.

Example:

```text
Official blog
News mirror
Search result
GitHub mirror
```

All may refer to the same underlying event.

Only the strongest source should normally trigger the notification.

---

# 15. NEW FREE AI WEBSITE DISCOVERY

Build a dedicated subsystem:

FREE_AI_DISCOVERY

Its job is to continuously discover newly appearing websites/platforms that provide:

* free AI models
* free inference
* free APIs
* free model hosting
* free AI endpoints
* free cloud AI access
* open-source model hosting
* free coding models
* free vision models
* free reasoning models
* free image/video generation
* free AI developer platforms

Search dynamically.

Do NOT assume that "free" means unlimited.

Classify:

```text
FREE
FREE_TIER
TRIAL
OPEN_SOURCE
OPEN_WEIGHTS
PAID_ONLY
UNKNOWN
```

Validate the claim from the actual website.

---

# 16. FREE-SERVICE VALIDATION

For every potentially free service:

extract:

```text
service_name
domain
models
API_available
free_status
limits
daily/monthly quota
registration_required
payment_method_required
region_restrictions
official_documentation
terms_url
source_url
last_verified
```

Do NOT claim:

"Always free"

unless the source explicitly supports that claim.

Prefer:

"Free tier available"

or:

"Free access currently verified"

with verification timestamp.

---

# 17. DATABASE DESIGN

Create appropriate tables/entities.

At minimum:

```text
providers
models
capabilities
features
sources
discoveries
discovery_snapshots
urls
search_queries
search_terms
free_services
change_events
comparisons
notifications
notification_deliveries
monitor_runs
```

Use relationships and indexes appropriately.

Add unique constraints for deduplication.

Use migrations.

Do NOT destroy existing database data.

---

# 18. TELEGRAM NOTIFICATION SYSTEM

Use:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Telegram must be implemented behind an abstraction such as:

```text
NotificationProvider
```

Notifications should be concise but informative.

Example:

```text
🆕 NEW AI DISCOVERY

Provider: Example AI
Model: Example Model

🧠 New capabilities:
• Structured Outputs
• X feature

✅ Already in your project:
• Tool Calling
• Vision

🆓 Free access:
Verified free tier

🔗 Official:
https://...

📅 First seen:
2026-08-18
```

Other event types:

```text
🚀 NEW MODEL
🆕 NEW CAPABILITY
🆓 NEW FREE AI SERVICE
💰 PRICE CHANGE
🔄 MODEL UPDATE
☁️ CLOUD AI UPDATE
📚 NEW DATASET
⚠️ DEPRECATION
🌐 NEW AI PLATFORM
```

Never spam repeated notifications.

---

# 19. NOTIFICATION DEDUPLICATION

A notification should only be sent when:

```text
new discovery
OR
meaningful change
OR
new capability
OR
new free status
OR
important source update
```

Store notification state.

Guarantee idempotency.

If the worker crashes after processing but before notification, the system must safely recover without causing uncontrolled duplicates.

---

# 20. MONITORING MUST RUN INDEPENDENTLY

Monitoring MUST NOT depend on the main API process.

Create a dedicated worker/service:

```text
ai-monitor-worker
```

Possible architecture:

```text
Scheduler
  ↓
Queue
  ↓
Workers
  ├── Source Monitor
  ├── Search Discovery
  ├── Free AI Discovery
  ├── Content Extraction
  ├── LLM Analysis
  ├── Comparison
  └── Telegram Notification
```

Use the project's existing queue/background infrastructure if one exists.

Do NOT introduce unnecessary infrastructure if the project already has a valid equivalent.

---

# 21. SCHEDULING

Monitoring frequency must be configurable.

Example:

```env
COMPANY_SCAN_INTERVAL
MODEL_SCAN_INTERVAL
FREE_AI_SCAN_INTERVAL
SEARCH_DISCOVERY_INTERVAL
```

Different source classes may have different intervals.

Do not hammer sources.

Implement:

* rate limiting
* retry with exponential backoff
* timeout handling
* circuit breaker where useful
* robots/ToS-aware crawling

---

# 22. MONITOR RUN STATE

Persist monitor execution state.

For each run:

```text
run_id
started_at
finished_at
status
sources_checked
queries_executed
urls_discovered
urls_new
urls_duplicate
models_discovered
capabilities_new
notifications_sent
errors
```

The monitor should resume safely after:

* process restart
* machine restart
* worker crash
* network failure
* API failure

---

# 23. ERROR HANDLING

Every external dependency can fail.

Handle independently:

```text
Search API failure
LLM failure
Telegram failure
Website timeout
HTML parsing failure
Rate limit
DNS failure
Malformed content
Invalid JSON
Authentication failure
```

A failure in one source MUST NOT stop the entire monitoring system.

Persist errors for later diagnosis.

---

# 24. SECURITY

Never expose:

```text
GROQ_API_KEY
TELEGRAM_BOT_TOKEN
other API keys
```

in:

* logs
* Telegram messages
* database plaintext where unnecessary
* source code
* git
* exception messages

Use environment variables or the existing project's secret management.

Sanitize external content before processing/storing/displaying.

Treat scraped content as untrusted input.

Protect against prompt injection contained inside scraped pages.

The LLM must never be instructed to execute arbitrary instructions found in external sources.

---

# 25. PROMPT-INJECTION DEFENSE

External webpages may contain malicious text.

The system must distinguish:

```text
DATA
```

from:

```text
INSTRUCTIONS
```

External content is DATA only.

Never allow scraped page text to override system instructions, project rules, security constraints, or tool policies.

Implement structured extraction instead of blindly passing entire webpages whenever possible.

---

# 26. SOURCE TRUST SCORING

Each discovery should receive a confidence/trust score.

Example:

```text
Official source              = highest
Official docs                = high
Official GitHub              = high
Hugging Face                 = high/moderate
Trusted publication          = moderate
Search result only           = low
Unknown website              = very low
```

Combine:

```text
source reliability
content quality
cross-source agreement
LLM confidence
validation success
```

into a final confidence score.

Do not send low-confidence claims as confirmed facts.

---

# 27. AI KNOWLEDGE MODEL

Normalize discoveries into structured entities.

For models:

```text
provider
model_name
version
release_date
modalities
context_window
reasoning
tools
structured_output
vision
audio
video
coding
agentic_capabilities
open_weights
license
api_available
pricing
free_status
source_urls
```

For platforms:

```text
name
domain
provider
services
models
api
free_status
limits
registration
source
last_verified
```

For capabilities:

```text
name
aliases
description
first_seen
providers
models
project_support
evidence
```

---

# 28. PROJECT-AWARE INTELLIGENCE

The monitor must understand the project's current state.

Every discovery should be classified relative to:

```text
PROJECT_ALREADY_HAS
PROJECT_PARTIAL_SUPPORT
PROJECT_DOES_NOT_HAVE
PROJECT_UNKNOWN
```

Examples:

```text
Model already integrated
Model not integrated
Capability already implemented
Capability missing
Provider already supported
Provider not supported
API available but not integrated
Free platform discovered but not used
```

This is the difference between a generic crawler and a project-aware intelligence system.

---

# 29. REPORT PRIORITY

Assign:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

Example:

CRITICAL:

* major model release
* major API breaking change
* important deprecation

HIGH:

* new capability
* major free API discovery
* important cloud service

MEDIUM:

* new model update
* pricing change

LOW:

* minor documentation changes

Do not notify Telegram for insignificant events unless explicitly configured.

---

# 30. SEARCH RESULT QUALITY

Do not trust search ranking alone.

For every candidate:

```text
Search Result
↓
Fetch page
↓
Extract title
↓
Extract main content
↓
Identify AI relevance
↓
Identify provider
↓
Identify model/service
↓
Validate
```

Reject obvious:

* spam
* SEO pages
* duplicates
* irrelevant AI content
* affiliate spam
* fake model listings
* copied announcements without useful information

---

# 31. MODEL DISCOVERY

Detect:

```text
new model
new model version
model rename
model alias
model deprecation
model replacement
model availability
model pricing
model context change
new modality
new capability
```

Keep model lineage.

Example:

```text
Model A
  ↓
Model A v2
  ↓
Model A v3
```

---

# 32. API / CLOUD MONITORING

Monitor cloud providers for:

* new models
* new endpoints
* availability changes
* pricing
* free tiers
* new regions
* SDK changes
* API changes
* deprecations

Particularly monitor:

```text
AWS
Azure
Google Cloud
OpenAI platform
Anthropic API
other major AI infrastructure providers
```

---

# 33. DATASET / RESEARCH DISCOVERY

Also discover relevant:

* AI datasets
* model releases
* technical reports
* research papers
* benchmark updates
* major open-source repositories

But maintain separate categories so Telegram is not flooded.

---

# 34. WEB SEARCH KEYWORD LEARNING

Track query performance.

Example:

```text
query
results_count
new_domains_found
new_models_found
new_services_found
duplicate_rate
usefulness_score
last_used
```

Queries that produce poor results should gradually be deprioritized.

Queries that discover valuable new domains should gain priority.

This creates an adaptive discovery engine.

---

# 35. NO DUPLICATE DOMAIN DISCOVERY

The system must distinguish:

```text
New URL
```

from:

```text
New Domain
```

Example:

```text
example.ai/model-a
example.ai/model-b
```

The domain is the same.

Do not notify:

"New AI website"

every time a new page is discovered.

Notify only when the domain itself is new OR the new page contains a genuinely important discovery.

---

# 36. ADMIN / DASHBOARD SUPPORT

If the project already has an admin/dashboard system, integrate:

```text
Monitor status
Last scan
Next scan
Providers monitored
Queries executed
New discoveries
New free services
Failed sources
Telegram status
LLM provider status
```

Do NOT redesign unrelated existing functionality.

---

# 37. AUDIT LOG

Every important operation must be auditable:

```text
who/what discovered
when
source
decision
comparison result
notification status
LLM provider
confidence
```

The system should be able to answer:

> Why was this notification sent?

with complete evidence.

---

# 38. TESTING REQUIREMENTS

Implement comprehensive tests for:

### Unit tests

* URL canonicalization
* URL deduplication
* content hashing
* semantic normalization
* capability classification
* notification deduplication
* query deduplication
* free-status classification

### Integration tests

* search → discovery
* discovery → validation
* validation → database
* database → comparison
* comparison → Telegram
* worker retry behavior

### Failure tests

* Groq unavailable
* Telegram unavailable
* search API unavailable
* source timeout
* malformed source
* duplicate discovery
* worker crash
* application restart

### Security tests

* secret leakage
* prompt injection
* malicious webpage content
* unsafe HTML
* log injection

---

# 39. OBSERVABILITY

Add structured logs and metrics.

Track:

```text
discoveries_total
new_domains_total
new_models_total
new_capabilities_total
free_services_total
duplicates_total
validation_failures
llm_failures
telegram_failures
search_failures
average_processing_time
```

Use the project's existing observability stack if available.

---

# 40. PERFORMANCE

Do not process every page through an expensive LLM.

Use layered filtering:

```text
cheap URL/domain filtering
        ↓
content relevance
        ↓
rule-based extraction
        ↓
hash comparison
        ↓
LLM only where needed
```

This reduces:

* API cost
* latency
* rate limiting
* unnecessary computation

---

# 41. DATA RETENTION

Retain historical evidence.

Do not overwrite old snapshots.

Keep enough history to answer:

```text
When was this model first discovered?
What changed?
When did the free tier appear?
When did the capability change?
Which source reported it first?
When was it last verified?
```

---

# 42. CONFIGURATION

Provide configuration for:

```env
GROQ_API_KEY=
COMPARISON_PROVIDER=groq
QUERY_GENERATION_PROVIDER=groq

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

MONITOR_ENABLED=true

COMPANY_SCAN_INTERVAL=
MODEL_SCAN_INTERVAL=
FREE_AI_SCAN_INTERVAL=
SEARCH_SCAN_INTERVAL=

MAX_RESULTS_PER_QUERY=
REQUEST_TIMEOUT=
MAX_CONCURRENT_REQUESTS=

NOTIFY_LOW_PRIORITY=false
```

Adapt names to the project's configuration conventions.

---

# 43. IMPLEMENTATION STRATEGY

Before changing code:

1. Inspect the entire repository structure.
2. Identify existing architecture.
3. Find current AI feature/model source file.
4. Find existing background workers/queues.
5. Find existing database layer.
6. Find existing configuration/secrets system.
7. Find existing notification infrastructure.
8. Find existing HTTP/browser/search utilities.
9. Reuse existing abstractions whenever practical.
10. Do not introduce duplicate infrastructure.

Then produce an implementation plan internally and execute it.

---

# 44. IMPORTANT: DO NOT BREAK EXISTING PROJECT

Preserve:

* existing APIs
* existing database behavior
* existing features
* existing UI
* existing authentication
* existing workflows
* existing tests

Unless a change is strictly required for this feature.

No arbitrary refactoring.

No unrelated redesign.

---

# 45. ACCEPTANCE CRITERIA

The implementation is NOT complete unless all of the following work:

### A. Existing capabilities

The monitor reads the current project capability/model source correctly.

### B. Empty capability file

The monitor performs a baseline discovery and stores it.

### C. Semantic comparison

A newly discovered capability is correctly classified as:

* existing
* new
* partial
* unknown

### D. Dynamic queries

The system can create new search queries using an LLM provider.

### E. Free AI discovery

The system discovers and validates new AI websites/platforms offering free access.

### F. URL deduplication

The same URL never generates repeated notifications.

### G. Semantic deduplication

Different URLs representing the same announcement are recognized as duplicates.

### H. Historical changes

Meaningful updates produce change events.

### I. Telegram

Important new events are delivered once to the configured Chat ID.

### J. Independent worker

Monitoring runs independently from the main application.

### K. Persistence

Restarting the application does not reset knowledge.

### L. Security

Credentials are protected and external webpage prompt injection is contained.

### M. Recovery

Temporary external failures do not permanently break monitoring.

---

# 46. FINAL OPERATING MODEL

The final system should continuously behave like:

```text
              ┌────────────────────────────┐
              │ Existing Project Knowledge │
              └──────────────┬─────────────┘
                             ↓
                    Project Capability Map
                             ↓
 ┌──────────────────────────────────────────────────────┐
 │                 AI INTELLIGENCE MONITOR              │
 │                                                      │
 │  Official Sources                                    │
 │  Search Engines                                      │
 │  GitHub                                              │
 │  Hugging Face                                        │
 │  Cloud Providers                                     │
 │  AI News / Research                                  │
 │  Free AI Discovery                                   │
 │                                                      │
 │              ↓ Dynamic Discovery ↓                   │
 │                                                      │
 │   Normalize → Deduplicate → Validate → Extract       │
 │                         ↓                            │
 │                 Semantic Comparison                 │
 │                         ↓                            │
 │              New / Existing / Changed               │
 │                         ↓                            │
 │                  Knowledge Database                 │
 │                         ↓                            │
 │               Priority + Confidence                 │
 │                         ↓                            │
 │                     Telegram                        │
 └──────────────────────────────────────────────────────┘
```

The system's ultimate purpose is:

> **Continuously discover what is happening in the AI ecosystem, understand what the current project already has, identify what is genuinely new or useful to the project, preserve historical evidence, and notify the user with high-signal information instead of repetitive noise.**

---

# 47. EXECUTION RULE

Do not stop after creating files or scaffolding.

Actually implement the system.

After implementation:

1. Run tests.
2. Run lint/type checks where applicable.
3. Run database migrations.
4. Run the monitoring worker.
5. Perform a controlled discovery test.
6. Test duplicate URL handling.
7. Test semantic comparison against the project's current feature/model file.
8. Test Telegram notification flow using configured credentials without exposing them.
9. Test worker restart/recovery.
10. Fix all objectively reproducible issues.
11. Document exactly what was implemented.
12. Report remaining limitations honestly.

Do not claim a feature works unless it was actually verified.

Do not modify unrelated project components.

Do not finish with a conceptual design only.

BUILD THE WORKING SYSTEM.
