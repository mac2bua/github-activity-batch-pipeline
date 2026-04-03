"""
Unit tests for Airflow DAGs

Tests cover DAG structure, task configuration, dependencies, and
basic functionality validation.

Run: pytest tests/test_airflow_dag.py -v
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

# Add dags directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))


class TestDAGStructure:
    """Test DAG structure and configuration"""

    def test_dag_imports(self) -> None:
        """Test that DAG module imports without errors"""
        try:
            import github_activity_pipeline
            assert github_activity_pipeline is not None
        except ImportError as e:
            pytest.fail(f"Failed to import DAG: {e}")

    def test_dag_exists(self) -> None:
        """Test that DAG object exists"""
        from github_activity_pipeline import dag
        assert dag is not None
        assert hasattr(dag, 'dag_id')

    def test_dag_id(self) -> None:
        """Test DAG ID is correct"""
        from github_activity_pipeline import dag
        assert dag.dag_id == 'github_activity_batch_pipeline'

    def test_schedule_interval(self) -> None:
        """Test DAG has daily schedule"""
        from github_activity_pipeline import dag
        assert dag.schedule_interval == '@daily'

    def test_catchup_enabled(self) -> None:
        """Test catchup is enabled for backfill"""
        from github_activity_pipeline import dag
        assert dag.catchup is True

    def test_max_active_runs(self) -> None:
        """Test only one run at a time"""
        from github_activity_pipeline import dag
        assert dag.max_active_runs == 1

    def test_dag_tags(self) -> None:
        """Test DAG has appropriate tags"""
        from github_activity_pipeline import dag
        assert dag.tags is not None
        assert 'github' in dag.tags
        assert 'batch' in dag.tags

    def test_dag_description(self) -> None:
        """Test DAG has a description"""
        from github_activity_pipeline import dag
        assert dag.description is not None
        assert len(dag.description) > 0


class TestTasks:
    """Test individual tasks"""

    def test_minimum_tasks(self) -> None:
        """Test DAG has at least 3 tasks"""
        from github_activity_pipeline import dag
        task_count = len(dag.tasks)
        assert task_count >= 3, f"Expected >= 3 tasks, got {task_count}"

    def test_download_task_exists(self) -> None:
        """Test download task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'download_github_archive' in task_ids

    def test_upload_task_exists(self) -> None:
        """Test upload task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'upload_to_gcs' in task_ids

    def test_load_task_exists(self) -> None:
        """Test load task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'load_to_bigquery' in task_ids

    def test_cleanup_task_exists(self) -> None:
        """Test cleanup task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'cleanup_temp_files' in task_ids

    def test_validate_task_exists(self) -> None:
        """Test validation task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'validate_data_quality' in task_ids

    def test_task_dependencies(self) -> None:
        """Test task dependencies are defined correctly"""
        from github_activity_pipeline import dag

        # Build dependency map
        dependencies: dict[str, list[str]] = {}
        for task in dag.tasks:
            dependencies[task.task_id] = [
                up.task_id for up in task.upstream_list
            ]

        # Check download has no upstream (first task)
        assert len(dependencies.get('download_github_archive', [])) == 0

        # Check upload depends on download
        assert 'download_github_archive' in dependencies.get('upload_to_gcs', [])

        # Check validate depends on upload
        assert 'upload_to_gcs' in dependencies.get('validate_data_quality', [])

        # Check load depends on validate
        assert 'validate_data_quality' in dependencies.get('load_to_bigquery', [])

        # Check cleanup depends on load (last task)
        assert 'load_to_bigquery' in dependencies.get('cleanup_temp_files', [])

    def test_task_owners(self) -> None:
        """Test tasks have owner configuration"""
        from github_activity_pipeline import dag
        for task in dag.tasks:
            assert hasattr(task, 'owner')
            assert task.owner is not None

    def test_task_retries_configured(self) -> None:
        """Test tasks have retry configuration"""
        from github_activity_pipeline import dag
        for task in dag.tasks:
            assert hasattr(task, 'retries')
            # All tasks should have retries configured (either default or explicit)
            assert task.retries is not None


class TestDownloadTask:
    """Test download task functionality"""

    def test_download_function_exists(self) -> None:
        """Test download function is defined"""
        from github_activity_pipeline import download_github_archive
        assert callable(download_github_archive)

    def test_upload_function_exists(self) -> None:
        """Test upload function is defined"""
        from github_activity_pipeline import upload_to_gcs
        assert callable(upload_to_gcs)

    def test_validate_function_exists(self) -> None:
        """Test validation function is defined"""
        from github_activity_pipeline import validate_data_quality
        assert callable(validate_data_quality)

    def test_download_function_docstring(self) -> None:
        """Test download function has docstring"""
        from github_activity_pipeline import download_github_archive
        assert download_github_archive.__doc__ is not None
        assert len(download_github_archive.__doc__) > 0


class TestSecondDAG:
    """Test the github_archive_dag.py DAG"""

    def test_second_dag_imports(self) -> None:
        """Test second DAG imports without errors"""
        try:
            import github_archive_dag
            assert github_archive_dag is not None
        except ImportError as e:
            pytest.fail(f"Failed to import github_archive_dag: {e}")

    def test_second_dag_exists(self) -> None:
        """Test second DAG object exists"""
        from github_archive_dag import dag
        assert dag is not None
        assert dag.dag_id == 'github_archive_batch_pipeline'

    def test_second_dag_tasks(self) -> None:
        """Test second DAG has required tasks"""
        from github_archive_dag import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'download_github_archive' in task_ids
        assert 'upload_to_gcs' in task_ids
        assert 'load_to_bigquery' in task_ids

    def test_second_dag_dependencies(self) -> None:
        """Test second DAG task dependencies"""
        from github_archive_dag import dag

        dependencies: dict[str, list[str]] = {}
        for task in dag.tasks:
            dependencies[task.task_id] = [
                up.task_id for up in task.upstream_list
            ]

        assert 'download_github_archive' in dependencies.get('upload_to_gcs', [])
        assert 'upload_to_gcs' in dependencies.get('load_to_bigquery', [])


class TestConfiguration:
    """Test configuration and constants"""

    def test_gcs_bucket_configured(self) -> None:
        """Test GCS bucket is configured"""
        from github_activity_pipeline import GCS_BUCKET
        assert GCS_BUCKET is not None
        assert len(GCS_BUCKET) > 0

    def test_bq_dataset_configured(self) -> None:
        """Test BigQuery dataset is configured"""
        from github_activity_pipeline import BQ_DATASET
        assert BQ_DATASET == 'github_activity'

    def test_bq_table_configured(self) -> None:
        """Test BigQuery table is configured"""
        from github_activity_pipeline import BQ_TABLE
        assert BQ_TABLE == 'github_events'

    def test_archive_url_configured(self) -> None:
        """Test GHE Archive URL is configured"""
        from github_activity_pipeline import GHE_ARCHIVE_URL
        assert GHE_ARCHIVE_URL == 'https://gharchive.org'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
