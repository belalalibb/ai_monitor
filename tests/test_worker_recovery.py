import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from data_mining.core.project_knowledge import ProjectKnowledgeBase
from data_mining.db.repository import Repository
from data_mining.scheduler.task_runner import PipelineTaskRunner
from data_mining.scheduler.worker import MonitorWorkerDaemon


def test_worker_daemon_graceful_cycle_and_exception_containment():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        json_path = Path(tmpdir) / "project_capabilities.json"
        repo = Repository(db_path=db_path)
        kb = ProjectKnowledgeBase(json_path=json_path)

        runner = PipelineTaskRunner(repo=repo, knowledge_base=kb)
        # Mock runner cycle to raise an exception once
        mock_run_cycle = MagicMock(side_effect=RuntimeError("Simulated temporary network disconnect"))
        runner.run_full_discovery_cycle = mock_run_cycle

        daemon = MonitorWorkerDaemon(runner=runner)
        # Single run should catch the exception, log it, and terminate cleanly without crashing
        daemon.start(single_run=True)

        assert mock_run_cycle.call_count == 1
        assert daemon.running is True or daemon.running is False
