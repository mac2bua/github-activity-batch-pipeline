#!/bin/bash
# Validate Airflow DAG syntax and configuration
# Usage: ./scripts/validate_airflow.sh
# Returns: 0 = pass, 1 = fail, 2 = skipped

set -e

echo "🔍 Validating Airflow DAGs..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DAG_DIR="$PROJECT_ROOT/airflow/dags"

# Track validation status
VALIDATION_PASSED=true
SKIPPED=false

# Check if DAG directory exists
if [ ! -d "$DAG_DIR" ]; then
    echo "❌ DAG directory not found: $DAG_DIR"
    exit 1
fi

# Find all Python DAG files
DAG_FILES=$(find "$DAG_DIR" -name "*.py" -not -name "__init__.py" -not -name ".*" 2>/dev/null)

if [ -z "$DAG_FILES" ]; then
    echo "❌ No DAG files found in $DAG_DIR"
    exit 1
fi

echo "📁 Found DAG files:"
for dag in $DAG_FILES; do
    echo "   - $(basename "$dag")"
done
echo ""

# Validate each DAG file
for DAG_FILE in $DAG_FILES; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Validating: $(basename "$DAG_FILE")"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check Python syntax
    echo "✅ Checking Python syntax..."
    if python3 -m py_compile "$DAG_FILE" 2>/dev/null; then
        echo "   ✓ Python syntax OK"
    else
        echo "   ✗ Python syntax errors found"
        VALIDATION_PASSED=false
        continue
    fi

    # Check for required imports
    echo "📦 Checking required imports..."
    python3 -c "
import ast
import sys

with open('$DAG_FILE', 'r') as f:
    tree = ast.parse(f.read())

imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.extend([alias.name for alias in node.names])
    elif isinstance(node, ast.ImportFrom):
        imports.append(node.module)

required = ['airflow', 'datetime', 'requests']
missing = [r for r in required if not any(r in str(i) for i in imports)]

if missing:
    print(f'   ✗ Missing imports: {missing}')
    sys.exit(1)
else:
    print('   ✓ All required imports present')
" || VALIDATION_PASSED=false

    # Check DAG structure
    echo "🔍 Checking DAG structure..."
    python3 -c "
import ast

with open('$DAG_FILE', 'r') as f:
    tree = ast.parse(f.read())

# Count task definitions
task_count = 0
dag_found = False
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        if hasattr(node.func, 'id') and node.func.id == 'DAG':
            dag_found = True
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id.lower()
                if 'task' in name or 'download' in name or 'upload' in name or 'load' in name:
                    task_count += 1

print(f'   Found {task_count} task definitions')
if dag_found:
    print('   ✓ DAG definition found')
else:
    print('   ✗ No DAG definition found')
    exit(1)

if task_count >= 3:
    print('   ✓ Minimum 3 tasks requirement met')
else:
    print('   ✗ Need at least 3 tasks')
    exit(1)
" || VALIDATION_PASSED=false

    # Check for Airflow operators
    echo "🔧 Checking Airflow operators..."
    if grep -qE "PythonOperator|BashOperator|GCSToBigQueryOperator|BigQueryInsertJobOperator" "$DAG_FILE" 2>/dev/null; then
        echo "   ✓ Airflow operators found"
    else
        echo "   ✗ No Airflow operators found"
        VALIDATION_PASSED=false
    fi

    # Check for task dependencies
    echo "🔗 Checking task dependencies..."
    if grep -q ">>" "$DAG_FILE" 2>/dev/null; then
        echo "   ✓ Task dependencies defined"
    else
        echo "   ⚠ No task dependencies found (>> operator)"
    fi

    # Check for docstrings
    echo "📝 Checking documentation..."
    if grep -q '"""' "$DAG_FILE" 2>/dev/null; then
        echo "   ✓ Module docstring present"
    else
        echo "   ⚠ No module docstring found"
    fi

    echo ""
done

# =============================================================================
# DAG PARSING TEST - Catches parameter errors before deployment
# =============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Running DAG parsing tests (catches parameter errors)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Try to import DAGs and instantiate operators
# Note: This test requires Airflow to be installed. Skip if not available.
export DAG_DIR="$DAG_DIR"
python3 << 'PYTHON_SCRIPT'
import sys
import importlib.util
import os

DAG_DIR = os.environ.get('DAG_DIR', 'airflow/dags')

print('   Checking if Airflow is installed...')

# Check if airflow.providers is available (not just namespace package)
airflow_providers_spec = importlib.util.find_spec('airflow.providers')
if airflow_providers_spec is None:
    print('   ⚠ Airflow providers not installed - skipping DAG parsing test')
    print('   Install with: pip install apache-airflow apache-airflow-providers-google')
    print('   (This is required for full validation)')
    sys.exit(2)  # Exit code 2 = skipped

sys.path.insert(0, DAG_DIR)

print('   Testing DAG imports and operator initialization...')

try:
    # Import DAGs
    import github_activity_pipeline
    import github_archive_dag
    print('   ✓ Both DAGs imported successfully')

    # Verify DAGs exist
    assert github_activity_pipeline.dag is not None
    assert github_archive_dag.dag is not None
    print('   ✓ DAG objects created')

    # Verify tasks can be accessed
    for dag in [github_activity_pipeline.dag, github_archive_dag.dag]:
        for task in dag.tasks:
            assert task.task_id is not None
    print('   ✓ All tasks accessible')

    # Test GCSToBigQueryOperator with valid params only
    from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

    # This should work (Airflow 2.8+ compatible params)
    test_op = GCSToBigQueryOperator(
        task_id='test_valid_params',
        bucket='test-bucket',
        source_objects=['raw/test/'],
        destination_project_dataset_table='project.dataset.table',
        source_format='NEWLINE_DELIMITED_JSON',
        write_disposition='WRITE_APPEND',
        dag=None,
    )
    print('   ✓ GCSToBigQueryOperator accepts valid params')

    # Verify load_task in github_activity_pipeline doesn't have invalid params
    load_task = None
    for task in github_activity_pipeline.dag.tasks:
        if task.task_id == 'load_to_bigquery':
            load_task = task
            break

    if load_task:
        kwargs = load_task.kwargs if hasattr(load_task, 'kwargs') else {}
        if 'clustering_fields' in kwargs:
            print('   ✗ ERROR: clustering_fields still present (incompatible with Airflow 2.8+)')
            sys.exit(1)
        if 'schema_fields' in kwargs:
            print('   ✗ ERROR: schema_fields still present (incompatible with Airflow 2.8+)')
            sys.exit(1)
        if 'time_partitioning' in kwargs:
            print('   ✗ ERROR: time_partitioning still present (incompatible with Airflow 2.8+)')
            sys.exit(1)
        print('   ✓ GCSToBigQueryOperator has no invalid params')

    print('')
    print('   All DAG parsing tests passed!')
    sys.exit(0)

except TypeError as e:
    if 'clustering_fields' in str(e) or 'schema' in str(e):
        print(f'   ✗ ERROR: Invalid operator parameters: {e}')
        print('   Fix: Remove schema_fields, clustering_fields, time_partitioning from GCSToBigQueryOperator')
        print('   These should be pre-created via Terraform.')
        sys.exit(1)
    else:
        print(f'   ✗ ERROR: {e}')
        sys.exit(1)
except Exception as e:
    print(f'   ✗ ERROR: DAG parsing failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

PARSING_EXIT_CODE=$?

if [ $PARSING_EXIT_CODE -eq 2 ]; then
    SKIPPED=true
    echo ""
    echo "⚠️  DAG parsing test SKIPPED (Airflow not installed)"
elif [ $PARSING_EXIT_CODE -eq 1 ]; then
    VALIDATION_PASSED=false
fi

echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$VALIDATION_PASSED" = true ]; then
    if [ "$SKIPPED" = true ]; then
        echo "⚠️  Airflow validation passed (parsing test skipped)"
        exit 2  # Exit code 2 = partial/skipped
    else
        echo "✅ All Airflow DAG validations passed!"
        exit 0
    fi
else
    echo "❌ Some validations failed. Please review the errors above."
    exit 1
fi