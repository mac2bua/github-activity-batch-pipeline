#!/bin/bash
# Run all validations for the GitHub Activity Batch Pipeline
set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  GitHub Activity Batch Pipeline - Validation Suite      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(dirname "$0")"

# Track validation results
declare -A results

# Validate Terraform
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  TERRAFORM VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_terraform.sh"; then
    results[terraform]="✅ PASS"
else
    results[terraform]="❌ FAIL"
fi
echo ""

# Validate Airflow
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  AIRFLOW VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_airflow.sh"; then
    results[airflow]="✅ PASS"
else
    results[airflow]="❌ FAIL"
fi
echo ""

# Validate dbt
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  DBT VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPT_DIR/validate_dbt.sh"; then
    results[dbt]="✅ PASS"
else
    results[dbt]="❌ FAIL"
fi
echo ""

# Check Docker Compose
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  DOCKER COMPOSE VALIDATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "$(dirname "$0")/../docker-compose.yml" ]; then
    echo "✅ docker-compose.yml found"
    if command -v docker &> /dev/null; then
        docker compose config --quiet && {
            echo "✅ Docker Compose syntax valid"
            results[docker]="✅ PASS"
        } || {
            echo "❌ Docker Compose syntax error"
            results[docker]="❌ FAIL"
        }
    else
        echo "ℹ️  Docker not installed, skipping config validation"
        results[docker]="⚠️  SKIP"
    fi
else
    echo "❌ docker-compose.yml not found"
    results[docker]="❌ FAIL"
fi
echo ""

# Check README
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  DOCUMENTATION CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "$(dirname "$0")/../README.md" ]; then
    echo "✅ README.md found"
    word_count=$(wc -w < "$(dirname "$0")/../README.md")
    echo "   Word count: $word_count"
    if [ $word_count -gt 500 ]; then
        echo "   ✅ README is comprehensive"
        results[readme]="✅ PASS"
    else
        echo "   ⚠️  README may be too short"
        results[readme]="⚠️  WARN"
    fi
else
    echo "❌ README.md not found"
    results[readme]="❌ FAIL"
fi
echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  VALIDATION SUMMARY                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
printf "%-20s %s\n" "Terraform:" "${results[terraform]}"
printf "%-20s %s\n" "Airflow:" "${results[airflow]}"
printf "%-20s %s\n" "dbt:" "${results[dbt]}"
printf "%-20s %s\n" "Docker Compose:" "${results[docker]}"
printf "%-20s %s\n" "Documentation:" "${results[readme]}"
echo ""

# Count passes
pass_count=0
for result in "${results[@]}"; do
    if [[ "$result" == *"PASS"* ]]; then
        pass_count=$((pass_count + 1))
    fi
done

total=${#results[@]}
echo "Passed: $pass_count/$total"

if [ $pass_count -eq $total ]; then
    echo "🎉 All validations passed!"
    exit 0
else
    echo "⚠️  Some validations failed or have warnings"
    exit 1
fi
