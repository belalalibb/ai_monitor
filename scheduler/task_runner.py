import logging
import uuid
from typing import Optional
from data_mining.comparison.change_detector import ChangeDetector
from data_mining.comparison.semantic_comparator import SemanticComparator
from data_mining.core.audit import AuditLogger
from data_mining.core.normalizer import canonicalize_url, compute_content_hash, compute_url_hash, extract_domain
from data_mining.core.project_knowledge import ProjectKnowledgeBase
from data_mining.db.repository import Repository
from data_mining.extractors.free_ai_extractor import FreeAIExtractor
from data_mining.extractors.html_extractor import HtmlContentExtractor
from data_mining.extractors.model_extractor import ModelExtractor
from data_mining.extractors.relevance_filter import RelevanceFilter
from data_mining.models.enums import RunStatus
from data_mining.models.schemas import MonitorRunStats, utc_now_iso
from data_mining.notifications.manager import NotificationManager
from data_mining.search.fetcher import HttpFetcher
from data_mining.search.query_engine import DynamicQueryEngine
from data_mining.search.web_search import WebSearchProvider
from data_mining.sync.project_sync import ProjectIntelligenceSync

logger = logging.getLogger("data_mining.task_runner")


class PipelineTaskRunner:
    """
    Coordinates and executes discovery pipelines:
    - Official Provider Scans
    - Dynamic Search Discovery
    - Free AI Platform Discovery
    - Project Intelligence Synchronization
    """

    def __init__(
        self,
        repo: Optional[Repository] = None,
        knowledge_base: Optional[ProjectKnowledgeBase] = None,
    ):
        self.repo = repo or Repository()
        self.kb = knowledge_base or ProjectKnowledgeBase()
        self.query_engine = DynamicQueryEngine(self.repo)
        self.search_provider = WebSearchProvider()
        self.fetcher = HttpFetcher()
        self.html_extractor = HtmlContentExtractor()
        self.relevance_filter = RelevanceFilter()
        self.model_extractor = ModelExtractor()
        self.free_ai_extractor = FreeAIExtractor()
        self.comparator = SemanticComparator(self.kb)
        self.change_detector = ChangeDetector()
        self.notifier = NotificationManager(repo=self.repo)
        self.audit = AuditLogger(self.repo)
        self.sync_engine = ProjectIntelligenceSync(repo=self.repo)

    def run_full_discovery_cycle(self, max_queries: int = 3) -> MonitorRunStats:
        """
        Executes a complete monitoring run cycle:
        1. Codebase Sync
        2. Official Providers Baseline Scan
        3. Dynamic Search Discovery
        4. Free AI Discovery
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        stats = MonitorRunStats(run_id=run_id, started_at=utc_now_iso())
        self.repo.start_monitor_run(run_id)

        try:
            # 1. Sync project intelligence
            self.sync_engine.sync_mirror()

            # 2. Execute dynamic search queries
            queries_to_run = self.query_engine.get_queries_to_run(limit=max_queries)
            for qid, q_text, q_cat in queries_to_run:
                stats.queries_executed += 1
                new_doms, new_mods, new_servs, dups = self._process_search_query(qid, q_text, q_cat, stats)
                self.query_engine.record_query_performance(
                    query_id=qid,
                    results_count=new_doms + new_mods + new_servs + dups,
                    new_domains=new_doms,
                    new_models=new_mods,
                    new_services=new_servs,
                    duplicates_count=dups,
                )

            # 3. Generate dynamic next-generation queries for subsequent cycles
            self.query_engine.generate_new_queries(category="new_models", count=2)
            self.query_engine.generate_new_queries(category="free_ai_services", count=2)

            stats.status = RunStatus.COMPLETED
        except Exception as e:
            logger.error(f"Error during discovery cycle {run_id}: {e}")
            stats.errors.append(str(e))
            stats.status = RunStatus.FAILED
        finally:
            stats.finished_at = utc_now_iso()
            self.repo.finish_monitor_run(stats)

        return stats

    def _process_search_query(
        self,
        query_id: int,
        query_text: str,
        category: str,
        stats: MonitorRunStats,
    ) -> tuple[int, int, int, int]:
        """
        Executes a single search query and processes discovered URLs through the pipeline.
        Returns (new_domains, new_models, new_services, duplicates).
        """
        results = self.search_provider.search(query=query_text, max_results=4, query_id=query_id)
        new_domains = 0
        new_models = 0
        new_services = 0
        duplicates = 0

        for res in results:
            stats.urls_discovered += 1
            canonical_url = canonicalize_url(res.url)
            url_hash = compute_url_hash(canonical_url)
            domain = extract_domain(canonical_url)

            is_domain_new = not self.repo.is_domain_known(domain)
            if is_domain_new:
                new_domains += 1

            # Check URL Deduplication
            if self.repo.is_url_known(url_hash):
                stats.urls_duplicate += 1
                duplicates += 1
                continue

            # Fetch page content
            fetch_res = self.fetcher.fetch_url(canonical_url)
            if not fetch_res:
                continue

            html_text, status_code = fetch_res
            extracted = self.html_extractor.extract(html_text, canonical_url)
            content_hash = compute_content_hash(extracted["text"])

            # Layered relevance check
            is_relevant, rel_score, reason = self.relevance_filter.evaluate(
                domain, extracted["title"], extracted["text"]
            )
            if not is_relevant:
                continue

            # Save URL
            url_id, is_url_new = self.repo.upsert_url(
                raw_url=res.url,
                canonical_url=canonical_url,
                url_hash=url_hash,
                domain=domain,
                content_hash=content_hash,
                discovered_by_query_id=query_id,
            )
            if is_url_new:
                stats.urls_new += 1

            # Pipeline Branch: Free AI Discovery vs Model Discovery
            if category == "free_ai_services":
                service = self.free_ai_extractor.extract_and_validate(
                    raw_text=extracted["text"],
                    source_url=canonical_url,
                    query_id=query_id,
                )
                if service:
                    s_id, is_new_service = self.repo.upsert_free_service(service)
                    if is_new_service:
                        stats.free_services_discovered += 1
                        new_services += 1

                    # Change detection & Event deduplication
                    change_event = self.change_detector.detect_free_service_changes(service, is_new=is_new_service)
                    if change_event:
                        event_group_id, is_new_event = self.repo.get_or_create_event_group(
                            canonical_event_key=change_event.canonical_event_key,
                            event_type=change_event.event_type,
                            provider=change_event.provider,
                            entity_name=change_event.entity_name,
                            title=change_event.title,
                        )
                        self.repo.save_change_event(change_event, event_group_id=event_group_id)

                        if is_new_event:
                            self.notifier.dispatch_free_service_event(
                                event=change_event,
                                service=service,
                                event_group_id=event_group_id,
                            )
                            stats.notifications_sent += 1

            else:
                # Model Extraction & Semantic Comparison
                model = self.model_extractor.extract_model(
                    raw_text=extracted["text"],
                    source_url=canonical_url,
                    query_id=query_id,
                )
                if model:
                    m_id, is_new_model = self.repo.upsert_model(model)
                    if is_new_model:
                        stats.models_discovered += 1
                        new_models += 1

                    # Semantic comparison against project knowledge
                    comp_res = self.comparator.compare_model(model)
                    self.repo.save_comparison(comp_res)

                    if comp_res.new_capabilities:
                        stats.capabilities_new += len(comp_res.new_capabilities)

                    # Change detection
                    change_event = self.change_detector.detect_model_changes(
                        new_model=model,
                        existing_model=None,
                        is_new=is_new_model,
                    )
                    if change_event:
                        event_group_id, is_new_event = self.repo.get_or_create_event_group(
                            canonical_event_key=change_event.canonical_event_key,
                            event_type=change_event.event_type,
                            provider=change_event.provider,
                            entity_name=change_event.entity_name,
                            title=change_event.title,
                        )
                        self.repo.save_change_event(change_event, event_group_id=event_group_id)

                        if is_new_event:
                            self.notifier.dispatch_model_event(
                                event=change_event,
                                model=model,
                                comparison=comp_res,
                                event_group_id=event_group_id,
                            )
                            stats.notifications_sent += 1

        return new_domains, new_models, new_services, duplicates
