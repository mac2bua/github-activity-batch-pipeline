"""
Unit tests for Airflow DAG
Run: pytest tests/test_airflow_dag.py
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add dags to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))


class TestDAGStructure:
    """Test DAG structure and configuration"""
    
    def test_dag_imports(self):
        """Test that DAG module imports without errors"""
        try:
            import github_activity_pipeline
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import DAG: {e}")
    
    def test_dag_exists(self):
        """Test that DAG object exists"""
        from github_activity_pipeline import dag
        assert dag is not None
        assert hasattr(dag, 'dag_id')
    
    def test_dag_id(self):
        """Test DAG ID is correct"""
        from github_activity_pipeline import dag
        assert dag.dag_id == 'github_activity_batch_pipeline'
    
    def test_schedule_interval(self):
        """Test DAG has daily schedule"""
        from github_activity_pipeline import dag
        assert dag.schedule_interval == '@daily'
    
    def test_catchup_enabled(self):
        """Test catchup is enabled for backfill"""
        from github_activity_pipeline import dag
        assert dag.catchup == True
    
    def test_max_active_runs(self):
        """Test only one run at a time"""
        from github_activity_pipeline import dag
        assert dag.max_active_runs == 1


class TestTasks:
    """Test individual tasks"""
    
    def test_minimum_tasks(self):
        """Test DAG has at least 3 tasks"""
        from github_activity_pipeline import dag
        task_count = len(dag.tasks)
        assert task_count >= 3, f"Expected >= 3 tasks, got {task_count}"
    
    def test_download_task_exists(self):
        """Test download task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'download_github_archive' in task_ids
    
    def test_upload_task_exists(self):
        """Test upload task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'upload_to_gcs' in task_ids
    
    def test_load_task_exists(self):
        """Test load task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'load_to_bigquery' in task_ids
    
    def test_cleanup_task_exists(self):
        """Test cleanup task exists"""
        from github_activity_pipeline import dag
        task_ids = [task.task_id for task in dag.tasks]
        assert 'cleanup_temp_files' in task_ids
    
    def test_task_dependencies(self):
        """Test task dependencies are defined"""
        from github_activity_pipeline import dag
        
        # Build dependency map
        dependencies = {}
        for task in dag.tasks:
            dependencies[task.task_id] = [up.task_id for up in task.upstream_list]
        
        # Check download has no upstream
        assert len(dependencies.get('download_github_archive', [])) == 0
        
        # Check upload depends on download
        assert 'download_github_archive' in dependencies.get('upload_to_gcs', [])
        
        # Check load depends on upload
        assert 'upload_to_gcs' in dependencies.get('load_to_bigquery', [])
        
        # Check cleanup depends on load
        assert 'load_to_bigquery' in dependencies.get('cleanup_temp_files', [])


class TestDownloadTask:
    """Test download task functionality"""
    
    def test_download_function_exists(self):
        """Test download function is defined"""
        from github_activity_pipeline import download_github_archive
        assert callable(download_github_archive)
    
    def test_upload_function_exists(self):
        """Test upload function is defined"""
        from github_activity_pipeline import upload_to_gcs
        assert callable(upload_to_gcs)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
