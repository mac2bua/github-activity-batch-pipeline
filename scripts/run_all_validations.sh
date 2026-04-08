#!/bin/bash
# Run all validations for the GitHub AI Contributions pipeline
# Compatible with bash 3.2+ (macOS)

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  GitHub AI Contributions - Validation Suite               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Track validation results
# Values: PASS, FAIL, SKIP
RESULT_TERRAFORM="FAIL"
RESULT_AIRFLOW="FAIL"
RESULT_DBT="FAIL"
RESULT_DOCKER="FAIL"
RESULT_README="FAIL"
PASS_COUNT=0
SKIP_COUNT=0
TOTAL=5

# Helper function to convert exit codes to status
exit_to_status() {
    local exit_code=$1
    if [ $exit_code -eq 0 ]; then
        echo "PASS"
    elif [ $exit_code -eq 2 ]; then
        echo "SKIP"
    else
        echo "FAIL"
    fi
}

# Validate Terraform
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  TERRAFORM VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_terraform.sh"; then
    RESULT_TERRAFORM="PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    RESULT_TERRAFORM="FAIL"
fi
echo ""

# Validate Airflow
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  AIRFLOW VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
AIRFLOW_EXIT=0
bash "$SCRIPT_DIR/validate_airflow.sh" || AIRFLOW_EXIT=$?
RESULT_AIRFLOW=$(exit_to_status $AIRFLOW_EXIT)
if [ "$RESULT_AIRFLOW" = "PASS" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
elif [ "$RESULT_AIRFLOW" = "SKIP" ]; then
    SKIP_COUNT=$((SKIP_COUNT + 1))
fi
echo ""

# Validate dbt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  DBT VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DBT_EXIT=0
bash "$SCRIPT_DIR/validate_dbt.sh" || DBT_EXIT=$?
RESULT_DBT=$(exit_to_status $DBT_EXIT)
if [ "$RESULT_DBT" = "PASS" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
elif [ "$RESULT_DBT" = "SKIP" ]; then
    SKIP_COUNT=$((SKIP_COUNT + 1))
fi
echo ""

# Check Docker Compose
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  DOCKER COMPOSE VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
    echo "✅ docker-compose.yml found"
    if command -v docker &> /dev/null; then
        if docker compose config --quiet 2>/dev/null; then
            echo "✅ Docker Compose syntax valid"
            RESULT_DOCKER="PASS"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "❌ Docker Compose syntax error"
            RESULT_DOCKER="FAIL"
        fi
    else
        echo "⚠️  Docker not installed - skipping config validation"
        RESULT_DOCKER="SKIP"
        SKIP_COUNT=$((SKIP_COUNT + 1))
    fi
else
    echo "❌ docker-compose.yml not found"
    RESULT_DOCKER="FAIL"
fi
echo ""

# Check README
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  DOCUMENTATION CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "$PROJECT_DIR/README.md" ]; then
    echo "✅ README.md found"
    word_count=$(wc -w < "$PROJECT_DIR/README.md" | tr -d ' ')
    echo "   Word count: $word_count"
    if [ "$word_count" -gt 500 ]; then
        echo "   ✅ README is comprehensive"
        RESULT_README="PASS"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "   ⚠️  README may be too short"
        RESULT_README="WARN"
    fi
else
    echo "❌ README.md not found"
    RESULT_README="FAIL"
fi
echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  VALIDATION SUMMARY                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
printf "%-20s %s\n" "Terraform:" "$RESULT_TERRAFORM"
printf "%-20s %s\n" "Airflow:" "$RESULT_AIRFLOW"
printf "%-20s %s\n" "dbt:" "$RESULT_DBT"
printf "%-20s %s\n" "Docker Compose:" "$RESULT_DOCKER"
printf "%-20s %s\n" "Documentation:" "$RESULT_README"
echo ""

# Calculate results
FAIL_COUNT=$((TOTAL - PASS_COUNT - SKIP_COUNT))

echo "Results: $PASS_COUNT passed, $SKIP_COUNT skipped, $FAIL_COUNT failed"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
    echo "❌ Some validations FAILED. Please fix the errors above."
    exit 1
elif [ $SKIP_COUNT -gt 0 ]; then
    echo "⚠️  All validations passed or were skipped."
    echo "   To run skipped validations, install:"
    echo "   - pip install apache-airflow apache-airflow-providers-google"
    echo "   - pip install dbt-bigquery"
    exit 0
else
    echo "🎉 All validations passed!"
    exit 0
fi