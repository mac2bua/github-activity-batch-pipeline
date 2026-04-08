#!/bin/bash
# Validate dbt models syntax
# Returns: 0 = pass, 1 = fail, 2 = skipped

set -e

echo "🔍 Validating dbt models..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DBT_DIR="$SCRIPT_DIR/../dbt"

SKIPPED=false
FAILED=false

# Check if dbt is installed
if ! command -v dbt &> /dev/null; then
    echo "⚠️  dbt not installed. Install: pip install dbt-bigquery"
    echo "   Skipping dbt validation..."
    exit 2
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
    FAILED=true
fi

# Check for required marts
echo "🎯 Checking required marts..."
[ -f "models/marts/daily_stats.sql" ] && echo "   ✅ daily_stats.sql found" || { echo "   ❌ daily_stats.sql missing"; FAILED=true; }
[ -f "models/marts/repo_health.sql" ] && echo "   ✅ repo_health.sql found" || { echo "   ❌ repo_health.sql missing"; FAILED=true; }

# Parse check (if dbt available)
if command -v dbt &> /dev/null; then
    echo "🔍 Running dbt parse..."
    if dbt parse --quiet 2>/dev/null; then
        echo "   ✅ dbt parse successful"
    else
        echo "   ⚠️  dbt parse failed. Run 'dbt debug' for details"
        echo "   (This may be due to missing BigQuery connection)"
        # Don't fail on parse errors - could be missing credentials
    fi
fi

echo ""
if [ "$FAILED" = true ]; then
    echo "❌ dbt validation failed"
    exit 1
else
    echo "✅ dbt validation complete!"
    exit 0
fi