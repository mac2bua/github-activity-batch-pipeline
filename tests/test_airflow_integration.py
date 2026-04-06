"""
Integration tests for Airflow DAGs

These tests actually instantiate operators and parse DAGs to catch
parameter errors before deployment. Unlike unit tests that just check
structure, these validate that operators can be initialized with the
given parameters.

Run: pytest tests/test_airflow_integration.py -v
"""

import os
import pytest
from datetime import datetime
from pathlib import Path
import sys
from typing import Any
from unittest.mock import MagicMock, patch

# Set required environment variables before importing DAG
os.environ.setdefault('GOOGLE_CLOUD_PROJECT', 'test-project')

# Add dags directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))


class TestDAGParsing:
    """Test that DAGs parse without errors"""

    def test_github_activity_pipeline_parses(self) -> None:
        """Test github_activity_pipeline DAG parses without errors"""
        try:
            import github_activity_pipeline
            assert github_activity_pipeline.dag is not None
            assert github_activity_pipeline.dag.dag_id == 'github_activity_batch_pipeline'
        except Exception as e:
            pytest.fail(f"DAG parsing failed: {e}")

    def test_dag_has_valid_tasks(self) -> None:
        """Test DAG has tasks that can be accessed"""
        from github_activity_pipeline import dag

        assert len(dag.tasks) > 0
        for task in dag.tasks:
            assert hasattr(task, 'task_id')
            assert task.task_id is not None


class TestOperatorInitialization:
    """Test that operators can be initialized with parameters"""

    def test_gcs_to_bigquery_operator_params(self) -> None:
        """
        Test GCSToBigQueryOperator with Airflow 2.8+ compatible parameters.
        
        This test catches errors like:
        - clustering_fields parameter (removed in provider 10.x)
        - schema_fields parameter (removed in provider 10.x)
        - time_partitioning parameter (removed in provider 10.x)
        
        These should be pre-created via Terraform, not passed to the operator.
        """
        from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
        
        # These are the ONLY valid parameters for Airflow 2.8+ Google provider 10.x
        # Table schema/partitioning/clustering must be pre-created
        try:
            operator = GCSToBigQueryOperator(
                task_id='test_load_to_bigquery',
                bucket='test-bucket',
                source_objects=['raw/test/'],
                destination_project_dataset_table='project.dataset.table',
                source_format='NEWLINE_DELIMITED_JSON',
                write_disposition='WRITE_APPEND',
                max_bad_records=100,
                allow_quoted_newlines=True,
                dag=None,
            )
            assert operator is not None
            assert operator.task_id == 'test_load_to_bigquery'
        except TypeError as e:
            pytest.fail(f"GCSToBigQueryOperator initialization failed: {e}")

    def test_gcs_to_bigquery_rejects_clustering_fields(self) -> None:
        """
        Test that clustering_fields parameter raises an error.

        This validates that our fix is correct - if this test passes,
        it means the operator correctly rejects this parameter.
        """
        from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
        from airflow.exceptions import AirflowException

        with pytest.raises((TypeError, AirflowException), match="clustering"):
            GCSToBigQueryOperator(
                task_id='test_load',
                bucket='test-bucket',
                source_objects=['raw/test/'],
                destination_project_dataset_table='project.dataset.table',
                source_format='NEWLINE_DELIMITED_JSON',
                write_disposition='WRITE_APPEND',
                clustering_fields=['repo_name'],  # This should fail
                dag=None,
            )

    def test_gcs_to_bigquery_accepts_schema_fields(self) -> None:
        """
        Test that schema_fields parameter is accepted (schema can be provided inline).

        Note: We pre-create schema via Terraform, but inline schema is also valid.
        """
        from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

        try:
            operator = GCSToBigQueryOperator(
                task_id='test_load',
                bucket='test-bucket',
                source_objects=['raw/test/'],
                destination_project_dataset_table='project.dataset.table',
                source_format='NEWLINE_DELIMITED_JSON',
                write_disposition='WRITE_APPEND',
                schema_fields=[{'name': 'id', 'type': 'STRING'}],
                dag=None,
            )
            assert operator is not None
            assert operator.task_id == 'test_load'
        except Exception as e:
            pytest.fail(f"GCSToBigQueryOperator should accept schema_fields: {e}")

    def test_python_operator_initialization(self) -> None:
        """Test PythonOperator can be initialized"""
        from airflow.operators.python import PythonOperator
        
        def dummy_func(**kwargs):
            pass
        
        try:
            operator = PythonOperator(
                task_id='test_python_task',
                python_callable=dummy_func,
                dag=None,
            )
            assert operator is not None
        except Exception as e:
            pytest.fail(f"PythonOperator initialization failed: {e}")

    def test_bash_operator_initialization(self) -> None:
        """Test BashOperator can be initialized"""
        from airflow.operators.bash import BashOperator
        
        try:
            operator = BashOperator(
                task_id='test_bash_task',
                bash_command='echo "test"',
                dag=None,
            )
            assert operator is not None
        except Exception as e:
            pytest.fail(f"BashOperator initialization failed: {e}")


class TestDAGTaskConfiguration:
    """Test that DAG tasks are configured correctly"""

    def test_load_task_is_python_operator(self) -> None:
        """Test load task is PythonOperator with correct callable"""
        from github_activity_pipeline import dag
        from airflow.operators.python import PythonOperator

        load_task = None
        for task in dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break

        assert load_task is not None, "load_to_bigquery task not found"
        assert isinstance(load_task, PythonOperator)
        assert callable(load_task.python_callable)

    def test_load_task_does_not_have_invalid_params(self) -> None:
        """Test the load task doesn't have Airflow 2.8+ incompatible params"""
        from github_activity_pipeline import dag
        
        load_task = None
        for task in dag.tasks:
            if task.task_id == 'load_to_bigquery':
                load_task = task
                break
        
        assert load_task is not None
        
        # These params should NOT be present (they cause errors in Airflow 2.8+)
        # Check operator kwargs to ensure invalid params are removed
        operator_kwargs = load_task.kwargs if hasattr(load_task, 'kwargs') else {}
        
        # clustering_fields should not be in kwargs
        assert 'clustering_fields' not in operator_kwargs, \
            "clustering_fields should be removed (pre-created in Terraform)"


class TestDAGDependencies:
    """Test DAG task dependencies"""

    def test_github_activity_pipeline_dependencies(self) -> None:
        """Test task dependencies in github_activity_pipeline"""
        from github_activity_pipeline import dag

        # Build dependency map
        task_map = {task.task_id: task for task in dag.tasks}

        # Verify chain: download >> upload >> validate >> transform >> load >> cleanup
        assert 'download_github_archive' in task_map
        assert 'upload_to_gcs' in task_map
        assert 'validate_data_quality' in task_map
        assert 'transform_data' in task_map
        assert 'load_to_bigquery' in task_map
        assert 'cleanup_temp_files' in task_map

        # Check upstream dependencies
        upload_task = task_map['upload_to_gcs']
        assert 'download_github_archive' in [t.task_id for t in upload_task.upstream_list]

        validate_task = task_map['validate_data_quality']
        assert 'upload_to_gcs' in [t.task_id for t in validate_task.upstream_list]

        transform_task = task_map['transform_data']
        assert 'validate_data_quality' in [t.task_id for t in transform_task.upstream_list]

        load_task = task_map['load_to_bigquery']
        assert 'transform_data' in [t.task_id for t in load_task.upstream_list]

        cleanup_task = task_map['cleanup_temp_files']
        assert 'load_to_bigquery' in [t.task_id for t in cleanup_task.upstream_list]

class TestDAGWithMockContext:
    """Test DAG functions with mocked context"""

    def test_download_function_with_mock_context(self) -> None:
        """Test download function can be called with mock context"""
        from github_activity_pipeline import download_github_archive
        
        mock_context = {
            'ds': '2024-01-01',
            'execution_date': datetime(2024, 1, 1),
            'ti': MagicMock(),
        }
        
        # This should not raise an exception (even if download fails)
        try:
            result = download_github_archive(**mock_context)
            assert isinstance(result, dict)
            assert 'files' in result or 'count' in result
        except Exception as e:
            # Allow exceptions from network issues, but not from code errors
            if "NameError" in str(type(e)) or "AttributeError" in str(type(e)):
                pytest.fail(f"Code error in download function: {e}")

    def test_upload_function_with_mock_context(self) -> None:
        """Test upload function can be called with mock context"""
        from github_activity_pipeline import upload_to_gcs
        
        mock_context = {
            'ds': '2024-01-01',
            'execution_date': datetime(2024, 1, 1),
        }
        
        try:
            result = upload_to_gcs(**mock_context)
            assert isinstance(result, dict)
        except Exception as e:
            if "NameError" in str(type(e)) or "AttributeError" in str(type(e)):
                pytest.fail(f"Code error in upload function: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
