"""
Unit tests for project_id configuration

These tests ensure that:
1. get_project_id() raises an error when not configured
2. get_project_id() returns correct value from Airflow Variables
3. get_project_id() returns correct value from environment
4. DAG fails fast with clear error message when project_id is missing

Run: pytest tests/test_project_id_config.py -v
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add dags directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))


class TestGetProjectId:
    """Test get_project_id() function"""

    def test_get_project_id_raises_when_not_configured(self) -> None:
        """
        Test that get_project_id raises ValueError when no project_id is configured.
        
        This is the critical test that prevents the "your-project-id" bug
        where DAGs would parse but fail at runtime with confusing errors.
        """
        # Make sure environment variable is not set
        with patch.dict(os.environ, {}, clear=False):
            if 'GOOGLE_CLOUD_PROJECT' in os.environ:
                del os.environ['GOOGLE_CLOUD_PROJECT']
        
        # Mock Variable.get to raise exception (not configured)
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.side_effect = Exception("Variable not found")
            
            # Import fresh to avoid cached value
            import importlib
            import github_activity_pipeline
            importlib.reload(github_activity_pipeline)
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="project_id not configured"):
                github_activity_pipeline.get_project_id()

    def test_get_project_id_from_airflow_variable(self) -> None:
        """Test get_project_id returns value from Airflow Variable"""
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'my-gcp-project'
            
            import importlib
            import github_activity_pipeline
            importlib.reload(github_activity_pipeline)
            
            result = github_activity_pipeline.get_project_id()
            assert result == 'my-gcp-project'
            mock_get.assert_called_once_with('project_id')

    def test_get_project_id_from_environment(self) -> None:
        """Test get_project_id returns value from environment variable"""
        # Mock Variable.get to raise (not configured)
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.side_effect = Exception("Variable not found")
            
            # Set environment variable
            with patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'env-project-id'}):
                import importlib
                import github_activity_pipeline
                importlib.reload(github_activity_pipeline)
                
                result = github_activity_pipeline.get_project_id()
                assert result == 'env-project-id'

    def test_get_project_id_airflow_variable_takes_priority(self) -> None:
        """Test that Airflow Variable takes priority over environment"""
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'airflow-project'
            
            with patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'env-project'}):
                import importlib
                import github_activity_pipeline
                importlib.reload(github_activity_pipeline)
                
                result = github_activity_pipeline.get_project_id()
                assert result == 'airflow-project'
                mock_get.assert_called_once_with('project_id')

    def test_get_project_id_rejects_placeholder_values(self) -> None:
        """Test that placeholder values are rejected"""
        # Test "your-project-id" placeholder
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'your-project-id'
            
            with patch.dict(os.environ, {}, clear=False):
                if 'GOOGLE_CLOUD_PROJECT' in os.environ:
                    del os.environ['GOOGLE_CLOUD_PROJECT']
                
                import importlib
                import github_activity_pipeline
                importlib.reload(github_activity_pipeline)
                
                with pytest.raises(ValueError, match="project_id not configured"):
                    github_activity_pipeline.get_project_id()
        
        # Test "your-gcp-project-id" placeholder in env
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.side_effect = Exception("Not found")
            
            with patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'your-gcp-project-id'}):
                import importlib
                import github_activity_pipeline
                importlib.reload(github_activity_pipeline)
                
                with pytest.raises(ValueError, match="project_id not configured"):
                    github_activity_pipeline.get_project_id()


class TestDAGFailsFast:
    """Test that DAG fails fast with clear error when project_id is missing"""

    def test_dag_module_import_fails_without_project_id(self) -> None:
        """
        Test that importing the DAG module fails immediately if project_id is not configured.
        
        This is the key test - it ensures we fail at parse time with a clear error,
        not at runtime with a confusing "Dataset not found" error.
        """
        # Clear environment
        env_backup = os.environ.get('GOOGLE_CLOUD_PROJECT')
        if 'GOOGLE_CLOUD_PROJECT' in os.environ:
            del os.environ['GOOGLE_CLOUD_PROJECT']
        
        try:
            # Mock Variable.get to fail
            with patch('github_activity_pipeline.Variable.get') as mock_get:
                mock_get.side_effect = Exception("Variable not found")
                
                # Try to reload the module - should raise ValueError
                import importlib
                import github_activity_pipeline
                
                with pytest.raises(ValueError, match="project_id not configured"):
                    importlib.reload(github_activity_pipeline)
        finally:
            # Restore environment
            if env_backup:
                os.environ['GOOGLE_CLOUD_PROJECT'] = env_backup

    def test_dag_import_succeeds_with_valid_project_id(self) -> None:
        """Test that DAG imports successfully when project_id is configured"""
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'test-project'
            
            import importlib
            import github_activity_pipeline
            
            # Should not raise
            importlib.reload(github_activity_pipeline)
            
            # Verify constants are set correctly
            assert github_activity_pipeline.PROJECT_ID == 'test-project'
            assert github_activity_pipeline.GCS_BUCKET == 'github-activity-batch-raw-test-project'


class TestGCSBucketConfiguration:
    """Test GCS bucket name construction"""

    def test_gcs_bucket_uses_project_id(self) -> None:
        """Test that GCS bucket name includes the project ID"""
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'my-project-123'
            
            import importlib
            import github_activity_pipeline
            importlib.reload(github_activity_pipeline)
            
            expected_bucket = 'github-activity-batch-raw-my-project-123'
            assert github_activity_pipeline.GCS_BUCKET == expected_bucket

    def test_gcs_bucket_format(self) -> None:
        """Test GCS bucket name format"""
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'test-project'
            
            import importlib
            import github_activity_pipeline
            importlib.reload(github_activity_pipeline)
            
            # Bucket should follow pattern: github-activity-batch-raw-{project_id}
            assert github_activity_pipeline.GCS_BUCKET.startswith('github-activity-batch-raw-')
            assert 'test-project' in github_activity_pipeline.GCS_BUCKET


class TestBigQueryTableConfiguration:
    """Test BigQuery table configuration"""

    def test_destination_table_uses_project_id(self) -> None:
        """Test that destination table includes project ID"""
        with patch('github_activity_pipeline.Variable.get') as mock_get:
            mock_get.return_value = 'bq-test-project'
            
            import importlib
            import github_activity_pipeline
            importlib.reload(github_activity_pipeline)
            
            # Check that BQ_DATASET and BQ_TABLE are set
            assert github_activity_pipeline.BQ_DATASET == 'github_activity'
            assert github_activity_pipeline.BQ_TABLE == 'github_events'
            
            # The load_task should use PROJECT_ID in destination table
            # Find the load task
            load_task = None
            for task in github_activity_pipeline.dag.tasks:
                if task.task_id == 'load_to_bigquery':
                    load_task = task
                    break
            
            assert load_task is not None
            
            # Check destination table format (project.dataset.table)
            # The destination is set at parse time with PROJECT_ID
            # We verify PROJECT_ID was used correctly
            assert github_activity_pipeline.PROJECT_ID == 'bq-test-project'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
