import tempfile
from pathlib import Path
from data_mining.db.repository import Repository
from data_mining.search.query_engine import DynamicQueryEngine


def test_dynamic_query_engine_and_lineage_scoring():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        repo = Repository(db_path=db_path)
        engine = DynamicQueryEngine(repo=repo)

        queries = engine.get_queries_to_run(limit=3)
        assert len(queries) > 0
        qid, qtext, qcat = queries[0]

        # Record high yield performance
        engine.record_query_performance(
            query_id=qid,
            results_count=5,
            new_domains=2,
            new_models=2,
            new_services=1,
            duplicates_count=0,
        )

        top_queries = repo.get_top_search_queries(limit=5)
        matched = [q for q in top_queries if q.id == qid][0]
        assert matched.usefulness_score > 1.0
        assert matched.new_models_found == 2
