#!/bin/bash
# Validate Airflow DAG syntax and configuration
# Usage: ./scripts/validate_airflow.sh
set -e

echo "🔍 Validating Airflow DAGs..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DAG_DIR="$PROJECT_ROOT/airflow/dags"

# Track validation status
VALIDATION_PASSED=true

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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$VALIDATION_PASSED" = true ]; then
    echo "✅ All Airflow DAG validations passed!"
    exit 0
else
    echo "❌ Some validations failed. Please review the errors above."
    exit 1
fi
