#!/bin/bash
# Validate Airflow DAG syntax and configuration
set -e

echo "🔍 Validating Airflow DAG..."

DAG_FILE="$(dirname "$0")/../airflow/dags/github_activity_pipeline.py"

# Check if file exists
if [ ! -f "$DAG_FILE" ]; then
    echo "❌ DAG file not found: $DAG_FILE"
    exit 1
fi

# Check Python syntax
echo "✅ Checking Python syntax..."
python3 -m py_compile "$DAG_FILE" && echo "   Python syntax OK"

# Check imports
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

required = ['airflow', 'datetime', 'requests', 'json']
missing = [r for r in required if not any(r in i for i in imports)]

if missing:
    print(f'❌ Missing imports: {missing}')
    sys.exit(1)
else:
    print('   All required imports present')
"

# Check DAG structure
echo "🔍 Checking DAG structure..."
python3 -c "
import ast

with open('$DAG_FILE', 'r') as f:
    tree = ast.parse(f.read())

# Count task definitions
task_count = 0
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                if 'task' in target.id.lower() or 'download' in target.id.lower() or 'upload' in target.id.lower() or 'load' in target.id.lower():
                    task_count += 1

print(f'   Found {task_count} task definitions')
if task_count >= 3:
    print('   ✅ Minimum 3 tasks requirement met')
else:
    print('   ❌ Need at least 3 tasks')
    exit(1)
"

# Check for Airflow operators
echo "🔧 Checking Airflow operators..."
grep -q "PythonOperator\|BashOperator\|GCSToBigQueryOperator" "$DAG_FILE" && {
    echo "   ✅ Airflow operators found"
} || {
    echo "   ❌ No Airflow operators found"
    exit 1
}

# Check for DAG definition
echo "📋 Checking DAG definition..."
grep -q "DAG(" "$DAG_FILE" && {
    echo "   ✅ DAG definition found"
} || {
    echo "   ❌ No DAG definition found"
    exit 1
}

# Check for task dependencies
echo "🔗 Checking task dependencies..."
grep -q ">>" "$DAG_FILE" && {
    echo "   ✅ Task dependencies defined"
} || {
    echo "   ⚠️  No task dependencies found (>> operator)"
}

echo "✅ Airflow DAG validation complete!"
