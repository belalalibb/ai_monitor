import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_mining.config import settings
from data_mining.scheduler.task_runner import PipelineTaskRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("data_mining.worker")


class MonitorWorkerDaemon:
    """
    Dedicated background worker process. Runs independently from any
    web or API server processes. Handles graceful shutdowns and periodic cycles.
    """

    def __init__(self, runner: Optional[PipelineTaskRunner] = None):
        self.runner = runner or PipelineTaskRunner()
        self.running = False
        self._setup_signals()

    def _setup_signals(self) -> None:
        try:
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        except Exception:
            pass  # Non-main thread or Windows platform quirks

    def _handle_shutdown(self, signum, frame) -> None:
        logger.info(f"Received termination signal ({signum}). Initiating graceful worker shutdown...")
        self.running = False

    def start(self, interval_seconds: Optional[int] = None, single_run: bool = False) -> None:
        interval = interval_seconds or settings.SEARCH_SCAN_INTERVAL
        pid = os.getpid()
        logger.info(f"Starting AI Intelligence Monitor Worker Daemon (PID: {pid}, Interval: {interval}s)")
        self.running = True

        cycle_count = 0
        while self.running:
            cycle_count += 1
            logger.info(f"--- Discovery Cycle #{cycle_count} Started ---")
            try:
                stats = self.runner.run_full_discovery_cycle()
                logger.info(
                    f"--- Cycle #{cycle_count} Completed: {stats.status.value} | "
                    f"URLs Discovered: {stats.urls_discovered} | Models: {stats.models_discovered} | "
                    f"Free Services: {stats.free_services_discovered} | Notifications Sent: {stats.notifications_sent} ---"
                )
            except Exception as e:
                logger.error(f"Error in discovery cycle #{cycle_count}: {e}", exc_info=True)

            if single_run or not self.running:
                break

            logger.info(f"Worker sleeping for {interval} seconds until next cycle...")
            # Sleep in short slices to respond quickly to shutdown signals
            for _ in range(int(interval)):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("AI Intelligence Monitor Worker Daemon terminated cleanly.")


def main():
    daemon = MonitorWorkerDaemon()
    daemon.start()


if __name__ == "__main__":
    main()
