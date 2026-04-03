#!/usr/bin/env python3
"""
DAG Integrity Tests

Validates the Airflow DAG structure, task dependencies, and configuration.
Run these tests before deploying to catch structural issues.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Create comprehensive airflow mock structure BEFORE any imports
class MockDAG:
    def __init__(self, dag_id, **kwargs):
        self.dag_id = dag_id
        self.task_dict = {}
        self.tasks = []
        self.schedule_interval = kwargs.get('schedule_interval', '@daily')
        self.catchup = kwargs.get('catchup', False)
    
    def get_task(self, task_id):
        return self.task_dict.get(task_id)

class MockTask:
    def __init__(self, task_id, **kwargs):
        self.task_id = task_id
        self.downstream_list = []
        self.upstream_list = []
        self.dag = kwargs.get('dag', None)
        if self.dag:
            self.dag.task_dict[task_id] = self
            self.dag.tasks.append(self)
    
    def __rshift__(self, other):
        """Support >> operator for task dependencies."""
        self.downstream_list.append(other)
        other.upstream_list.append(self)
        return other

# Build mock module structure
mock_airflow = MagicMock()
mock_airflow.DAG = MockDAG

mock_models = MagicMock()
mock_airflow.models = mock_models

mock_operators = MagicMock()
mock_airflow.operators = mock_operators

mock_python_op = MagicMock()
mock_python_op.PythonOperator = MockTask
mock_airflow.operators.python = mock_python_op

mock_bash_op = MagicMock()
mock_bash_op.BashOperator = MockTask
mock_airflow.operators.bash = mock_bash_op

mock_providers = MagicMock()
mock_airflow.providers = mock_providers

mock_google = MagicMock()
mock_providers.google = mock_google

mock_cloud = MagicMock()
mock_google.cloud = mock_cloud

mock_hooks = MagicMock()
mock_cloud.hooks = mock_hooks
mock_cloud.hooks.gcs = MagicMock()
mock_cloud.hooks.gcs.GCSHook = MagicMock

mock_transfers = MagicMock()
mock_cloud.transfers = mock_transfers
mock_transfers.gcs_to_bigquery = MagicMock()
mock_transfers.gcs_to_bigquery.GCSToBigQueryOperator = MockTask

# Inject mocks
sys.modules['airflow'] = mock_airflow
sys.modules['airflow.models'] = mock_models
sys.modules['airflow.operators'] = mock_operators
sys.modules['airflow.operators.python'] = mock_python_op
sys.modules['airflow.operators.bash'] = mock_bash_op
sys.modules['airflow.providers'] = mock_providers
sys.modules['airflow.providers.google'] = mock_google
sys.modules['airflow.providers.google.cloud'] = mock_cloud
sys.modules['airflow.providers.google.cloud.hooks'] = mock_hooks
sys.modules['airflow.providers.google.cloud.hooks.gcs'] = mock_cloud.hooks.gcs
sys.modules['airflow.providers.google.cloud.transfers'] = mock_transfers
sys.modules['airflow.providers.google.cloud.transfers.gcs_to_bigquery'] = mock_transfers.gcs_to_bigquery

# Now import the DAG
sys.path.insert(0, str(Path(__file__).parent.parent / 'airflow' / 'dags'))
from github_activity_pipeline import dag

print("=" * 60)
print("DAG INTEGRITY TESTS")
print("=" * 60)

# Test 1: DAG exists
print("\n✓ Test 1: DAG object exists")
assert dag is not None, "DAG object not found"
print(f"  DAG ID: {dag.dag_id}")

# Test 2: All tasks exist
print("\n✓ Test 2: All required tasks exist")
expected_tasks = [
    'download_github_archive',
    'upload_to_gcs',
    'validate_data_quality',
    'transform_data',
    'load_to_bigquery',
    'cleanup_temp_files'
]
for task_id in expected_tasks:
    assert task_id in dag.task_dict, f"Task {task_id} not found"
    print(f"  - {task_id}: OK")

# Test 3: Task dependencies (chain)
print("\n✓ Test 3: Task dependencies form correct chain")
task_order = [
    'download_github_archive',
    'upload_to_gcs',
    'validate_data_quality',
    'transform_data',
    'load_to_bigquery',
    'cleanup_temp_files'
]

for i in range(len(task_order) - 1):
    current_task = dag.get_task(task_order[i])
    next_task = dag.get_task(task_order[i + 1])
    
    # Check that next_task is in current_task's downstream list
    assert next_task in current_task.downstream_list, \
        f"{task_order[i]} should be upstream of {task_order[i + 1]}"
    print(f"  {task_order[i]} >> {task_order[i + 1]}: OK")

# Test 4: Task count
print("\n✓ Test 4: Task count")
assert len(dag.tasks) == 6, f"Expected 6 tasks, got {len(dag.tasks)}"
print(f"  Total tasks: {len(dag.tasks)}")

# Test 5: DAG schedule
print("\n✓ Test 5: DAG schedule configuration")
assert dag.schedule_interval == '@daily', "Schedule should be @daily"
assert dag.catchup is True, "Catchup should be enabled"
print(f"  Schedule: {dag.schedule_interval}")
print(f"  Catchup: {dag.catchup}")

print("\n" + "=" * 60)
print("ALL DAG INTEGRITY TESTS PASSED ✓")
print("=" * 60)
