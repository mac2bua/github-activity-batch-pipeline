#!/bin/bash
# Run all validations for the GitHub Activity Batch Pipeline
# Compatible with bash 3.2+ (macOS)

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  GitHub Activity Batch Pipeline - Validation Suite      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Track validation results (using simple variables for bash 3.2 compatibility)
RESULT_TERRAFORM=""
RESULT_AIRFLOW=""
RESULT_DBT=""
RESULT_DOCKER=""
RESULT_README=""
PASS_COUNT=0
TOTAL=5

# Validate Terraform
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  TERRAFORM VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_terraform.sh"; then
    RESULT_TERRAFORM="✅ PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    RESULT_TERRAFORM="❌ FAIL"
fi
echo ""

# Validate Airflow
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  AIRFLOW VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_airflow.sh"; then
    RESULT_AIRFLOW="✅ PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    RESULT_AIRFLOW="❌ FAIL"
fi
echo ""

# Validate dbt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  DBT VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_dbt.sh"; then
    RESULT_DBT="✅ PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    RESULT_DBT="❌ FAIL"
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
            RESULT_DOCKER="✅ PASS"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "❌ Docker Compose syntax error"
            RESULT_DOCKER="❌ FAIL"
        fi
    else
        echo "ℹ️  Docker not installed, skipping config validation"
        RESULT_DOCKER="⚠️  SKIP"
    fi
else
    echo "❌ docker-compose.yml not found"
    RESULT_DOCKER="❌ FAIL"
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
        RESULT_README="✅ PASS"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "   ⚠️  README may be too short"
        RESULT_README="⚠️  WARN"
    fi
else
    echo "❌ README.md not found"
    RESULT_README="❌ FAIL"
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
echo "Passed: $PASS_COUNT/$TOTAL"

if [ $PASS_COUNT -eq $TOTAL ]; then
    echo "🎉 All validations passed!"
    exit 0
else
    echo "⚠️  Some validations failed or have warnings"
    exit 1
fi
