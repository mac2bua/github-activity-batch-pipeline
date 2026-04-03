#!/bin/bash
# End-to-End DAG Test Script
# Triggers the DAG, monitors execution, and reports results

set -e

DAG_ID="github_activity_batch_pipeline"
EXECUTION_DATE="${1:-2024-06-15T00:00:00+00:00}"
AIRFLOW_URL="http://localhost:8080"
MAX_WAIT_MINUTES=30
POLL_INTERVAL_SECONDS=30

echo "============================================================"
echo "BATCH PIPELINE E2E TEST"
echo "============================================================"
echo "DAG ID: $DAG_ID"
echo "Execution Date: $EXECUTION_DATE"
echo "Max Wait: ${MAX_WAIT_MINUTES}m"
echo "Poll Interval: ${POLL_INTERVAL}s"
echo "============================================================"

# Trigger DAG run
echo ""
echo "[1/4] Triggering DAG run..."
TRIGGER_RESPONSE=$(curl -s -X POST \
  "$AIRFLOW_URL/api/v1/dags/$DAG_ID/dagRuns" \
  -H "Content-Type: application/json" \
  -u "admin:admin" \
  -d "{
    \"dag_run_id\": \"test_run_$(date +%s)\",
    \"execution_date\": \"$EXECUTION_DATE\",
    \"conf\": {}
  }")

DAG_RUN_ID=$(echo "$TRIGGER_RESPONSE" | grep -o '"dag_run_id":"[^"]*"' | cut -d'"' -f4)
echo "DAG Run ID: $DAG_RUN_ID"

if [ -z "$DAG_RUN_ID" ]; then
    echo "ERROR: Failed to trigger DAG"
    echo "Response: $TRIGGER_RESPONSE"
    exit 1
fi

echo "✓ DAG triggered successfully"

# Monitor task execution
echo ""
echo "[2/4] Monitoring task execution..."
START_TIME=$(date +%s)
PREVIOUS_STATUS=""

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED_MINUTES=$(( (CURRENT_TIME - START_TIME) / 60 ))
    
    if [ $ELAPSED_MINUTES -ge $MAX_WAIT_MINUTES ]; then
        echo "✗ TIMEOUT: DAG did not complete within ${MAX_WAIT_MINUTES} minutes"
        exit 1
    fi
    
    # Get DAG run status
    DAG_STATUS=$(curl -s "$AIRFLOW_URL/api/v1/dags/$DAG_ID/dagRuns/$DAG_RUN_ID" \
      -u "admin:admin" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$DAG_STATUS" != "$PREVIOUS_STATUS" ]; then
        echo "  DAG Status: $DAG_STATUS (${ELAPSED_MINUTES}m elapsed)"
        PREVIOUS_STATUS="$DAG_STATUS"
    fi
    
    if [ "$DAG_STATUS" = "success" ]; then
        echo "✓ DAG completed successfully"
        break
    elif [ "$DAG_STATUS" = "failed" ]; then
        echo "✗ DAG failed"
        break
    fi
    
    sleep $POLL_INTERVAL_SECONDS
done

# Get task details
echo ""
echo "[3/4] Task Results:"
echo "-----------------------------------------------------------"

TASKS_RESPONSE=$(curl -s "$AIRFLOW_URL/api/v1/dags/$DAG_ID/dagRuns/$DAG_RUN_ID/taskInstances" \
  -u "admin:admin")

# Parse and display task results (simplified)
echo "$TASKS_RESPONSE" | grep -o '"task_id":"[^"]*","state":"[^"]*"' | while read -r line; do
    TASK_ID=$(echo "$line" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)
    STATE=$(echo "$line" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$STATE" = "success" ]; then
        echo "  ✓ $TASK_ID: $STATE"
    elif [ "$STATE" = "failed" ]; then
        echo "  ✗ $TASK_ID: $STATE"
    else
        echo "  ○ $TASK_ID: $STATE"
    fi
done

echo "-----------------------------------------------------------"

# Get logs for failed tasks
echo ""
echo "[4/4] Failed Task Logs (if any):"
echo "-----------------------------------------------------------"

FAILED_TASKS=$(echo "$TASKS_RESPONSE" | grep -o '"task_id":"[^"]*","state":"failed"' | cut -d'"' -f4)

if [ -z "$FAILED_TASKS" ]; then
    echo "No failed tasks - all tasks succeeded!"
else
    for TASK_ID in $FAILED_TASKS; do
        echo ""
        echo "=== $TASK_ID ==="
        curl -s "$AIRFLOW_URL/api/v1/dags/$DAG_ID/dagRuns/$DAG_RUN_ID/taskInstances/$TASK_ID/logs/1" \
          -u "admin:admin" | grep -o '"content":"[^"]*"' | cut -d'"' -f4 | head -50
    done
fi

echo ""
echo "============================================================"
echo "E2E TEST COMPLETE"
echo "============================================================"

# Exit with appropriate code
if [ "$DAG_STATUS" = "success" ]; then
    echo "Result: SUCCESS ✓"
    exit 0
else
    echo "Result: FAILED ✗"
    exit 1
fi
