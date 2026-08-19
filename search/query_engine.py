import logging
from typing import List, Optional, Tuple
from data_mining.db.repository import Repository
from data_mining.llm.factory import get_llm_provider
from data_mining.models.schemas import SearchQueryItem

logger = logging.getLogger("data_mining.query_engine")

SEED_QUERIES = [
    # Free AI Discovery
    ("free AI inference API unlimited 2026", "free_ai_services"),
    ("free LLM API keys open source models", "free_ai_services"),
    ("free AI model hosting platform endpoints", "free_ai_services"),
    ("free vision model API playground", "free_ai_services"),
    ("free reasoning model API deepseek r1", "free_ai_services"),
    # New Model Releases
    ("new AI model release official announcement", "new_models"),
    ("OpenAI new model release blog", "new_models"),
    ("Anthropic Claude new model release", "new_models"),
    ("Google DeepMind new Gemini model", "new_models"),
    ("DeepSeek new model announcement", "new_models"),
    ("Mistral AI new release docs", "new_models"),
    ("Meta Llama new open weights release", "open_weights"),
    ("Qwen new model weights HuggingFace", "open_weights"),
    # Cloud AI & APIs
    ("Azure AI new model catalog update", "cloud_ai"),
    ("AWS Bedrock new foundation models", "cloud_ai"),
    ("Groq new supported models speed", "cloud_ai"),
]


class DynamicQueryEngine:
    """
    Manages search query generation, query performance evaluation,
    and query lineage tracking.
    """

    def __init__(self, repo: Optional[Repository] = None):
        self.repo = repo or Repository()
        self.llm = get_llm_provider()
        self._seed_initial_queries()

    def _seed_initial_queries(self) -> None:
        for q, cat in SEED_QUERIES:
            self.repo.upsert_search_query(query=q, category=cat, discovered_by="seed")

    def get_queries_to_run(self, limit: int = 5) -> List[Tuple[int, str, str]]:
        """
        Returns list of (query_id, query_text, category) prioritizing high usefulness
        and less recently used queries.
        """
        items = self.repo.get_top_search_queries(limit=limit)
        return [(item.id or 0, item.query, item.category) for item in items]

    def generate_new_queries(
        self,
        category: str = "new_models",
        recent_discoveries: Optional[List[str]] = None,
        count: int = 3,
    ) -> List[int]:
        """
        Dynamically generates new queries using the LLM provider,
        stores them in DB, and returns their query IDs.
        """
        existing = [q.query for q in self.repo.get_top_search_queries(limit=30)]
        new_query_texts = self.llm.generate_search_queries(
            category=category,
            existing_queries=existing,
            recent_discoveries=recent_discoveries or ["LLM", "Reasoning", "DeepSeek", "Claude"],
            count=count,
        )

        created_ids: List[int] = []
        for q_text in new_query_texts:
            qid = self.repo.upsert_search_query(
                query=q_text,
                category=category,
                discovered_by="llm_generator",
            )
            created_ids.append(qid)
            logger.info(f"Generated new dynamic query [{category}]: '{q_text}' (ID: {qid})")

        return created_ids

    def record_query_performance(
        self,
        query_id: int,
        results_count: int,
        new_domains: int,
        new_models: int,
        new_services: int,
        duplicates_count: int,
    ) -> None:
        """
        Updates the query's usefulness score based on verified yield.
        """
        self.repo.record_query_outcome(
            query_id=query_id,
            results_count=results_count,
            new_domains=new_domains,
            new_models=new_models,
            new_services=new_services,
            duplicates_count=duplicates_count,
        )
