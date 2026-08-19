from enum import Enum


class DiscoveryType(str, Enum):
    MODEL = "model"
    CAPABILITY = "capability"
    FREE_SERVICE = "free_service"
    API = "api"
    CLOUD_SERVICE = "cloud_service"
    DATASET = "dataset"
    PLATFORM = "platform"
    TOOL = "tool"


class FreeStatus(str, Enum):
    FREE = "free"                      # Completely free without strict credit limits
    FREE_TIER = "free_tier"            # Free tier with quotas (daily/monthly credits)
    TRIAL = "trial"                    # Temporary trial credits/period
    OPEN_SOURCE = "open_source"        # Open source software / weights
    OPEN_WEIGHTS = "open_weights"      # Model weights available for self-hosting
    PAID_ONLY = "paid_only"            # Paid only / subscription required
    UNKNOWN = "unknown"                # Status unverified


class ComparisonStatus(str, Enum):
    PROJECT_ALREADY_HAS = "PROJECT_ALREADY_HAS"
    PROJECT_PARTIAL_SUPPORT = "PROJECT_PARTIAL_SUPPORT"
    PROJECT_DOES_NOT_HAVE = "PROJECT_DOES_NOT_HAVE"
    PROJECT_UNKNOWN = "PROJECT_UNKNOWN"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class SourceReliability(str, Enum):
    OFFICIAL_SITE = "official_site"
    OFFICIAL_DOCS = "official_docs"
    OFFICIAL_RELEASE_NOTES = "official_release_notes"
    OFFICIAL_MODEL_CARD = "official_model_card"
    OFFICIAL_GITHUB = "official_github"
    OFFICIAL_RESEARCH_PAPER = "official_research_paper"
    HUGGING_FACE = "hugging_face"
    CLOUD_DOCS = "cloud_docs"
    TRUSTED_NEWS = "trusted_news"
    SEARCH_RESULT = "search_result"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    NEW_MODEL = "NEW_MODEL"
    NEW_CAPABILITY = "NEW_CAPABILITY"
    NEW_FREE_AI_SERVICE = "NEW_FREE_AI_SERVICE"
    PRICE_CHANGE = "PRICE_CHANGE"
    MODEL_UPDATE = "MODEL_UPDATE"
    CLOUD_AI_UPDATE = "CLOUD_AI_UPDATE"
    NEW_DATASET = "NEW_DATASET"
    DEPRECATION = "DEPRECATION"
    NEW_AI_PLATFORM = "NEW_AI_PLATFORM"
    SYSTEM_SYNC = "SYSTEM_SYNC"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"
    SUPPRESSED_DUPLICATE = "suppressed_duplicate"


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
