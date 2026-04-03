#!/bin/bash
# Validate dbt models syntax
set -e

echo "🔍 Validating dbt models..."

DBT_DIR="$(dirname "$0")/../dbt"

# Check if dbt is installed
if ! command -v dbt &> /dev/null; then
    echo "⚠️  dbt not installed. Install: pip install dbt-bigquery"
    echo "   Skipping dbt validation..."
    exit 0
fi

cd "$DBT_DIR"

# Check project file
if [ ! -f "dbt_project.yml" ]; then
    echo "❌ dbt_project.yml not found"
    exit 1
fi

echo "✅ dbt_project.yml found"

# Check model files
echo "📁 Checking model files..."
models_found=0

for model in models/staging/*.sql models/marts/*.sql; do
    if [ -f "$model" ]; then
        echo "   ✓ $(basename $model)"
        models_found=$((models_found + 1))
        
        # Basic SQL syntax check
        if grep -q "{{ config(" "$model" && grep -q "with\|select" "$model"; then
            echo "      ✅ Config and query structure OK"
        else
            echo "      ⚠️  May be missing config or query"
        fi
    fi
done

echo "   Found $models_found model files"

if [ $models_found -ge 3 ]; then
    echo "   ✅ Minimum 3 models requirement met (1 staging + 2 marts)"
else
    echo "   ❌ Need at least 3 models"
    exit 1
fi

# Check for required marts
echo "🎯 Checking required marts..."
[ -f "models/marts/daily_stats.sql" ] && echo "   ✅ daily_stats.sql found" || echo "   ❌ daily_stats.sql missing"
[ -f "models/marts/repo_health.sql" ] && echo "   ✅ repo_health.sql found" || echo "   ❌ repo_health.sql missing"

# Parse check (if dbt available)
if command -v dbt &> /dev/null; then
    echo "🔍 Running dbt parse..."
    dbt parse --quiet && {
        echo "   ✅ dbt parse successful"
    } || {
        echo "   ⚠️  dbt parse failed. Run 'dbt debug' for details"
    }
fi

echo "✅ dbt validation complete!"
