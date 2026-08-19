import argparse
import json
import sys
from pathlib import Path
from pprint import pprint

# Ensure project root is in sys.path when running from inside data_mining directory
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from data_mining.config import settings
from data_mining.core.project_knowledge import ProjectKnowledgeBase
from data_mining.core.source_registry import get_default_providers
from data_mining.db.repository import Repository
from data_mining.notifications.telegram import TelegramNotificationProvider
from data_mining.scheduler.task_runner import PipelineTaskRunner
from data_mining.scheduler.worker import MonitorWorkerDaemon
from data_mining.sync.project_sync import ProjectIntelligenceSync


def main():
    parser = argparse.ArgumentParser(
        prog="data_mining",
        description="AI Intelligence Monitor & Data Mining CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Run a manual discovery cycle")
    scan_parser.add_argument("--limit", type=int, default=3, help="Max queries to run")

    # Command: worker
    worker_parser = subparsers.add_parser("worker", help="Start the standalone monitor daemon")
    worker_parser.add_argument("--interval", type=int, default=None, help="Scan interval in seconds")

    # Command: sync
    subparsers.add_parser("sync", help="Synchronize project intelligence from codebase")

    # Command: stats
    subparsers.add_parser("stats", help="Show database metrics and entity counts")

    # Command: queries
    subparsers.add_parser("queries", help="List active search queries and performance scores")

    # Command: providers
    subparsers.add_parser("providers", help="List monitored AI providers")

    # Command: free-ai
    subparsers.add_parser("free-ai", help="List discovered free AI services")

    # Command: test-notify
    subparsers.add_parser("test-notify", help="Send a test notification to Telegram")

    args = parser.parse_args()

    if not args.command or args.command == "stats":
        repo = Repository()
        stats = repo.get_stats_summary()
        print("\n==============================")
        print("  AI INTELLIGENCE MONITOR DB  ")
        print("==============================")
        for k, v in stats.items():
            print(f"  {k:<20}: {v}")
        print("==============================\n")

    elif args.command == "scan":
        print(f"Executing manual discovery cycle (limit={args.limit} queries)...")
        runner = PipelineTaskRunner()
        run_stats = runner.run_full_discovery_cycle(max_queries=args.limit)
        print(f"\nDiscovery Cycle Completed: {run_stats.status.value}")
        print(f"  URLs Discovered : {run_stats.urls_discovered}")
        print(f"  New URLs Saved  : {run_stats.urls_new}")
        print(f"  Models Found    : {run_stats.models_discovered}")
        print(f"  Free Services   : {run_stats.free_services_discovered}")
        print(f"  Notifications   : {run_stats.notifications_sent}")
        if run_stats.errors:
            print(f"  Errors: {run_stats.errors}")

    elif args.command == "worker":
        daemon = MonitorWorkerDaemon()
        daemon.start(interval_seconds=args.interval)

    elif args.command == "sync":
        sync_engine = ProjectIntelligenceSync()
        cap_map = sync_engine.sync_mirror()
        print("\nProject Intelligence Mirror Synchronized:")
        print(f"  Providers    : {cap_map.providers}")
        print(f"  Models       : {cap_map.models}")
        print(f"  Capabilities : {cap_map.capabilities}")
        print(f"  Features     : {cap_map.features}")
        print(f"  Integrations : {cap_map.integrations}")
        print(f"  Saved to     : {settings.PROJECT_CAPABILITIES_PATH}\n")

    elif args.command == "queries":
        from data_mining.search.query_engine import DynamicQueryEngine
        repo = Repository()
        engine = DynamicQueryEngine(repo)
        queries = repo.get_top_search_queries(limit=25)
        print(f"\n{'ID':<4} {'Score':<6} {'Category':<18} {'Query'}")
        print("-" * 75)
        for q in queries:
            print(f"{q.id:<4} {q.usefulness_score:<6.2f} {q.category:<18} {q.query}")
        print("-" * 75 + "\n")

    elif args.command == "providers":
        from data_mining.core.source_registry import init_default_providers
        repo = Repository()
        init_default_providers(repo)
        providers = repo.get_providers(monitored_only=False)
        print("\nMonitored AI Providers Registry:")
        for p in providers:
            print(f"  • {p.name:<15} ({p.domain:<22}) - {', '.join(p.categories)}")
        print()

    elif args.command == "free-ai":
        repo = Repository()
        services = repo.get_all_free_services()
        print(f"\nDiscovered Free AI Platforms ({len(services)}):")
        for s in services:
            print(f"  • {s['service_name']} ({s['domain']}) | Status: {s['free_status']} | Limits: {s['limits']}")
        print()

    elif args.command == "test-notify":
        telegram = TelegramNotificationProvider()
        status = telegram.send_message(
            title="🔔 AI Monitor Test Notification",
            body="This is a verified test message from the AI Intelligence Monitor subsystem.",
        )
        print(f"Test notification status: {status.value}")


if __name__ == "__main__":
    main()
