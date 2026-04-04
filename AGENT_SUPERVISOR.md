# Agent Supervisor Instructions

**Mission:** Ensure the batch-debugger agent NEVER STOPS until the BATCH pipeline is PROVEN production-ready.

---

## Success Criteria (ALL must be met)

The agent must prove:

1. ✅ **2+ consecutive DAG runs succeed** with different dates
   - Run 1: 2024-06-15
   - Run 2: 2024-01-01 (or different date)
   - Both must complete with ALL 6 tasks green

2. ✅ **BigQuery data verified:**
   - Row count matches GCS files
   - Schema matches terraform/bigquery.tf exactly
   - event_id is STRING (not INTEGER)
   - All REQUIRED fields populated (no NULLs)
   - Partitioning by event_date working
   - Clustering by repo_name, actor_login, event_type working

3. ✅ **All tests passing:**
   - Unit tests: 9/9+ passing
   - DAG integrity: 5/5 passing
   - Integration tests: passing

4. ✅ **No known issues:**
   - No error logs in last 2 DAG runs
   - No warnings about schema, auth, or timeouts
   - No manual intervention required

5. ✅ **Documentation complete:**
   - BUGFIX_SUMMARY.md updated with all fixes
   - DEPLOYMENT.md has current instructions
   - READY_FOR_DEPLOYMENT.md reflects current state

**ONLY when ALL 5 criteria are met:** Update status to "COMPLETE" and notify user.

---

## Supervisor Loop (Every 30 Minutes)

```
Every 30 minutes:
1. Read ~/clawd/memory/agent-debugger-status.md
2. Check agent status:
   - If RUNNING: Continue monitoring
   - If COMPLETED: Verify all 5 success criteria
   - If FAILED/STOPPED: Diagnose why, respawn agent
3. Check Airflow status:
   - curl http://localhost:8080/api/v1/dags/github_activity_batch_pipeline/dagRuns
   - Verify recent runs
4. Check git status:
   - cd ~/Repositories/github-activity-batch-pipeline
   - git status (should be clean or agent is working)
   - git log --oneline -5 (track progress)
5. Update HEARTBEAT.md with current status
6. If agent stopped unexpectedly: Respawn with same instructions
7. Continue loop
```

---

## Agent Status File Format

Agent writes to: `~/clawd/memory/agent-debugger-status.md`

```markdown
# Debugger Agent Status

**Iteration:** N

**Current Status:** [RUNNING | COMPLETED | FAILED]

**DAG Run ID:** [run_id]

**Task Results:**
- task1: [success | failed | running | pending]
- task2: ...

**Errors Found:** [list of errors in this iteration]

**Fixes Applied:** [list of fixes in this iteration]

**Next Action:** [what agent is doing next]

**Progress:** X/6 tasks passing
```

---

## Respawning Agent

If agent stops unexpectedly:

```bash
openclaw agent --agent batch-debugger \
  --message "Continue debugging BATCH pipeline. Read AGENT_INSTRUCTIONS.md. \
             Current status: [read from status file]. \
             Last error: [read from status file]. \
             Continue the loop: copy DAG → restart → trigger → monitor → fix → repeat." \
  --thinking high
```

---

## Escalation

**Only notify user when:**
- ✅ ALL 5 success criteria met (pipeline proven ready)
- ❌ Agent keeps failing after 10+ iterations (need human decision)
- ❌ Critical infrastructure issue (Airflow down, GCP credentials expired)

**Do NOT notify for:**
- Individual task failures (agent handles these)
- Normal debug iterations
- Progress updates (user can check status file)

---

## Cron Schedule

Set up cron job to run every 30 minutes:
- Check agent status
- Verify progress
- Respawn if needed
- Update HEARTBEAT.md

---

## Current State (Initial)

**Agent:** batch-debugger  
**Status:** RUNNING (Iteration 1)  
**DAG Run:** manual__2024-06-15T00:00:00+00:00  
**Current Task:** download_github_archive (running)

**Next Check:** 30 minutes from spawn
