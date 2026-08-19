import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent


class Settings(BaseSettings):
    # Provider & API Keys
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    COMPARISON_PROVIDER: str = Field(default="groq", description="Provider for semantic comparison")
    QUERY_GENERATION_PROVIDER: str = Field(default="groq", description="Provider for search query generation")

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Telegram bot token")
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, description="Telegram chat ID for notifications")

    # Monitoring Control
    MONITOR_ENABLED: bool = Field(default=True, description="Master enable switch for monitoring")
    NOTIFY_LOW_PRIORITY: bool = Field(default=False, description="Whether to send notifications for low priority events")

    # Scan Intervals (in seconds)
    COMPANY_SCAN_INTERVAL: int = Field(default=3600, description="Interval for official provider scans (seconds)")
    MODEL_SCAN_INTERVAL: int = Field(default=1800, description="Interval for model updates scan (seconds)")
    FREE_AI_SCAN_INTERVAL: int = Field(default=3600, description="Interval for free AI platform discovery (seconds)")
    SEARCH_SCAN_INTERVAL: int = Field(default=1800, description="Interval for general dynamic search scan (seconds)")
    PROJECT_SYNC_INTERVAL: int = Field(default=600, description="Interval for syncing codebase capabilities mirror (seconds)")

    # Performance & Concurrency Limits
    MAX_RESULTS_PER_QUERY: int = Field(default=5, description="Max search results to process per query")
    REQUEST_TIMEOUT: int = Field(default=15, description="HTTP request timeout in seconds")
    MAX_CONCURRENT_REQUESTS: int = Field(default=5, description="Max concurrent web requests")
    RATE_LIMIT_DOMAIN_DELAY: float = Field(default=1.0, description="Delay between requests to the same domain (seconds)")

    # Storage & Persistence
    DB_PATH: Path = Field(default=BASE_DIR / "ai_monitor.db", description="Path to SQLite database file")
    PROJECT_CAPABILITIES_PATH: Path = Field(
        default=BASE_DIR / "project_capabilities.json",
        description="Path to project capabilities map JSON file"
    )

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
